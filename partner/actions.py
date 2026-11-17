# partner/actions.py
"""Action policy + verified actions.

Two guarantees the roadmap asks for:

1. **An action policy engine** — every action type has a tier
   (``read_only`` / ``safe`` / ``needs_approval`` / ``forbidden``). Unknown
   types default to *needs_approval*, never to allowed.
2. **Verified actions, honest failures** — an action is not "done" until its
   post-condition is checked. A failed verification, a failed precondition, or
   an exception is recorded as such; nothing is silently swallowed.

Every outcome lands in the audit trail (``partner/audit.py``), so a bad day is
reconstructable instead of invisible.
"""
from __future__ import annotations

import logging
import threading
import time
import uuid

logger = logging.getLogger(__name__)

READ_ONLY = "read_only"
SAFE = "safe"
NEEDS_APPROVAL = "needs_approval"
FORBIDDEN = "forbidden"
TIERS = (READ_ONLY, SAFE, NEEDS_APPROVAL, FORBIDDEN)

# Default tiers. Reads are free, writes inside her sandbox are safe, anything
# that leaves the sandbox or speaks as her needs approval, and self/OS-level
# damage is forbidden outright.
DEFAULT_TIERS = {
    "read_file": READ_ONLY,
    "list_dir": READ_ONLY,
    "calendar_read": READ_ONLY,
    "mail_read": READ_ONLY,
    "search_web": READ_ONLY,
    "research": READ_ONLY,
    "checkpoint_save": SAFE,
    "note_write": SAFE,
    "knowledge_ingest": SAFE,
    "cycle_plan": SAFE,
    "create_file": NEEDS_APPROVAL,
    "send_email": NEEDS_APPROVAL,
    "open_app": NEEDS_APPROVAL,
    "type_text": NEEDS_APPROVAL,
    "run_shell": FORBIDDEN,
    "delete_file": FORBIDDEN,
    "self_modify": FORBIDDEN,
}

_SECRET_HINTS = ("password", "token", "secret", "api_key", "apikey", "credential")

# Audit records stay tiny; persisted pending params must round-trip intact (a
# restored file write needs the whole body, not the first 400 chars of it).
_PENDING_STRING_LIMIT = 8000


class ActionPolicy:

    def __init__(self, tiers: dict | None = None):
        self._lock = threading.RLock()
        self._tiers = dict(DEFAULT_TIERS)
        if tiers:
            self._tiers.update(tiers)

    def register(self, action_type: str, tier: str) -> str:
        if tier not in TIERS:
            raise ValueError(f"unknown tier: {tier!r}")
        with self._lock:
            self._tiers[str(action_type)] = tier
        return tier

    def tier_of(self, action_type: str) -> str:
        with self._lock:
            return self._tiers.get(str(action_type), NEEDS_APPROVAL)

    def authorize(self, action_type: str) -> tuple[str, bool, str]:
        tier = self.tier_of(action_type)
        if tier == FORBIDDEN:
            return tier, False, "forbidden_action"
        if tier == NEEDS_APPROVAL:
            return tier, False, "approval_required"
        return tier, True, "allowed"

    def snapshot(self) -> dict:
        with self._lock:
            return dict(self._tiers)


