# partner/tools.py
"""Tool surface of the Partner subsystem.

Small flat tools — presence, briefing, inbox read, draft (approval-gated), and
calendar. Nothing here sends mail or acts outside the action policy.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _guard(name, handler):
    def wrapped(**kwargs):
        try:
            return handler(**kwargs)
        except ValueError as exc:
            return {"error": str(exc), "tool": name}
        except Exception as exc:
            logger.error("[Partner] tool %s failed: %s", name, exc)
            return {"error": str(exc), "tool": name}
    return wrapped


def register_partner_tools(registry, partner):
    """Register partner tools on a ToolRegistry (no-op when unavailable)."""
    if registry is None or partner is None:
        return 0

    engine = partner

    def _status():
        return engine.status()

    def _presence_set(quiet_mode=None, activity=None):
        changed = {}
        if quiet_mode is not None:
            changed["quiet_mode"] = engine.set_quiet(bool(quiet_mode))
        if activity is not None:
            if not engine.set_activity(str(activity)):
                return {"error": f"unknown activity: {activity!r}"}
            changed["activity"] = engine.presence.activity
        return {"changed": changed, "presence": engine.presence.status()}

    def _briefing():
        return {"text": engine.briefing()}

    def _mail_summary(limit=10, unread_only=True):
        summary = engine.mail_summary(limit=int(limit or 10), unread_only=bool(unread_only))
        if not summary.get("available"):
            summary["note"] = "no mailbox configured (set MAI_MAIL_IMAP_HOST/USER/PASSWORD)"
        return summary

    def _mail_draft(to, subject, body, reason=""):
        draft = engine.draft_mail(to=to, subject=subject, body=body, reason=reason)
        return {
            "draft": draft,
            "note": "draft saved for approval — nothing is sent automatically",
        }

    def _file_create(path, content, reason=""):
        record = engine.request_file(path=path, content=content, reason=reason)
        return {
            "approval": {
                "id": record.get("id"),
                "action_type": record.get("action_type"),
                "status": record.get("status"),
                "description": record.get("description"),
            },
            "note": (
                "file write parked for approval — nothing is written until it is "
                "approved via /api/partner/approvals or partner_status"
            ),
        }

    def _calendar_upcoming(hours=None):
        events = engine.calendar_upcoming(hours=hours)
        return {
            "events": [event.to_dict() for event in events],
            "count": len(events),
            "available": bool(getattr(engine.calendar, "available", False)),
        }

    registry.register(
        name="partner_status",
        description="Presence, trust, pending approvals, outbox, mail, calendar and idle-cycle status.",
        handler=_guard("partner_status", _status),
        parameters={},
        category="partner",
    )

    registry.register(
        name="presence_set",
        description="Set Mai's presence: quiet mode (observes but never initiates) or her activity class (coding, working, focus, idle, conversation, away).",
        handler=_guard("presence_set", _presence_set),
        parameters={
            "quiet_mode": {"type": "boolean", "description": "Sees everything, initiates nothing"},
            "activity": {"type": "string", "description": "coding | working | focus | idle | conversation | away"},
        },
        category="partner",
    )

    registry.register(
        name="partner_briefing",
        description="Compose the current briefing: ongoing projects and commitments, upcoming calendar, unread inbox, drafts awaiting approval.",
        handler=_guard("partner_briefing", _briefing),
        parameters={},
        category="partner",
    )

    registry.register(
        name="mail_summary",
        description="Summarize recent inbox messages (read-only; never marks mail as read).",
        handler=_guard("mail_summary", _mail_summary),
        parameters={
            "limit": {"type": "number", "description": "How many messages"},
            "unread_only": {"type": "boolean", "description": "Only unread messages"},
        },
        category="partner",
    )

    registry.register(
        name="mail_draft",
        description="Draft an outgoing email into the approval-gated outbox. Nothing is sent.",
        handler=_guard("mail_draft", _mail_draft),
        parameters={
            "to": {"type": "string", "description": "Recipient address"},
            "subject": {"type": "string", "description": "Subject line"},
            "body": {"type": "string", "description": "Body text"},
            "reason": {"type": "string", "description": "Why this draft exists"},
        },
        category="partner",
    )

    registry.register(
        name="file_create",
        description=(
            "Request a text file write inside Mai's workspace. It is parked for "
            "approval; nothing is written until the user approves it."
        ),
        handler=_guard("file_create", _file_create),
        parameters={
            "path": {"type": "string", "description": "Relative path inside the workspace, e.g. briefs/monday.md"},
            "content": {"type": "string", "description": "UTF-8 text to write (max 4000 chars)"},
            "reason": {"type": "string", "description": "Why this file should exist"},
        },
        category="partner",
    )

    registry.register(
        name="calendar_upcoming",
        description="List upcoming calendar events from the local .ics calendar.",
        handler=_guard("calendar_upcoming", _calendar_upcoming),
        parameters={
            "hours": {"type": "number", "description": "Look-ahead window in hours"},
        },
        category="partner",
    )

    return 7
