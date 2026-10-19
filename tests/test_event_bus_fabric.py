"""Tests for the Event Fabric transport (priority, middleware, retry,
request/response, telemetry) and legacy compatibility."""
import json
import threading
import time

import pytest

from core.event_bus import MIDDLEWARE_ORDER, EventBus
from core.event_registry import EventSpec, RetryPolicy
from core.mai_message import MaiMessage, Priority, correlation_scope


def wait_for(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def _bus(**kwargs):
    """EventBus pre-registered with the fabric topics used in this suite.

    Fabric (non-legacy) publishes are validated against the Event Registry,
    so every topic published via ``MaiMessage`` must be declared first.
    """
    bus = EventBus(**kwargs)
    for name in ("t", "control.x", "gate", "bg", "hi", "work", "data.query"):
        bus.register_spec(EventSpec(name=name))
    return bus


class TestLegacyCompat:

    def test_publish_is_synchronous(self):
        bus = EventBus()
        order = []
        bus.subscribe("t", lambda d: order.append("ran"))
        bus.publish("t", {"a": 1})
        assert order == ["ran"]

    def test_handler_receives_payload_dict(self):
        bus = EventBus()
        captured = {}
        bus.subscribe("t", lambda d: captured.update(d))
        bus.publish("t", {"a": 1, "b": 2})
        assert captured == {"a": 1, "b": 2}

    def test_payload_identity_preserved(self):
        bus = EventBus()
        data = {"x": [1]}
        seen = []
        bus.subscribe("t", lambda d: seen.append(d))
        bus.publish("t", data)
        assert seen[0] is data

    def test_data_none_becomes_empty_dict(self):
        bus = EventBus()
        seen = []
        bus.subscribe("t", lambda d: seen.append(d))
        bus.publish("t")
        assert seen == [{}]

    def test_handler_error_is_isolated(self):
        bus = EventBus()
        order = []

        def bad(d):
            order.append("bad")
            raise RuntimeError("boom")

        bus.subscribe("t", bad)
        bus.subscribe("t", lambda d: order.append("good"))
        result = bus.publish("t", {})
        assert result is None
        assert order == ["bad", "good"]

    def test_emit_and_on_aliases(self):
        bus = EventBus()
        seen = []
        bus.on("t", lambda d: seen.append(d))
        bus.emit("t", a=1, b=2)
        assert seen == [{"a": 1, "b": 2}]

    def test_unsubscribe_stops_delivery(self):
        bus = EventBus()
        seen = []
        sub = bus.subscribe("t", lambda d: seen.append(1))
        bus.publish("t", {})
        bus.unsubscribe(sub)
        bus.publish("t", {})
        assert len(seen) == 1

    def test_unsubscribe_type_check(self):
        bus = EventBus()
        with pytest.raises(TypeError):
            bus.unsubscribe("not a sub")

    def test_subscribe_requires_callable(self):
        bus = EventBus()
        with pytest.raises(ValueError):
            bus.subscribe("t", 42)

    def test_clear_removes_all(self):
        bus = EventBus()
        seen = []
        bus.subscribe("t", lambda d: seen.append(1))
        bus.clear()
        bus.publish("t", {})
        assert seen == []

    def test_publish_async_delivers(self):
        bus = EventBus()
        delivered = threading.Event()
        payloads = []

        def handler(d):
            payloads.append(d)
            delivered.set()

        bus.subscribe("t", handler)
        bus.publish_async("t", {"v": 1})
        assert delivered.wait(5.0)
        assert payloads == [{"v": 1}]
        bus.shutdown()

    def test_legacy_publish_recorded_without_registration(self):
        bus = EventBus()
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert bus.stats()["total_published"] == 1
        assert bus.traces()[0]["version"] == 0
        assert bus.traces()[0]["outcome"] == "SUCCESS"


class TestMaiMessageDispatch:

    def test_publish_message_sync(self):
        bus = _bus()
        seen = []
        bus.subscribe("control.x", lambda d: seen.append(d))
        msg = MaiMessage(type="control.x", payload={"v": 1})
        bus.publish_message(msg, wait=True)
        assert seen == [{"v": 1}]

    def test_receive_message_handler_gets_envelope(self):
        bus = _bus()
        seen = []
        bus.subscribe("control.x", lambda m: seen.append(m), receive_message=True)
        msg = MaiMessage(type="control.x", payload={"v": 1})
        bus.publish_message(msg, wait=True)
        assert isinstance(seen[0], MaiMessage)
        assert seen[0].payload == {"v": 1}
        assert seen[0].type == "control.x"

    def test_publish_message_async(self):
        bus = _bus()
        delivered = threading.Event()
        seen = []
        bus.subscribe("control.x", lambda d: (seen.append(d), delivered.set()))
        msg = MaiMessage(type="control.x", payload={"v": 1})
        bus.publish_message(msg)
        assert delivered.wait(5.0)
        assert seen == [{"v": 1}]
        bus.shutdown()

    def test_default_source_applied(self):
        bus = EventBus(default_source="test")
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert bus.traces()[-1]["source"] == "test"

    def test_explicit_source_overrides(self):
        bus = EventBus(default_source="test")
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {}, source="custom")
        assert bus.traces()[-1]["source"] == "custom"

    def test_wildcard_subscription(self):
        bus = EventBus()
        seen = []
        bus.subscribe("state.*", lambda d: seen.append(d.get("k")))
        bus.publish("state.memory.stored", {"k": 1})
        bus.publish("state.memory.retrieved", {"k": 2})
        bus.publish("control.x", {"k": 9})
        assert seen == [1, 2]

    def test_wildcard_does_not_match_sibling_namespace(self):
        bus = EventBus()
        seen = []
        bus.subscribe("state.*", lambda d: seen.append(1))
        bus.publish("control.shutdown", {})
        assert seen == []

    def test_exact_and_wildcard_both_deliver(self):
        bus = EventBus()
        seen = []
        bus.subscribe("state.a", lambda d: seen.append("exact"))
        bus.subscribe("state.*", lambda d: seen.append("wild"))
        bus.publish("state.a", {})
        assert sorted(seen) == ["exact", "wild"]


