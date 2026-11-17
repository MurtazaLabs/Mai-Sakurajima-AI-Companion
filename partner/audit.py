# partner/audit.py
"""Append-only audit trail for verified actions.

One JSON object per line (JSONL) so a write is O(1) and a crash can at worst
truncate the last line. Records are the honest account of what Mai did: the
tier she was allowed, whether the action ran, and whether its post-condition
was verified.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

logger = logging.getLogger(__name__)


class ActionAuditLog:

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._last_error = ""

    def append(self, record: dict) -> dict:
        if not isinstance(record, dict):
            raise TypeError("audit record must be a dict")
        with self._lock:
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, sort_keys=True) + "\n")
            except OSError as exc:
                # Never raise into an action path: the action already happened,
                # or didn't; losing the log line must not change its outcome.
                self._last_error = str(exc)
                logger.error("[Audit] Failed to append record (%s): %s", self.path, exc)
        return record

    def recent(self, limit: int = 20) -> list[dict]:
        records = self._read_all()
        return records[-max(1, int(limit)):][::-1]

    def query(self, action_type: str | None = None, status: str | None = None,
              limit: int = 50) -> list[dict]:
        records = self._read_all()
        if action_type:
            records = [r for r in records if r.get("action_type") == action_type]
        if status:
            records = [r for r in records if r.get("status") == status]
        return records[-max(1, int(limit)):][::-1]

    def stats(self) -> dict:
        records = self._read_all()
        by_status: dict[str, int] = {}
        by_tier: dict[str, int] = {}
        for record in records:
            by_status[record.get("status", "unknown")] = by_status.get(record.get("status", "unknown"), 0) + 1
            by_tier[record.get("tier", "unknown")] = by_tier.get(record.get("tier", "unknown"), 0) + 1
        return {
            "total": len(records),
            "by_status": by_status,
            "by_tier": by_tier,
            "last_error": self._last_error,
        }

    # -- internals ---------------------------------------------------

    def _read_all(self) -> list[dict]:
        with self._lock:
            if not self.path.exists():
                return []
            records = []
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    for line in handle:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                        except ValueError:
                            # A torn trailing line after a crash: skip, don't fail.
                            logger.warning("[Audit] Skipping unreadable record line")
                            continue
                        if isinstance(entry, dict):
                            records.append(entry)
            except OSError as exc:
                logger.error("[Audit] Failed to read log (%s): %s", self.path, exc)
            return records

    def size_bytes(self) -> int:
        try:
            return os.path.getsize(self.path)
        except OSError:
            return 0
