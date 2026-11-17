# continuity/projects.py
"""Project memory — structured record of what is ongoing and where it stands.

Progress, priority and completion are **not** stored here: a project holds a
``goal_id`` and reads those values through ``GoalManager`` (the existing
source of truth). Continuity owns the parts goals never had — decisions taken,
open questions, blockers, dependencies, deadlines and the next checkpoint.
"""
from __future__ import annotations

import logging
import threading
import time

from continuity.models import PROJECT_STATUSES, Project, parse_due

logger = logging.getLogger(__name__)

# Goal-owned terminal lifecycle states, mirrored onto the project record. A
# terminal goal always wins: the project cannot claim to be running when the
# goal that owns its progress is done or abandoned.
_GOAL_TERMINAL_TO_PROJECT = {"completed": "completed", "cancelled": "abandoned"}


class ProjectMemory:

    def __init__(self, store, goal_manager=None, event_bus=None, on_change=None):
        self._store = store
        self.goal_manager = goal_manager
        self.event_bus = event_bus
        self._on_change = on_change
        self._lock = threading.RLock()

    # -- internals ---------------------------------------------------

    def _changed(self) -> None:
        if self._on_change is not None:
            try:
                self._on_change()
            except Exception as exc:
                logger.warning("[Projects] change hook failed: %s", exc)

    def _publish(self, event_type: str, payload: dict) -> None:
        if not self.event_bus:
            return
        try:
            from core.mai_message import publish_event
            publish_event(self.event_bus, event_type, payload, source="continuity")
        except Exception as exc:
            logger.warning("[Projects] event publish failed (%s): %s", event_type, exc)

    def _load(self, project_id: str) -> Project | None:
        raw = self._store.read()["projects"].get(project_id)
        return Project.from_dict(raw) if raw else None

    def _save(self, project: Project) -> None:
        with self._store.transaction() as document:
            document["projects"][project.id] = project.to_dict()

    # -- lifecycle ---------------------------------------------------

    def create(self, name, summary="", goal_id=None, deadline=None,
               dependencies=None, next_checkpoint="", notes="") -> Project | None:
        name = str(name or "").strip()
        if not name:
            return None
        try:
            deadline_at = parse_due(deadline)
        except ValueError as exc:
            raise ValueError(str(exc)) from None

        with self._lock:
            existing = self.find(name)
            if existing is not None:
                return existing
            project = Project(
                name=name,
                summary=summary,
                deadline=deadline_at,
                dependencies=dependencies,
                next_checkpoint=next_checkpoint,
                notes=notes,
                goal_id=goal_id or None,
            )
            if not project.goal_id and self.goal_manager is not None:
                try:
                    goal = self.goal_manager.create(
                        description=name,
                        priority="normal",
                        context={"source": "continuity", "project_id": project.id},
                    )
                    if goal is not None:
                        project.goal_id = goal.id
                except Exception as exc:
                    logger.warning("[Projects] goal creation failed: %s", exc)
            self._save(project)

        self._publish("data.continuity.project_created", {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "goal_id": project.goal_id,
        })
        self._changed()
        return project

    def update(self, project_id, **fields) -> Project | None:
        allowed = {
            "name", "summary", "status", "goal_id", "deadline",
            "dependencies", "next_checkpoint", "notes",
        }
        with self._lock:
            project = self._load(project_id)
            if project is None:
                return None
            changed = []
            for key, value in fields.items():
                if key not in allowed or value is None:
                    continue
                if key == "status":
                    if value not in PROJECT_STATUSES:
                        raise ValueError(f"unknown project status: {value!r}")
                    # An explicit status write owns the current status: the
                    # goal mirror must not resume it later.
                    project.status_source = "user"
                elif key == "deadline":
                    value = parse_due(value)
                elif key == "dependencies":
                    value = [str(d) for d in value if str(d).strip()]
                setattr(project, key, value)
                changed.append(key)
            if not changed:
                return project
            project.touch()
            self._save(project)

        if "status" in changed:
            self._sync_goal_status(project)
        self._publish("data.continuity.project_updated", {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "changed": changed,
        })
        self._changed()
        return project

    def _sync_goal_status(self, project: Project) -> None:
        """Mirror a terminal project status onto its goal (one owner per fact)."""
        if not project.goal_id or self.goal_manager is None:
            return
        try:
            if project.status == "completed":
                self.goal_manager.complete(project.goal_id)
            elif project.status == "abandoned":
                self.goal_manager.cancel(project.goal_id)
        except Exception as exc:
            logger.warning("[Projects] goal status sync failed: %s", exc)

    def complete(self, project_id) -> bool:
        project = self.update(project_id, status="completed")
        if project is None:
            return False
        with self._lock:
            project.completed_at = time.time()
            self._save(project)
        self._changed()
        return True

    # -- structure ---------------------------------------------------

    def record_decision(self, project_id, text) -> dict | None:
        return self._structure(project_id, "decision", text)

    def raise_question(self, project_id, text) -> dict | None:
        return self._structure(project_id, "question", text)

    def add_blocker(self, project_id, text) -> dict | None:
        return self._structure(project_id, "blocker", text)

    def _structure(self, project_id, kind, text) -> dict | None:
        with self._lock:
            project = self._load(project_id)
            if project is None:
                return None
            if kind == "decision":
                entry = project.add_decision(text)
            elif kind == "question":
                entry = project.add_open_question(text)
            else:
                entry = project.add_blocker(text)
            if entry is None:
                return None
            self._save(project)
        self._publish("data.continuity.project_updated", {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "changed": [kind],
        })
        self._changed()
        return entry

    def resolve_question(self, project_id, question_id) -> bool:
        return self._resolve(project_id, "question", question_id)

    def clear_blocker(self, project_id, blocker_id) -> bool:
        return self._resolve(project_id, "blocker", blocker_id)

    def _resolve(self, project_id, kind, entry_id) -> bool:
        with self._lock:
            project = self._load(project_id)
            if project is None:
                return False
            ok = (
                project.resolve_open_question(entry_id)
                if kind == "question"
                else project.clear_blocker(entry_id)
            )
            if not ok:
                return False
            self._save(project)
        self._publish("data.continuity.project_updated", {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "changed": [f"{kind}_resolved"],
        })
        self._changed()
        return True

    def add_step(self, project_id, description) -> dict | None:
        """Add a subtask to the linked goal — progress then lives in GoalManager."""
        with self._lock:
            project = self._load(project_id)
            if project is None or not project.goal_id or self.goal_manager is None:
                return None
            subtask = self.goal_manager.add_subtask(project.goal_id, description)
        if subtask is not None:
            self._changed()
        return subtask

    def complete_step(self, project_id, description) -> bool:
        with self._lock:
            project = self._load(project_id)
            if project is None or not project.goal_id or self.goal_manager is None:
                return False
            goal = self.goal_manager.get(project.goal_id)
            if goal is None:
                return False
            needle = str(description or "").strip().lower()
            if not needle:
                return False
            match = None
            for subtask in goal.subtasks:
                if subtask.get("completed"):
                    continue
                if needle in str(subtask.get("description", "")).lower():
                    match = subtask
                    break
            if match is None:
                return False
            ok = self.goal_manager.complete_subtask(project.goal_id, match["id"])
        if ok:
            self._changed()
        return ok

    # -- reconciliation ----------------------------------------------

    def reconcile(self, project_ids=None) -> dict:
        """Pull goal-owned lifecycle status onto linked projects.

        ``GoalManager`` pauses the lowest-priority excess goal when the active
        cap is reached (and completes/cancels goals on its own paths). That
        happens deep inside the goal store, so no event reaches continuity.
        This is a deliberate **pull**: reconciling on read keeps the project
        record honest without a second writer, a subscription, or a second
        source of truth.

        ``blocked`` is a continuity-owned sub-state of active work, so a
        scheduler pause never erases it; a *terminal* goal status always wins.
        """
        if self.goal_manager is None:
            return {"changed": 0, "details": []}
        changes = []
        with self._lock:
            raw_map = self._store.read()["projects"]
            ids = list(raw_map) if project_ids is None else [
                i for i in project_ids if i in raw_map
            ]
            for project_id in ids:
                project = Project.from_dict(raw_map[project_id])
                change = self._mirror_from_goal(project)
                if change is None:
                    continue
                self._save(project)
                changes.append(change)
        for change in changes:
            logger.info(
                "[Projects] Status mirrored from goal: %s %s -> %s",
                change["name"][:40], change["from"], change["to"],
            )
        return {"changed": len(changes), "details": changes}

    def _mirror_from_goal(self, project: Project) -> dict | None:
        """Apply a goal-owned status to ``project`` in place; return the change.

        Symmetric for pauses: a goal pause relaxes an actively running project,
        and a resume lifts a pause **this mirror wrote earlier**. A pause the
        agent or user set deliberately stays put — ``status_source`` records
        which of the two it was.
        """
        if not project.goal_id or project.is_terminal:
            return None
        try:
            goal = self.goal_manager.get(project.goal_id)
        except Exception as exc:
            logger.debug("[Projects] goal status read failed: %s", exc)
            return None
        if goal is None:
            return None
        goal_status = getattr(goal, "status", "")
        if goal_status == "paused":
            # Preemption is transient — only relax an actively running project.
            target = "paused" if project.status == "active" else None
        elif goal_status == "active":
            # Resume only the pause the mirror itself applied.
            mirrored_pause = project.status == "paused" and project.status_source == "goal"
            target = "active" if mirrored_pause else None
        else:
            target = _GOAL_TERMINAL_TO_PROJECT.get(goal_status)
        if target is None or target == project.status:
            return None
        previous = project.status
        project.status = target
        project.status_source = "goal"
        project.touch()
        if target == "completed":
            project.completed_at = time.time()
        return {
            "id": project.id,
            "name": project.name,
            "from": previous,
            "to": target,
            "goal_status": goal_status,
        }

    # -- reads -------------------------------------------------------

    def get(self, project_id) -> Project | None:
        with self._lock:
            project = self._load(project_id)
            if project is None:
                return None
            if self._mirror_from_goal(project) is not None:
                self._save(project)
            return project

    def find(self, name) -> Project | None:
        needle = str(name or "").strip().lower()
        if not needle:
            return None
        with self._lock:
            for raw in self._store.read()["projects"].values():
                project = Project.from_dict(raw)
                if project.name.lower() == needle and not project.is_terminal:
                    return project
        return None

    def list(self, status=None, include_terminal=True) -> list[Project]:
        self.reconcile()
        with self._lock:
            projects = [Project.from_dict(raw) for raw in self._store.read()["projects"].values()]
        if status:
            projects = [p for p in projects if p.status == status]
        elif not include_terminal:
            projects = [p for p in projects if not p.is_terminal]
        priority = {"active": 0, "blocked": 1, "paused": 2, "completed": 3, "abandoned": 4}
        projects.sort(key=lambda p: (priority.get(p.status, 5), -p.updated_at))
        return projects

    def progress(self, project) -> float:
        """Read through to the linked goal — never a second copy of progress."""
        goal_id = getattr(project, "goal_id", None)
        if goal_id and self.goal_manager is not None:
            try:
                goal = self.goal_manager.get(goal_id)
                if goal is not None:
                    return round(float(goal.progress()), 3)
            except Exception as exc:
                logger.debug("[Projects] goal progress read failed: %s", exc)
        return 1.0 if project.status == "completed" else 0.0

    def describe(self, project, include_details=False) -> dict:
        data = project.to_dict()
        data["progress"] = self.progress(project)
        data["open_questions_live"] = len(project.open_questions_live())
        data["blockers_live"] = len(project.blockers_live())
        goal_id = project.goal_id
        goal_info = None
        if goal_id and self.goal_manager is not None:
            try:
                goal = self.goal_manager.get(goal_id)
                if goal is not None:
                    goal_info = {
                        "id": goal.id,
                        "status": goal.status,
                        "priority": goal.priority,
                        "progress": round(float(goal.progress()), 3),
                    }
            except Exception as exc:
                logger.debug("[Projects] goal describe failed: %s", exc)
        data["goal"] = goal_info
        if not include_details:
            for key in ("decisions", "open_questions", "blockers", "notes"):
                data.pop(key, None)
        return data

    def stats(self) -> dict:
        projects = self.list()
        return {
            "total": len(projects),
            "active": sum(1 for p in projects if p.status == "active"),
            "blocked": sum(1 for p in projects if p.status == "blocked"),
            "completed": sum(1 for p in projects if p.status == "completed"),
            "open_questions": sum(len(p.open_questions_live()) for p in projects),
            "blockers": sum(len(p.blockers_live()) for p in projects),
        }