class TestPriorityScheduling:

    def test_high_jumps_background(self):
        bus = _bus(worker_count=1)
        order = []
        gate = threading.Event()

        def gate_handler(d):
            gate.wait(5.0)

        bus.subscribe("gate", gate_handler)
        bus.subscribe("bg", lambda d: order.append("bg"))
        bus.subscribe("hi", lambda d: order.append("hi"))

        bus.publish_message(MaiMessage(type="gate", priority=Priority.NORMAL))
        assert wait_for(lambda: bus._pool.info()["active"] == 1)
        bus.publish_message(MaiMessage(type="bg", priority=Priority.BACKGROUND))
        bus.publish_message(MaiMessage(type="hi", priority=Priority.HIGH))
        bus.publish_message(MaiMessage(type="hi", priority=Priority.HIGH))
        bus.publish_message(MaiMessage(type="bg", priority=Priority.BACKGROUND))
        gate.set()
        assert wait_for(lambda: len(order) == 4)
        assert order == ["hi", "hi", "bg", "bg"]
        bus.shutdown()

    def test_background_drop_oldest(self):
        bus = _bus(worker_count=1, max_queue=2)
        delivered = []
        gate = threading.Event()

        def gate_handler(d):
            gate.wait(5.0)

        bus.subscribe("gate", gate_handler)
        bus.subscribe("bg", lambda d: delivered.append(d["n"]))

        bus.publish_message(MaiMessage(type="gate", priority=Priority.NORMAL))
        assert wait_for(lambda: bus._pool.info()["active"] == 1)
        for n in (1, 2, 3):
            bus.publish_message(MaiMessage(
                type="bg", payload={"n": n}, priority=Priority.BACKGROUND))
        gate.set()
        assert wait_for(lambda: len(delivered) == 2)
        assert delivered == [2, 3]
        snap = bus._pool.queue_snapshot()
        assert snap["BACKGROUND"]["dropped"] == 1
        bus.shutdown()

    def test_bounded_concurrency(self):
        bus = _bus(worker_count=2)
        lock = threading.Lock()
        active = 0
        max_active = 0
        delivered = []
        done = threading.Event()

        def handler(d):
            nonlocal active, max_active
            with lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.05)
            delivered.append(d["n"])
            with lock:
                active -= 1
            if len(delivered) == 6:
                done.set()

        bus.subscribe("work", handler)
        for n in range(6):
            bus.publish_message(MaiMessage(type="work", payload={"n": n}))
        assert done.wait(5.0)
        assert max_active <= 2
        assert sorted(delivered) == list(range(6))
        bus.shutdown()


