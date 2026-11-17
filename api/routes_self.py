"""Self-awareness domain logic for the Mai API (T7).

Read-only surface: status, own-code search/read, health, errors and a diagnosis
run. There is deliberately no "apply fix" endpoint — the boundary is that she
diagnoses and the user approves.
"""
import logging
from typing import Any

from api.errors import safe_error

logger = logging.getLogger("api.server")


class SelfMixin:
    """Self-awareness inspection handlers."""

    self_awareness: Any = None
    brain: Any = None

    def _self_engine(self):
        engine = getattr(self, "self_awareness", None)
        if engine is None and self.brain is not None:
            engine = getattr(self.brain, "self_awareness", None)
        return engine

    def self_status(self):
        engine = self._self_engine()
        if engine is None:
            return {"error": "self_unavailable"}
        try:
            return engine.status()
        except Exception as e:
            logger.exception("[routes_self] status: %s", e)
            return {"error": safe_error(e)}

    def self_index(self, query="", limit=10):
        engine = self._self_engine()
        if engine is None:
            return {"error": "self_unavailable"}
        try:
            hits = engine.search_code(query, limit=int(limit or 10))
            return {"query": query, "count": len(hits), "modules": hits}
        except Exception as e:
            logger.exception("[routes_self] index: %s", e)
            return {"error": safe_error(e)}

    def self_code(self, module="", max_lines=400):
        engine = self._self_engine()
        if engine is None:
            return {"error": "self_unavailable"}
        try:
            return engine.read_code(module, max_lines=int(max_lines or 400))
        except Exception as e:
            logger.exception("[routes_self] code: %s", e)
            return {"error": safe_error(e)}

    def self_health(self):
        engine = self._self_engine()
        if engine is None:
            return {"error": "self_unavailable"}
        try:
            return engine.health()
        except Exception as e:
            logger.exception("[routes_self] health: %s", e)
            return {"error": safe_error(e)}

    def self_errors(self, limit=40):
        engine = self._self_engine()
        if engine is None:
            return {"error": "self_unavailable"}
        try:
            return engine.errors(limit=int(limit or 40))
        except Exception as e:
            logger.exception("[routes_self] errors: %s", e)
            return {"error": safe_error(e)}

    def self_diagnose(self):
        engine = self._self_engine()
        if engine is None:
            return {"error": "self_unavailable"}
        try:
            return engine.diagnose()
        except Exception as e:
            logger.exception("[routes_self] diagnose: %s", e)
            return {"error": safe_error(e)}

    def self_report(self):
        engine = self._self_engine()
        if engine is None:
            return {"error": "self_unavailable"}
        try:
            return {"text": engine.report()}
        except Exception as e:
            logger.exception("[routes_self] report: %s", e)
            return {"error": safe_error(e)}
