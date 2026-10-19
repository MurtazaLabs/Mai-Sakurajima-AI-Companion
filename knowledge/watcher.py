import fnmatch
import hashlib
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)


class DirectoryWatcher:

    def __init__(self, builder, directories=None, interval=60.0, patterns=("*.md", "*.txt", "*.py", "*.json", "*.yaml", "*.csv")):
        self.builder = builder
        self.directories = list(directories or [])
        self.interval = interval
        self.patterns = patterns
        self._running = False
        self._thread = None
        self._lock = threading.RLock()
        self._known_files = {}
        self._content_hashes = {}

    def add_directory(self, path):
        if os.path.isdir(path):
            with self._lock:
                if path not in self.directories:
                    self.directories.append(path)
                    logger.info("[Watcher] Added directory: %s", path)
            return True
        logger.warning("[Watcher] Not a directory: %s", path)
        return False

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.info("[Watcher] Started (interval=%ss)", self.interval)

    def stop(self):
        with self._lock:
            self._running = False

    def is_alive(self):
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def _run(self):
        while True:
            with self._lock:
                if not self._running:
                    return
            try:
                with self._lock:
                    dirs = list(self.directories)
                for d in dirs:
                    if not os.path.isdir(d):
                        continue
                    for root, _, files in os.walk(d):
                        for fn in files:
                            if not any(fnmatch.fnmatch(fn, p) for p in self.patterns):
                                continue
                            path = os.path.join(root, fn)
                            mtime = os.path.getmtime(path)
                            last = self._known_files.get(path)
                            if last and mtime <= last:
                                continue
                            try:
                                with open(path, "rb") as f:
                                    content_hash = hashlib.md5(f.read()).hexdigest()
                            except Exception as e:
                                logger.warning("[Watcher] hash: %s", e)
                                continue
                            prev_hash = self._content_hashes.get(path)
                            if prev_hash and content_hash == prev_hash:
                                self._known_files[path] = mtime
                                continue
                            self._known_files[path] = mtime
                            self._content_hashes[path] = content_hash
                            try:
                                self.builder.build_from_file(path)
                            except Exception as e:
                                logger.warning("[Watcher] Index error %s: %s", path, e)
            except Exception as e:
                logger.error("[Watcher] Scan error: %s", e)
            for _ in range(int(self.interval * 10)):
                with self._lock:
                    if not self._running:
                        return
                time.sleep(0.1)

    def stats(self):
        with self._lock:
            return {
                "running": self._running,
                "directories": list(self.directories),
                "interval": self.interval,
                "known_files": len(self._known_files),
            }