class TestMiddleware:

    def test_chain_order(self):
        bus = EventBus()
        order = []
        for name in MIDDLEWARE_ORDER:
            bus.set_middleware(name, lambda m, b, n=name: order.append(n))
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert order == list(MIDDLEWARE_ORDER)

    def test_unknown_slot_rejected(self):
        bus = EventBus()
        with pytest.raises(ValueError):
            bus.set_middleware("bogus", lambda m, b: None)

    def test_non_callable_rejected(self):
        bus = EventBus()
        with pytest.raises(TypeError):
            bus.set_middleware("validation", 42)

    def test_middleware_abort_blocks_delivery(self):
        bus = EventBus()
        seen = []
        bus.set_middleware("authorization", lambda m, b: (_ for _ in ()).throw(PermissionError("denied")))
        bus.subscribe("t", lambda d: seen.append(1))
        bus.publish("t", {})
        assert seen == []
        assert bus.stats()["failures"] == 1
        assert bus.traces()[-1]["error"].startswith("middleware:")

    def test_version_validation(self):
        bus = EventBus()
        bus.register_spec(EventSpec(name="control.v", version=1))
        seen = []
        bus.subscribe("control.v", lambda d: seen.append(1))
        msg = MaiMessage(type="control.v", version=2)
        bus.publish_message(msg, wait=True)
        assert seen == []
        assert bus.traces()[-1]["outcome"] == "FAILED"

    def test_legacy_skips_validation(self):
        bus = EventBus()
        bus.register_spec(EventSpec(name="control.v", version=1))
        seen = []
        bus.subscribe("control.v", lambda d: seen.append(1))
        bus.publish("control.v", {})  # version 0 legacy -> not validated
        assert seen == [1]


