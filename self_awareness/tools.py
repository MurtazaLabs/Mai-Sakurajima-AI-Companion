# self_awareness/tools.py
"""Tool surface of the Self subsystem — read and diagnose only.

Every tool is a read: index/search/read own code, inspect health and errors,
run a diagnosis, read the report. No tool applies a patch, edits a file or
restarts a component; the roadmap boundary is the point.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _guard(name, handler):
    def wrapped(**kwargs):
        try:
            return handler(**kwargs)
        except ValueError as exc:
            return {"error": str(exc), "tool": name}
        except Exception as exc:
            logger.error("[Self] tool %s failed: %s", name, exc)
            return {"error": str(exc), "tool": name}
    return wrapped


def register_self_tools(registry, engine):
    """Register the self-awareness tools on a ToolRegistry."""
    if registry is None or engine is None:
        return 0

    def _status():
        return engine.status()

    def _diagnose():
        report = engine.diagnose()
        counts = report.get("counts") or {}
        return {
            "findings": report.get("findings") or [],
            "counts": counts,
            "healthy": bool(report.get("healthy")),
            "boundary": report.get("boundary"),
            "note": "read-only diagnosis — no fix is applied; proposals need your approval",
        }

    def _report():
        return {"text": engine.report()}

    def _index(query="", limit=10):
        hits = engine.search_code(query, limit=int(limit or 10))
        return {"query": query, "count": len(hits), "modules": hits}

    def _read_code(module, max_lines=400):
        return engine.read_code(module, max_lines=int(max_lines or 400))

    def _health():
        return engine.health()

    def _errors(limit=40):
        return engine.errors(limit=int(limit or 40))

    registry.register(
        name="self_status",
        description=(
            "Index coverage, health summary, last diagnosis and the "
            "read-only boundary of Mai's self-awareness."
        ),
        handler=_guard("self_status", _status),
        parameters={},
        category="self",
    )

    registry.register(
        name="self_index",
        description=(
            "Search Mai's own code index by module, class, function or docstring. "
            "Returns paths and modules; use self_read_code to read one."
        ),
        handler=_guard("self_index", _index),
        parameters={
            "query": {"type": "string", "description": "Module, symbol or phrase"},
            "limit": {"type": "number", "description": "Max hits"},
        },
        category="self",
    )

    registry.register(
        name="self_read_code",
        description=(
            "Read a module of Mai's own source (relative path or dotted module "
            "name). Read-only."
        ),
        handler=_guard("self_read_code", _read_code),
        parameters={
            "module": {"type": "string", "description": "e.g. voice/stt.py or voice.stt"},
            "max_lines": {"type": "number", "description": "Line budget (max 2000)"},
        },
        category="self",
    )

    registry.register(
        name="self_health",
        description="Component health from HealthRegistry: statuses, heartbeats and recent errors.",
        handler=_guard("self_health", _health),
        parameters={},
        category="self",
    )

    registry.register(
        name="self_errors",
        description=(
            "Recent ERROR/CRITICAL log lines, grouped by signature with counts "
            "and examples (tail of the app log)."
        ),
        handler=_guard("self_errors", _errors),
        parameters={
            "limit": {"type": "number", "description": "Max signatures"},
        },
        category="self",
    )

    registry.register(
        name="self_diagnose",
        description=(
            "Run a proactive self-diagnosis over health, logs and the code index. "
            "Findings carry proposals; nothing is fixed or restarted."
        ),
        handler=_guard("self_diagnose", _diagnose),
        parameters={},
        category="self",
    )

    registry.register(
        name="self_report",
        description="Read the last self-diagnosis report as text.",
        handler=_guard("self_report", _report),
        parameters={},
        category="self",
    )

    return 7
