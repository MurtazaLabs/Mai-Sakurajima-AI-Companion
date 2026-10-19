import logging
import threading
import time

logger = logging.getLogger(__name__)


class HealthRegistry:

    OK = "ok"
    WARN = "warn"
    ERROR = "error"
    STALLED = "stalled"

    def __init__(self, event_bus=None, stall_timeout=30.0):
        self.event_bus = event_bus
        self.stall_timeout = stall_timeout
        self._lock = threading.RLock()
        self._components = {}

    def register(self, name, component=None):
        with self._lock:
            self._components[name] = {
                "name": name,
                "status": self.OK,
                "last_heartbeat": time.time(),
                "heartbeat_count": 0,
                "errors": [],
                "error_count": 0,
                "component": component,
            }

    def unregister(self, name):
        with self._lock:
            self._components.pop(name, None)

    def heartbeat(self, name):
        with self._lock:
            entry = self._components.get(name)
            if entry is None:
                self.register(name)
                entry = self._components[name]
            entry["last_heartbeat"] = time.time()
            entry["heartbeat_count"] += 1
            entry["status"] = self.OK

    def heartbeat_all(self):
        """Reset heartbeat + status for every registered component.

        Used at boot completion: components built early in a long boot would
        otherwise trip ``check_stalled()`` the moment supervision starts.
        """
        with self._lock:
            now = time.time()
            for name in self._components:
                entry = self._components[name]
                entry["last_heartbeat"] = now
                entry["status"] = self.OK

    def report_error(self, name, error):
        with self._lock:
            entry = self._components.get(name)
            if entry is None:
                self.register(name)
                entry = self._components[name]
            entry["status"] = self.ERROR
            entry["error_count"] += 1
            entry["errors"].append({"error": str(error), "timestamp": time.time()})
            if len(entry["errors"]) > 50:
                entry["errors"] = entry["errors"][-50:]
        if self.event_bus:
            from core.event_specs import HEALTH_ERROR
            from core.mai_message import publish_event
            publish_event(self.event_bus, HEALTH_ERROR, {
                "name": name,
                "error": str(error),
                "error_count": entry["error_count"],
            }, source="health")

    def resolve(self, name):
        with self._lock:
            entry = self._components.get(name)
            if entry:
                entry["status"] = self.OK

    def check_stalled(self):
        now = time.time()
        with self._lock:
            for name, entry in self._components.items():
                # Only components with a proven periodic heartbeat (≥2 beats)
                # are stall-checked. Construction-time single heartbeats (all
                # boot-time builders) must never be flagged stale.
                if entry.get("heartbeat_count", 0) < 2:
                    continue
                if (now - entry["last_heartbeat"]) > self.stall_timeout:
                    entry["status"] = self.STALLED

    def status(self, name):
        with self._lock:
            entry = self._components.get(name)
            if entry is None:
                return {"name": name, "status": "unknown"}
            return {
                "name": entry["name"],
                "status": entry["status"],
                "last_heartbeat": entry["last_heartbeat"],
                "error_count": entry["error_count"],
            }

    def stats(self):
        self.check_stalled()
        with self._lock:
            return {
                "components": {
                    name: {
                        "status": entry["status"],
                        "last_heartbeat": entry["last_heartbeat"],
                        "error_count": entry["error_count"],
                        "uptime": round(time.time() - entry["last_heartbeat"], 1),
                    }
                    for name, entry in sorted(self._components.items())
                },
                "summary": {
                    "total": len(self._components),
                    "ok": sum(1 for e in self._components.values() if e["status"] == self.OK),
                    "warn": sum(1 for e in self._components.values() if e["status"] == self.WARN),
                    "error": sum(1 for e in self._components.values() if e["status"] == self.ERROR),
                    "stalled": sum(1 for e in self._components.values() if e["status"] == self.STALLED),
                },
            }

    def __contains__(self, name):
        return name in self._components