class TestRetry:

    def test_never_no_retry(self):
        bus = EventBus()
        calls = []

        def handler(d):
            calls.append(1)
            raise RuntimeError("boom")

        bus.subscribe("t", handler)
        bus.publish("t", {})
        assert len(calls) == 1
        assert bus.traces()[-1]["attempt"] == 1
        assert bus.traces()[-1]["outcome"] == "FAILED"

    def test_immediate_retry_until_success(self):
        bus = EventBus()
        bus.register_spec(EventSpec(
            name="control.r", retry=RetryPolicy.IMMEDIATE, max_attempts=3))
        calls = []

        def handler(d):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("not yet")

        bus.subscribe("control.r", handler)
        bus.publish_message(MaiMessage(type="control.r"), wait=True)
        assert len(calls) == 3
        assert bus.traces()[-1]["outcome"] == "SUCCESS"
        assert [t["attempt"] for t in bus.traces()] == [1, 2, 3]
        assert bus.stats()["failures"] == 2

    def test_immediate_exhausted(self):
        bus = EventBus()
        bus.register_spec(EventSpec(
            name="control.r", retry=RetryPolicy.IMMEDIATE, max_attempts=2))
        calls = []

        def handler(d):
            calls.append(1)
            raise RuntimeError("always")

        bus.subscribe("control.r", handler)
        bus.publish_message(MaiMessage(type="control.r"), wait=True)
        assert len(calls) == 2
        assert bus.traces()[-1]["outcome"] == "FAILED"

    def test_dead_letter_after_exhaustion(self):
        bus = EventBus()
        bus.register_spec(EventSpec(
            name="control.dl", retry=RetryPolicy.DEAD_LETTER, max_attempts=2))

        def handler(d):
            raise RuntimeError("poison")

        bus.subscribe("control.dl", handler)
        bus.publish_message(MaiMessage(type="control.dl"), wait=True)
        letters = bus.dead_letters()
        assert len(letters) == 1
        assert letters[0]["type"] == "control.dl"
        assert letters[0]["attempts"] == 2
        assert bus.stats()["dead_letters"] == 1

    def test_ignore_swallows(self):
        bus = EventBus()
        bus.register_spec(EventSpec(name="control.i", retry=RetryPolicy.IGNORE))

        def handler(d):
            raise RuntimeError("swallow me")

        bus.subscribe("control.i", handler)
        bus.publish_message(MaiMessage(type="control.i"), wait=True)
        assert bus.dead_letters() == []
        assert bus.traces()[-1]["outcome"] == "FAILED"

    def test_exponential_sync_backoff(self):
        bus = EventBus()
        bus.register_spec(EventSpec(
            name="control.e", retry=RetryPolicy.EXPONENTIAL, max_attempts=2))
        calls = []

        def handler(d):
            calls.append(1)
            raise RuntimeError("again")

        bus.subscribe("control.e", handler)
        t0 = time.time()
        bus.publish_message(MaiMessage(type="control.e"), wait=True)
        assert len(calls) == 2
        assert time.time() - t0 >= 0.04  # slept at least the base backoff
        assert [t["attempt"] for t in bus.traces()] == [1, 2]

    def test_retry_async_path(self):
        bus = EventBus()
        bus.register_spec(EventSpec(
            name="control.a", retry=RetryPolicy.IMMEDIATE, max_attempts=3))
        calls = []
        done = threading.Event()

        def handler(d):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("retry me")
            done.set()

        bus.subscribe("control.a", handler)
        bus.publish_message(MaiMessage(type="control.a"))
        assert done.wait(5.0)
        assert len(calls) == 3
        bus.shutdown()


class TestRequestResponse:

    def test_publish_wait_returns_results(self):
        bus = EventBus()
        bus.subscribe("q", lambda d: "a")
        bus.subscribe("q", lambda d: "b")
        results = bus.publish_wait("q", {})
        assert results == ["a", "b"]

    def test_request_first_non_none(self):
        bus = EventBus()
        bus.subscribe("q", lambda d: None)
        bus.subscribe("q", lambda d: 42)
        bus.subscribe("q", lambda d: "ignored")
        assert bus.request("q", {}) == 42

    def test_request_none_when_all_none(self):
        bus = EventBus()
        bus.subscribe("q", lambda d: None)
        assert bus.request("q", {}) is None

    def test_stream_yields_non_none(self):
        bus = EventBus()
        bus.subscribe("q", lambda d: None)
        bus.subscribe("q", lambda d: 1)
        bus.subscribe("q", lambda d: 2)
        assert list(bus.stream("q", {})) == [1, 2]

    def test_request_with_envelope(self):
        bus = _bus()
        bus.subscribe("data.query", lambda d: len(d.get("items", [])))
        assert bus.request(MaiMessage(type="data.query", payload={"items": [1, 2, 3]})) == 3


