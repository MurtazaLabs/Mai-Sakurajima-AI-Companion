# continuity/commitments.py
"""Commitments ledger — promises with a due window, never silently dropped.

A commitment is created when Mai says she will do something ("I'll research
forex tonight"). ``sweep()`` runs on the scheduler: anything still open past
its due window becomes ``missed`` and is published. Missed commitments carry a
``surfaced_at`` marker so the next ritual turn reports them **once** instead of
repeating them every turn — or, worse, forgetting them.
"""
from __future__ import annotations

import builtins
import logging
import threading
import time

from continuity.models import COMMITMENT_STATUSES, Commitment, parse_due

logger = logging.getLogger(__name__)


class CommitmentsLedger:

    def __init__(self, store, event_bus=None, on_change=None):
        self._store = store
        self.event_bus = event_bus
        self._on_change = on_change
        self._lock = threading.RLock()

    # -- internals ---------------------------------------------------

    def _changed(self) -> None:
        if self._on_change is not None:
            try:
                self._on_change()
            except Exception as exc:
                logger.warning("[Commitments] change hook failed: %s", exc)

    def _publish(self, event_type: str, payload: dict) -> None:
        if not self.event_bus:
            return
        try:
            from core.mai_message import publish_event
            publish_event(self.event_bus, event_type, payload, source="continuity")
        except Exception as exc:
            logger.warning("[Commitments] event publish failed (%s): %s", event_type, exc)

    def _save(self, commitment: Commitment) -> None:
        with self._store.transaction() as document:
            document["commitments"][commitment.id] = commitment.to_dict()

    # -- writes ------------------------------------------------------

    def add(self, promise, due_at=None, due_in_hours=None, project_id=None,
            note="") -> Commitment | None:
        promise = str(promise or "").strip()
        if not promise:
            return None
        if due_at is None and due_in_hours is not None:
            try:
                due_at = time.time() + float(due_in_hours) * 3600.0
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid due_in_hours: {due_in_hours!r}") from exc
        try:
            due_at = parse_due(due_at)
        except ValueError as exc:
            raise ValueError(str(exc)) from None

        commitment = Commitment(
            promise=promise,
            due_at=due_at,
            project_id=project_id,
            note=note,
        )
        self._save(commitment)
        self._publish("data.continuity.commitment_added", {
            "id": commitment.id,
            "promise": commitment.promise,
            "due_at": commitment.due_at,
        })
        self._changed()
        return commitment

    def resolve(self, commitment_id, outcome) -> Commitment | None:
        outcome = str(outcome or "").strip().lower()
        if outcome not in ("kept", "missed", "cancelled"):
            raise ValueError(f"unknown commitment outcome: {outcome!r}")
        with self._lock:
            raw = self._store.read()["commitments"].get(commitment_id)
            if raw is None:
                return None
            commitment = Commitment.from_dict(raw)
            if commitment.status in ("kept", "cancelled"):
                return commitment
            commitment.status = outcome
            commitment.resolved_at = time.time()
            commitment.updated_at = time.time()
            if outcome == "missed":
                commitment.surfaced_at = commitment.resolved_at
            self._save(commitment)
        self._publish("data.continuity.commitment_resolved", {
            "id": commitment.id,
            "promise": commitment.promise,
            "status": commitment.status,
        })
        self._changed()
        return commitment

    def keep(self, commitment_id) -> Commitment | None:
        return self.resolve(commitment_id, "kept")

    def cancel(self, commitment_id) -> Commitment | None:
        return self.resolve(commitment_id, "cancelled")

    def sweep(self, now=None) -> dict:
        """Mark overdue open commitments as missed and publish each one."""
        now = time.time() if now is None else float(now)
        missed = []
        with self._lock:
            for raw in self._store.read()["commitments"].values():
                commitment = Commitment.from_dict(raw)
                if not commitment.is_overdue(now):
                    continue
                commitment.status = "missed"
                commitment.resolved_at = now
                commitment.updated_at = now
                with self._store.transaction() as document:
                    document["commitments"][commitment.id] = commitment.to_dict()
                missed.append(commitment)

        for commitment in missed:
            logger.info("[Commitments] Missed: %s", commitment.promise[:60])
            self._publish("data.continuity.commitment_missed", {
                "id": commitment.id,
                "promise": commitment.promise,
                "due_at": commitment.due_at,
            })
        if missed:
            self._changed()
        return {
            "checked_at": now,
            "missed": [c.to_dict() for c in missed],
            "missed_count": len(missed),
        }

    # -- reads -------------------------------------------------------

    def get(self, commitment_id) -> Commitment | None:
        with self._lock:
            raw = self._store.read()["commitments"].get(commitment_id)
        return Commitment.from_dict(raw) if raw else None

    def list(self, status=None) -> builtins.list[Commitment]:
        with self._lock:
            items = [
                Commitment.from_dict(raw)
                for raw in self._store.read()["commitments"].values()
            ]
        if status:
            items = [c for c in items if c.status == status]
        items.sort(key=lambda c: (c.status != "open", c.due_at or float("inf"), -c.created_at))
        return items

    def due(self, now=None) -> builtins.list[Commitment]:
        now = time.time() if now is None else float(now)
        return [c for c in self.list(status="open") if c.is_overdue(now)]

    def unsurfaced(self) -> builtins.list[Commitment]:
        return [c for c in self.list(status="missed") if not c.surfaced]

    def mark_surfaced(self, commitment_ids) -> int:
        ids = [c for c in (commitment_ids or []) if c]
        if not ids:
            return 0
        marked = 0
        with self._lock:
            for commitment_id in ids:
                raw = self._store.read()["commitments"].get(commitment_id)
                if raw is None:
                    continue
                commitment = Commitment.from_dict(raw)
                if commitment.surfaced:
                    continue
                commitment.surfaced_at = time.time()
                with self._store.transaction() as document:
                    document["commitments"][commitment.id] = commitment.to_dict()
                marked += 1
        if marked:
            self._changed()
        return marked

    def stats(self) -> dict:
        with self._lock:
            items = [
                Commitment.from_dict(raw)
                for raw in self._store.read()["commitments"].values()
            ]
        return {
            "total": len(items),
            "open": sum(1 for c in items if c.status == "open"),
            "kept": sum(1 for c in items if c.status == "kept"),
            "missed": sum(1 for c in items if c.status == "missed"),
            "cancelled": sum(1 for c in items if c.status == "cancelled"),
            "unsurfaced_missed": sum(1 for c in items if c.status == "missed" and not c.surfaced),
        }


__all__ = ["CommitmentsLedger", "COMMITMENT_STATUSES"]
