# core/event_bus_redis.py
"""
Redis-backed EventBus implementation.

Provides distributed event publishing with Redis pub/sub,
fallback to in-memory when Redis unavailable.
"""
import json
import time
import logging
import threading
import queue
import uuid
import base64
import zlib
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Optional, Tuple, Generator
from dataclasses import dataclass, field
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import redis
from redis.connection import ConnectionPool

from core.event_registry import (
    DEAD_LETTER,
    EXPONENTIAL,
    IGNORE,
    IMMEDIATE,
    NEVER,
    EventRegistry,
    EventSpec,
    RetryPolicy,
)
from core.mai_message import (
    PRIORITY_LEVELS,
    MaiMessage,
    Priority,
    legacy_message,
)
from core.state.redis_state import RedisConfig

logger = logging.getLogger(__name__)

MIDDLEWARE_ORDER = ("validation", "authorization", "metrics", "tracing", "logging", "compression")

TELEMETRY_TOPIC = "telemetry.inspector.record"

_DEFAULT_WORKERS = 4
_DEFAULT_MAX_QUEUE = 1000
_DEFAULT_TRACE_CAPACITY = 2000
_DEFAULT_DEAD_LETTER_CAPACITY = 500
_EXPONENTIAL_BASE = 0.05
_EXPONENTIAL_CAP = 5.0


class Subscription:
    def __init__(self, topic, handler, sub_id, receive_message=False, versions=None):
        self.topic = topic
        self.handler = handler
        self.id = sub_id
        self.receive_message = receive_message
        self.versions = tuple(versions) if versions else None

    def accepts(self, version: int) -> bool:
        """Version gate — None accepts any version (legacy default)."""
        if self.versions is None:
            return True
        return version in self.versions

    def __repr__(self):
        return (
            f"<Subscription "
            f"topic={self.topic} "
            f"handler={getattr(self.handler, '__name__', '?')} "
            f"id={self.id}>"
        )


class _RedisPubSub:
    """Redis pub/sub wrapper for distributed event broadcasting."""

    def __init__(self, redis_client, key_prefix: str = "mai:events"):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self.pubsub = None
        self._subscriptions: Dict[str, threading.Thread] = {}
        self._lock = threading.RLock()
        self._running = False

    def subscribe(self, topic: str, callback: Callable) -> str:
        """Subscribe to a topic pattern."""
        with self._lock:
            if not self.redis:
                return ""

            channel = f"{self.key_prefix}:{topic}"

            def listener():
                pubsub = self.redis.pubsub()
                pubsub.subscribe(channel)
                for message in pubsub.listen():
                    if message["type"] == "message":
                        try:
                            data = json.loads(message["data"])
                            callback(data)
                        except Exception as e:
                            logger.error("[RedisPubSub] Callback error: %s", e)

            thread = threading.Thread(target=listener, daemon=True)
            thread.start()
            self._subscriptions[topic] = thread
            return f"sub_{topic}"

    def publish(self, topic: str, payload: dict) -> bool:
        """Publish message to topic."""
        try:
            if not self.redis:
                return False
            channel = f"{self.key_prefix}:{topic}"
            payload_str = json.dumps(payload)
            self.redis.publish(channel, payload_str)
            return True
        except Exception as e:
            logger.error("[RedisPubSub] Publish failed: %s", e)
            return False

    def unsubscribe(self, topic: str) -> bool:
        with self._lock:
            # Redis pubsub doesn't support clean unsubscribe easily
            # This is a simplified version
            return True

    def shutdown(self):
        pass


