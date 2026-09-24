"""External watchdog process — monitors daemon health and auto-restarts.

Two usage modes:

1. **Subprocess watchdog** (separate process):
       python -m native.watchdog --pid 1234

   Polls every 5s; if the target PID dies, re-launches the daemon.

2. **In-process health monitor** (thread):
       wd = HealthMonitor(port=8000)
       wd.start()

   Polls ``/api/health`` every 10s; emits events on failure/recovery.
"""
import os
import sys
import time
import json
import logging
import subprocess
import threading
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)


class HealthMonitor:
    """In-process thread that polls the daemon health endpoint.

    Calls ``on_failure`` when the daemon becomes unresponsive and
    ``on_recovery`` when it comes back.
    """

    def __init__(self, host="127.0.0.1", port=8000, interval=10.0,
                 on_failure=None, on_recovery=None):
        self._url = f"http://{host}:{port}/api/health"
        self._interval = interval
        self._on_failure = on_failure
        self._on_recovery = on_recovery
        self._healthy = True
        self._running = False
        self._thread: threading.Thread | None = None

    def _check(self) -> bool:
        try:
            resp = urllib.request.urlopen(self._url, timeout=5)
            return resp.status == 200
        except Exception:
            return False

    def _loop(self):
        while self._running:
            ok = self._check()
            if not ok and self._healthy:
                self._healthy = False
                logger.warning("[Watchdog] Daemon unhealthy")
                if self._on_failure:
                    self._on_failure()
            elif ok and not self._healthy:
                self._healthy = True
                logger.info("[Watchdog] Daemon recovered")
                if self._on_recovery:
                    self._on_recovery()
            time.sleep(self._interval)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True,
                                        name="health-monitor")
        self._thread.start()
        logger.info("[Watchdog] Health monitor started (every %.1fs)",
                    self._interval)

    def stop(self):
        self._running = False
        self._thread = None


def _watch_pid(pid: int, daemon_args: list[str]):
    """Watch a PID; restart daemon if it dies."""
    logger.info("[Watchdog] Watching PID %d", pid)
    while True:
        try:
            os.waitpid(pid, 0)
        except ChildProcessError:
            pass
        logger.warning("[Watchdog] PID %d died — restarting", pid)
        proc = subprocess.Popen(daemon_args)
        pid = proc.pid
        logger.info("[Watchdog] Restarted as PID %d", pid)
        time.sleep(2)


def main():
    """CLI entry point: python -m native.watchdog --pid <pid> [--restart args...]"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
    )
    args = sys.argv[1:]
    if "--pid" in args:
        idx = args.index("--pid")
        pid = int(args[idx + 1])
        rest = args[idx + 2:]
        if "--restart" in rest:
            rest = rest[rest.index("--restart") + 1:]
        _watch_pid(pid, rest or [sys.executable, "run_daemon.py"])
    else:
        logger.error("Usage: python -m native.watchdog --pid <pid> [--restart args...]")
        sys.exit(1)


if __name__ == "__main__":
    main()
