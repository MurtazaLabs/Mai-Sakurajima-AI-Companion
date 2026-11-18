"""Research domain logic for the Mai API (T4)."""
import logging
from typing import Any

from api.errors import safe_error

logger = logging.getLogger("api.server")


class ResearchMixin:
    """Background research jobs: queue, status, reports, cancel."""

    research: Any = None
    brain: Any = None

    def _research_engine(self):
        engine = getattr(self, "research", None)
        if engine is None and self.brain is not None:
            engine = getattr(self.brain, "research", None)
        return engine

    def research_status(self):
        engine = self._research_engine()
        if engine is None:
            return {"error": "research_unavailable"}
        try:
            return engine.status()
        except Exception as exc:
            logger.exception("[routes_research] status: %s", exc)
            return {"error": safe_error(exc)}

    def research_list(self, limit=20):
        engine = self._research_engine()
        if engine is None:
            return {"error": "research_unavailable"}
        try:
            return {"jobs": engine.list(limit=int(limit or 20))}
        except Exception as exc:
            logger.exception("[routes_research] list: %s", exc)
            return {"error": safe_error(exc)}

    def research_get(self, job_id):
        engine = self._research_engine()
        if engine is None:
            return {"error": "research_unavailable"}
        try:
            job = engine.get(job_id)
            return job if job is not None else {"error": "unknown_job"}
        except Exception as exc:
            logger.exception("[routes_research] get: %s", exc)
            return {"error": safe_error(exc)}

    def research_start(self, query="", depth="standard", urls=None):
        engine = self._research_engine()
        if engine is None:
            return {"error": "research_unavailable"}
        try:
            return engine.start(query=query, depth=depth, urls=urls or [])
        except Exception as exc:
            logger.exception("[routes_research] start: %s", exc)
            return {"error": safe_error(exc)}

    def research_cancel(self, job_id):
        engine = self._research_engine()
        if engine is None:
            return {"error": "research_unavailable"}
        try:
            return engine.cancel(job_id)
        except Exception as exc:
            logger.exception("[routes_research] cancel: %s", exc)
            return {"error": safe_error(exc)}

    def research_report(self, job_id):
        engine = self._research_engine()
        if engine is None:
            return {"error": "research_unavailable"}
        try:
            return engine.report(job_id)
        except Exception as exc:
            logger.exception("[routes_research] report: %s", exc)
            return {"error": safe_error(exc)}
