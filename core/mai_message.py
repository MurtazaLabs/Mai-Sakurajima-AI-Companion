# core/mai_message.py
"""MaiMessage envelope — the single message schema of the Event Fabric.

The envelope standardizes cross-subsystem communication:

- One schema for every message (`MaiMessage`)
- Priority scheduling levels (`Priority`)
- Correlation propagation via thread-local scope (`correlation_scope`)
- Legacy adapter for the existing ad-hoc ``publish(topic, dict)`` sites

See ``docs/event-fabric-architecture.md`` (v2.1) for the full design.
"""
from __future__ import annotations

import logging
import secrets
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class Priority(IntEnum):
    """Scheduling priority. Lower value = higher priority."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


PRIORITY_LEVELS = list(Priority)


def _resolve_priority(value: Any) -> Priority:
    """Coerce str/int/Priority input to a Priority, defaulting to NORMAL."""
    if isinstance(value, Priority):
        return value
    if isinstance(value, bool):
        return Priority.NORMAL
    if isinstance(value, int):
        try:
            return Priority(value)
        except ValueError:
            return Priority.NORMAL
    if isinstance(value, str):
        try:
            return Priority[value.strip().upper()]
        except (KeyError, AttributeError):
            return Priority.NORMAL
    return Priority.NORMAL


def new_message_id() -> str:
    """Generate a short unique message id (``msg_xxxxxxxx``)."""
    return "msg_" + secrets.token_hex(4)


def new_correlation_id() -> str:
    """Generate a conversation correlation id (``conversation_xxxxxxxxxxxx``)."""
    return "conversation_" + secrets.token_hex(6)


# ── Thread-local correlation context ──────────────────────────────

_local = threading.local()


def set_correlation(correlation_id: str | None) -> None:
    """Set the correlation id inherited by messages published on this thread."""
    _local.correlation_id = correlation_id


def clear_correlation() -> None:
    """Clear the thread-local correlation id."""
    _local.correlation_id = None


def current_correlation_id() -> str | None:
    """Return the active correlation id on this thread, or None."""
    return getattr(_local, "correlation_id", None)


@contextmanager
def ensure_correlation(prefix: str = "operation") -> Iterator[str]:
    """Context manager: yield the active correlation id, seeding one for the
    duration of the block if this thread has none.

    Used at subsystem entry points (memory store, voice listen) so every
    message produced by an operation carries a stable correlation id even
    when the operation runs outside a Brain conversation scope. The
    previous thread-local value is restored on exit (leak-free).
    """
    previous = current_correlation_id()
    if previous:
        yield previous
        return
    cid = f"{prefix}_" + secrets.token_hex(6)
    set_correlation(cid)
    try:
        yield cid
    finally:
        clear_correlation()


class correlation_scope:
    """Context manager that scopes correlation propagation.

    Every ``MaiMessage`` created inside the scope inherits the correlation
    id (unless it carries its own). The previous thread-local value is
    restored on exit.

    Usage::

        with correlation_scope("conversation_abc"):
            bus.publish("control.memory.store", {...})   # inherits cid
    """

    def __init__(self, correlation_id: str | None = None):
        self._provided = correlation_id
        self._previous = None

    def __enter__(self) -> str:
        self._previous = current_correlation_id()
        if self._provided:
            set_correlation(self._provided)
        elif self._previous is None:
            set_correlation(new_correlation_id())
        return current_correlation_id()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._previous is None:
            clear_correlation()
        else:
            set_correlation(self._previous)


# ── Envelope ──────────────────────────────────────────────────────


@dataclass
class MaiMessage:
    """The Event Fabric envelope.

    Attributes:
        type: Semantic topic (e.g. ``control.memory.store``).
        payload: Domain data (dict).
        id: Unique message id (auto-generated if omitted).
        timestamp: Epoch seconds (auto-set if omitted).
        version: Payload version. Legacy messages are version 0.
        source: Publishing subsystem (e.g. ``reasoning``).
        target: Intended subsystem (empty = broadcast).
        priority: Scheduling priority (default NORMAL).
        correlation_id: Conversation correlation id (inherits thread-local).
        causation_id: Id of the message that caused this one.
        metadata: Non-domain context (retry count, latency, fabric fields).
    """

    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    id: str | None = None
    timestamp: float | None = None
    version: int = 1
    source: str = ""
    target: str = ""
    priority: Priority = Priority.NORMAL
    correlation_id: str | None = None
    causation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.type:
            raise ValueError("MaiMessage.type is required")
        if not self.id:
            self.id = new_message_id()
        if self.timestamp is None:
            self.timestamp = time.time()
        self.priority = _resolve_priority(self.priority)
        if not self.correlation_id:
            self.correlation_id = current_correlation_id()
        if not isinstance(self.payload, dict):
            self.payload = {"value": self.payload}

    @property
    def is_legacy(self) -> bool:
        """True when wrapped from the legacy ``(topic, dict)`` call style."""
        return self.metadata.get("legacy", False) or self.version == 0

    @property
    def namespace(self) -> str:
        """control / data / state / legacy namespace of the topic."""
        first = self.type.split(".", 1)[0]
        if first in ("control", "data", "state"):
            return first
        return "legacy"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "type": self.type,
            "version": self.version,
            "source": self.source,
            "target": self.target,
            "priority": self.priority.name,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "payload": self.payload,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MaiMessage:
        data = dict(data or {})
        priority = _resolve_priority(data.pop("priority", "NORMAL"))
        msg = cls(**data)
        msg.priority = priority
        return msg

    def reply(
        self,
        payload: dict[str, Any] | None = None,
        type: str | None = None,
        target: str | None = None,
        priority: Any = None,
    ) -> MaiMessage:
        """Create a reply message linked via ``causation_id``."""
        return MaiMessage(
            type=type or self.type,
            payload=payload if payload is not None else {},
            source=self.target or "system",
            target=target or self.source,
            priority=_resolve_priority(priority) if priority is not None else self.priority,
            correlation_id=self.correlation_id,
            causation_id=self.id,
        )


def legacy_message(topic: str, data: dict[str, Any] | None = None,
                   source: str = "", correlation_id: str | None = None) -> MaiMessage:
    """Wrap a legacy ``(topic, dict)`` publish into a MaiMessage (version 0)."""
    msg = MaiMessage(
        type=topic,
        payload=data if data is not None else {},
        version=0,
        source=source,
    )
    msg.metadata["legacy"] = True
    if correlation_id:
        msg.correlation_id = correlation_id
    return msg


def publish_event(bus, event_type: str, payload: dict[str, Any] | None = None,
                  source: str = "") -> None:
    """Fabric publish of a semantic event.

    Wraps ``payload`` in a :class:`MaiMessage` (version 1) and dispatches
    synchronously (``wait=True``) so ordering and block-on-dispatch semantics
    are identical to the legacy ``publish(topic, data)`` call. The ``source``
    is required for registered events — the authorization middleware rejects
    anonymous publishers.
    """
    bus.publish_message(
        MaiMessage(
            type=event_type,
            payload=payload if payload is not None else {},
            source=source,
        ),
        wait=True,
    )
