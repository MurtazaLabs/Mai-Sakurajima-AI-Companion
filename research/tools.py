"""Tools for the research engine (read-only web, artifacts written in-sandbox)."""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _guard(name, handler):
    def wrapped(**kwargs):
        try:
            return handler(**kwargs)
        except Exception as exc:
            logger.error("[Research] tool %s failed: %s", name, exc)
            return {"error": str(exc), "tool": name}
    return wrapped


def register_research_tools(registry, engine) -> int:
    if registry is None or engine is None:
        return 0

    def _start(query="", depth="standard", urls=None):
        return engine.start(query=query, depth=depth, urls=urls)

    def _status():
        return engine.status()

    def _list(limit=20):
        return {"jobs": engine.list(limit=int(limit or 20))}

    def _report(job_id=""):
        return engine.report(job_id)

    registry.register(
        name="research_start",
        description="Start a background research job. Provide a query and/or seed URLs; "
                    "it fetches public pages, writes a note to the vault and reports back.",
        handler=_guard("research_start", _start),
        parameters={
            "query": {"type": "string", "description": "Research question"},
            "depth": {"type": "string", "description": "quick, standard or deep"},
            "urls": {"type": "array", "description": "Optional seed URLs"},
        },
        category="research",
    )
    registry.register(
        name="research_status",
        description="Research queue status (queued, running, done, ready reports).",
        handler=_guard("research_status", _status),
        parameters={},
        category="research",
    )
    registry.register(
        name="research_list",
        description="List recent research jobs with status and artifact paths.",
        handler=_guard("research_list", _list),
        parameters={
            "limit": {"type": "number", "description": "Maximum jobs (default 20)"},
        },
        category="research",
    )
    registry.register(
        name="research_report",
        description="Read a finished research report (marks it as reported).",
        handler=_guard("research_report", _report),
        parameters={
            "job_id": {"type": "string", "description": "Research job id"},
        },
        category="research",
    )
    return 4
