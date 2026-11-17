# core/atomic_document.py
"""A small JSON document with atomic, transactional writes.

Shared by subsystems that persist a handful of structured facts (continuity,
partner). One instance owns one file; ``transaction()`` mutates the live
document and flushes on a clean exit, restoring the pre-transaction snapshot if
the mutation raises. Writes go through a temp file in the same directory and
``os.replace`` (atomic on Windows and POSIX), so a crash mid-write can never
leave a half-written document.
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


class AtomicDocument:

    def __init__(self, path, defaults: dict | None = None, label: str = "document"):
        self.path = Path(path)
        self.label = label
        self._defaults = copy.deepcopy(dict(defaults or {}))
        self._lock = threading.RLock()
        self._data = self._load()

    # -- reads -------------------------------------------------------

    def _empty(self) -> dict:
        return copy.deepcopy(self._defaults)

    def _load(self) -> dict:
        with self._lock:
            if not self.path.exists():
                return self._empty()
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    raw = json.load(handle)
            except (OSError, ValueError) as exc:
                logger.error(
                    "[%s] Store unreadable (%s) — starting from defaults: %s",
                    self.label, self.path, exc,
                )
                return self._empty()
            if not isinstance(raw, dict):
                logger.error("[%s] Store root is not an object — starting from defaults", self.label)
                return self._empty()
            document = self._empty()
            if not self._defaults:
                return raw
            # Only declared keys are restored, and only when the stored shape
            # still matches the declared one — a corrupt section is dropped
            # instead of poisoning the whole document.
            for key, default in self._defaults.items():
                if key in raw and isinstance(raw[key], type(default)):
                    document[key] = raw[key]
            return document

    def read(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._data)

    # -- writes ------------------------------------------------------

    @contextmanager
    def transaction(self):
        """Mutate the live document in place; flush on a clean exit."""
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
                dir=str(self.path.parent), suffix=".tmp", prefix="doc_",
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
            logger.error("[%s] Failed to persist (%s): %s", self.label, self.path, exc)
