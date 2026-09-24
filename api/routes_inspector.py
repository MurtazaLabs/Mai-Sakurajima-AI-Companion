"""Event Inspector domain logic for the Mai API.

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for route registration and ``api.static_serving``
for the web page.
"""
import logging
from typing import Any, Dict, Optional
from api.errors import safe_error

logger = logging.getLogger("api.server")


class InspectorMixin:
    """Event Fabric observability endpoints (timeline, traces, stats, health)."""

    # Set by MaiAPI at runtime — declared here for type checker
    inspector: Any = None
    event_bus: Any = None

    # ── Helpers ──────────────────────────────────────────────────

    def _inspector_or_empty(self):
        if self.inspector is not None:
            return self.inspector
        return None

    # ── Endpoint handlers ─────────────────────────────────────────

    def inspector_records(self, filters: Optional[Dict[str, Any]] = None,
                          limit: int = 100, offset: int = 0):
        inspector = self._inspector_or_empty()
        if inspector is None:
            return {"records": [], "total": 0}
        try:
            records = inspector.records(filters=filters, limit=limit, offset=offset)
            return {"records": records, "total": len(records)}
        except Exception as e:
            logger.exception("[Inspector] records: %s", e)
            return {"records": [], "total": 0, "error": safe_error(e)}

    def inspector_record(self, record_id: str):
        inspector = self._inspector_or_empty()
        if inspector is None:
            return {"record": None}
        try:
            return {"record": inspector.record(record_id)}
        except Exception as e:
            logger.exception("[Inspector] record: %s", e)
            return {"record": None, "error": safe_error(e)}

    def inspector_trace(self, correlation_id: str):
        inspector = self._inspector_or_empty()
        if inspector is None:
            return {"correlation_id": correlation_id, "count": 0, "nodes": []}
        try:
            return inspector.trace(correlation_id)
        except Exception as e:
            logger.exception("[Inspector] trace: %s", e)
            return {"correlation_id": correlation_id, "count": 0, "nodes": [], "error": safe_error(e)}

    def inspector_subscribers(self):
        inspector = self._inspector_or_empty()
        if inspector is None:
            return {"subscribers": []}
        try:
            return {"subscribers": inspector.subscriber_stats()}
        except Exception as e:
            logger.exception("[Inspector] subscribers: %s", e)
            return {"subscribers": [], "error": safe_error(e)}

    def inspector_queues(self):
        inspector = self._inspector_or_empty()
        if inspector is None:
            return {"queues": {}}
        try:
            return {"queues": inspector.queue_snapshot()}
        except Exception as e:
            logger.exception("[Inspector] queues: %s", e)
            return {"queues": {}, "error": safe_error(e)}

    def inspector_dead_letters(self, since: Optional[float] = None):
        inspector = self._inspector_or_empty()
        if inspector is None:
            return {"dead_letters": [], "total": 0}
        try:
            items = inspector.dead_letters(since=since)
            return {"dead_letters": items, "total": len(items)}
        except Exception as e:
            logger.exception("[Inspector] dead letters: %s", e)
            return {"dead_letters": [], "total": 0, "error": safe_error(e)}

    def inspector_latency(self, scope: str = "type"):
        inspector = self._inspector_or_empty()
        if inspector is None:
            return {"latency": []}
        try:
            return {"latency": inspector.latency(scope=scope)}
        except Exception as e:
            logger.exception("[Inspector] latency: %s", e)
            return {"latency": [], "error": safe_error(e)}

    def inspector_health(self):
        inspector = self._inspector_or_empty()
        if inspector is None:
            return {"status": "unavailable", "fabric": {}, "components": None}
        try:
            return inspector.health()
        except Exception as e:
            logger.exception("[Inspector] health: %s", e)
            return {"status": "error", "error": safe_error(e)}

    def inspector_summary(self):
        inspector = self._inspector_or_empty()
        if inspector is None:
            return {"status": "unavailable", "buffered": 0}
        try:
            return inspector.summary()
        except Exception as e:
            logger.exception("[Inspector] summary: %s", e)
            return {"status": "error", "error": safe_error(e)}

    def inspector_export(self):
        inspector = self._inspector_or_empty()
        if inspector is None:
            return {"error": "no_inspector"}
        try:
            return inspector.export()
        except Exception as e:
            logger.exception("[Inspector] export: %s", e)
            return {"error": safe_error(e)}
