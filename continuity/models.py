# continuity/models.py
"""Records owned by the Continuity Engine.

These are *continuity-owned* facts only — decisions, open questions, blockers,
due windows and resumable checkpoints. Progress, priority and completion of an
ongoing project stay owned by :class:`agency.goals.GoalManager`: a project
references a goal id and reads through it, never duplicating its numbers.
"""
from __future__ import annotations

import re
import time
import uuid
from datetime import datetime

PROJECT_STATUSES = ("active", "paused", "blocked", "completed", "abandoned")
_TERMINAL_PROJECT_STATUSES = ("completed", "abandoned")
COMMITMENT_STATUSES = ("open", "kept", "missed", "cancelled")

_REL_DUE_RE = re.compile(
    r"^\s*(?:in\s+)?(\d+(?:\.\d+)?)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)\s*$",
    re.IGNORECASE,
)
_ISO_DUE_FORMATS = ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d")


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _text(value) -> str:
    return str(value or "").strip()


def parse_due(value, now: float | None = None) -> float | None:
    """Normalize a due window to epoch seconds.

    Accepts an epoch number, an ISO date/datetime string, or a relative window
    such as ``"in 3h"``, ``"90m"`` or ``"2d"``. Empty input means "no due
    window". An unparseable non-empty value raises ``ValueError`` — silently
    dropping a promised deadline would be a dishonest ledger.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    now = time.time() if now is None else float(now)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)

    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        pass

    match = _REL_DUE_RE.match(text)
    if match:
        amount = float(match.group(1))
        unit = match.group(2).lower()
        if unit.startswith("m"):
            multiplier = 60
        elif unit.startswith("h"):
            multiplier = 3600
        else:
            multiplier = 86400
        return now + amount * multiplier

    for fmt in _ISO_DUE_FORMATS:
        try:
            return datetime.strptime(text, fmt).timestamp()
        except ValueError:
            continue

    raise ValueError(f"unparseable due window: {value!r}")


class Project:
    """An ongoing project: goal, status, decisions, blockers, next checkpoint."""

    def __init__(
        self,
        name: str = "",
        summary: str = "",
        status: str = "active",
        goal_id: str | None = None,
        deadline: float | None = None,
        dependencies=None,
        next_checkpoint: str = "",
        notes: str = "",
        project_id: str | None = None,
        created_at: float | None = None,
        updated_at: float | None = None,
        completed_at: float = 0.0,
        decisions=None,
        open_questions=None,
        blockers=None,
    ):
        now = time.time()
        self.id = project_id or _new_id("prj")
        self.name = _text(name)
        self.summary = _text(summary)
        self.status = status if status in PROJECT_STATUSES else "active"
        self.goal_id = goal_id or None
        self.deadline = float(deadline) if deadline else None
        self.dependencies = [str(d) for d in (dependencies or []) if _text(d)]
        self.next_checkpoint = _text(next_checkpoint)
        self.notes = _text(notes)
        self.decisions = list(decisions or [])
        self.open_questions = list(open_questions or [])
        self.blockers = list(blockers or [])
        self.created_at = float(created_at or now)
        self.updated_at = float(updated_at or now)
        self.completed_at = float(completed_at or 0.0)

    # -- mutations ---------------------------------------------------

    def touch(self) -> None:
        self.updated_at = time.time()

    def add_decision(self, text: str) -> dict | None:
        text = _text(text)
        if not text:
            return None
        entry = {"id": _new_id("dec"), "text": text, "at": time.time()}
        self.decisions.append(entry)
        self.touch()
        return entry

    def add_open_question(self, text: str) -> dict | None:
        text = _text(text)
        if not text:
            return None
        entry = {"id": _new_id("q"), "text": text, "at": time.time(), "resolved_at": 0.0}
        self.open_questions.append(entry)
        self.touch()
        return entry

    def resolve_open_question(self, question_id: str) -> bool:
        for entry in self.open_questions:
            if entry.get("id") == question_id and not entry.get("resolved_at"):
                entry["resolved_at"] = time.time()
                self.touch()
                return True
        return False

    def add_blocker(self, text: str) -> dict | None:
        text = _text(text)
        if not text:
            return None
        entry = {"id": _new_id("blk"), "text": text, "at": time.time(), "cleared_at": 0.0}
        self.blockers.append(entry)
        self.touch()
        return entry

    def clear_blocker(self, blocker_id: str) -> bool:
        for entry in self.blockers:
            if entry.get("id") == blocker_id and not entry.get("cleared_at"):
                entry["cleared_at"] = time.time()
                self.touch()
                return True
        return False

    def set_next_checkpoint(self, text: str) -> None:
        self.next_checkpoint = _text(text)
        self.touch()

    def open_questions_live(self) -> list[dict]:
        return [q for q in self.open_questions if not q.get("resolved_at")]

    def blockers_live(self) -> list[dict]:
        return [b for b in self.blockers if not b.get("cleared_at")]

    @property
    def is_terminal(self) -> bool:
        return self.status in _TERMINAL_PROJECT_STATUSES

    # -- serialization -----------------------------------------------

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "status": self.status,
            "goal_id": self.goal_id,
            "deadline": self.deadline,
            "dependencies": list(self.dependencies),
            "next_checkpoint": self.next_checkpoint,
            "notes": self.notes,
            "decisions": list(self.decisions),
            "open_questions": list(self.open_questions),
            "blockers": list(self.blockers),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data) -> "Project":
        data = data if isinstance(data, dict) else {}
        return cls(
            name=data.get("name", ""),
            summary=data.get("summary", ""),
            status=data.get("status", "active"),
            goal_id=data.get("goal_id"),
            deadline=data.get("deadline"),
            dependencies=data.get("dependencies") or [],
            next_checkpoint=data.get("next_checkpoint", ""),
            notes=data.get("notes", ""),
            project_id=data.get("id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            completed_at=data.get("completed_at") or 0.0,
            decisions=data.get("decisions") or [],
            open_questions=data.get("open_questions") or [],
            blockers=data.get("blockers") or [],
        )


class Commitment:
    """A promise with a due window ('I'll research X tonight')."""

    def __init__(
        self,
        promise: str = "",
        due_at: float | None = None,
        status: str = "open",
        project_id: str | None = None,
        note: str = "",
        commitment_id: str | None = None,
        created_at: float | None = None,
        updated_at: float | None = None,
        resolved_at: float = 0.0,
        surfaced_at: float = 0.0,
    ):
        now = time.time()
        self.id = commitment_id or _new_id("cmt")
        self.promise = _text(promise)
        self.due_at = float(due_at) if due_at else None
        self.status = status if status in COMMITMENT_STATUSES else "open"
        self.project_id = project_id or None
        self.note = _text(note)
        self.created_at = float(created_at or now)
        self.updated_at = float(updated_at or now)
        self.resolved_at = float(resolved_at or 0.0)
        self.surfaced_at = float(surfaced_at or 0.0)

    def is_overdue(self, now: float | None = None) -> bool:
        if self.status != "open" or self.due_at is None:
            return False
        now = time.time() if now is None else float(now)
        return self.due_at <= now

    @property
    def surfaced(self) -> bool:
        return self.surfaced_at > 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "promise": self.promise,
            "due_at": self.due_at,
            "status": self.status,
            "project_id": self.project_id,
            "note": self.note,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
            "surfaced_at": self.surfaced_at,
        }

    @classmethod
    def from_dict(cls, data) -> "Commitment":
        data = data if isinstance(data, dict) else {}
        return cls(
            promise=data.get("promise", ""),
            due_at=data.get("due_at"),
            status=data.get("status", "open"),
            project_id=data.get("project_id"),
            note=data.get("note", ""),
            commitment_id=data.get("id"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            resolved_at=data.get("resolved_at") or 0.0,
            surfaced_at=data.get("surfaced_at") or 0.0,
        )


class Checkpoint:
    """Resumable progress marker for a long-running task."""

    def __init__(
        self,
        task_id: str = "",
        step: int = 0,
        state=None,
        note: str = "",
        created_at: float | None = None,
        updated_at: float | None = None,
        resume_count: int = 0,
    ):
        now = time.time()
        self.task_id = _text(task_id)
        self.step = max(0, int(step or 0))
        self.state = dict(state or {})
        self.note = _text(note)
        self.created_at = float(created_at or now)
        self.updated_at = float(updated_at or now)
        self.resume_count = max(0, int(resume_count or 0))

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "step": self.step,
            "state": dict(self.state),
            "note": self.note,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resume_count": self.resume_count,
        }

    @classmethod
    def from_dict(cls, data) -> "Checkpoint":
        data = data if isinstance(data, dict) else {}
        return cls(
            task_id=data.get("task_id", ""),
            step=data.get("step", 0),
            state=data.get("state") or {},
            note=data.get("note", ""),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            resume_count=data.get("resume_count", 0),
        )
