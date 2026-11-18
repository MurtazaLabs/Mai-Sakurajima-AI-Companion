# continuity/engine.py
"""Continuity Engine — one coherent account of "what's going on".

A *thin reconciler*, following the ``BrainGraph`` facade pattern: it owns no
fact that another subsystem already owns. Projects read progress from
``GoalManager``; focus reads from ``CognitiveState``; runtime truth reads from
``SharedState``. What continuity adds is the structure goals never had —
decisions, open questions, blockers, due windows, resumable checkpoints — plus
one reconciled snapshot every front-end (desktop, Discord, background cycles)
reads instead of inventing its own half-truth.
"""
from __future__ import annotations

import logging
import threading
import time

from continuity.checkpoints import CheckpointStore
from continuity.commitments import CommitmentsLedger
from continuity.projects import ProjectMemory
from continuity.store import ContinuityStore

logger = logging.getLogger(__name__)


def _ago(timestamp, now=None) -> str:
    if not timestamp:
        return "no due window"
    now = time.time() if now is None else now
    delta = now - float(timestamp)
    if delta < 0:
        remaining = -delta
        if remaining < 3600:
            return f"in {int(remaining // 60)}m"
        if remaining < 86400:
            return f"in {remaining / 3600:.1f}h"
        return f"in {remaining / 86400:.1f}d"
    if delta < 60:
        return "just now"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{delta / 3600:.1f}h ago"
    return f"{delta / 86400:.1f}d ago"