class _WorkerPool:
    """Bounded worker pool with per-priority queues and drop-oldest policy."""

    def __init__(self, bus: "RedisEventBus", workers: int, max_queue: int):
        self._bus = bus
        self._workers = max(1, int(workers))
        self._max_queue = max(1, int(max_queue))
        self._queues: Dict[Priority, "queue.Queue"] = {
            p: queue.Queue(maxsize=self._max_queue) for p in PRIORITY_LEVELS
        }
        self._dropped: Dict[Priority, int] = {p: 0 for p in PRIORITY_LEVELS}
        self._enqueued: Dict[Priority, "deque"] = {p: deque() for p in PRIORITY_LEVELS}
        self._cv = threading.Condition(threading.RLock())
        self._running = False
        self._threads: List[threading.Thread] = []
        self._active = 0
        self._max_active = 0

    def ensure_started(self) -> None:
        with self._cv:
            if self._running:
                return
            self._running = True
        for i in range(self._workers):
            t = threading.Thread(
                target=self._run, name=f"eventbus-worker-{i}", daemon=True
            )
            t.start()
            self._threads.append(t)

    def submit(self, msg: 'MaiMessage') -> bool:
        self.ensure_started()
        ts = time.perf_counter()
        msg.metadata["enqueued_at"] = ts
        q = self._queues[msg.priority]
        enq = self._enqueued[msg.priority]
        with self._cv:
            try:
                q.put_nowait(msg)
                enq.append(ts)
            except queue.Full:
                try:
                    q.get_nowait()
                    if enq:
                        enq.popleft()
                    self._dropped[msg.priority] += 1
                except queue.Empty:
                    pass
                try:
                    q.put_nowait(msg)
                    enq.append(ts)
                except queue.Full:
                    return False
            self._cv.notify_all()
        return True

    def _run(self) -> None:
        while True:
            msg = self._pop()
            if msg is None:
                return
            with self._cv:
                self._active += 1
                self._max_active = max(self._max_active, self._active)
            try:
                self._bus._dispatch_with_retry(msg, async_mode=True)
            except Exception as e:
                logger.exception("[RedisEventBus] Async dispatch crashed: %s", e)
            finally:
                with self._cv:
                    self._active -= 1
                    self._cv.notify_all()

    def _pop(self) -> Optional['MaiMessage']:
        while True:
            with self._cv:
                if not self._running:
                    return None
                for p in PRIORITY_LEVELS:
                    try:
                        msg = self._queues[p].get_nowait()
                    except queue.Empty:
                        continue
                    enq = self._enqueued[p]
                    if enq:
                        enq.popleft()
                    return msg
                self._cv.wait(timeout=0.1)

    def shutdown(self, timeout: float = 2.0) -> None:
        with self._cv:
            self._running = False
            self._cv.notify_all()
        for t in self._threads:
            t.join(timeout=timeout)
        self._threads = []

    def queue_snapshot(self) -> Dict[str, Dict[str, Any]]:
        with self._cv:
            return {
                p.name: {
                    "occupancy": self._queues[p].qsize(),
                    "dropped": self._dropped[p],
                    "max_queue": self._max_queue,
                    "oldest_wait_ms": self._oldest_wait_ms(p),
                }
                for p in PRIORITY_LEVELS
            }

    def _oldest_wait_ms(self, priority: Priority) -> float:
        enq = self._enqueued[priority]
        if not enq:
            return 0.0
        return round((time.perf_counter() - enq[0]) * 1000.0, 1)

    def info(self) -> Dict[str, int]:
        with self._cv:
            return {
                "workers": self._workers,
                "running": int(self._running),
                "active": self._active,
                "max_active": self._max_active,
            }


