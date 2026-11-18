# partner/mail.py
"""Email — read-only IMAP inbox + an approval-gated outbox.

Read is deliberately read-only (``SELECT ... readonly``) and never marks
anything seen. Sending is not implemented: drafts are written to the outbox and
must be approved, and ``Outbox.send`` refuses with a truthful reason rather than
pretending. The roadmap's rule is "sending starts approval-gated", and an SMTP
transport is a separate, explicit decision.
"""
from __future__ import annotations

import email
import imaplib
import logging
import time
import uuid
from dataclasses import dataclass
from email.header import decode_header, make_header

logger = logging.getLogger(__name__)


@dataclass
class MailMessage:
    uid: str
    subject: str = ""
    sender: str = ""
    date: str = ""
    unread: bool = False
    snippet: str = ""

    def to_dict(self) -> dict:
        return {
            "uid": self.uid,
            "subject": self.subject,
            "sender": self.sender,
            "date": self.date,
            "unread": self.unread,
            "snippet": self.snippet,
        }


class MailboxSource:
    """Interface every mailbox implementation satisfies."""

    name = "none"
    available = False

    def list_recent(self, limit: int = 10, unread_only: bool = False) -> list[MailMessage]:
        raise NotImplementedError


class NullMailbox(MailboxSource):
    """Used when no IMAP account is configured — the boot never half-connects."""

    name = "null"
    available = False

    def __init__(self, reason: str = "no mailbox configured"):
        self.reason = reason

    def list_recent(self, limit: int = 10, unread_only: bool = False) -> list[MailMessage]:
        return []


class ImapMailbox(MailboxSource):
    """Read-only IMAP reader. Connections are opened per call and closed."""

    name = "imap"
    available = True

    def __init__(self, host, username, password, port=993, folder="INBOX",
                 use_ssl=True, timeout=15.0, conn_factory=None):
        self.host = host
        self.username = username
        self.password = password
        self.port = int(port)
        self.folder = folder or "INBOX"
        self.use_ssl = bool(use_ssl)
        self.timeout = float(timeout)
        self._conn_factory = conn_factory
        self.last_error = ""

    def _connect(self):
        if self._conn_factory is not None:
            return self._conn_factory()
        cls = imaplib.IMAP4_SSL if self.use_ssl else imaplib.IMAP4
        try:
            return cls(self.host, self.port, timeout=self.timeout)
        except TypeError:
            # Older signatures without a timeout kwarg.
            return cls(self.host, self.port)

    def list_recent(self, limit: int = 10, unread_only: bool = False) -> list[MailMessage]:
        limit = max(1, int(limit))
        connection = None
        try:
            connection = self._connect()
            connection.login(self.username, self.password)
            # readonly=True: summarizing the inbox must never mark mail as read.
            connection.select(self.folder, readonly=True)
            criteria = "UNSEEN" if unread_only else "ALL"
            status, data = connection.search(None, criteria)
            if status != "OK" or not data or not data[0]:
                return []
            uids = data[0].split()[-limit:]
            messages = []
            for uid in reversed(uids):
                try:
                    status, fetched = connection.fetch(uid, "(FLAGS BODY.PEEK[])")
                except Exception as exc:
                    logger.warning("[Mail] fetch failed for uid %s: %s", uid, exc)
                    continue
                if status != "OK" or not fetched or not isinstance(fetched[0], tuple):
                    continue
                messages.append(_parse_message(
                    uid.decode() if isinstance(uid, bytes) else str(uid),
                    fetched[0][1], fetched[0][0],
                ))
            return messages
        except Exception as exc:
            self.last_error = str(exc)
            logger.warning("[Mail] IMAP read failed: %s", exc)
            return []
        finally:
            if connection is not None:
                try:
                    connection.logout()
                except Exception as exc:
                    logger.debug("[Mail] logout failed: %s", exc)


