# observability/event_inspector.py
"""Event Inspector — the observability surface of the Event Fabric.

The Inspector is a passive observer. It subscribes once to the fabric's
internal telemetry channel (``telemetry.inspector.record``) and keeps:

- A bounded ring buffer of live message records (the timeline)
- Per-event-type latency windows (p50/p95/p99)
- Per-subscriber handler statistics
- Fabric-derived health (queue saturation, failure spikes, dead letters)
- One-shot JSONL export to ``logs/inspector/``

It never mutates fabric state and never runs on the publish hot path beyond a
single ring-buffer append (capture < 100 us).

See ``docs/event-inspector-specification.md`` (v1.0).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from typing import Any, Callable, Dict, List, Optional

from core.event_bus import TELEMETRY_TOPIC
from core.event_metadata import sanitize_record

logger = logging.getLogger(__name__)

DEFAULT_CAPACITY = 10000
DEFAULT_LATENCY_WINDOW = 1000
DEFAULT_LOG_DIR = "logs/inspector"
DEFAULT_WINDOWS = (60, 300, 3600)  # summary rollup windows (s)

# Published (legacy, fire-and-forget) each time the ring buffer overflows —
# throttled to one event per OVERFLOW_THROTTLE_S.
OVERFLOW_TOPIC = "telemetry.inspector.overflow"
OVERFLOW_THROTTLE_S = 1.0

_OK = "ok"
_WARN = "warn"
_RED = "error"


def _percentile(sorted_values: List[float], pct: float) -> Optional[float]:
    if not sorted_values:
        return None
    idx = max(0, min(len(sorted_values) - 1, int(len(sorted_values) * pct / 100.0)))
    return round(sorted_values[idx], 3)


class EventInspector:
    """Ring-buffer store + view model for fabric telemetry."""

    def __init__(
        self,
        capacity: int = DEFAULT_CAPACITY,
        log_dir: str = DEFAULT_LOG_DIR,
        event_bus: Any = None,
        health_registry: Any = None,
    ):
        self.capacity = int(capacity)
        self.name = "event_inspector"
        self._log_dir = log_dir
        self._lock = threading.RLock()
        self._buffer: deque = deque(maxlen=self.capacity)
        self._type_latency: Dict[str, deque] = {}
        self._subscribers: Dict[str, Dict[str, Any]] = {}
        self._start_ts = time.time()
        self._last_capture = 0.0
        self._capture_count = 0
        self._overflow_count = 0
        self._last_overflow_ts = 0.0

        self.health_registry = health_registry
        if self.health_registry is not None:
            try:
                self.health_registry.register(self.name)
            except Exception as e:
                logger.debug("[Inspector] health register: %s", e)

        self.event_bus = event_bus
        if self.event_bus is not None:
            self.attach(self.event_bus)

        # Start periodic heartbeat to prevent "stalled" status when no telemetry
        self._hb_thread: Optional[threading.Thread] = None
        self._hb_stop = threading.Event()
        self._start_heartbeat()

    # ── Lifecycle ─────────────────────────────────────────────────

    def attach(self, event_bus: Any) -> Optional[Any]:
        """Subscribe to the fabric telemetry channel (idempotent)."""
        if event_bus is None or not hasattr(event_bus, "subscribe"):
            return None
        self.event_bus = event_bus
        try:
            return event_bus.subscribe(
                TELEMETRY_TOPIC, self._on_telemetry, receive_message=True
            )
        except Exception as e:
            logger.exception("[Inspector] attach: %s", e)
            return None

    def shutdown(self) -> None:
        self._stop_heartbeat()
        if self.health_registry is not None and self.name in self.health_registry:
            try:
                self.health_registry.unregister(self.name)
            except Exception:
                pass

    def _start_heartbeat(self) -> None:
        """Start background heartbeat thread to prevent 'stalled' status."""
        if self.health_registry is None:
            return
        self._hb_stop = threading.Event()
        self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True, name="EventInspector-HB")
        self._hb_thread.start()

    def _stop_heartbeat(self) -> None:
        if self._hb_thread is not None and self._hb_thread.is_alive():
            self._hb_stop.set()
            self._hb_thread.join(timeout=2.0)

    def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to health registry (every 10s)."""
        while not self._hb_stop.is_set():
            try:
                if self.health_registry is not None:
                    self.health_registry.heartbeat(self.name)
            except Exception:
                pass
            self._hb_stop.wait(10.0)

    # ── Capture (runs on a fabric worker thread) ──────────────────

    def _on_telemetry(self, msg: Any) -> None:
        record = msg.payload if isinstance(msg.payload, dict) else {}
        if not record.get("id"):
            return
        if record.get("type") == OVERFLOW_TOPIC:
            return  # meta-observability records are never re-captured (loop guard)
        now = time.time()
        should_notify_overflow = False
        with self._lock:
            if len(self._buffer) >= self.capacity:
                self._overflow_count += 1
                if now - self._last_overflow_ts >= OVERFLOW_THROTTLE_S:
                    self._last_overflow_ts = now
                    should_notify_overflow = True
            self._buffer.append(record)
            self._capture_count += 1
            self._last_capture = now
            self._accumulate_latency(
                record.get("type", "?"), record.get("execution_ms")
            )
            self._accumulate_subscribers(record)
        if should_notify_overflow:
            self._publish_overflow(record)
        if self.health_registry is not None:
            try:
                self.health_registry.heartbeat(self.name)
            except Exception:
                pass

    def _publish_overflow(self, dropped: Dict[str, Any]) -> None:
        if self.event_bus is None:
            return
        try:
            self.event_bus.publish(OVERFLOW_TOPIC, {
                "capacity": self.capacity,
                "overflow_total": self._overflow_count,
                "dropped_type": dropped.get("type"),
                "dropped_at": dropped.get("timestamp"),
            })
        except Exception as e:
            logger.debug("[Inspector] overflow publish: %s", e)

    def _accumulate_latency(self, event_type: str, execution_ms: Any) -> None:
        if execution_ms is None:
            return
        window = self._type_latency.get(event_type)
        if window is None:
            window = deque(maxlen=DEFAULT_LATENCY_WINDOW)
            self._type_latency[event_type] = window
        window.append(float(execution_ms))

    def _accumulate_subscribers(self, record: Dict[str, Any]) -> None:
        names = record.get("subscribers") or []
        failures = set(record.get("handler_failures") or [])
        times = record.get("handler_times_ms") or {}
        for name in names:
            entry = self._subscribers.get(name)
            if entry is None:
                entry = {
                    "count": 0,
                    "failures": 0,
                    "last_time": 0.0,
                    "durations": deque(maxlen=DEFAULT_LATENCY_WINDOW),
                    "types": defaultdict(int),
                }
                self._subscribers[name] = entry
            entry["count"] += 1
            entry["types"][record.get("type", "?")] += 1
            entry["last_time"] = record.get("timestamp") or time.time()
            if name in failures:
                entry["failures"] += 1
            duration = times.get(name)
            if duration is not None:
                entry["durations"].append(float(duration))

    # ── Timeline queries ──────────────────────────────────────────

    def records(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        """Timeline records, newest first. Passthrough filters."""
        filters = filters or {}
        with self._lock:
            items = list(reversed(self._buffer))
        result = []
        for rec in items:
            if self._matches(rec, filters):
                result.append(sanitize_record(rec))
        return result[offset:offset + max(1, int(limit))]

    @staticmethod
    def _matches(rec: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        for key, value in filters.items():
            if value is None:
                continue
            if key == "type" and not rec.get("type", "").startswith(value):
                return False
            elif key == "correlation_id" and rec.get("correlation_id") != value:
                return False
            elif key == "source" and rec.get("source") != value:
                return False
            elif key == "outcome" and rec.get("outcome") != value:
                return False
            elif key == "priority":
                expected = value.upper() if isinstance(value, str) else value
                if rec.get("priority") != expected:
                    return False
            elif key == "since" and rec.get("timestamp", 0) < value:
                return False
            elif key == "retries" and rec.get("attempt", 1) <= 1:
                return False
        return True

    def record(self, record_id: str) -> Optional[dict]:
        with self._lock:
            for rec in self._buffer:
                if rec.get("id") == record_id:
                    return sanitize_record(rec)
        return None

    # ── Correlation traces ────────────────────────────────────────

    def trace(self, correlation_id: str) -> Dict[str, Any]:
        """Reconstruct a conversation's causation tree from a correlation id.

        Returns nodes sorted by time, each with a ``depth`` (0 = root) and an
        ``attempt`` carried from the record. Retries appear as siblings under
        the same causation edge.
        """
        with self._lock:
            items = [
                rec for rec in self._buffer
                if rec.get("correlation_id") == correlation_id
            ]
        items.sort(key=lambda r: r.get("timestamp", 0.0))
        by_id = {r.get("id"): r for r in items}
        depth_map: Dict[str, int] = {}
        for rec in items:
            depth = 0
            cursor = rec.get("causation_id")
            hops = 0
            while cursor in by_id and hops < 64:
                depth += 1
                cursor = by_id[cursor].get("causation_id")
                hops += 1
            depth_map[rec.get("id")] = depth
        nodes = []
        for rec in items:
            node = dict(rec)
            node["depth"] = depth_map.get(rec.get("id"), 0)
            nodes.append(sanitize_record(node))
        return {
            "correlation_id": correlation_id,
            "count": len(nodes),
            "first_ts": items[0].get("timestamp") if items else None,
            "last_ts": items[-1].get("timestamp") if items else None,
            "nodes": nodes,
        }

    # ── Subscriber graph ──────────────────────────────────────────

    def subscriber_stats(self) -> List[dict]:
        rows = []
        with self._lock:
            for name, entry in sorted(self._subscribers.items()):
                durations = sorted(entry["durations"])
                rows.append({
                    "name": name,
                    "count": entry["count"],
                    "failures": entry["failures"],
                    "p50": _percentile(durations, 50),
                    "p95": _percentile(durations, 95),
                    "last_time": entry["last_time"],
                    "types": dict(sorted(entry["types"].items())),
                })
        return rows

    # ── Latency ───────────────────────────────────────────────────

    def latency(self, scope: str = "type") -> List[dict]:
        rows = []
        with self._lock:
            if scope == "subscriber":
                return self.subscriber_stats()
            for event_type, window in sorted(self._type_latency.items()):
                vals = sorted(window)
                rows.append({
                    "type": event_type,
                    "count": len(vals),
                    "p50": _percentile(vals, 50),
                    "p95": _percentile(vals, 95),
                    "p99": _percentile(vals, 99),
                })
        return rows

    # ── Queue + health ────────────────────────────────────────────

    def queue_snapshot(self) -> Dict[str, Any]:
        if self.event_bus is None:
            return {}
        try:
            stats = self.event_bus.stats()
            return stats.get("queue", {})
        except Exception as e:
            logger.debug("[Inspector] queue snapshot: %s", e)
            return {}

    def dead_letters(self, since: Optional[float] = None) -> List[dict]:
        if self.event_bus is None:
            return []
        try:
            items = self.event_bus.dead_letters()
        except Exception as e:
            logger.debug("[Inspector] dead letters: %s", e)
            return []
        if since is None:
            return items
        return [d for d in items if d.get("timestamp", 0) >= since]

    def fabric_health(self) -> Dict[str, Any]:
        """Derived fabric health, independent of the HealthRegistry."""
        now = time.time()
        window = self._window(300)
        total = len(window)
        failures = sum(1 for r in window if r.get("outcome") != "SUCCESS")
        failure_rate = (failures / total) if total else 0.0

        issues: List[str] = []
        warnings: List[str] = []
        queues = self.queue_snapshot()
        sat_level = 0
        for name, q in queues.items():
            maxq = q.get("max_queue", 0)
            occ = q.get("occupancy", 0)
            if maxq and occ > 0.8 * maxq:
                sat_level = max(sat_level, 1)
                warnings.append(f"queue:{name} saturated ({occ}/{maxq})")

        recent_dead = len(self.dead_letters(since=now - 300))
        if recent_dead:
            warnings.append(f"{recent_dead} dead letter(s) in last 5m")

        if total and failure_rate > 0.25:
            issues.append(f"failure rate {failure_rate:.0%} in last 5m")
        elif total and failure_rate > 0.05:
            warnings.append(f"failure rate {failure_rate:.0%} in last 5m")

        if self._last_capture and (now - self._last_capture) > 300:
            warnings.append("no fabric telemetry in last 5m")

        status = _RED if issues else (_WARN if warnings else _OK)
        return {
            "status": status,
            "issues": issues,
            "warnings": warnings,
            "window": window,
            "traffic": {
                "messages": total,
                "failures": failures,
                "failure_rate": round(failure_rate, 4),
            },
            "queue": queues,
            "dead_letters_5m": recent_dead,
        }

    def health(self) -> Dict[str, Any]:
        fabric = self.fabric_health()
        registry_stats = None
        if self.health_registry is not None:
            try:
                registry_stats = self.health_registry.stats()
            except Exception as e:
                logger.debug("[Inspector] health registry: %s", e)
        combined = _RED if fabric["status"] == _RED else \
            (_WARN if fabric["status"] == _WARN else _OK)
        return {
            "status": combined,
            "fabric": fabric,
            "components": registry_stats,
        }

    # ── Summary (cheap poll endpoint) ─────────────────────────────

    def summary(self) -> Dict[str, Any]:
        now = time.time()
        with self._lock:
            total_count = self._capture_count
            overflow = self._overflow_count
            buffered = len(self._buffer)
        counts = {}
        for win in DEFAULT_WINDOWS:
            snaps = self._window(win)
            counts[str(win)] = {
                "messages": len(snaps),
                "failures": sum(1 for r in snaps if r.get("outcome") != "SUCCESS"),
            }
        failed_total = sum(1 for r in self._window(300) if r.get("outcome") != "SUCCESS")
        total_300 = len(self._window(300))
        failure_rate = round(failed_total / total_300, 4) if total_300 else 0.0
        health = self.fabric_health()
        return {
            "status": health["status"],
            "capture_count": total_count,
            "buffered": buffered,
            "capacity": self.capacity,
            "overflow": overflow,
            "uptime_s": round(now - self._start_ts, 1),
            "last_capture": self._last_capture,
            "windows": counts,
            "failure_rate_5m": failure_rate,
            "queue": health["queue"],
            "dead_letters_5m": health["dead_letters_5m"],
            "warnings": health["warnings"],
            "issues": health["issues"],
        }

    # ── Export ────────────────────────────────────────────────────

    def export(self) -> Dict[str, Any]:
        """Write the current buffer to JSONL and clear it (blocking)."""
        os.makedirs(self._log_dir, exist_ok=True)
        filename = time.strftime("inspector-%Y%m%d-%H%M%S.jsonl")
        path = os.path.join(self._log_dir, filename)
        with self._lock:
            snapshot = list(self._buffer)
            self._buffer.clear()
        with open(path, "w", encoding="utf-8") as f:
            for rec in snapshot:
                f.write(json.dumps(sanitize_record(rec), default=str) + "\n")
        logger.info("[Inspector] Exported %d records to %s", len(snapshot), path)
        return {"path": path, "count": len(snapshot)}

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            subscribers = {
                name: entry["count"]
                for name, entry in self._subscribers.items()
            }
            return {
                "buffered": len(self._buffer),
                "capacity": self.capacity,
                "captured": self._capture_count,
                "overflow": self._overflow_count,
                "last_capture": self._last_capture,
                "event_types": len(self._type_latency),
                "subscribers": subscribers,
            }

    def _window(self, seconds: float) -> List[dict]:
        cutoff = time.time() - seconds
        with self._lock:
            return [
                rec for rec in self._buffer
                if (rec.get("timestamp") or 0.0) >= cutoff
            ]