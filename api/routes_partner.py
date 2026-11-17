"""Partner domain logic for the Mai API (presence + approvals).

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for how this is composed.

Approvals were previously unreachable: the action policy could park an action
in ``needs_approval`` and only in-process code could release it. These handlers
close that loop — list what is waiting, approve it (execution still runs through
the verified action engine), or reject it (recorded as ``rejected`` in the
audit trail).

Nothing here approves on the caller's behalf beyond the explicit request: a
draft approval still cannot send mail, and the approve path is the only way a
``needs_approval`` action ever runs.
"""
import logging
from typing import Any

from api.errors import safe_error

logger = logging.getLogger("api.server")


class PartnerMixin:
    """Presence, approval list, and approval/rejection handlers."""

    # Set by MaiAPI at runtime — declared here for the type checker
    partner: Any = None
    brain: Any = None

    def _partner_engine(self):
        engine = getattr(self, "partner", None)
        if engine is None and self.brain is not None:
            engine = getattr(self.brain, "partner", None)
        return engine

    def partner_status(self):
        engine = self._partner_engine()
        if engine is None:
            return {"error": "partner_unavailable"}
        try:
            return engine.status()
        except Exception as e:
            logger.exception("[routes_partner] status: %s", e)
            return {"error": safe_error(e)}

    def partner_approvals(self):
        """Everything currently parked behind an approval gate."""
        engine = self._partner_engine()
        if engine is None:
            return {"error": "partner_unavailable"}
        try:
            actions = engine.actions.pending()
            drafts = engine.outbox.list(status="needs_approval")
            return {
                "actions": actions,
                "drafts": drafts,
                "count": len(actions) + len(drafts),
            }
        except Exception as e:
            logger.exception("[routes_partner] approvals: %s", e)
            return {"error": safe_error(e)}

    def partner_approve(self, approval_id):
        engine = self._partner_engine()
        if engine is None:
            return {"error": "partner_unavailable"}
        try:
            record = engine.actions.approve(approval_id, approver="api")
            if record is not None:
                return {"kind": "action", "approval": record}
            draft = engine.outbox.approve(approval_id)
            if draft is not None:
                engine.publish()
                return {
                    "kind": "draft",
                    "draft": draft,
                    "note": "draft approved — sending still requires a transport",
                }
            return {"error": "unknown_approval", "id": approval_id}
        except Exception as e:
            logger.exception("[routes_partner] approve: %s", e)
            return {"error": safe_error(e)}

    def partner_reject(self, approval_id, reason=""):
        engine = self._partner_engine()
        if engine is None:
            return {"error": "partner_unavailable"}
        try:
            record = engine.actions.reject(approval_id, reason=reason, rejected_by="api")
            if record is not None:
                return {"kind": "action", "approval": record}
            draft = engine.outbox.reject(approval_id)
            if draft is not None:
                engine.publish()
                return {"kind": "draft", "draft": draft}
            return {"error": "unknown_approval", "id": approval_id}
        except Exception as e:
            logger.exception("[routes_partner] reject: %s", e)
            return {"error": safe_error(e)}
