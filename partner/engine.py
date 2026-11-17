# partner/engine.py
"""M23 Partner — presence, initiative, verified actions, mail, calendar, cycles.

The facade ties the pieces together and keeps them honest:

- ``presence`` decides whether she may approach, interrupt, or initiate.
- ``actions`` enforces the tier policy and verifies post-conditions.
- ``outbox`` holds drafts that need approval; nothing sends itself.
- ``cycles`` plans idle backlog work and checkpoints it.
- ``briefing`` composes the ritual text from continuity + calendar + inbox.

Everything observable is published on the state bus (``state.partner.updated``)
and every action lands in the audit trail.
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from core.atomic_document import AtomicDocument
from partner.actions import ActionPolicy, VerifiedActionEngine
from partner.audit import ActionAuditLog
from partner.calendar import IcsCalendar
from partner.cycles import IdleWorkCycle
from partner.mail import MailboxSource, NullMailbox, Outbox
from partner.presence import PresencePolicy
from partner.workspace import MAX_CONTENT_CHARS, PartnerWorkspace

logger = logging.getLogger(__name__)

_DOCUMENT_DEFAULTS = {
    "version": 1,
    "presence": {"quiet_mode": False},
    "rituals": {},
    "drafts": {},
    "pending_actions": {},
}


class PartnerEngine:

    def __init__(self, store_path=None, audit_path=None, event_bus=None,
                 continuity=None, cognitive_state=None, shared_state=None,
                 mail: MailboxSource | None = None, calendar=None,
                 quiet_mode: bool = False, min_trust: float = 0.6,
                 initiative_cooldown: float = 3600.0,
                 cycle_interval: float = 3600.0, max_backlog_items: int = 3,
                 upcoming_hours: float = 24.0, workspace_dir=None):
        if store_path is None or audit_path is None:
            try:
                from config.paths import ROOT_DIR
                data_dir = ROOT_DIR / "data"
            except Exception:
                data_dir = Path("data")
            store_path = store_path or (data_dir / "partner.json")
            audit_path = audit_path or (data_dir / "partner_actions.jsonl")

        self.continuity = continuity
        # Assigned by the self-awareness builder; the briefing reads one line.
        self.self_awareness = None
        self.cognitive_state = cognitive_state
        self.shared_state = shared_state
        self.event_bus = event_bus
        self.upcoming_hours = float(upcoming_hours)
        self._lock = threading.RLock()
        self._last_brief: dict = {}

        self.store = AtomicDocument(store_path, defaults=_DOCUMENT_DEFAULTS, label="Partner")
        self.workspace = PartnerWorkspace(
            workspace_dir if workspace_dir is not None
            else Path(self.store.path).parent / "partner_files"
        )
        self.presence = PresencePolicy(
            store=self.store,
            quiet_mode=quiet_mode,
            min_trust=min_trust,
            initiative_cooldown=initiative_cooldown,
        )
        self.audit = ActionAuditLog(audit_path)
        # The store makes approval-gated actions outlive this process: the
        # pending descriptors are persisted (executors are closures and are
        # rebuilt on approval via a registered executor factory).
        self.actions = VerifiedActionEngine(
            policy=ActionPolicy(),
            audit=self.audit,
            event_bus=event_bus,
            on_change=self.publish,
            store=self.store,
        )
        # create_file is the approval-tier action the partner can genuinely
        # perform: a sandboxed write, verifiable, and re-executable after a
        # restart from its persisted params.
        self.actions.register_verifier("create_file", self._verify_file)
        self.actions.register_executor_factory("create_file", self._file_executor)
        self.outbox = Outbox(self.store)
        self.mail = mail if mail is not None else NullMailbox()
        self.calendar = calendar if calendar is not None else IcsCalendar(_default_ics_path())
        self.cycles = IdleWorkCycle(
            continuity=continuity,
            presence=self.presence,
            actions=self.actions,
            interval=cycle_interval,
            max_items=max_backlog_items,
            event_bus=event_bus,
        )

    # -- trust / presence --------------------------------------------

    def trust(self) -> float:
        """Relationship trust, read from its owner (SharedState)."""
        shared = self.shared_state
        if shared is None:
            return 0.5
        try:
            with shared.lock:
                return float(shared.relationship_scores.trust)
        except Exception as exc:
            logger.debug("[Partner] trust read failed: %s", exc)
            return 0.5

    def set_quiet(self, flag: bool) -> bool:
        value = self.presence.set_quiet(flag)
        self.publish()
        self._publish("data.partner.presence", {"quiet_mode": value})
        return value

    def set_activity(self, activity: str) -> bool:
        changed = self.presence.set_activity(activity)
        if changed:
            self.publish()
        return changed

    def refresh_activity(self, window_title: str = "", idle_seconds: float | None = None) -> str:
        """Refresh the activity class from live signals.

        With no signal at all, detection falls back to ``idle`` — but a tick
        must not use that fallback to erase an activity someone set on purpose
        (the scheduler ticks every 15 minutes and T3 window-title tracking has
        not landed yet). So the fallback only applies when there is evidence
        of idleness, not when there is no evidence of anything.
        """
        activity = self.presence.detect_activity(
            cognitive_state=self.cognitive_state,
            window_title=window_title,
            idle_seconds=idle_seconds,
        )
        if activity == "idle" and not window_title and idle_seconds is None:
            return self.presence.activity
        self.presence.set_activity(activity)
        return activity

    def initiate(self, now: float | None = None) -> dict:
        """May she start a conversation? (Initiative + disagreement gates.)"""
        decision = self.presence.should_initiate(self.trust(), now)
        return decision.to_dict()

    def may_disagree(self) -> dict:
        return self.presence.may_disagree(self.trust()).to_dict()

    # -- briefing ----------------------------------------------------

    def briefing(self, now: float | None = None, include_mail: bool = True,
                 include_continuity: bool = True) -> str:
        now = time.time() if now is None else float(now)
        ritual = self.presence.ritual_for(now) or "no ritual window"
        header = [f"PARTNER BRIEF — {ritual} · activity {self.presence.activity}"]
        if self.presence.quiet_mode:
            header.append("(quiet mode — she observes, does not initiate)")
        lines = [" · ".join(header)]

        if include_continuity and self.continuity is not None:
            try:
                brief = self.continuity.brief()
            except Exception as exc:
                logger.warning("[Partner] continuity brief failed: %s", exc)
                brief = ""
            if brief:
                lines.append(brief)

        events = self.calendar_upcoming(now=now)
        if events:
            lines.append(f"Calendar (next {int(self.upcoming_hours)}h):")
            for event in events[:5]:
                when = time.strftime("%H:%M", time.localtime(event.start))
                entry = f"  - {when} {event.summary}"
                if event.location:
                    entry += f" @ {event.location}"
                lines.append(entry)

        if include_mail and getattr(self.mail, "available", False):
            messages = self.mail_summary(limit=5, unread_only=True)
            if messages.get("count"):
                lines.append(f"Inbox: {messages['count']} unread")
                for message in messages.get("messages", [])[:3]:
                    lines.append(f"  - {message.get('sender', '')[:40]}: {message.get('subject', '')[:60]}")

        drafts = self.outbox.stats()
        if drafts.get("needs_approval"):
            lines.append(f"Drafts awaiting approval: {drafts['needs_approval']}")

        pending = self.actions.stats().get("pending_approval", 0)
        if pending:
            lines.append(f"Actions awaiting approval: {pending}")

        self_awareness = getattr(self, "self_awareness", None)
        if self_awareness is not None:
            try:
                line = self_awareness.brief_line()
            except Exception as exc:
                logger.warning("[Partner] self-awareness line failed: %s", exc)
                line = ""
            if line:
                lines.append(line)

        return "\n".join(lines)

    def maybe_brief(self, now: float | None = None) -> dict:
        """Emit the ritual briefing once per window, never in quiet mode."""
        now = time.time() if now is None else float(now)
        ritual = self.presence.ritual_for(now)
        if ritual is None:
            return {"briefed": False, "reason": "no_ritual_window"}
        if self.presence.quiet_mode:
            return {"briefed": False, "reason": "quiet_mode"}
        if not self.presence.ritual_due(ritual, now):
            return {"briefed": False, "reason": "already_briefed_today", "ritual": ritual}

        text = self.briefing(now=now)
        self.presence.mark_ritual(ritual, now)
        with self._lock:
            self._last_brief = {"ritual": ritual, "at": now, "text": text}
        self._publish("data.partner.briefing", {"ritual": ritual, "text": text})
        self.publish()
        logger.info("[Partner] %s briefing emitted (%d chars)", ritual, len(text))
        return {"briefed": True, "ritual": ritual, "text": text}

    # -- mail / calendar ---------------------------------------------

    def mail_summary(self, limit: int = 10, unread_only: bool = False) -> dict:
        messages = self.mail.list_recent(limit=limit, unread_only=unread_only)
        return {
            "count": len(messages),
            "messages": [m.to_dict() for m in messages],
            "source": getattr(self.mail, "name", "unknown"),
            "available": bool(getattr(self.mail, "available", False)),
            "last_error": getattr(self.mail, "last_error", ""),
        }

    def calendar_upcoming(self, hours: float | None = None, now: float | None = None) -> list:
        hours = self.upcoming_hours if hours is None else float(hours)
        return self.calendar.upcoming(hours=hours, now=now)

    def draft_mail(self, to, subject, body, reason="") -> dict:
        return self.outbox.draft(to=to, subject=subject, body=body, reason=reason)

    def request_file(self, path, content, reason="") -> dict:
        """Park a workspace file write behind the approval tier.

        Nothing is written here. The executor runs only after an explicit
        approval — in this process, or in a later one through the registered
        ``create_file`` factory, which rebuilds it from the persisted params.
        """
        text = "" if content is None else str(content)
        if len(text) > MAX_CONTENT_CHARS:
            raise ValueError(f"content too large (max {MAX_CONTENT_CHARS} chars)")
        params = {"path": str(path or "").strip(), "content": text}
        description = f"write {params['path']}"
        if reason:
            description = f"{description} — {str(reason)[:120]}"
        executor, precondition = self._file_executor({"params": params})
        return self.actions.execute(
            "create_file",
            description=description,
            params=params,
            executor=executor,
            precondition=precondition,
        )

    def _file_executor(self, entry):
        """Build ``(executor, precondition)`` for a create_file entry."""
        params = dict(entry.get("params") or {})
        path = params.get("path", "")
        content = params.get("content", "")

        def precondition() -> tuple[bool, str]:
            target, error = self.workspace.resolve(path)
            if target is None:
                return False, error
            if len(str(content)) > MAX_CONTENT_CHARS:
                return False, "content too large"
            return True, "workspace ready"

        return (lambda: self.workspace.write(path, content)), precondition

    def _verify_file(self, result):
        """Post-condition: the file really exists with the bytes reported."""
        if not isinstance(result, dict) or not result.get("path"):
            return False, "no file written"
        if not self.workspace.exists(result["path"]):
            return False, "file missing after write"
        target, _error = self.workspace.resolve(result["path"])
        if target is None or target.stat().st_size != result.get("bytes"):
            return False, "size mismatch after write"
        return True, f"{result['path']} ({result['bytes']} bytes)"

    # -- scheduler tick ----------------------------------------------

    def tick(self, now: float | None = None) -> dict:
        now = time.time() if now is None else float(now)
        self.refresh_activity()
        brief = self.maybe_brief(now)
        cycle = self.cycles.run(now)
        return {"brief": brief, "cycle": cycle, "checked_at": now}

    # -- event feed --------------------------------------------------

    def publish(self) -> None:
        if not self.event_bus:
            return
        try:
            from core.mai_message import publish_event
            stats = self.actions.stats()
            publish_event(self.event_bus, "state.partner.updated", {
                "quiet_mode": self.presence.quiet_mode,
                "activity": self.presence.activity,
                "pending_approvals": stats.get("pending_approval", 0),
                "drafts_needing_approval": self.outbox.stats().get("needs_approval", 0),
                "last_brief": (self._last_brief or {}).get("ritual", ""),
            }, source="partner")
        except Exception as exc:
            logger.warning("[Partner] state publish failed: %s", exc)

    def _publish(self, event_type: str, payload: dict) -> None:
        if not self.event_bus:
            return
        try:
            from core.mai_message import publish_event
            publish_event(self.event_bus, event_type, payload, source="partner")
        except Exception as exc:
            logger.warning("[Partner] event publish failed (%s): %s", event_type, exc)

    # -- introspection -----------------------------------------------

    def status(self) -> dict:
        return {
            "presence": self.presence.status(),
            "trust": round(self.trust(), 3),
            "actions": self.actions.stats(),
            "outbox": self.outbox.stats(),
            "mail": {
                "source": getattr(self.mail, "name", "unknown"),
                "available": bool(getattr(self.mail, "available", False)),
                "last_error": getattr(self.mail, "last_error", ""),
            },
            "calendar": self.calendar.stats(),
            "workspace": self.workspace.stats(),
            "cycles": self.cycles.status(),
            "last_brief": dict(self._last_brief),
        }

    def health(self) -> dict:
        return {"ok": True, "quiet_mode": self.presence.quiet_mode}


def _default_ics_path():
    try:
        from config.partner import PARTNER_CALENDAR_ICS
        return PARTNER_CALENDAR_ICS
    except Exception:
        from pathlib import Path
        return Path("data") / "calendar.ics"


__all__ = ["PartnerEngine", "PresencePolicy", "IdleWorkCycle"]
