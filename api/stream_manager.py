import asyncio
import json
import threading
import logging
from typing import Any

from core.event_specs import VERTEX_SPECS

logger = logging.getLogger("api.stream")

_STATE_PREFIX = "state."


def _state_topics() -> list:
    """Every ``state.*`` topic in the event catalog.

    Derived from ``VERTEX_SPECS`` instead of being hand-listed. A state topic
    missing from this list is a silent connection bug: the publisher succeeds
    and logs, but no SSE/WebSocket client ever receives it, so the UI shows a
    stale or empty picture with nothing in any log to explain why.
    """
    return [
        spec.name for spec in VERTEX_SPECS
        if spec.name.startswith(_STATE_PREFIX)
    ]


STREAM_TOPICS = _state_topics()

class StreamManager:
    """Bridges sync EventBus events to async SSE clients."""

    def __init__(self, event_bus=None):
        self._event_bus: Any = event_bus
        self._lock = threading.RLock()
        self._queues = []
        self._subs = []
        self._known_topics = set()
        self._loop = None

    @property
    def client_count(self):
        with self._lock:
            return len(self._queues)

    def wire(self, event_bus):
        self._event_bus = event_bus
        for topic in STREAM_TOPICS:
            self.subscribe_to(topic)

    def add_queue(self, queue, loop=None):
        with self._lock:
            self._queues.append(queue)
            if loop is not None:
                self._loop = loop

    def remove_queue(self, queue):
        with self._lock:
            if queue in self._queues:
                self._queues.remove(queue)

    def subscribe_to(self, topic):
        if topic in self._known_topics:
            return
        self._known_topics.add(topic)
        if not self._event_bus:
            logger.warning("No event bus — cannot subscribe to '%s'", topic)
            return
        try:
            sub = self._event_bus.on(topic, self._make_handler(topic))
            self._subs.append(sub)
        except Exception as e:
            logger.warning("Cannot subscribe to '%s': %s", topic, e, exc_info=True)

    def _make_handler(self, topic):
        topic_str = str(topic)
        def handler(data):
            payload = json.dumps({"topic": topic_str, "data": data}, default=str)
            with self._lock:
                queues = list(self._queues)
            if not queues:
                return
            loop = self._loop
            if loop is None:
                logger.warning("[Stream] no event loop captured — events are being dropped")
                return
            for q in queues:
                try:
                    loop.call_soon_threadsafe(q.put_nowait, payload)
                except Exception as e:
                    logger.exception("[Stream] put: %s", e)
        return handler
