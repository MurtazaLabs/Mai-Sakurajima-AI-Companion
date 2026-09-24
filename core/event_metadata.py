"""Payload-safe metadata extraction for fabric telemetry records.

Phase 3 of the Event Inspector: enrich telemetry records with small,
non-domain context extracted from message payloads. Extraction is
allowlist-driven — only registered event-type prefixes produce metadata,
and each extractor may only emit values that are typed, bounded, and
never free-text user content. Whatever the registry emits is written into
the record's ``metadata`` field by :meth:`EventBus._record`; the Inspector
and export paths carry it without further interpretation.
"""
from __future__ import annotations

import threading
from typing import Any, Callable, Dict, Optional

# ── Allowlists (static, defensive) ────────────────────────────────
# Kept local to core/ to avoid layer breaches (agency/ imports are not
# allowed here). Subsystems may register richer extractors at boot via
# MetadataExtractorRegistry.register().

DEFAULT_TOOLS = frozenset({
    "get_brain_state", "set_emotion", "set_topic", "store_memory",
    "search_memories", "recall", "retrieve_knowledge", "get_beliefs",
    "update_belief", "reason", "execute_action", "get_execution_stats",
    "graph_query", "graph_search", "graph_reason", "obsidian_sync",
})

DEFAULT_EMOTIONS = frozenset({
    "happy", "sad", "angry", "neutral", "affection", "affectionate",
    "energy", "energetic", "stress", "stressed", "lonely", "annoyed",
})

DEFAULT_MEMORY_TYPES = frozenset({
    "semantic", "episodic", "autobiographical", "procedural",
    "working", "emotional",
})

DEFAULT_ACTIONS = frozenset({
    "open_app", "open_url", "search", "run_command", "type_text",
})

MAX_METADATA_KEYS = 6
MAX_VALUE_LEN = 64
MAX_ERROR_LEN = 200

# Keys a metadata dict may carry when leaving the Inspector. Mirrors the
# outputs of the default extractors; unknown keys are dropped at the read
# boundary even if a poisoned record smuggles them in.
SAFE_METADATA_KEYS = frozenset({
    "tool_name", "text_len", "emotion", "query_len", "result_count",
    "memory_type", "duration_ms", "success", "step_count", "level", "action",
})

# The only keys a telemetry record may carry when leaving the Inspector.
# ``depth`` is added by trace assembly; everything else mirrors the
# record shape built in EventBus._record(). Anything not listed here is
# dropped at every read boundary (queries, traces, export) — this is the
# enforcement point that guarantees payload content can never leak even
# if a future record shape regresses.
SAFE_RECORD_KEYS = frozenset({
    "id", "timestamp", "type", "version", "source", "target", "priority",
    "correlation_id", "causation_id", "outcome", "error", "attempt",
    "subscribers", "handler_times_ms", "handler_failures",
    "queue_delay_ms", "execution_ms", "metadata", "depth",
})