def _parse_message(uid, raw: bytes, meta: bytes = b"") -> MailMessage:
    message = email.message_from_bytes(raw)
    subject = _header_text(message.get("Subject", ""))
    sender = _header_text(message.get("From", ""))
    date = _header_text(message.get("Date", ""))
    # The unread flag lives in the FETCH metadata, not in the message headers.
    unread = "\\Seen" not in (meta.decode("latin-1", "replace") if isinstance(meta, bytes) else str(meta))
    return MailMessage(
        uid=str(uid),
        subject=subject,
        sender=sender,
        date=date,
        unread=unread,
        snippet=_body_snippet(message),
    )


def _header_text(value) -> str:
    if not value:
        return ""
    try:
        return str(make_header(decode_header(value)))
    except Exception:
        return str(value)


def _body_snippet(message, limit: int = 200) -> str:
    try:
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True) or b""
                    return _clean(payload.decode(part.get_content_charset() or "utf-8", "replace"), limit)
            return ""
        payload = message.get_payload(decode=True) or b""
        return _clean(payload.decode(message.get_content_charset() or "utf-8", "replace"), limit)
    except Exception as exc:
        logger.debug("[Mail] body parse failed: %s", exc)
        return ""


def _clean(text: str, limit: int) -> str:
    collapsed = " ".join(str(text).split())
    return collapsed[:limit]


class Outbox:
    """Approval-gated outgoing mail. Nothing here sends anything."""

    def __init__(self, store):
        self._store = store

    def draft(self, to, subject, body, reason="") -> dict:
        to = str(to or "").strip()
        subject = str(subject or "").strip()
        body = str(body or "").strip()
        if not to or not subject:
            raise ValueError("draft requires a recipient and a subject")
        entry = {
            "id": "draft_" + uuid.uuid4().hex[:8],
            "to": to,
            "subject": subject[:200],
            "body": body[:5000],
            "reason": str(reason or "")[:300],
            "status": "needs_approval",
            "created_at": time.time(),
            "resolved_at": 0.0,
            "sent": False,
        }
        with self._store.transaction() as document:
            document.setdefault("drafts", {})[entry["id"]] = entry
        return dict(entry)

    def get(self, draft_id) -> dict | None:
        try:
            entry = (self._store.read().get("drafts") or {}).get(str(draft_id or ""))
        except Exception as exc:
            logger.warning("[Mail] draft read failed: %s", exc)
            return None
        return dict(entry) if entry else None

    def list(self, status=None) -> list[dict]:
        try:
            drafts = list((self._store.read().get("drafts") or {}).values())
        except Exception as exc:
            logger.warning("[Mail] draft list failed: %s", exc)
            return []
        if status:
            drafts = [d for d in drafts if d.get("status") == status]
        drafts.sort(key=lambda d: -float(d.get("created_at", 0)))
        return [dict(d) for d in drafts]

    def approve(self, draft_id) -> dict | None:
        return self._set_status(draft_id, "approved")

    def reject(self, draft_id) -> dict | None:
        return self._set_status(draft_id, "rejected")

    def send(self, draft_id) -> dict:
        """Refuse to send. Approval alone does not grant a transport."""
        draft = self.get(draft_id)
        if draft is None:
            return {"sent": False, "reason": f"unknown draft: {draft_id}"}
        if draft.get("status") != "approved":
            return {"sent": False, "reason": f"draft is {draft.get('status')}, not approved"}
        return {
            "sent": False,
            "reason": "no SMTP transport configured — approved drafts must be sent manually",
            "draft_id": draft["id"],
        }

    def _set_status(self, draft_id, status) -> dict | None:
        draft_id = str(draft_id or "")
        with self._store.transaction() as document:
            drafts = document.setdefault("drafts", {})
            entry = drafts.get(draft_id)
            if entry is None:
                return None
            entry["status"] = status
            entry["resolved_at"] = time.time()
        return dict(entry)

    def stats(self) -> dict:
        drafts = self.list()
        return {
            "total": len(drafts),
            "needs_approval": sum(1 for d in drafts if d.get("status") == "needs_approval"),
            "approved": sum(1 for d in drafts if d.get("status") == "approved"),
            "rejected": sum(1 for d in drafts if d.get("status") == "rejected"),
        }


__all__ = [
    "ImapMailbox",
    "MailboxSource",
    "MailMessage",
    "NullMailbox",
    "Outbox",
]