class VerifiedActionEngine:

    def __init__(self, policy=None, audit=None, event_bus=None, on_change=None,
                 store=None):
        self.policy = policy or ActionPolicy()
        self.audit = audit
        self.event_bus = event_bus
        self._on_change = on_change
        self._store = store
        self._lock = threading.RLock()
        self._verifiers: dict[str, object] = {}
        self._factories: dict[str, object] = {}
        self._pending: dict[str, dict] = {}
        if self._store is not None:
            self._restore_pending()

    # -- registration ------------------------------------------------

    def register_verifier(self, action_type: str, verifier) -> None:
        """``verifier(result)`` returns truthy when the post-condition holds."""
        with self._lock:
            self._verifiers[str(action_type)] = verifier

    def register_executor_factory(self, action_type: str, factory) -> None:
        """Rebuild an executor for a pending action that outlived its process.

        Executors are closures and cannot be serialized, so an approval that
        survives a restart is re-executed through ``factory(entry)`` — the
        entry carries ``params``/``description``/``cycle_id``. Return a
        callable, or ``(executor, precondition)``. Without a factory a restored
        approval still lists and rejects, but approving it reports
        ``no_executor_after_restart`` instead of pretending to run.
        """
        with self._lock:
            self._factories[str(action_type)] = factory

    # -- execution ---------------------------------------------------

    def execute(self, action_type, description="", executor=None, params=None,
                precondition=None, cycle_id=None, approved=False) -> dict:
        """Run one action under policy, verify it, and record the outcome."""
        action_type = str(action_type or "").strip()
        tier, allowed, reason = self.policy.authorize(action_type)
        record = {
            "id": "act_" + uuid.uuid4().hex[:10],
            "action_type": action_type,
            "tier": tier,
            "description": str(description or "")[:300],
            "params": _sanitize(params),
            "cycle_id": cycle_id,
            "status": "",
            "verified": None,
            "verification": "",
            "error": "",
            "started_at": time.time(),
            "ended_at": 0.0,
            "duration": 0.0,
        }

        if tier == FORBIDDEN:
            return self._finish(record, "denied", error="forbidden_action")

        if tier == NEEDS_APPROVAL and not approved:
            with self._lock:
                self._pending[record["id"]] = {
                    "action_type": action_type,
                    "executor": executor,
                    "precondition": precondition,
                    "params": params,
                    "description": description,
                    "cycle_id": cycle_id,
                    "created_at": time.time(),
                    "restored": False,
                }
            self._persist_pending()
            record["pending_reason"] = "approval_required"
            return self._finish(record, "pending_approval")

        if precondition is not None:
            try:
                outcome = precondition()
            except Exception as exc:
                return self._finish(record, "blocked", error=f"precondition raised: {exc}")
            ok, detail = _unpack_condition(outcome)
            record["precondition"] = detail
            if not ok:
                return self._finish(record, "blocked", error=detail or "precondition_failed")

        if executor is None or not callable(executor):
            return self._finish(record, "failed", error="no_executor")

        try:
            result = executor()
        except Exception as exc:
            logger.warning("[Actions] %s failed: %s", action_type, exc)
            return self._finish(record, "failed", error=str(exc))

        record["result"] = _sanitize(result)

        with self._lock:
            verifier = self._verifiers.get(action_type)
        if verifier is None:
            # No post-condition registered: report success without claiming
            # verification (the record says so explicitly).
            record["verification"] = "no_verifier_registered"
            return self._finish(record, "succeeded")

        try:
            verdict = verifier(result)
        except Exception as exc:
            record["verification"] = f"verifier raised: {exc}"
            return self._finish(record, "unverified")
        ok, detail = _unpack_condition(verdict)
        record["verified"] = bool(ok)
        record["verification"] = detail or ("post_condition_met" if ok else "post_condition_failed")
        return self._finish(record, "succeeded" if ok else "unverified")

    def approve(self, record_id, approver="user") -> dict | None:
        """Execute a pending action after explicit approval.

        Works for approvals restored from disk too: the executor is rebuilt
        through a registered factory (see ``register_executor_factory``).
        """
        with self._lock:
            pending = self._pending.pop(str(record_id or ""), None)
        if pending is None:
            return None
        executor, precondition, resolve_error = self._resolve_executor(pending)
        self._persist_pending()
        if executor is None:
            record = self._pending_record(record_id, pending)
            return self._finish(record, "failed",
                                error=resolve_error or "no_executor")
        record = self.execute(
            action_type=pending["action_type"],
            description=pending["description"],
            executor=executor,
            params=pending["params"],
            precondition=precondition,
            cycle_id=pending["cycle_id"],
            approved=True,
        )
        record["approved_by"] = approver
        record["approved_at"] = time.time()
        return record

    def reject(self, record_id, reason="", rejected_by="user") -> dict | None:
        """Decline a pending action without running it."""
        with self._lock:
            pending = self._pending.pop(str(record_id or ""), None)
        if pending is None:
            return None
        self._persist_pending()
        record = self._pending_record(record_id, pending)
        record["error"] = str(reason or "rejected")
        record["rejected_by"] = rejected_by
        return self._finish(record, "rejected")

    def pending(self) -> list[dict]:
        with self._lock:
            entries = {
                rid: {k: v for k, v in data.items()
                      if k not in ("executor", "precondition")}
                for rid, data in self._pending.items()
            }
        return [
            {"id": rid, **data, "resumable": self._can_execute(data)}
            for rid, data in entries.items()
        ]

    # -- introspection -----------------------------------------------

    def recent(self, limit=20) -> list[dict]:
        return self.audit.recent(limit) if self.audit else []

    def stats(self) -> dict:
        stats = self.audit.stats() if self.audit else {"total": 0, "by_status": {}, "by_tier": {}}
        with self._lock:
            stats["pending_approval"] = len(self._pending)
            stats["pending_resumable"] = sum(
                1 for data in self._pending.values() if self._can_execute(data)
            )
            stats["pending_durable"] = self._store is not None
            stats["verifiers"] = sorted(self._verifiers)
        return stats

    # -- persistence -------------------------------------------------

    def _restore_pending(self) -> None:
        """Rehydrate pending descriptors written by a previous process."""
        try:
            document = self._store.read()
        except Exception as exc:
            logger.warning("[Actions] pending store unreadable: %s", exc)
            return
        entries = document.get("pending_actions") or {}
        if not isinstance(entries, dict):
            logger.warning("[Actions] pending store shape invalid — ignoring")
            return
        restored = 0
        with self._lock:
            for record_id, entry in entries.items():
                if not isinstance(entry, dict) or not entry.get("action_type"):
                    continue
                self._pending[str(record_id)] = {
                    "action_type": str(entry["action_type"]),
                    "executor": None,
                    "precondition": None,
                    "params": entry.get("params"),
                    "description": entry.get("description", ""),
                    "cycle_id": entry.get("cycle_id"),
                    "created_at": float(entry.get("created_at") or time.time()),
                    "restored": True,
                }
                restored += 1
        if restored:
            logger.info("[Actions] restored %d pending approval(s) from disk", restored)

    def _persist_pending(self) -> None:
        """Atomically mirror the pending set — closures stay in memory only."""
        if self._store is None:
            return
        with self._lock:
            snapshot = {
                record_id: {
                    "action_type": data["action_type"],
                    "description": str(data.get("description") or "")[:300],
                    "params": _sanitize(data.get("params"), max_str=_PENDING_STRING_LIMIT),
                    "cycle_id": data.get("cycle_id"),
                    "created_at": float(data.get("created_at") or time.time()),
                    "tier": self.policy.tier_of(data["action_type"]),
                }
                for record_id, data in self._pending.items()
            }
        try:
            with self._store.transaction() as document:
                document["pending_actions"] = snapshot
        except Exception as exc:
            logger.warning("[Actions] pending persist failed: %s", exc)

    # -- internals ---------------------------------------------------

    def _can_execute(self, data: dict) -> bool:
        if callable(data.get("executor")):
            return True
        with self._lock:
            return data.get("action_type") in self._factories

    def _resolve_executor(self, pending: dict):
        """Return ``(executor, precondition, error)`` for a pending entry."""
        if callable(pending.get("executor")):
            return pending["executor"], pending.get("precondition"), ""
        with self._lock:
            factory = self._factories.get(pending.get("action_type"))
        if factory is None:
            error = "no_executor_after_restart" if pending.get("restored") else "no_executor"
            return None, None, error
        try:
            built = factory(dict(pending))
        except Exception as exc:
            logger.warning(
                "[Actions] executor factory failed for %s: %s",
                pending.get("action_type"), exc,
            )
            return None, None, f"executor_factory_failed: {exc}"
        if isinstance(built, tuple):
            executor = built[0] if built else None
            precondition = built[1] if len(built) > 1 else None
        else:
            executor, precondition = built, None
        if not callable(executor):
            return None, None, "executor_factory_returned_nothing"
        return executor, precondition, ""

    def _pending_record(self, record_id, pending: dict) -> dict:
        return {
            "id": str(record_id),
            "action_type": pending["action_type"],
            "tier": self.policy.tier_of(pending["action_type"]),
            "description": str(pending.get("description") or "")[:300],
            "params": _sanitize(pending.get("params")),
            "cycle_id": pending.get("cycle_id"),
            "status": "",
            "verified": None,
            "verification": "",
            "error": "",
            "restored": bool(pending.get("restored")),
            "started_at": time.time(),
            "ended_at": 0.0,
            "duration": 0.0,
        }

    def _finish(self, record: dict, status: str, error: str = "") -> dict:
        record["status"] = status
        if error:
            record["error"] = error
        record["ended_at"] = time.time()
        record["duration"] = round(record["ended_at"] - record["started_at"], 4)
        if self.audit is not None:
            self.audit.append(record)
        self._publish("data.partner.action", {
            "id": record["id"],
            "action_type": record["action_type"],
            "tier": record["tier"],
            "status": status,
            "verified": record["verified"],
        })
        if self._on_change is not None:
            try:
                self._on_change()
            except Exception as exc:
                logger.warning("[Actions] change hook failed: %s", exc)
        return record

    def _publish(self, event_type: str, payload: dict) -> None:
        if not self.event_bus:
            return
        try:
            from core.mai_message import publish_event
            publish_event(self.event_bus, event_type, payload, source="partner")
        except Exception as exc:
            logger.warning("[Actions] event publish failed (%s): %s", event_type, exc)


def _unpack_condition(outcome) -> tuple[bool, str]:
    """Accept ``bool`` or ``(bool, detail)`` from preconditions/verifiers."""
    if isinstance(outcome, tuple) and len(outcome) >= 2:
        return bool(outcome[0]), str(outcome[1] or "")
    if isinstance(outcome, dict) and "ok" in outcome:
        return bool(outcome["ok"]), str(outcome.get("detail", "") or "")
    return bool(outcome), ""


def _sanitize(value, depth: int = 0, max_str: int = 500):
    """Keep audit records small and free of obvious credentials.

    ``max_str`` is raised for pending persistence so a restored action keeps the
    parameters it will be re-executed with.
    """
    if depth > 3:
        return "..."
    if isinstance(value, dict):
        clean = {}
        for key, item in value.items():
            text_key = str(key).lower()
            if any(hint in text_key for hint in _SECRET_HINTS):
                clean[key] = "[redacted]"
            else:
                clean[key] = _sanitize(item, depth + 1, max_str)
        return clean
    if isinstance(value, (list, tuple)):
        return [_sanitize(item, depth + 1, max_str) for item in value[:20]]
    if isinstance(value, str):
        return value[:max_str]
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return str(value)[:200]