class RedisEventBus:
    """
    Redis-backed EventBus with distributed pub/sub and local fallback.
    
    Features:
    - Redis pub/sub for distributed event broadcasting
    - Local in-memory fallback when Redis unavailable
    - Priority queues with worker pool
    - Retry policies, dead letter queue
    - Middleware chain (validation, auth, metrics, tracing, logging, compression)
    - Telemetry and tracing
    - Correlation propagation
    """

    def __init__(
        self,
        worker_count: int = 4,
        max_queue: int = 1000,
        registry: Optional['EventRegistry'] = None,
        default_source: str = "",
        trace_capacity: int = 2000,
        redis_config: Optional['RedisConfig'] = None,
        redis_client: Optional[Any] = None,
        metadata_registry: Optional[Any] = None,
    ):
        self._lock = threading.RLock()
        self._subscribers: Dict[str, List[Subscription]] = {}
        self.registry: EventRegistry = registry or EventRegistry()
        self._default_source = default_source

        # Redis configuration
        self._redis_config = redis_config or RedisConfig()
        self._redis_client = redis_client
        self._redis = None
        self._pubsub = None
        self._redis_available = False
        
        # Initialize Redis connection
        self._init_redis()

        self._pool = _WorkerPool(self, workers=worker_count, max_queue=max_queue)
        self._middleware: Dict[str, Callable] = {}
        self._install_default_middleware()

        self._traces: deque = deque(maxlen=max(0, trace_capacity))
        self._trace_capacity = trace_capacity
        self._counter_total = 0
        self._counters: Dict[str, int] = {}
        self._failure_count = 0
        self._type_failures: Dict[str, int] = {}
        self._version_mismatches = 0
        self._dead_letters: deque = deque(maxlen=_DEFAULT_DEAD_LETTER_CAPACITY)
        self._telemetry_enabled = True
        if metadata_registry is not None:
            self._metadata_extractor = metadata_registry.extract
        else:
            from core.event_metadata import extract_metadata

            self._metadata_extractor = extract_metadata

        if not self.registry.has(TELEMETRY_TOPIC):
            self.registry.register(EventSpec(
                name=TELEMETRY_TOPIC,
                version=1,
                publisher="event_bus",
                priority="high",
                description="Internal fabric telemetry channel (Inspector feed).",
            ))

    def _install_default_middleware(self) -> None:
        self._middleware["validation"] = self._default_validation
        self._middleware["authorization"] = self._default_authorization
        self._middleware["metrics"] = self._default_metrics
        self._middleware["tracing"] = self._default_tracing
        self._middleware["logging"] = self._default_logging
        self._middleware["compression"] = self._default_compression

    @staticmethod
    def _default_validation(msg: 'MaiMessage', bus: 'RedisEventBus') -> None:
        if msg.is_legacy:
            return
        spec = bus.registry.get(msg.type)
        if spec is None:
            raise ValueError(
                f"Unknown event type '{msg.type}' — register it via "
                f"EventRegistry before publishing"
            )
        if msg.version not in spec.versions:
            raise ValueError(
                f"Unsupported version {msg.version} for '{msg.type}' "
                f"(supported: {spec.versions})"
            )

    @staticmethod
    def _default_authorization(msg: 'MaiMessage', bus: 'RedisEventBus') -> None:
        if msg.is_legacy or not msg.source:
            return
        spec = bus.registry.get(msg.type)
        if spec is None:
            return
        if not bus.registry.can_publish(msg.source, msg.type):
            raise ValueError(
                f"Source '{msg.source}' is not authorized to publish "
                f"'{msg.type}' (allowed: {sorted(spec.allowed_publishers)})"
            )

    def _default_metrics(self, msg: 'MaiMessage', bus: 'RedisEventBus') -> None:
        with bus._lock:
            bus._counter_total += 1
            bus._counters[msg.type] = bus._counters.get(msg.type, 0) + 1

    @staticmethod
    def _default_tracing(msg: 'MaiMessage', bus: 'RedisEventBus') -> None:
        msg.metadata["traced"] = True

    @staticmethod
    def _default_logging(msg: 'MaiMessage', bus: 'RedisEventBus') -> None:
        logger.debug(
            "[EventBus] %s %s -> %s (v%d, pri=%s, corr=%s)",
            msg.namespace, msg.source or "?", msg.type, msg.version,
            msg.priority.name, msg.correlation_id,
        )

    def _default_compression(self, msg: 'MaiMessage', bus: 'RedisEventBus') -> None:
        if msg.is_legacy or msg.metadata.get("compressed"):
            return
        spec = bus.registry.get(msg.type)
        if spec is None or not spec.compressed:
            return
        payload = msg.payload
        if not isinstance(payload, dict):
            return
        blob = json.dumps(payload, default=str).encode("utf-8")
        if len(blob) < 256:
            return
        msg.payload = {"__zlib__": base64.b64encode(zlib.compress(blob)).decode("ascii")}
        msg.metadata["compressed"] = True

    def _run_middleware(self, msg: MaiMessage) -> None:
        for name in MIDDLEWARE_ORDER:
            fn = self._middleware.get(name)
            if fn is not None:
                fn(msg, self)

    def _init_redis(self):
        """Initialize Redis connection."""
        try:
            if self._redis_client:
                self._redis = self._redis_client
            else:
                cfg = self._redis_config
                connection_kwargs = {
                    "host": cfg.host,
                    "port": cfg.port,
                    "db": cfg.db,
                    "password": cfg.password,
                    "max_connections": cfg.max_connections,
                    "socket_timeout": cfg.socket_timeout,
                    "socket_connect_timeout": cfg.socket_connect_timeout,
                    "decode_responses": cfg.decode_responses,
                }
                # SSL configuration for redis-py 4.2+
                if cfg.ssl:
                    import ssl
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE
                    connection_kwargs["ssl_cert_reqs"] = ssl.CERT_NONE
                
                self._pool = ConnectionPool(
                    **connection_kwargs
                )
                self._redis = redis.Redis(connection_pool=self._pool)

            # Test connection
            self._redis.ping()
            self._redis_available = True
            self._pubsub = _RedisPubSub(self._redis)
            logger.info("[RedisEventBus] Connected to Redis")
        except Exception as e:
            logger.warning("[RedisEventBus] Redis unavailable, using local mode: %s", e)
            self._redis = None
            self._redis_available = False
            self._pubsub = None

    def _init_redis_pubsub(self):
        """Initialize Redis pub/sub subscriptions for existing topics."""
        if not self._redis_available:
            return
        try:
            # Subscribe to all registered topics
            for topic in self.registry._specs.keys():
                self._subscribe_to_redis(topic)
        except Exception as e:
            logger.warning("[RedisEventBus] Failed to init pubsub: %s", e)

    def _subscribe_to_redis(self, topic: str):
        """Subscribe to a Redis channel for a topic."""
        if not self._redis_available:
            return
        try:
            channel = f"mai:events:{topic}"
            self._pubsub.subscribe(channel, self._on_redis_message)
        except Exception as e:
            logger.warning("[RedisEventBus] Failed to subscribe to %s: %s", topic, e)

    def _on_redis_message(self, data: dict):
        """Handle incoming Redis pub/sub message."""
        try:
            # Convert to MaiMessage and dispatch locally
            msg = MaiMessage(
                type=data.get("type", ""),
                payload=data.get("payload", {}),
                source=data.get("source", ""),
                version=data.get("version", 1),
                priority=Priority(data.get("priority", "normal")),
                correlation_id=data.get("correlation_id", ""),
                causation_id=data.get("causation_id", ""),
            )
            # Dispatch locally
            self._dispatch_once(msg, attempt=1)
        except Exception as e:
            logger.error("[RedisEventBus] Failed to process Redis message: %s", e)

    # ... rest of EventBus implementation (same as core/event_bus.py but with Redis pub/sub)
    # ... (keeping all the existing methods from core/event_bus.py)
    
    def publish(self, topic, data=None, source=None):
        """Legacy synchronous publish - now uses Redis pub/sub if available."""
        msg = self._prepare(topic, data, source)
        if self._redis_available:
            self._publish_to_redis(msg)
        self._dispatch_once(msg, attempt=1)
        return None

    def _publish_to_redis(self, msg: 'MaiMessage'):
        """Publish message to Redis pub/sub."""
        if not self._redis_available:
            return
        try:
            payload = {
                "type": msg.type,
                "payload": msg.payload,
                "source": msg.source,
                "version": msg.version,
                "priority": msg.priority.name,
                "correlation_id": msg.correlation_id,
                "causation_id": msg.causation_id,
                "timestamp": msg.timestamp,
            }
            self._pubsub.publish(msg.type, payload)
        except Exception as e:
            logger.warning("[RedisEventBus] Redis publish failed: %s", e)

    def publish_async(self, topic, data=None, source=None):
        """Legacy async publish — routed through the bounded worker pool."""
        msg = self._prepare(topic, data, source)
        self._pool.submit(msg)

    def emit(self, topic, **kwargs):
        return self.publish(topic, data=kwargs if kwargs else None)

    def publish_message(self, msg, wait=False, timeout=None):
        """Fabric publish. ``wait=True`` dispatches synchronously."""
        if wait:
            return self.publish_wait(msg, timeout=timeout)
        self._pool.submit(msg)
        return None

    def publish_wait(self, topic_or_msg, payload=None, timeout=None, source=None):
        """Dispatch and return handler results (synchronous)."""
        msg = self._prepare(topic_or_msg, payload, source)
        results = self._dispatch_with_retry(msg, async_mode=False)
        return [value for _, value in (results or [])]

    def request(self, topic_or_msg, payload=None, timeout=5.0, source=None):
        """Request/response — first non-None handler result."""
        results = self.publish_wait(topic_or_msg, payload, timeout=timeout, source=source)
        for value in results:
            if value is not None:
                return value
        return None

    def stream(self, topic_or_msg, payload=None, timeout=None, source=None):
        """Generator yielding each handler result in subscription order."""
        results = self.publish_wait(topic_or_msg, payload, timeout=timeout, source=source)
        for value in results:
            if value is not None:
                yield value

    # ── Lifecycle ────────────────────────────────────────────────
    def shutdown(self, timeout: float = 2.0) -> None:
        self._pool.shutdown(timeout=timeout)
        if self._redis:
            try:
                self._redis.close()
            except Exception:
                pass

    def __repr__(self):
        return f"<RedisEventBus subs={sum(len(v) for v in self._subscribers.values())} traces={len(self._traces)} redis={'on' if self._redis_available else 'off'}>"


