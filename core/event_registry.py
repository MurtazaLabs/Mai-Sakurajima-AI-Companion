# core/event_registry.py
"""Event Registry — the single source of truth for every event type.

Each event type is declared once (publisher, consumers, version, retry
policy, priority). The registry then serves:

- Validation (is this event type known? is the version supported?)
- Retry policy lookup for the EventBus
- Capabilities matrix generation (who publishes/consumes what)
- Namespace classification (control.* / data.* / state.*)

See ``docs/event-fabric-architecture.md`` (v2.1) for the full design.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ── Semantic namespaces ───────────────────────────────────────────

CONTROL = "control"   # intent / commands
DATA = "data"         # information
STATE = "state"       # truth / persisted state

NAMESPACES = (CONTROL, DATA, STATE)


def namespace_of(event_type: str) -> str:
    """Classify an event type into control / data / state / legacy."""
    first = str(event_type).split(".", 1)[0]
    if first in NAMESPACES:
        return first
    return "legacy"


def is_semantic(event_type: str) -> bool:
    """True when the event type uses a semantic namespace prefix."""
    return namespace_of(event_type) != "legacy"


# ── Retry policies ────────────────────────────────────────────────

NEVER = "never"              # single attempt, failure recorded
IMMEDIATE = "immediate"      # retry without delay up to max_attempts
EXPONENTIAL = "exponential"  # retry with 2^n backoff up to max_attempts
DEAD_LETTER = "dead_letter"  # after max_attempts, move to dead-letter list
IGNORE = "ignore"            # swallow failures, no retry, no dead letter


class RetryPolicy(str, Enum):
    NEVER = NEVER
    IMMEDIATE = IMMEDIATE
    EXPONENTIAL = EXPONENTIAL
    DEAD_LETTER = DEAD_LETTER
    IGNORE = IGNORE

    @classmethod
    def resolve(cls, value: Any) -> RetryPolicy:
        if isinstance(value, RetryPolicy):
            return value
        try:
            return cls(str(value).lower())
        except ValueError:
            return cls.NEVER


# ── Event specification ───────────────────────────────────────────


@dataclass
class EventSpec:
    """Declaration of one event type."""

    name: str
    version: int = 1
    description: str = ""
    publisher: str = ""
    publishers: tuple[str, ...] = ()
    consumers: list[str] = field(default_factory=list)
    priority: str = "normal"
    retry: RetryPolicy = RetryPolicy.NEVER
    max_attempts: int = 1
    payload_keys: tuple[str, ...] = ()
    supported_versions: tuple[int, ...] = ()
    compressed: bool = False

    def __post_init__(self) -> None:
        self.retry = RetryPolicy.resolve(self.retry)
        self.priority = self.priority.lower()

    @property
    def namespace(self) -> str:
        return namespace_of(self.name)

    @property
    def versions(self) -> tuple[int, ...]:
        if self.supported_versions:
            return tuple(self.supported_versions)
        return (self.version,)

    @property
    def allowed_publishers(self) -> tuple[str, ...]:
        """Subsystems allowed to publish this event (``publishers`` wins)."""
        if self.publishers:
            return tuple(self.publishers)
        if self.publisher:
            return (self.publisher,)
        return ()


class EventRegistry:
    """Thread-safe registry of declared event types."""

    def __init__(self) -> None:
        self._specs: dict[str, EventSpec] = {}
        self._lock = threading.RLock()

    def register(self, spec: EventSpec, replace: bool = False) -> EventSpec:
        """Register an event type. Raises ValueError on conflict.

        Re-registering an identical spec is idempotent. Re-registering the
        same name with different content requires ``replace=True``.
        """
        if not isinstance(spec, EventSpec):
            raise TypeError("Expected an EventSpec")
        if not spec.name:
            raise ValueError("EventSpec.name is required")
        with self._lock:
            existing = self._specs.get(spec.name)
            if existing is not None and not replace:
                if existing != spec:
                    raise ValueError(
                        f"Event type '{spec.name}' already registered with "
                        f"different content (version {existing.version}). "
                        f"Use replace=True to override."
                    )
                return existing
            self._specs[spec.name] = spec
        return spec

    def register_many(self, specs: list[EventSpec]) -> int:
        count = 0
        for spec in specs:
            self.register(spec)
            count += 1
        return count

    def get(self, name: str, default: Any = None) -> EventSpec | None:
        with self._lock:
            return self._specs.get(name, default)

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._specs

    def all_events(self) -> list[EventSpec]:
        with self._lock:
            return sorted(self._specs.values(), key=lambda s: s.name)

    def supports_version(self, name: str, version: int) -> bool:
        spec = self.get(name)
        if spec is None:
            return False
        return version in spec.versions

    def retry_policy(self, name: str) -> tuple[RetryPolicy, int]:
        """Return (policy, max_attempts) for an event type."""
        spec = self.get(name)
        if spec is None:
            return RetryPolicy.NEVER, 1
        return spec.retry, max(1, spec.max_attempts)

    def can_publish(self, source: str, name: str) -> bool:
        """Capabilities check: may ``source`` publish ``name``?

        Unregistered events and events with no declared publisher are
        open (authorization is opt-in per event type). A declared
        publisher set is enforced strictly.
        """
        spec = self.get(name)
        if spec is None:
            return True
        allowed = spec.allowed_publishers
        if not allowed:
            return True
        return bool(source) and source in allowed

    def capabilities_matrix(self) -> list[dict[str, Any]]:
        """Living documentation: who publishes/consumes what, with policies."""
        rows = []
        for spec in self.all_events():
            rows.append({
                "name": spec.name,
                "version": spec.version,
                "supported_versions": list(spec.versions),
                "namespace": spec.namespace,
                "publisher": spec.publisher,
                "publishers": list(spec.allowed_publishers),
                "consumers": list(spec.consumers),
                "priority": spec.priority,
                "retry": spec.retry.value,
                "max_attempts": spec.max_attempts,
                "compressed": spec.compressed,
                "description": spec.description,
            })
        return rows

    def to_markdown(self) -> str:
        """Render the registry as a Markdown capabilities matrix.

        The output is a sliceable, diffable form of ``capabilities_matrix()``
        suitable for checking into the docs folder.
        """
        rows = self.capabilities_matrix()
        lines = [
            "# Event Registry — Capabilities Matrix",
            "",
            "_Generated from EventRegistry.to_markdown(). Do not edit by hand._",
            "",
        ]
        if not rows:
            lines.append("*(no event types registered)*")
            return "\n".join(lines) + "\n"
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["namespace"]] = counts.get(row["namespace"], 0) + 1
        lines.append(
            f"**{len(rows)} event types** — "
            + " · ".join(f"{ns}: {n}" for ns, n in sorted(counts.items()))
            + "\n"
        )
        lines.append("| Event | Version | Namespace | Publishers | Consumers | Priority | Retry | Compressed | Description |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for row in rows:
            pubs = ", ".join(row["publishers"]) or "—"
            cons = ", ".join(row["consumers"]) or "—"
            desc = row["description"].replace("|", "\\|") or "—"
            lines.append(
                f"| `{row['name']}` | {row['version']} | {row['namespace']} "
                f"| {pubs} | {cons} | {row['priority']} | {row['retry']} "
                f"| {'yes' if row['compressed'] else ''} | {desc} |"
            )
        return "\n".join(lines) + "\n"

    def summary(self) -> dict[str, Any]:
        specs = self.all_events()
        by_ns: dict[str, int] = {}
        for spec in specs:
            by_ns[spec.namespace] = by_ns.get(spec.namespace, 0) + 1
        return {
            "total": len(specs),
            "namespaces": by_ns,
            "publishers": sorted({s.publisher for s in specs if s.publisher}),
        }
