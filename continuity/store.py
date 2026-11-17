# continuity/store.py
"""Single-document JSON persistence for the Continuity Engine.

One file holds projects, commitments and checkpoints so a write is atomic
across all three. Writes go through a temp file in the same directory and
``os.replace`` (atomic on Windows and POSIX), so a crash mid-write can never
leave a half-written ledger.
"""
from __future__ import annotations

import copy
import json
import logging
import os
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

_DOC_KEYS = ("projects", "commitments", "checkpoints")
_DOC_VERSION = 1


def _empty_document() -> dict:
    return {
        "version": _DOC_VERSION,
        "projects": {},
        "commitments": {},
        "checkpoints": {},
    }


class ContinuityStore:

    def __init__(self, path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._data = self._load()

    # -- reads -------------------------------------------------------

    def _load(self) -> dict:
        with self._lock:
            if not self.path.exists():
                return _empty_document()
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    raw = json.load(handle)
            except (OSError, ValueError) as exc:
                logger.error(
                    "[Continuity] Store unreadable (%s) — starting from an empty ledger: %s",
                    self.path, exc,
                )
                return _empty_document()
            if not isinstance(raw, dict):
                logger.error("[Continuity] Store root is not an object — starting empty")
                return _empty_document()
            document = _empty_document()
            for key in _DOC_KEYS:
                if isinstance(raw.get(key), dict):
                    document[key] = raw[key]
            if isinstance(raw.get("version"), int):
                document["version"] = raw["version"]
            return document

    def read(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._data)

    # -- writes ------------------------------------------------------

    @contextmanager
    def transaction(self):
        """Mutate the live document in place; flush on a clean exit.

        A mutation that raises restores the pre-transaction snapshot, so a
        failed operation never leaves a partially-applied ledger in memory.
        """
        with self._lock:
            snapshot = copy.deepcopy(self._data)
            try:
                yield self._data
            except BaseException:
                self._data = snapshot
                raise
            self._flush()

    def _flush(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            handle = tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", delete=False,
                dir=str(self.path.parent), suffix=".tmp", prefix="continuity_",
            )
            try:
                with handle as stream:
                    json.dump(self._data, stream, indent=2, sort_keys=True)
                os.replace(handle.name, self.path)
            except BaseException:
                try:
                    os.unlink(handle.name)
                except OSError:
                    pass
                raise
        except OSError as exc:
            logger.error("[Continuity] Failed to persist store (%s): %s", self.path, exc)