class TestTelemetry:

    def test_stats_counters(self):
        bus = EventBus()
        bus.subscribe("a", lambda d: None)
        bus.publish("a", {})
        bus.publish("a", {})
        bus.publish("b", {})
        stats = bus.stats()
        assert stats["total_published"] == 3
        assert stats["per_type"] == {"a": 2, "b": 1}
        assert stats["traces"] == 3
        assert set(stats["queue"].keys()) == {"CRITICAL", "HIGH", "NORMAL", "LOW", "BACKGROUND"}

    def test_trace_fields(self):
        bus = EventBus()
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        rec = bus.traces()[0]
        assert rec["type"] == "t"
        assert rec["outcome"] == "SUCCESS"
        assert rec["version"] == 0
        assert "execution_ms" in rec
        assert "subscribers" in rec

    def test_trace_filters(self):
        bus = EventBus()
        bus.subscribe("control.x", lambda d: None)
        bus.subscribe("data.y", lambda d: None)
        bus.publish("control.x", {})
        bus.publish("data.y", {})
        assert len(bus.traces({"type": "control"})) == 1
        assert len(bus.traces({"outcome": "SUCCESS"})) == 2
        assert len(bus.traces({"source": "nope"})) == 0

    def test_clear_traces(self):
        bus = EventBus()
        bus.publish("t", {})
        bus.clear_traces()
        assert bus.traces() == []
        assert bus.stats()["traces"] == 0

    def test_failure_counting(self):
        bus = EventBus()
        bus.subscribe("t", lambda d: (_ for _ in ()).throw(RuntimeError("x")))
        bus.publish("t", {})
        assert bus.stats()["failures"] == 1
        assert bus.stats()["type_failures"] == {"t": 1}


class TestCorrelationThroughBus:

    def test_publish_inherits_scope(self):
        bus = EventBus()
        bus.subscribe("t", lambda d: None)
        with correlation_scope("conversation_t1"):
            bus.publish("t", {})
        assert bus.traces()[-1]["correlation_id"] == "conversation_t1"

    def test_message_carries_own_correlation(self):
        bus = _bus()
        bus.subscribe("t", lambda d: None)
        msg = MaiMessage(type="t", correlation_id="conversation_own")
        bus.publish_message(msg, wait=True)
        assert bus.traces()[-1]["correlation_id"] == "conversation_own"

    def test_no_scope_no_correlation(self):
        bus = EventBus()
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert bus.traces()[-1]["correlation_id"] is None


class TestRegistryEnforcement:

    def test_unknown_semantic_topic_rejected(self):
        bus = _bus()
        seen = []
        bus.subscribe("control.unknown", lambda d: seen.append(d))
        msg = MaiMessage(type="control.unknown", payload={})
        bus.publish_message(msg, wait=True)
        assert seen == []
        assert bus.traces()[-1]["outcome"] == "FAILED"
        assert "Unknown event type" in bus.traces()[-1]["error"]
        assert bus.stats()["failures"] == 1

    def test_legacy_topic_still_allowed(self):
        bus = EventBus()
        seen = []
        bus.subscribe("anything.old", lambda d: seen.append(d))
        bus.publish("anything.old", {"ok": 1})
        assert seen == [{"ok": 1}]

    def test_authorization_denies_foreign_source(self):
        bus = _bus()
        bus.register_spec(EventSpec(
            name="data.private", publisher="memory", version=1))
        seen = []
        bus.subscribe("data.private", lambda d: seen.append(d))
        msg = MaiMessage(type="data.private", source="voice", payload={})
        bus.publish_message(msg, wait=True)
        assert seen == []
        assert bus.traces()[-1]["outcome"] == "FAILED"
        assert "not authorized" in bus.traces()[-1]["error"]

    def test_authorization_allows_declared_publisher(self):
        bus = _bus()
        bus.register_spec(EventSpec(
            name="data.private", publishers=("memory", "voice"), version=1))
        seen = []
        bus.subscribe("data.private", lambda d: seen.append(d))
        msg = MaiMessage(type="data.private", source="voice", payload={"v": 1})
        bus.publish_message(msg, wait=True)
        assert seen == [{"v": 1}]

    def test_open_spec_allows_any_source(self):
        bus = _bus()
        bus.register_spec(EventSpec(name="data.open", version=1))
        seen = []
        bus.subscribe("data.open", lambda d: seen.append(d))
        msg = MaiMessage(type="data.open", source="anything", payload={})
        bus.publish_message(msg, wait=True)
        assert seen == [{}]

    def test_compression_roundtrip(self):
        bus = _bus()
        bus.register_spec(EventSpec(name="data.big", version=1, compressed=True))
        seen = []
        bus.subscribe("data.big", lambda d: seen.append(d))
        big = {"blob": "x" * 2000, "n": 42}
        msg = MaiMessage(type="data.big", payload=big)
        bus.publish_message(msg, wait=True)
        assert seen == [big]
        rec = bus.traces()[-1]
        assert rec["outcome"] == "SUCCESS"

    def test_small_payload_not_compressed(self):
        bus = _bus()
        bus.register_spec(EventSpec(name="data.small", version=1, compressed=True))
        seen = []
        bus.subscribe("data.small", lambda d: seen.append(d))
        msg = MaiMessage(type="data.small", payload={"tiny": 1})
        bus.publish_message(msg, wait=True)
        assert seen == [{"tiny": 1}]

    def test_subscribe_version_gate_skips_mismatch(self):
        bus = _bus()
        bus.register_spec(EventSpec(name="data.v", version=1, supported_versions=(1, 2)))
        seen_old = []
        seen_new = []
        bus.subscribe("data.v", lambda d: seen_old.append(d), versions=(1,))
        bus.subscribe("data.v", lambda d: seen_new.append(d), versions=(2,))
        bus.publish_message(MaiMessage(type="data.v", version=1, payload={"v": 1}), wait=True)
        assert seen_old == [{"v": 1}]
        assert seen_new == []
        stats = bus.stats()
        assert stats["version_mismatches"] == 1
        assert stats["subscribers"] == 2

    def test_subscribe_without_versions_accepts_any(self):
        bus = _bus()
        bus.register_spec(EventSpec(name="data.v", version=1, supported_versions=(1, 2)))
        seen = []
        bus.subscribe("data.v", lambda d: seen.append(d))
        bus.publish_message(MaiMessage(type="data.v", version=2, payload={}), wait=True)
        assert seen == [{}]