class ContinuityEngine:

    def __init__(self, store_path=None, event_bus=None, goal_manager=None,
                 cognitive_state=None, shared_state=None):
        if store_path is None:
            from config.paths import ROOT_DIR
            store_path = ROOT_DIR / "data" / "continuity.json"
        self.store = ContinuityStore(store_path)
        self.event_bus = event_bus
        self.goal_manager = goal_manager
        self.cognitive_state = cognitive_state
        self.shared_state = shared_state
        self._lock = threading.RLock()
        self._last_snapshot_at = 0.0

        self.projects = ProjectMemory(
            store=self.store,
            goal_manager=goal_manager,
            event_bus=event_bus,
            on_change=self.publish,
        )
        self.commitments = CommitmentsLedger(
            store=self.store,
            event_bus=event_bus,
            on_change=self.publish,
        )
        self.checkpoints = CheckpointStore(
            store=self.store,
            event_bus=event_bus,
            on_change=self.publish,
        )

    # -- reconciliation ----------------------------------------------

    def snapshot(self) -> dict:
        """The reconciled state object. Every field is read from its owner."""
        now = time.time()
        projects = [self.projects.describe(p) for p in self.projects.list(include_terminal=False)]
        due = self.commitments.due(now)
        missed = self.commitments.unsurfaced()
        open_commitments = self.commitments.list(status="open")
        checkpoints = self.checkpoints.stats()

        snapshot = {
            "generated_at": now,
            "projects": projects,
            "project_stats": self.projects.stats(),
            "goals": self._active_goals(),
            "commitments": {
                "open": len(open_commitments),
                "due": [self._commitment_view(c, now) for c in due],
                "missed_unsurfaced": [self._commitment_view(c, now) for c in missed],
                "stats": self.commitments.stats(),
            },
            "checkpoints": checkpoints,
            "focus": self._focus(),
            "runtime": self._runtime(),
        }
        with self._lock:
            self._last_snapshot_at = now
        return snapshot

    def _active_goals(self) -> list[dict]:
        if self.goal_manager is None or not hasattr(self.goal_manager, "list"):
            return []
        try:
            return [
                {k: goal.to_dict()[k] for k in (
                    "id", "description", "priority", "status", "progress", "turn_count",
                )}
                for goal in self.goal_manager.list(status="active")
            ]
        except Exception as exc:
            logger.debug("[Continuity] goal read failed: %s", exc)
            return []

    def _focus(self) -> dict:
        if self.cognitive_state is None or not hasattr(self.cognitive_state, "get"):
            return {}
        try:
            state = self.cognitive_state.get() or {}
        except Exception as exc:
            logger.debug("[Continuity] cognitive read failed: %s", exc)
            return {}
        return {
            "topic": state.get("current_topic", ""),
            "goal": state.get("current_goal") or "",
            "task": state.get("active_task", ""),
            "intent": state.get("conversation_intent", ""),
            "confidence": state.get("confidence", 0.5),
        }

    def _runtime(self) -> dict:
        shared = self.shared_state
        if shared is None:
            return {}
        runtime: dict = {}
        try:
            with shared.lock:
                runtime = {
                    "is_thinking": bool(getattr(shared.runtime, "is_thinking", False)),
                    "session_turns": int(getattr(shared.runtime, "current_session_turns", 0)),
                    "speaker": getattr(shared.runtime, "current_speaker_name", ""),
                    "conversation_active": bool(
                        getattr(shared.runtime, "conversation_active", False)
                    ),
                }
        except Exception as exc:
            logger.debug("[Continuity] shared_state read failed: %s", exc)
            return {}
        return runtime

    @staticmethod
    def _commitment_view(commitment, now) -> dict:
        data = commitment.to_dict()
        data["window"] = _ago(commitment.due_at, now)
        return data

    # -- prompt / ritual context -------------------------------------

    def brief(self, max_chars: int = 900, mark_surfaced: bool = False) -> str:
        """Compact text block for the system prompt. Empty when nothing is ongoing."""
        now = time.time()
        lines: list[str] = []

        projects = self.projects.list(include_terminal=False)[:3]
        if projects:
            lines.append("Ongoing projects:")
            for project in projects:
                percent = round(self.projects.progress(project) * 100)
                entry = f"  - {project.name} [{project.status}, {percent}%]"
                if project.next_checkpoint:
                    entry += f" — next: {project.next_checkpoint}"
                live_blockers = project.blockers_live()
                if live_blockers:
                    entry += f" — blocked: {live_blockers[0].get('text', '')[:80]}"
                lines.append(entry)

        due = self.commitments.due(now)[:3]
        if due:
            lines.append("Due now:")
            for commitment in due:
                lines.append(f"  - \"{commitment.promise[:100]}\" ({_ago(commitment.due_at, now)})")

        missed = self.commitments.unsurfaced()
        if missed:
            lines.append("Promises missed and not yet reported:")
            for commitment in missed[:3]:
                lines.append(
                    f"  - \"{commitment.promise[:100]}\" (due {_ago(commitment.due_at, now)})"
                )
            if mark_surfaced:
                try:
                    self.commitments.mark_surfaced([c.id for c in missed])
                except Exception as exc:
                    logger.warning("[Continuity] mark_surfaced failed: %s", exc)

        focus = self._focus()
        focus_bits = []
        if focus.get("goal"):
            focus_bits.append(f"goal: {focus['goal']}")
        if focus.get("task"):
            focus_bits.append(f"task: {focus['task']}")
        if focus_bits:
            lines.append("Current focus: " + " · ".join(focus_bits))

        text = "\n".join(lines).strip()
        return text[:max_chars]

    # -- scheduler / event feed --------------------------------------

    def check_commitments(self, now=None) -> dict:
        """Scheduler hook: mark overdue promises missed, then publish state."""
        summary = self.commitments.sweep(now)
        self.publish()
        return summary

    def publish(self) -> None:
        """Push the reconciled snapshot onto the state bus (UI truth)."""
        if not self.event_bus:
            return
        try:
            snapshot = self.snapshot()
            payload = {
                "projects": len(snapshot["projects"]),
                "open_commitments": snapshot["commitments"]["open"],
                "due": len(snapshot["commitments"]["due"]),
                "missed": len(snapshot["commitments"]["missed_unsurfaced"]),
                "checkpoints": snapshot["checkpoints"]["total"],
            }
            from core.mai_message import publish_event
            publish_event(self.event_bus, "state.continuity.updated", payload, source="continuity")
        except Exception as exc:
            logger.warning("[Continuity] state publish failed: %s", exc)

    # -- introspection -----------------------------------------------

    def stats(self) -> dict:
        return {
            "projects": self.projects.stats(),
            "commitments": self.commitments.stats(),
            "checkpoints": self.checkpoints.stats(),
            "last_snapshot_at": self._last_snapshot_at,
            "store_path": str(self.store.path),
        }

    def health(self) -> dict:
        return {"ok": True, "stats": self.stats()}
