# self_awareness/engine.py
"""T7 Self — the facade over the index, the feeds and the diagnosis.

``tick()`` is what the scheduler calls during idle time: refresh the code index
(cheap, incremental), then diagnose health + logs since the last check. Every
finding is a proposal; nothing here edits code or restarts a component.

The engine is intentionally not a second source of truth: health comes from
``HealthRegistry``, errors come from the log and the registry, code facts come
from ``ast``. It only reads them.
"""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path

from config import self_awareness as cfg
from core.event_specs import SELF_DIAGNOSIS, SELF_INDEX_BUILT, STATE_SELF_UPDATED
from self_awareness.code_index import OwnCodeIndex
from self_awareness.diagnosis import BOUNDARY, SelfDiagnosis
from self_awareness.feeds import HealthErrorFeeds

logger = logging.getLogger(__name__)


class SelfAwarenessEngine:

    def __init__(self, root=None, store_dir=None, event_bus=None,
                 health_registry=None, log_path=None,
                 diagnosis_interval=None, error_threshold=None,
                 error_limit=None, max_log_bytes=None, excludes=None,
                 max_modules=None, clock=None):
        self.root = Path(root or cfg.ROOT_DIR)
        self.store_dir = Path(store_dir or (self.root / "data" / "self_awareness"))
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.event_bus = event_bus
        self.interval = float(
            cfg.SELF_DIAGNOSIS_INTERVAL if diagnosis_interval is None else diagnosis_interval
        )
        self._clock = clock or time.time
        self._lock = threading.RLock()
        self._last_run = 0.0
        self._last_index: dict = {}

        self.index = OwnCodeIndex(
            root=self.root,
            store_path=self.store_dir / "code_index.json",
            excludes=cfg.SELF_INDEX_EXCLUDES if excludes is None else excludes,
            max_modules=cfg.SELF_MAX_MODULES if max_modules is None else max_modules,
        )
        self.feeds = HealthErrorFeeds(
            health_registry=health_registry,
            log_path=cfg.SELF_LOG_PATH if log_path is None else log_path,
            max_log_bytes=cfg.SELF_MAX_LOG_BYTES if max_log_bytes is None else max_log_bytes,
            error_limit=cfg.SELF_ERROR_LIMIT if error_limit is None else error_limit,
        )
        self.diagnosis = SelfDiagnosis(
            index=self.index,
            feeds=self.feeds,
            store_path=self.store_dir / "diagnoses.jsonl",
            error_threshold=cfg.SELF_ERROR_THRESHOLD if error_threshold is None else error_threshold,
        )

    # -- index -------------------------------------------------------

    def refresh_index(self, force: bool = False) -> dict:
        summary = self.index.refresh(force=force)
        with self._lock:
            self._last_index = summary
        self._publish(SELF_INDEX_BUILT, {
            "modules": summary["modules"],
            "changed": summary["changed"] + summary["added"],
            "parse_errors": summary["parse_errors"],
        })
        self.publish()
        return summary

    def search_code(self, query: str, limit: int = 10) -> list[dict]:
        return self.index.search(query, limit=limit)

    def read_code(self, module: str, max_lines: int = 400) -> dict:
        return self.index.read_module(module, max_lines=max_lines)

    # -- feeds -------------------------------------------------------

    def health(self) -> dict:
        return self.feeds.health()

    def errors(self, limit: int | None = None) -> dict:
        return self.feeds.recent_errors(limit=limit)

    # -- diagnosis ---------------------------------------------------

    def diagnose(self, refresh: bool = False) -> dict:
        if refresh:
            self.refresh_index()
        report = self.diagnosis.analyze()
        with self._lock:
            self._last_run = self._clock()
        counts = report.get("counts") or {}
        self._publish(SELF_DIAGNOSIS, {
            "findings": len(report.get("findings") or []),
            "error": counts.get("error", 0),
            "warn": counts.get("warn", 0),
            "healthy": bool(report.get("healthy")),
        })
        self.publish()
        return report

    def tick(self, now: float | None = None) -> dict:
        """Idle-time proactive check. No-op until the interval has elapsed."""
        now = self._clock() if now is None else float(now)
        with self._lock:
            last = self._last_run
        if last and (now - last) < self.interval:
            return {"diagnosed": False, "reason": "not_due", "checked_at": now}
        index = self.refresh_index()
        report = self.diagnose()
        # Record the caller's clock (diagnose() stamps wall time, which would
        # make a deterministic tick schedule look premature).
        with self._lock:
            self._last_run = now
        return {
            "diagnosed": True,
            "findings": len(report.get("findings") or []),
            "healthy": bool(report.get("healthy")),
            "modules": index.get("modules", 0),
            "checked_at": now,
        }

    # -- presentation ------------------------------------------------

    def brief_line(self) -> str:
        """One sentence for the ritual briefing (cheap: no scan, no parse)."""
        index = self.index.stats()
        health = self.feeds.health()
        summary = health.get("summary") or {}
        unhealthy = health.get("unhealthy") or []
        last = self.diagnosis.summary()
        if unhealthy:
            names = ", ".join(
                f"{item.get('name')}:{item.get('status')}" for item in unhealthy[:3]
            )
            head = f"Self-check: {names}"
        elif not health.get("available"):
            head = "Self-check: health registry unavailable"
        else:
            head = f"Self-check: {summary.get('ok', 0)}/{summary.get('total', 0)} components ok"
        tail = f"{index.get('modules', 0)} modules indexed"
        if last.get("findings"):
            tail += f", last diagnosis found {last['findings']}"
        if last.get("counts", {}).get("error"):
            tail += f" ({last['counts']['error']} error)"
        return f"{head}; {tail}. Read-only — fixes wait for your approval."

    def report(self) -> str:
        return self.diagnosis.report_text()

    # -- status / events ---------------------------------------------

    def status(self) -> dict:
        health = self.feeds.health()
        return {
            "boundary": BOUNDARY,
            "index": self.index.stats(),
            "last_index": dict(self._last_index),
            "health": {
                "available": health.get("available", False),
                "summary": health.get("summary", {}),
                "unhealthy": health.get("unhealthy", []),
            },
            "diagnosis": self.diagnosis.summary(),
            "interval": self.interval,
            "last_run": self._last_run,
        }

    def publish(self) -> None:
        if not self.event_bus:
            return
        try:
            health = self.feeds.health()
            summary = health.get("summary") or {}
            last = self.diagnosis.summary()
            self._publish(STATE_SELF_UPDATED, {
                "healthy": bool(last.get("healthy", True)),
                "unhealthy": len(health.get("unhealthy") or []),
                "components": summary.get("total", 0),
                "modules": self.index.stats().get("modules", 0),
                "findings": last.get("findings", 0),
            })
        except Exception as exc:
            logger.warning("[Self] state publish failed: %s", exc)

    def _publish(self, event_type: str, payload: dict) -> None:
        if not self.event_bus:
            return
        try:
            from core.mai_message import publish_event
            publish_event(self.event_bus, event_type, payload, source="self")
        except Exception as exc:
            logger.warning("[Self] event publish failed (%s): %s", event_type, exc)


__all__ = ["SelfAwarenessEngine"]
