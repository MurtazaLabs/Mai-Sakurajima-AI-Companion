# continuity/checkpoints.py
"""Checkpoints — resumable progress for tasks that outlive one turn.

A research job or coding session writes a checkpoint after each meaningful
step. If it is interrupted, ``resume()`` hands back the last step and state so
the work continues instead of restarting (or vanishing).
"""
from __future__ import annotations

import logging
import threading
import time

from continuity.models import Checkpoint

logger = logging.getLogger(__name__)


class CheckpointStore:

    def __init__(self, store, event_bus=None, on_change=None):
        self._store = store
        self.event_bus = event_bus
        self._on_change = on_change
        self._lock = threading.RLock()

    def _changed(self) -> None:
        if self._on_change is not None:
            try:
                self._on_change()
            except Exception as exc:
                logger.warning("[Checkpoints] change hook failed: %s", exc)

    def _publish(self, event_type: str, payload: dict) -> None:
        if not self.event_bus:
            return
        try:
            from core.mai_message import publish_event
            publish_event(self.event_bus, event_type, payload, source="continuity")
        except Exception as exc:
            logger.warning("[Checkpoints] event publish failed (%s): %s", event_type, exc)

    def save(self, task_id, step=0, state=None, note="") -> Checkpoint | None:
        task_id = str(task_id or "").strip()
        if not task_id:
            return None
        with self._lock:
            raw = self._store.read()["checkpoints"].get(task_id)
            previous = Checkpoint.from_dict(raw) if raw else None
            checkpoint = Checkpoint(
                task_id=task_id,
                step=step,
                state=state if state is not None else (previous.state if previous else {}),
                note=note or (previous.note if previous else ""),
                created_at=previous.created_at if previous else None,
                resume_count=previous.resume_count if previous else 0,
            )
            with self._store.transaction() as document:
                document["checkpoints"][task_id] = checkpoint.to_dict()
        self._publish("data.continuity.checkpoint_saved", {
            "task_id": checkpoint.task_id,
            "step": checkpoint.step,
        })
        self._changed()
        return checkpoint

    def get(self, task_id) -> Checkpoint | None:
        with self._lock:
            raw = self._store.read()["checkpoints"].get(str(task_id or "").strip())
        return Checkpoint.from_dict(raw) if raw else None

    def list(self) -> list[Checkpoint]:
        with self._lock:
            items = [
                Checkpoint.from_dict(raw)
                for raw in self._store.read()["checkpoints"].values()
            ]
        items.sort(key=lambda c: -c.updated_at)
        return items

    def resume(self, task_id) -> dict | None:
        """Return the checkpoint to continue, recording that it was resumed."""
        with self._lock:
            raw = self._store.read()["checkpoints"].get(str(task_id or "").strip())
            if raw is None:
                return None
            checkpoint = Checkpoint.from_dict(raw)
            checkpoint.resume_count += 1
            checkpoint.updated_at = time.time()
            with self._store.transaction() as document:
                document["checkpoints"][checkpoint.task_id] = checkpoint.to_dict()
        self._changed()
        return {
            "task_id": checkpoint.task_id,
            "step": checkpoint.step,
            "state": dict(checkpoint.state),
            "note": checkpoint.note,
            "resume_count": checkpoint.resume_count,
        }

    def clear(self, task_id) -> bool:
        task_id = str(task_id or "").strip()
        removed = False
        with self._lock:
            if task_id in self._store.read()["checkpoints"]:
                with self._store.transaction() as document:
                    removed = document["checkpoints"].pop(task_id, None) is not None
        if removed:
            self._changed()
        return removed

    def stats(self) -> dict:
        items = self.list()
        return {
            "total": len(items),
            "resumed": sum(c.resume_count for c in items),
            "latest": items[0].to_dict() if items else None,
        }
