# self_awareness/feeds.py
"""Health and error feeds — what the system already knows, made readable.

Two sources, both read-only:

- ``HealthRegistry``: component status, heartbeats, per-component errors.
- The application log: ERROR/CRITICAL lines, grouped into signatures so "STT
  failed to load" three times is one finding, not three log lines.

Nothing here writes, rotates or truncates a log.
"""
from __future__ import annotations

import logging
import re
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_LEVEL_RE = re.compile(r"\b(ERROR|CRITICAL)\b")
_TRACEBACK = "Traceback (most recent call last)"
_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T][\d:,\.]+\s*[|]?\s*")
_LEVEL_TOKEN_RE = re.compile(r"^\s*(ERROR|CRITICAL|WARNING|INFO|DEBUG)\s*[|]?\s*")
_DIGITS_RE = re.compile(r"\d+")


class HealthErrorFeeds:

    def __init__(self, health_registry=None, log_path=None, max_log_bytes=512 * 1024,
                 error_limit=40):
        self.health_registry = health_registry
        self.log_path = Path(log_path) if log_path else None
        self.max_log_bytes = max(4096, int(max_log_bytes))
        self.error_limit = max(1, int(error_limit))

    # -- health ------------------------------------------------------

    def health(self) -> dict:
        registry = self.health_registry
        if registry is None:
            return {
                "available": False,
                "components": {},
                "summary": {"total": 0, "ok": 0, "warn": 0, "error": 0, "stalled": 0},
                "unhealthy": [],
                "errors": [],
            }
        try:
            snapshot = registry.stats()
        except Exception as exc:
            logger.warning("[SelfFeeds] health snapshot failed: %s", exc)
            return {"available": False, "error": str(exc), "components": {},
                    "summary": {}, "unhealthy": [], "errors": []}
        components = snapshot.get("components") or {}
        unhealthy = [
            {"name": name, **details}
            for name, details in sorted(components.items())
            if details.get("status") in ("warn", "error", "stalled")
        ]
        try:
            errors = registry.recent_errors(self.error_limit)
        except Exception as exc:
            logger.debug("[SelfFeeds] registry errors unavailable: %s", exc)
            errors = []
        return {
            "available": True,
            "components": components,
            "summary": snapshot.get("summary") or {},
            "unhealthy": unhealthy,
            "errors": errors,
        }

    # -- log tail ----------------------------------------------------

    def _tail(self) -> tuple[str, bool]:
        if self.log_path is None:
            return "", False
        try:
            size = self.log_path.stat().st_size
            with open(self.log_path, "rb") as handle:
                truncated = size > self.max_log_bytes
                if truncated:
                    handle.seek(size - self.max_log_bytes)
                return handle.read().decode("utf-8", "replace"), truncated
        except OSError as exc:
            logger.debug("[SelfFeeds] log unreadable (%s): %s", self.log_path, exc)
            return "", False

    def recent_errors(self, limit: int | None = None) -> dict:
        limit = self.error_limit if limit is None else max(1, int(limit))
        text, truncated = self._tail()
        lines = [
            line for line in text.splitlines()
            if _LEVEL_RE.search(line) or _TRACEBACK in line
        ]
        groups: dict[str, dict] = {}
        for position, line in enumerate(lines):
            signature = _signature(line)
            group = groups.get(signature)
            if group is None:
                group = groups[signature] = {
                    "signature": signature,
                    "count": 0,
                    "first_line": position + 1,
                    "last_line": position + 1,
                    "examples": [],
                }
            group["count"] += 1
            group["last_line"] = position + 1
            if len(group["examples"]) < 3 and line not in group["examples"]:
                group["examples"].append(line.strip()[:300])
        ordered = sorted(groups.values(), key=lambda item: (-item["count"], -item["last_line"]))
        return {
            "file": str(self.log_path) if self.log_path else "",
            "available": bool(lines) or (self.log_path is not None and self.log_path.exists()),
            "truncated": truncated,
            "scanned_bytes": min(self.max_log_bytes, self.log_path.stat().st_size) if self.log_path and self.log_path.exists() else 0,
            "total": len(lines),
            "groups": ordered[:limit],
            "checked_at": time.time(),
        }

    def stats(self) -> dict:
        health = self.health()
        errors = self.recent_errors()
        return {
            "health_available": health.get("available", False),
            "components": len(health.get("components") or {}),
            "unhealthy": len(health.get("unhealthy") or []),
            "log": errors.get("file", ""),
            "log_available": errors.get("available", False),
            "error_lines": errors.get("total", 0),
        }


def _signature(line: str) -> str:
    text = _TIMESTAMP_RE.sub("", line.strip())
    text = _LEVEL_TOKEN_RE.sub("", text).strip()
    # Group repeated failures regardless of ids/ports/counts in the message.
    return _DIGITS_RE.sub("#", text)[:160]


__all__ = ["HealthErrorFeeds"]
