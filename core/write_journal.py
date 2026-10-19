import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable

logger = logging.getLogger(__name__)


class WriteJournal:
    """Async write journal that batches and defers backend writes.

    Callers enqueue backend writes during the hot path; a background
    drain thread flushes them asynchronously.  Each backend registers
    a *batch* callable that receives [(arg, kwarg), ...] and persists
    them in one shot.
    """

    def __init__(self, drain_interval: float = 2.0, max_batch: int = 50):
        self._drain_interval = drain_interval
        self._max_batch = max_batch
        self._queue: deque[tuple[str, tuple, dict]] = deque()
        self._lock = threading.RLock()
        self._running = False
        self._thread: threading.Thread | None = None
        self._backends: dict[str, Callable] = {}

    def register(self, name: str, batch_fn: Callable):
        """Register a backend that accepts ``batch_fn([(args, kwargs), ...])``."""
        self._backends[name] = batch_fn

    def backends(self):
        """Snapshot of registered backends (used when reconstructing)."""
        with self._lock:
            return dict(self._backends)

    def is_alive(self):
        """True while the drain thread is running (crash detector probe)."""
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def enqueue(self, backend: str, *args, **kwargs):
        """Add a write to the queue (returns immediately)."""
        with self._lock:
            self._queue.append((backend, args, kwargs))

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._drain_loop, daemon=True, name="WriteJournal")
        self._thread.start()
        logger.info("[WriteJournal] Started (interval=%ss)", self._drain_interval)

    def stop(self, timeout: float = 5.0):
        self._running = False
        if self._thread:
            self._thread.join(timeout=timeout)

    def drain(self):
        """Synchronously flush all pending entries."""
        with self._lock:
            snapshot = list(self._queue)
            self._queue.clear()
        self._flush(snapshot)

    def _drain_loop(self):
        while self._running:
            time.sleep(self._drain_interval)
            with self._lock:
                snapshot = list(self._queue)
                self._queue.clear()
            if snapshot:
                self._flush(snapshot)

    def _flush(self, entries):
        grouped: dict[str, list] = defaultdict(list)
        for backend, args, kwargs in entries:
            grouped[backend].append((args, kwargs))
        for backend_name, batch in grouped.items():
            fn = self._backends.get(backend_name)
            if fn is None:
                logger.warning("[WriteJournal] No registered backend: %s", backend_name)
                continue
            try:
                while batch:
                    chunk = batch[:self._max_batch]
                    batch = batch[self._max_batch:]
                    fn(chunk)
            except Exception as e:
                logger.error("[WriteJournal] %s batch error: %s", backend_name, e)