def _int_meta(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _text_len(value: Any) -> Optional[int]:
    return len(value) if isinstance(value, str) else None


def _speech(payload: dict) -> dict:
    """control.speech.* — utterance size and emotion label."""
    meta: dict = {}
    for key in ("text", "transcript"):
        n = _text_len(payload.get(key))
        if n is not None:
            meta["text_len"] = n
            break
    emotion = payload.get("emotion")
    if emotion in DEFAULT_EMOTIONS:
        meta["emotion"] = emotion
    return meta


def _memory(payload: dict) -> dict:
    """data.memory.* — query size, result count, memory layer."""
    meta: dict = {}
    q = _text_len(payload.get("query"))
    if q is not None:
        meta["query_len"] = q
    count = _int_meta(payload.get("result_count") or payload.get("count"))
    if count is not None:
        meta["result_count"] = count
    mtype = payload.get("memory_type")
    if mtype in DEFAULT_MEMORY_TYPES:
        meta["memory_type"] = mtype
    return meta


def _tool(payload: dict) -> dict:
    """data.tool.* — tool identity, duration, success."""
    meta: dict = {}
    name = payload.get("name") or payload.get("tool") or payload.get("tool_name")
    if name in DEFAULT_TOOLS:
        meta["tool_name"] = name
    duration = _int_meta(payload.get("duration") or payload.get("elapsed_ms"))
    if duration is not None:
        meta["duration_ms"] = duration
    ok = payload.get("success")
    if isinstance(ok, bool):
        meta["success"] = ok
    return meta


def _knowledge(payload: dict) -> dict:
    """data.knowledge.* — query size and result count."""
    meta: dict = {}
    q = _text_len(payload.get("query"))
    if q is not None:
        meta["query_len"] = q
    count = _int_meta(payload.get("result_count") or payload.get("count"))
    if count is not None:
        meta["result_count"] = count
    return meta


def _reasoning(payload: dict) -> dict:
    """control.reasoning.* — reasoning depth."""
    meta: dict = {}
    steps = _int_meta(payload.get("step_count") or payload.get("steps"))
    if steps is not None:
        meta["step_count"] = steps
    return meta


def _dream(payload: dict) -> dict:
    """dream.* — consolidation level (0-4)."""
    level = payload.get("level")
    if isinstance(level, int) and 0 <= level <= 4:
        return {"level": level}
    return {}


def _system(payload: dict) -> dict:
    """control.system.* — allowed action class."""
    action = payload.get("action")
    if action in DEFAULT_ACTIONS:
        return {"action": action}
    return {}


_DEFAULT_EXTRACTORS: Dict[str, Callable[[dict], dict]] = {
    "control.speech": _speech,
    "data.memory": _memory,
    "data.tool": _tool,
    "data.knowledge": _knowledge,
    "control.reasoning": _reasoning,
    "dream": _dream,
    "control.system": _system,
}


class MetadataExtractorRegistry:
    """Prefix-keyed extractors with an output safety filter.

    ``extract()`` is the hot path (called once per published message);
    it is a plain dict walk with no locks — the registry is configured at
    boot, before the fabric starts, and is not mutated at runtime.
    """

    def __init__(self, extractors: Optional[Dict[str, Callable[[dict], dict]]] = None):
        self._extractors: Dict[str, Callable[[dict], dict]] = dict(
            extractors if extractors is not None else _DEFAULT_EXTRACTORS
        )

    def register(self, prefix: str, extractor: Callable[[dict], dict]) -> None:
        """Register (or replace) an extractor for an event-type prefix."""
        self._extractors[prefix] = extractor

    def unregister(self, prefix: str) -> None:
        self._extractors.pop(prefix, None)

    def known_prefixes(self):
        return sorted(self._extractors)

    def extract(self, msg_type: str, payload: Any) -> dict:
        """Safe metadata for a message, or {} when no extractor matches."""
        if payload is None or not isinstance(payload, dict):
            return {}
        segments = msg_type.split(".")
        for cut in range(len(segments), 0, -1):
            extractor = self._extractors.get(".".join(segments[:cut]))
            if extractor is not None:
                try:
                    return self._sanitize(extractor(payload))
                except Exception:
                    return {}
        return {}

    @staticmethod
    def _sanitize(meta: dict) -> dict:
        """Defense-in-depth: typed, bounded, allowlist of known keys only."""
        out: dict = {}
        for key, value in meta.items():
            if len(out) >= MAX_METADATA_KEYS:
                break
            if not isinstance(key, str) or not key:
                continue
            if isinstance(value, str):
                if len(value) > MAX_VALUE_LEN:
                    continue
                if not value.isprintable():
                    continue
            elif isinstance(value, bool):
                pass
            elif isinstance(value, int):
                pass
            elif isinstance(value, float):
                pass
            else:
                continue
            out[key] = value
        return out


# Module-level default instance (project pattern: core/singletons).
_default_registry = MetadataExtractorRegistry()
_lock = threading.RLock()


def extract_metadata(msg_type: str, payload: Any) -> dict:
    """Module-level helper used by :meth:`EventBus._record`."""
    return _default_registry.extract(msg_type, payload)


def register_extractor(prefix: str, extractor: Callable[[dict], dict]) -> None:
    """Boot-time registration for subsystems with domain knowledge."""
    with _lock:
        _default_registry.register(prefix, extractor)


def sanitize_record(record: Any) -> dict:
    """Output boundary filter for telemetry records (Phase 4).

    Applies at every point a record leaves the Inspector (query, trace,
    export). Keeps only :data:`SAFE_RECORD_KEYS`; drops any payload or
    unknown key outright, truncates error text, coerces handler timings to
    floats, and re-runs metadata through the allowlist sanitizer. So even
    if a record in the buffer regresses to carry payload content, nothing
    on the wire or in the export can contain it.
    """
    if not isinstance(record, dict):
        return {}
    out: dict = {}
    for key in SAFE_RECORD_KEYS:
        if key not in record:
            continue
        value = record[key]
        if key == "error":
            if isinstance(value, str):
                if not value.isprintable():
                    value = "".join(c for c in value if c.isprintable())
                out[key] = value[:MAX_ERROR_LEN]
            elif value is None:
                out[key] = None
            else:
                out[key] = str(value)[:MAX_ERROR_LEN]
        elif key == "metadata":
            if isinstance(value, dict):
                out[key] = {
                    k: v for k, v in value.items()
                    if k in SAFE_METADATA_KEYS and _meta_value_ok(v)
                }
        elif key in ("subscribers", "handler_failures"):
            if isinstance(value, (list, tuple)):
                out[key] = [str(v)[:MAX_VALUE_LEN] for v in value]
        elif key == "handler_times_ms":
            if isinstance(value, dict):
                out[key] = {
                    str(k)[:MAX_VALUE_LEN]: float(v)
                    for k, v in value.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)
                }
        elif key == "priority":
            if isinstance(value, str):
                out[key] = value.upper()
        elif key in ("attempt", "depth", "version"):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                out[key] = int(value)
        elif key in ("timestamp", "queue_delay_ms", "execution_ms"):
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                out[key] = value
        elif key in ("id", "type", "source", "target",
                     "correlation_id", "causation_id", "outcome"):
            if value is None:
                out[key] = None
            elif isinstance(value, str):
                out[key] = value[:MAX_VALUE_LEN] if key != "id" else value[:128]
    return out


def _meta_value_ok(value: Any) -> bool:
    """Type gate for metadata values escaping via sanitize_record."""
    if isinstance(value, str):
        return len(value) <= MAX_VALUE_LEN and value.isprintable()
    return isinstance(value, (bool, int, float))