class TestStreamTopicCoverage:
    """The SSE/WebSocket bridge must forward *every* ``state.*`` topic.

    Regression: STREAM_TOPICS was a hand-maintained list, so newly catalogued
    state topics (``state.monologue.generated``,
    ``state.needs.updated``, then the retrieval/tool pair) were published
    successfully yet silently dropped for every streaming client — the UI went
    stale with nothing in any log to explain why. It is now derived from the
    catalog; these tests pin that derivation.
    """

    def test_every_catalog_state_topic_is_forwarded(self):
        from api.stream_manager import STREAM_TOPICS
        from core.event_specs import VERTEX_SPECS

        catalog = {s.name for s in VERTEX_SPECS if s.name.startswith("state.")}
        assert catalog, "no state topics in the catalog"
        assert catalog <= set(STREAM_TOPICS)

    def test_no_non_state_topic_leaks_into_the_ui_stream(self):
        from api.stream_manager import STREAM_TOPICS

        assert [t for t in STREAM_TOPICS if not t.startswith("state.")] == []

    def test_wired_bus_delivers_every_state_topic_to_a_client(self):
        import asyncio

        from api.stream_manager import STREAM_TOPICS, StreamManager
        from core.event_specs import register_event_specs

        bus = EventBus(worker_count=2)
        register_event_specs(bus)
        mgr = StreamManager()
        mgr.wire(bus)

        queue = asyncio.Queue()

        class _Loop:
            @staticmethod
            def call_soon_threadsafe(fn, *args):
                fn(*args)

        mgr.add_queue(queue, _Loop)

        for topic in STREAM_TOPICS:
            bus.publish(topic, {})

        received = []
        for _ in STREAM_TOPICS:
            item = queue.get_nowait()
            received.append(json.loads(item)["topic"])

        assert sorted(received) == sorted(STREAM_TOPICS)
        bus.shutdown()


class TestLifecycle:

    def test_shutdown_idempotent(self):
        bus = EventBus()
        bus.publish_async("t", {})
        bus.shutdown()
        bus.shutdown()

    def test_pool_restartable_after_shutdown(self):
        bus = EventBus(worker_count=1)
        bus.shutdown()
        delivered = threading.Event()
        bus.subscribe("t", lambda d: delivered.set())
        bus.publish_async("t", {})
        assert delivered.wait(5.0)
        bus.shutdown()