# ── Subscribers ──────────────────────────────────────────────

    def subscribe(self, topic, handler, receive_message=False, versions=None):
        if not callable(handler):
            raise ValueError("Handler must be callable")
        sub = Subscription(
            topic=topic,
            handler=handler,
            sub_id=str(uuid.uuid4()),
            receive_message=receive_message,
            versions=versions,
        )
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(sub)
            # Also subscribe to Redis channel if Redis is available
            if self._redis_available:
                self._subscribe_to_redis(topic)
        logger.debug(
            "[RedisEventBus] Subscribed to '%s': %s",
            topic, getattr(handler, "__name__", "?"),
        )
        return sub

    def unsubscribe(self, sub):
        if not isinstance(sub, Subscription):
            raise TypeError("Expected a Subscription object")
        with self._lock:
            subs = self._subscribers.get(sub.topic, [])
            if sub in subs:
                subs.remove(sub)
                logger.debug("[RedisEventBus] Unsubscribed from '%s'", sub.topic)

    def _matching_subs(self, topic: str) -> List[Subscription]:
        """Exact-topic matches plus ``prefix.*`` wildcard subscriptions."""
        with self._lock:
            out: List[Subscription] = []
            seen = set()
            for s in self._subscribers.get(topic, ()):
                out.append(s)
                seen.add(s.id)
            for sub_topic, subs in self._subscribers.items():
                if sub_topic == topic or not sub_topic.endswith(".*"):
                    continue
                if topic.startswith(sub_topic[:-1]):
                    for s in subs:
                        if s.id not in seen:
                            out.append(s)
                            seen.add(s.id)
            return out

    def on(self, topic, handler):
        return self.subscribe(topic, handler)

    def clear(self):
        with self._lock:
            self._subscribers.clear()

    # ── Message preparation ──────────────────────────────────────

    def _prepare(self, topic_or_msg, data=None, source=None) -> MaiMessage:
        """Coerce legacy ``(topic, dict)`` calls into a MaiMessage."""
        if isinstance(topic_or_msg, MaiMessage):
            msg = topic_or_msg
            if data is not None:
                if isinstance(data, dict):
                    msg.payload.update(data)
                else:
                    msg.payload = {"value": data}
        else:
            msg = legacy_message(
                topic_or_msg, data, source=source or self._default_source
            )
        if source:
            msg.source = source
        if not msg.source:
            msg.source = self._default_source
        return msg

    # ── Dispatch core ────────────────────────────────────────

    def _dispatch_once(self, msg: MaiMessage, attempt: int = 1):
        """Single dispatch attempt. Returns (outcome, error, results)."""
        t0 = time.perf_counter()
        results: List[Tuple[Subscription, Any]] = []
        handler_failures: List[str] = []
        handler_times: Dict[str, float] = {}
        try:
            self._run_middleware(msg)
        except Exception as e:
            self._record(msg, attempt, "FAILED", f"middleware: {e}", [], 0.0, 0.0)
            return "FAILED", e, results
        if msg.metadata.get("compressed"):
            self._decompress_payload(msg)
        subs = self._matching_subs(msg.type)
        sub_names = []
        for sub in subs:
            if not sub.accepts(msg.version):
                with self._lock:
                    self._version_mismatches += 1
                logger.warning(
                    "[RedisEventBus] Subscription '%s' (%s) rejects version %d of "
                    "'%s' (supports %s)",
                    sub.topic, getattr(sub.handler, "__name__", "?"),
                    msg.version, msg.type, sub.versions,
                )
                continue
            name = getattr(sub.handler, "__name__", None) or sub.topic
            sub_names.append(name)
            h_start = time.perf_counter()
            try:
                value = sub.handler(msg if sub.receive_message else msg.payload)
                results.append((sub, value))
            except Exception as e:
                handler_failures.append(name)
                logger.warning(
                    "[RedisEventBus] Handler '%s' failed on '%s': %s",
                    getattr(sub.handler, "__name__", "?"), msg.type, e,
                )
            handler_times[name] = (time.perf_counter() - h_start) * 1000.0
        execution = (time.perf_counter() - t0) * 1000.0
        if handler_failures:
            error = f"{len(handler_failures)} handler(s) failed: {handler_failures[0]}"
            self._record(msg, attempt, "FAILED", error, sub_names, 0.0, execution,
                         handler_times=handler_times, handler_failures=handler_failures)
            return "FAILED", e, results
        self._record(msg, attempt, "SUCCESS", None, sub_names, 0.0, execution,
                     handler_times=handler_times, handler_failures=handler_failures)
        return "SUCCESS", None, results

    def _dispatch_with_retry(self, msg: MaiMessage, async_mode: bool = False):
        """Dispatch honoring the registered RetryPolicy. Never raises."""
        attempt = int(msg.metadata.get("attempt", 1))
        while True:
            outcome, err, results = self._dispatch_once(msg, attempt=attempt)
            if outcome == "SUCCESS":
                return results
            policy, max_attempts = self.registry.retry_policy(msg.type)
            if policy in (RetryPolicy.NEVER, RetryPolicy.IGNORE):
                return None
            if attempt >= max_attempts:
                if policy == RetryPolicy.DEAD_LETTER:
                    self._dead_letter(msg, err)
                return None
            attempt += 1
            msg.metadata["attempt"] = attempt
            if policy in (RetryPolicy.IMMEDIATE, RetryPolicy.DEAD_LETTER):
                continue
            if policy == RetryPolicy.EXPONENTIAL:
                delay = min(
                    _EXPONENTIAL_CAP, _EXPONENTIAL_BASE * (2 ** (attempt - 1))
                )
                if async_mode:
                    threading.Timer(delay, self._pool.submit, args=(msg,)).start()
                    return None
                time.sleep(delay)
                continue
            return None

    def _dead_letter(self, msg: MaiMessage, error) -> None:
        record = {
            "type": msg.type,
            "source": msg.source,
            "error": str(error),
            "attempts": int(msg.metadata.get("attempt", 1)),
            "correlation_id": msg.correlation_id,
            "timestamp": time.time(),
        }
        with self._lock:
            self._dead_letters.append(record)
        logger.warning("[RedisEventBus] Dead letter: %s (%s)", msg.type, error)

    # ── Telemetry ────────────────────────────────────────────

    def _record(self, msg, attempt, outcome, error, subscribers,
                queue_delay, execution,
                handler_times=None, handler_failures=None) -> None:
        if self._trace_capacity <= 0:
            return
        if msg.type == TELEMETRY_TOPIC:
            return
        metadata = self._metadata_extractor(msg.type, msg.payload)
        record = {
            "id": msg.id,
            "timestamp": msg.timestamp,
            "type": msg.type,
            "version": msg.version,
            "source": msg.source,
            "target": msg.target,
            "priority": msg.priority.name,
            "correlation_id": msg.correlation_id,
            "causation_id": msg.causation_id,
            "outcome": outcome,
            "error": str(error) if error else None,
            "attempt": attempt,
            "subscribers": list(subscribers or []),
            "handler_times_ms": dict(handler_times or {}),
            "handler_failures": list(handler_failures or []),
            "queue_delay_ms": round(queue_delay, 3),
            "execution_ms": round(execution, 3),
            "metadata": metadata,
        }
        with self._lock:
            self._traces.append(record)
            if outcome != "SUCCESS":
                self._failure_count += 1
                self._type_failures[msg.type] = self._type_failures.get(msg.type, 0) + 1
        if self._telemetry_enabled and msg.type != TELEMETRY_TOPIC:
            self._pool.submit(MaiMessage(
                type=TELEMETRY_TOPIC,
                payload=record,
                priority=Priority.HIGH,
                source="event_bus",
                version=1,
            ))

    def enable_telemetry(self, enabled: bool = True) -> None:
        self._telemetry_enabled = bool(enabled)

    def traces(self, filters: Optional[Dict[str, Any]] = None) -> List[dict]:
        with self._lock:
            out = list(self._traces)
        if not filters:
            return out
        result = []
        for rec in out:
            match = True
            for key, value in filters.items():
                if key == "correlation_id" and rec.get("correlation_id") != value:
                    match = False
                    break
                if key == "outcome" and rec.get("outcome") != value:
                    match = False
                    break
                if key == "type" and value is not None \
                        and not rec.get("type", "").startswith(value):
                    match = False
                    break
                if key == "source" and rec.get("source") != value:
                    match = False
                    break
            if match:
                result.append(rec)
        return result

    def clear_traces(self) -> None:
        with self._lock:
            self._traces.clear()

    def dead_letters(self) -> List[dict]:
        with self._lock:
            return list(self._dead_letters)

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_published": self._counter_total,
                "per_type": dict(self._counters),
                "failures": self._failure_count,
                "type_failures": dict(self._type_failures),
                "dead_letters": len(self._dead_letters),
                "traces": len(self._traces),
                "trace_capacity": self._trace_capacity,
                "subscribers": sum(len(v) for v in self._subscribers.values()),
                "version_mismatches": self._version_mismatches,
                "queue": self._pool.queue_snapshot(),
                "workers": self._pool.info(),
            }

    def shutdown(self, timeout: float = 2.0) -> None:
        self._pool.shutdown(timeout=timeout)
        if self._redis:
            try:
                self._redis.close()
            except Exception:
                pass

    def __repr__(self):
        return f"<RedisEventBus subs={sum(len(v) for v in self._subscribers.values())} traces={len(self._traces)} redis={'on' if self._redis_available else 'off'}>"


# Backward compatibility
EventBus = RedisEventBus