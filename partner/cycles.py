# partner/cycles.py
"""Autonomous work cycles — what she picks up during idle time.

A cycle is deliberately narrow and honest: it *selects* backlog work from the
Continuity Engine (due commitments, project checkpoints, resumable tasks) and
records a resumable plan for each item through the verified action engine. It
does not claim research happened — the plan is a checkpoint, and the audit
record says exactly that.

Gating: quiet mode, a non-idle activity class, or an unelapsed cooldown means the
cycle does not run at all.
"""
from __future__ import annotations

import logging
import time
import uuid

logger = logging.getLogger(__name__)


class IdleWorkCycle:

    def __init__(self, continuity=None, presence=None, actions=None,
                 interval: float = 3600.0, max_items: int = 3, event_bus=None):
        self.continuity = continuity
        self.presence = presence
        self.actions = actions
        self.interval = float(interval)
        self.max_items = max(1, int(max_items))
        self.event_bus = event_bus
        self._last_run = 0.0
        self._last_summary: dict = {}

        if self.actions is not None:
            self.actions.register_verifier("cycle_plan", self._verify_plan)

    # -- backlog -----------------------------------------------------

    def candidates(self, now: float | None = None) -> list[dict]:
        now = time.time() if now is None else float(now)
        if self.continuity is None:
            return []
        items: list[dict] = []
        try:
            for commitment in self.continuity.commitments.due(now):
                items.append({
                    "kind": "commitment",
                    "id": commitment.id,
                    "title": commitment.promise,
                })
            for project in self.continuity.projects.list(include_terminal=False):
                if project.next_checkpoint:
                    items.append({
                        "kind": "project",
                        "id": project.id,
                        "title": f"{project.name}: {project.next_checkpoint}",
                    })
            for checkpoint in self.continuity.checkpoints.list():
                items.append({
                    "kind": "resume",
                    "id": checkpoint.task_id,
                    "title": f"resume {checkpoint.task_id} at step {checkpoint.step}",
                })
        except Exception as exc:
            logger.warning("[Cycle] backlog read failed: %s", exc)
            return []
        return items[: max(self.max_items, 1)]

    # -- execution ---------------------------------------------------

    def run(self, now: float | None = None) -> dict:
        now = time.time() if now is None else float(now)

        if self.presence is not None:
            if self.presence.quiet_mode:
                return self._skip("quiet_mode", now)
            if self.presence.activity != "idle":
                return self._skip(f"activity_{self.presence.activity}", now)
        if self._last_run and (now - self._last_run) < self.interval:
            return self._skip("cooldown", now, deferred_until=self._last_run + self.interval)

        items = self.candidates(now)
        if not items:
            self._last_run = now
            summary = {"ran": True, "reason": "nothing_to_do", "cycle_id": "", "items": [], "records": []}
            self._last_summary = summary
            return summary

        if self.continuity is None or self.actions is None:
            return self._skip("cycle_dependencies_missing", now)

        cycle_id = "cycle_" + uuid.uuid4().hex[:8]
        records = []
        for item in items[: self.max_items]:
            task_id = f"{cycle_id}:{item['kind']}:{item['id']}"
            record = self.actions.execute(
                "cycle_plan",
                description=f"Plan {item['kind']} work: {item['title'][:120]}",
                params={"item": item, "cycle_id": cycle_id},
                cycle_id=cycle_id,
                precondition=self._precondition,
                executor=lambda item=item, task_id=task_id, cycle_id=cycle_id:
                    self._plan(item, task_id, cycle_id),
            )
            records.append(record)

        self._last_run = now
        summary = {
            "ran": True,
            "reason": "ok",
            "cycle_id": cycle_id,
            "items": items[: self.max_items],
            "records": records,
            "planned": sum(1 for r in records if r.get("status") == "succeeded"),
            "failed": sum(1 for r in records if r.get("status") not in ("succeeded", "pending_approval")),
        }
        self._last_summary = summary
        self._publish({
            "cycle_id": cycle_id,
            "items": len(items),
            "planned": summary["planned"],
            "failed": summary["failed"],
        })
        logger.info(
            "[Cycle] %s planned %d/%d backlog item(s)",
            cycle_id, summary["planned"], len(records),
        )
        return summary

    # -- internals ---------------------------------------------------

    def _precondition(self) -> tuple[bool, str]:
        if self.continuity is None or not hasattr(self.continuity, "checkpoints"):
            return False, "continuity unavailable"
        return True, "continuity ready"

    def _plan(self, item: dict, task_id: str, cycle_id: str) -> dict:
        self.continuity.checkpoints.save(
            task_id=task_id,
            step=0,
            note=f"planned: {item['title'][:150]}",
            state={"item": item, "cycle_id": cycle_id},
        )
        return {"checkpoint_task": task_id, "step": 0, "kind": item["kind"]}

    def _verify_plan(self, result) -> tuple[bool, str]:
        """Post-condition: the planned work really is resumable."""
        if not isinstance(result, dict) or not result.get("checkpoint_task"):
            return False, "no checkpoint written"
        checkpoint = self.continuity.checkpoints.get(result["checkpoint_task"])
        if checkpoint is None:
            return False, "checkpoint missing after save"
        return True, f"checkpoint {checkpoint.task_id} at step {checkpoint.step}"

    def _skip(self, reason: str, now: float, deferred_until: float = 0.0) -> dict:
        summary = {
            "ran": False,
            "reason": reason,
            "cycle_id": "",
            "items": [],
            "records": [],
            "deferred_until": deferred_until,
            "checked_at": now,
        }
        self._last_summary = summary
        return summary

    def _publish(self, payload: dict) -> None:
        if not self.event_bus:
            return
        try:
            from core.mai_message import publish_event
            publish_event(self.event_bus, "data.partner.cycle", payload, source="partner")
        except Exception as exc:
            logger.warning("[Cycle] event publish failed: %s", exc)

    # -- introspection -----------------------------------------------

    def status(self) -> dict:
        return {
            "interval": self.interval,
            "max_items": self.max_items,
            "last_run": self._last_run,
            "last_summary": dict(self._last_summary),
            "backlog": len(self.candidates()),
        }
