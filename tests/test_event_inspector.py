"""Tests for the Event Inspector (observability/event_inspector.py) and its
EventBus telemetry hook + API routes."""
import json
import os
import threading
import time

import pytest
from fastapi.testclient import TestClient

from core.event_bus import EventBus
from core.event_registry import EventSpec, RetryPolicy
from core.mai_message import MaiMessage, Priority
from observability.event_inspector import DEFAULT_CAPACITY, EventInspector


def wait_for(predicate, timeout=8.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


# Topics published via MaiMessage (non-legacy) in this suite. Legacy
# ``publish()`` calls are exempt from registry validation.
_INSPECTOR_TOPICS = ("t", "a", "b", "c", "gate", "bg", "t2",
                     "control.a", "control.x", "data.b", "data.memory.search")


def _bus(*topics, **kwargs):
    bus = EventBus(**kwargs)
    for name in (_INSPECTOR_TOPICS + tuple(topics)):
        bus.register_spec(EventSpec(name=name))
    return bus


class TestCapture:

    def test_attaches_and_captures(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {"v": 1})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        rec = inspector.records(limit=1)[0]
        assert rec["type"] == "t"
        assert rec["correlation_id"] is None
        bus.shutdown()

    def test_async_message_capture(self):
        bus = _bus()
        inspector = EventInspector(event_bus=bus)
        delivered = threading.Event()
        bus.subscribe("t", lambda d: delivered.set())
        bus.publish_message(MaiMessage(type="t", payload={"v": 1}))
        assert delivered.wait(5.0)
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        bus.shutdown()

    def test_handlers_receive_envelope_for_telemetry(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] >= 1)
        rec = inspector.records(limit=1)[0]
        assert rec["type"] == "t"
        assert "<lambda>" in rec["subscribers"]
        assert "execution_ms" in rec
        bus.shutdown()

    def test_multiple_publishes_captured_in_order(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        for i in range(5):
            bus.publish("t", {"i": i})
        assert wait_for(lambda: inspector.stats()["captured"] == 5)
        newest = inspector.records(limit=1)[0]
        assert newest["type"] == "t"
        assert newest["attempt"] == 1
        bus.shutdown()


class TestRingBuffer:

    def test_capacity_drop_oldest(self):
        bus = EventBus()
        cap = 10
        inspector = EventInspector(capacity=cap, event_bus=bus)
        bus.subscribe("t", lambda d: None)
        total = cap + 5
        for i in range(total):
            bus.publish("t", {"i": i})
        deadline = time.time() + 8
        while time.time() < deadline and inspector.stats()["captured"] < total:
            time.sleep(0.02)
        assert inspector.stats()["buffered"] == cap
        assert inspector.stats()["overflow"] >= 5
        assert len(inspector.records(limit=total)) == cap
        bus.shutdown()

    def test_capacity_bounded_memory(self):
        bus = EventBus()
        inspector = EventInspector(capacity=25, event_bus=bus)
        bus.subscribe("t", lambda d: None)
        for i in range(50):
            bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] >= 25)
        deadline = time.time() + 8
        while time.time() < deadline and inspector.stats()["captured"] < 50:
            time.sleep(0.02)
        assert inspector.stats()["buffered"] == 25
        bus.shutdown()


class TestQueries:

    def test_type_prefix_filter(self):
        bus, inspector = self._seed(["control.a", "data.b", "control.c"])
        assert len(inspector.records({"type": "control"})) == 2
        assert len(inspector.records({"type": "data"})) == 1
        bus.shutdown()

    def test_outcome_and_source_filter(self):
        bus, inspector = self._seed(["t"])
        good = bus.traces()[0]
        assert len(inspector.records({"outcome": "SUCCESS"})) == 1
        assert len(inspector.records({"source": good["source"]})) >= 1
        bus.shutdown()

    def test_correlation_filter(self):
        bus = _bus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        bus.publish_message(MaiMessage(type="t", correlation_id="conversation_x", payload={}))
        bus.publish_message(MaiMessage(type="t", correlation_id="conversation_y", payload={}))
        assert wait_for(lambda: inspector.stats()["captured"] == 2)
        assert len(inspector.records({"correlation_id": "conversation_x"})) == 1
        bus.shutdown()

    def test_since_filter(self):
        bus = _bus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        bus.publish_message(MaiMessage(type="t", timestamp=time.time() - 1000, payload={}))
        bus.publish_message(MaiMessage(type="t", timestamp=time.time(), payload={}))
        assert wait_for(lambda: inspector.stats()["captured"] == 2)
        assert len(inspector.records({"since": time.time() - 100})) == 1
        bus.shutdown()

    def test_record_lookup(self):
        bus = _bus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {"v": 7})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        msg = MaiMessage(type="t", payload={})
        bus.publish_message(msg, wait=True)
        assert wait_for(lambda: inspector.stats()["captured"] == 2)
        found = inspector.record(msg.id)
        assert found is not None
        assert found["id"] == msg.id
        assert inspector.record("missing") is None
        bus.shutdown()

    def _seed(self, topics):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        for t in topics:
            bus.subscribe(t, lambda d: None)
            bus.publish(t, {})
        assert wait_for(lambda: inspector.stats()["captured"] == len(topics))
        return bus, inspector


class TestTraces:

    def test_causation_tree_depths(self):
        bus = _bus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("a", lambda d: None)
        bus.subscribe("b", lambda d: None)
        bus.subscribe("c", lambda d: None)
        root = MaiMessage(type="a", correlation_id="conversation_t1", source="brain")
        child = root.reply({}, type="b", target="brain")
        grandchild = child.reply({}, type="c", target="brain")
        bus.publish_message(root, wait=True)
        bus.publish_message(child, wait=True)
        bus.publish_message(grandchild, wait=True)
        assert wait_for(lambda: inspector.stats()["captured"] == 3)
        trace = inspector.trace("conversation_t1")
        assert trace["count"] == 3
        depths = {n["type"]: n["depth"] for n in trace["nodes"]}
        assert depths["a"] == 0
        assert depths["b"] == 1
        assert depths["c"] == 2

    def test_retries_share_causation(self):
        bus = EventBus()
        bus.register_spec(EventSpec(
            name="control.retry", retry=RetryPolicy.IMMEDIATE, max_attempts=3))
        inspector = EventInspector(event_bus=bus)
        calls = []

        def handler(d):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("again")
        bus.subscribe("control.retry", handler)
        msg = MaiMessage(type="control.retry", correlation_id="conversation_r1")
        bus.publish_message(msg, wait=True)
        assert wait_for(lambda: inspector.stats()["captured"] == 3)
        trace = inspector.trace("conversation_r1")
        attempts = sorted(n["attempt"] for n in trace["nodes"])
        assert attempts == [1, 2, 3]
        causation = {n["attempt"]: n["causation_id"] for n in trace["nodes"]}
        assert len(set(causation.values())) == 1

    def test_unknown_correlation_empty(self):
        inspector = EventInspector()
        trace = inspector.trace("conversation_nope")
        assert trace["count"] == 0
        assert trace["nodes"] == []

    def test_retries_filter(self):
        bus = EventBus()
        bus.register_spec(EventSpec(
            name="control.retry", retry=RetryPolicy.IMMEDIATE, max_attempts=3))
        inspector = EventInspector(event_bus=bus)
        calls = []

        def handler(d):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("again")
        bus.subscribe("control.retry", handler)
        bus.publish_message(MaiMessage(type="control.retry"), wait=True)
        assert wait_for(lambda: inspector.stats()["captured"] == 3)
        retried = inspector.records({"retries": 1})
        assert len(retried) == 2
        assert all(r["attempt"] > 1 for r in retried)
        assert len(inspector.records({"retries": None})) == 3
        bus.shutdown()


class TestStats:

    def test_subscriber_stats(self):
        bus, inspector = self._seed_topics(["t"])
        bus.subscribe("t", lambda d: None)
        for _ in range(4):
            bus.publish("t", {})
        assert wait_for(lambda: sum(s["count"] for s in inspector.subscriber_stats()) == 4)
        rows = inspector.subscriber_stats()
        names = [r["name"] for r in rows]
        assert "<lambda>" in names
        row = [r for r in rows if r["name"] == "<lambda>"][0]
        assert row["count"] == 4
        assert row["failures"] == 0
        bus.shutdown()

    def test_subscriber_failures(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)

        def bad(d):
            raise RuntimeError("x")
        bus.subscribe("t", bad)
        bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        rows = inspector.subscriber_stats()
        row = [r for r in rows if r["name"] == "bad"][0]
        assert row["failures"] == 1
        bus.shutdown()

    def test_latency_percentiles(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)

        def slow(d):
            time.sleep(0.01)
        bus.subscribe("t", slow)
        for _ in range(5):
            bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 5)
        rows = inspector.latency()
        row = [r for r in rows if r["type"] == "t"][0]
        assert row["count"] == 5
        assert row["p50"] > 0
        assert row["p95"] >= row["p50"]
        assert row["p99"] >= row["p95"]
        bus.shutdown()

    def test_latency_subscriber_scope(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        rows = inspector.latency(scope="subscriber")
        assert any(r["name"] == "<lambda>" for r in rows)

    def test_queue_snapshot_passthrough(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        snap = inspector.queue_snapshot()
        assert set(snap.keys()) == {"CRITICAL", "HIGH", "NORMAL", "LOW", "BACKGROUND"}
        assert inspector.queue_snapshot()["HIGH"]["max_queue"] > 0
        bus.shutdown()

    def test_queue_snapshot_oldest_wait(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        snap = inspector.queue_snapshot()
        for name in ("CRITICAL", "HIGH", "NORMAL", "LOW", "BACKGROUND"):
            assert "oldest_wait_ms" in snap[name]
            assert snap[name]["oldest_wait_ms"] >= 0
        bus.shutdown()

    def test_subscriber_types_aggregation(self):
        bus, inspector = self._seed_topics(["t"])
        bus.subscribe("t", lambda d: None)
        for _ in range(3):
            bus.publish("t", {})
        assert wait_for(lambda: sum(s["count"] for s in inspector.subscriber_stats()) == 3)
        row = [r for r in inspector.subscriber_stats() if r["name"] == "<lambda>"][0]
        assert row["types"] == {"t": 3}
        bus.shutdown()

    def _seed_topics(self, topics):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        for t in topics:
            bus.publish(t, {})
        return bus, inspector


class TestHealth:

    def test_ok_status(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        health = inspector.health()
        assert health["status"] in ("ok", "warn", "error")
        assert "window" in health["fabric"]
        assert len(health["fabric"]["window"]) >= 1
        assert health["fabric"]["traffic"]["messages"] >= 1
        bus.shutdown()

    def test_failure_rate_warning(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        bad = lambda d: (_ for _ in ()).throw(RuntimeError("boom"))  # noqa: E731
        bus.subscribe("t2", bad)
        for _ in range(9):
            bus.publish("t", {})
        bus.publish("t2", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 10)
        fabric = inspector.fabric_health()
        assert 0.05 < fabric["traffic"]["failure_rate"] <= 0.25
        assert fabric["status"] == "warn"
        assert any("failure rate" in w for w in fabric["warnings"])
        bus.shutdown()

    def test_dead_letter_health(self):
        bus = EventBus()
        bus.register_spec(EventSpec(
            name="control.poison", retry=RetryPolicy.DEAD_LETTER, max_attempts=2))
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("control.poison", lambda d: (_ for _ in ()).throw(RuntimeError("poison")))
        bus.publish_message(MaiMessage(type="control.poison"), wait=True)
        assert wait_for(lambda: len(inspector.dead_letters()) == 1)
        fabric = inspector.fabric_health()
        assert fabric["dead_letters_5m"] >= 1
        assert "dead letter" in " ".join(fabric["warnings"]).lower()
        bus.shutdown()

    def test_queue_saturation_warning(self):
        bus = _bus(worker_count=1, max_queue=1)
        inspector = EventInspector(event_bus=bus)
        gate = threading.Event()
        bus.subscribe("gate", lambda d: gate.wait(5.0))
        bus.publish_message(MaiMessage(type="gate", priority=Priority.NORMAL))
        assert wait_for(lambda: bus._pool.info()["active"] == 1)
        for _ in range(3):
            bus.publish_message(MaiMessage(type="bg", priority=Priority.BACKGROUND))
        fabric = inspector.fabric_health()
        assert fabric["queue"]["BACKGROUND"]["occupancy"] == 1
        assert any("saturated" in w for w in fabric["warnings"])
        gate.set()
        bus.shutdown()

    def test_health_registry_integration(self):
        from observability.health import HealthRegistry
        bus = EventBus()
        hr = HealthRegistry(event_bus=bus)
        inspector = EventInspector(event_bus=bus, health_registry=hr)
        assert "event_inspector" in hr
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        hr_stats = inspector.health()["components"]
        assert hr_stats is not None
        assert hr_stats["components"]["event_inspector"]["status"] == "ok"
        bus.shutdown()

    def test_shutdown_unregisters(self):
        from observability.health import HealthRegistry
        bus = EventBus()
        hr = HealthRegistry(event_bus=bus)
        inspector = EventInspector(event_bus=bus, health_registry=hr)
        inspector.shutdown()
        assert "event_inspector" not in hr
        bus.shutdown()


class TestExport:

    def test_export_writes_and_clears(self, tmp_path):
        bus = EventBus()
        log_dir = str(tmp_path / "inspector")
        inspector = EventInspector(log_dir=log_dir, event_bus=bus)
        bus.subscribe("t", lambda d: None)
        for i in range(3):
            bus.publish("t", {"i": i})
        assert wait_for(lambda: inspector.stats()["captured"] == 3)
        result = inspector.export()
        assert result["count"] == 3
        assert os.path.exists(result["path"])
        assert inspector.stats()["buffered"] == 0
        with open(result["path"], encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 3
        assert {l["type"] for l in lines} == {"t"}
        bus.shutdown()


class TestConcurrency:

    def test_parallel_publishers_no_loss(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus, capacity=2000)
        bus.subscribe("t", lambda d: None)
        errors = []

        def worker():
            try:
                for _ in range(10):
                    bus.publish("t", {})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=20)
        assert not errors
        assert wait_for(lambda: inspector.stats()["captured"] == 80)
        assert inspector.stats()["buffered"] == 80
        bus.shutdown()


class TestLoopGuard:

    def test_no_telemetry_recursion(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        for _ in range(3):
            bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 3)
        # no runaway — traces hold only the real messages, not telemetry echo
        deadline = time.time() + 2
        while time.time() < deadline:
            assert len(bus.traces()) == 3
            assert inspector.stats()["captured"] == 3
            time.sleep(0.05)
        bus.shutdown()

    def test_single_message_single_trace(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        assert len(bus.traces()) == 1
        bus.shutdown()

    def test_telemetry_disable(self):
        bus = EventBus()
        bus.enable_telemetry(False)
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        time.sleep(0.2)
        assert inspector.stats()["captured"] == 0
        bus.shutdown()


class TestOverflowEvent:

    def test_overflow_publishes_event(self):
        bus = EventBus()
        inspector = EventInspector(capacity=3, event_bus=bus)
        events = []
        bus.subscribe("telemetry.inspector.overflow", lambda d: events.append(d))
        bus.subscribe("t", lambda d: None)
        for i in range(10):
            bus.publish("t", {"i": i})
        deadline = time.time() + 8
        while time.time() < deadline and inspector.stats()["captured"] < 10:
            time.sleep(0.02)
        assert wait_for(lambda: len(events) >= 1)
        ev = events[0]
        assert ev["capacity"] == 3
        assert ev["overflow_total"] >= 1
        assert ev["dropped_type"] == "t"
        bus.shutdown()

    def test_overflow_records_never_recaptured(self):
        bus = EventBus()
        inspector = EventInspector(capacity=3, event_bus=bus)
        bus.subscribe("t", lambda d: None)
        for i in range(10):
            bus.publish("t", {"i": i})
        deadline = time.time() + 8
        while time.time() < deadline and inspector.stats()["captured"] < 10:
            time.sleep(0.02)
        deadline = time.time() + 1.5
        while time.time() < deadline:
            assert inspector.stats()["captured"] == 10
            time.sleep(0.05)
        types = {r["type"] for r in inspector.records(limit=100)}
        assert "telemetry.inspector.overflow" not in types
        bus.shutdown()


# ──────────────────────────────────────────────────────────────
#  API routes
# ──────────────────────────────────────────────────────────────

from unittest.mock import MagicMock, patch

from api.server import app as api_app


def _patch_mai(**attrs):
    return patch.multiple("api.server.mai", **attrs, create=True)


@pytest.fixture
def inspector_route_client():
    client = TestClient(api_app)
    yield client
    try:
        client.close()
    except Exception:
        pass


class TestAPIRoutes:

    def _make_inspector(self):
        bus = _bus()
        inspector = EventInspector(event_bus=bus)
        return bus, inspector

    def test_records_endpoint(self, inspector_route_client, tmp_path):
        bus, inspector = self._make_inspector()
        bus.subscribe("control.x", lambda d: None)
        bus.publish("control.x", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        with _patch_mai(inspector=inspector):
            r = inspector_route_client.get("/api/inspector/records")
            assert r.status_code == 200
            body = r.json()
            assert body["total"] == 1
            assert body["records"][0]["type"] == "control.x"
        bus.shutdown()

    def test_records_filter_type(self, inspector_route_client, tmp_path):
        bus, inspector = self._make_inspector()
        bus.subscribe("control.a", lambda d: None)
        bus.subscribe("data.b", lambda d: None)
        bus.publish("control.a", {})
        bus.publish("data.b", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 2)
        with _patch_mai(inspector=inspector):
            r = inspector_route_client.get("/api/inspector/records?type=control")
            assert r.status_code == 200
            assert r.json()["total"] == 1
        bus.shutdown()

    def test_record_endpoint(self, inspector_route_client, tmp_path):
        bus, inspector = self._make_inspector()
        msg = MaiMessage(type="t", payload={})
        bus.publish_message(msg, wait=True)
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        with _patch_mai(inspector=inspector):
            r = inspector_route_client.get(f"/api/inspector/record/{msg.id}")
            assert r.status_code == 200
            assert r.json()["record"]["id"] == msg.id
        bus.shutdown()

    def test_trace_endpoint(self, inspector_route_client, tmp_path):
        bus, inspector = self._make_inspector()
        msg = MaiMessage(type="t", correlation_id="conversation_api", payload={})
        bus.publish_message(msg, wait=True)
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        with _patch_mai(inspector=inspector):
            r = inspector_route_client.get("/api/inspector/trace/conversation_api")
            assert r.status_code == 200
            assert r.json()["count"] == 1
        bus.shutdown()

    def test_subscribers_endpoint(self, inspector_route_client, tmp_path):
        bus, inspector = self._make_inspector()
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        with _patch_mai(inspector=inspector):
            r = inspector_route_client.get("/api/inspector/subscribers")
            assert r.status_code == 200
            assert isinstance(r.json()["subscribers"], list)
        bus.shutdown()

    def test_queues_and_latency_endpoints(self, inspector_route_client, tmp_path):
        bus, inspector = self._make_inspector()
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        with _patch_mai(inspector=inspector):
            q = inspector_route_client.get("/api/inspector/queues")
            assert q.status_code == 200
            assert "BACKGROUND" in q.json()["queues"]
            assert "oldest_wait_ms" in q.json()["queues"]["HIGH"]
            l = inspector_route_client.get("/api/inspector/latency")
            assert l.status_code == 200
            assert any(row["type"] == "t" for row in l.json()["latency"])
        bus.shutdown()

    def test_dead_letters_endpoint(self, inspector_route_client, tmp_path):
        bus = EventBus()
        bus.register_spec(EventSpec(
            name="control.poison", retry=RetryPolicy.DEAD_LETTER, max_attempts=2))
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("control.poison", lambda d: (_ for _ in ()).throw(RuntimeError("poison")))
        bus.publish_message(MaiMessage(type="control.poison"), wait=True)
        assert wait_for(lambda: len(inspector.dead_letters()) == 1)
        with _patch_mai(inspector=inspector):
            r = inspector_route_client.get("/api/inspector/dead_letters")
            assert r.status_code == 200
            body = r.json()
            assert body["total"] == 1
            assert body["dead_letters"][0]["type"] == "control.poison"
        bus.shutdown()

    def test_records_retries_param(self, inspector_route_client, tmp_path):
        bus = EventBus()
        bus.register_spec(EventSpec(
            name="control.retry", retry=RetryPolicy.IMMEDIATE, max_attempts=3))
        inspector = EventInspector(event_bus=bus)
        calls = []

        def handler(d):
            calls.append(1)
            if len(calls) < 3:
                raise RuntimeError("again")
        bus.subscribe("control.retry", handler)
        bus.publish_message(MaiMessage(type="control.retry"), wait=True)
        assert wait_for(lambda: inspector.stats()["captured"] == 3)
        with _patch_mai(inspector=inspector):
            all_recs = inspector_route_client.get("/api/inspector/records")
            assert all_recs.json()["total"] == 3
            retried = inspector_route_client.get("/api/inspector/records?retries=1")
            assert retried.json()["total"] == 2
            assert all(r["attempt"] > 1 for r in retried.json()["records"])
        bus.shutdown()

    def test_health_and_summary(self, inspector_route_client, tmp_path):
        bus, inspector = self._make_inspector()
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        with _patch_mai(inspector=inspector):
            h = inspector_route_client.get("/api/inspector/health")
            assert h.status_code == 200
            assert "fabric" in h.json()
            s = inspector_route_client.get("/api/inspector/summary")
            assert s.status_code == 200
            assert s.json()["buffered"] == 1
        bus.shutdown()

    def test_export_endpoint(self, inspector_route_client, tmp_path):
        bus, inspector = self._make_inspector()
        inspector._log_dir = str(tmp_path / "inspector")
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        with _patch_mai(inspector=inspector):
            r = inspector_route_client.post("/api/inspector/export")
            assert r.status_code == 200
            assert r.json()["count"] == 1
        bus.shutdown()

    def test_unavailable_inspector(self, inspector_route_client):
        with _patch_mai(inspector=None):
            r = inspector_route_client.get("/api/inspector/records")
            assert r.status_code == 200
            assert r.json()["records"] == []
            s = inspector_route_client.get("/api/inspector/summary")
            assert s.status_code == 200
            assert s.json()["status"] == "unavailable"

    def test_inspector_page_served(self, inspector_route_client):
        r = inspector_route_client.get("/inspector")
        assert r.status_code == 200
        assert "Event Inspector" in r.text
        assert "js/inspector.js" in r.text


def _poisoned_record(record_id="msg_poison", correlation_id="conversation_x"):
    """A record that regressed to carry payload content (future-drift test)."""
    return {
        "id": record_id,
        "timestamp": time.time(),
        "type": "data.memory.search",
        "version": 1,
        "source": "test",
        "target": "",
        "priority": "NORMAL",
        "correlation_id": correlation_id,
        "causation_id": None,
        "outcome": "SUCCESS",
        "error": "x" * 500,
        "attempt": 1,
        "subscribers": ["handler_a"],
        "handler_times_ms": {"handler_a": 1.5, "bad": "nan"},
        "handler_failures": [],
        "queue_delay_ms": 0.1,
        "execution_ms": 1.5,
        "metadata": {"result_count": 3, "query": "TOP SECRET"},
        "payload": {"query": "TOP SECRET", "text": "user said something private"},
    }


def _inject(inspector, record):
    with inspector._lock:
        inspector._buffer.append(record)
        inspector._capture_count += 1


class TestSanitize:

    def test_sanitize_record_strips_payload_and_unknown(self):
        from core.event_metadata import sanitize_record
        out = sanitize_record(_poisoned_record())
        assert "payload" not in out
        assert "query" not in out["metadata"]
        assert out["metadata"] == {"result_count": 3}
        assert out["type"] == "data.memory.search"

    def test_sanitize_record_truncates_error_and_coerces(self):
        from core.event_metadata import sanitize_record
        out = sanitize_record(_poisoned_record())
        assert len(out["error"]) == 200
        assert out["handler_times_ms"] == {"handler_a": 1.5}
        assert out["attempt"] == 1

    def test_sanitize_record_non_dict_input(self):
        from core.event_metadata import sanitize_record
        assert sanitize_record(None) == {}
        assert sanitize_record(["x"]) == {}

    def test_records_query_never_leaks_payload(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus, capacity=50)
        _inject(inspector, _poisoned_record())
        out = inspector.records(limit=10)
        assert len(out) == 1
        rec = out[0]
        assert "payload" not in rec
        assert "TOP SECRET" not in json.dumps(rec)
        bus.shutdown()

    def test_record_detail_never_leaks_payload(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        _inject(inspector, _poisoned_record("msg_poison2"))
        rec = inspector.record("msg_poison2")
        assert rec is not None
        assert "payload" not in rec
        assert "TOP SECRET" not in json.dumps(rec)
        bus.shutdown()

    def test_trace_never_leaks_payload(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        _inject(inspector, _poisoned_record("msg_a", "conversation_x"))
        _inject(inspector, _poisoned_record("msg_b", "conversation_x"))
        trace = inspector.trace("conversation_x")
        assert trace["count"] == 2
        for node in trace["nodes"]:
            assert "payload" not in node
            assert "TOP SECRET" not in json.dumps(node)
        bus.shutdown()

    def test_export_never_leaks_payload(self, tmp_path):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus, log_dir=str(tmp_path / "insp"))
        _inject(inspector, _poisoned_record("msg_x", "conversation_y"))
        result = inspector.export()
        with open(result["path"], encoding="utf-8") as f:
            lines = [json.loads(line) for line in f if line.strip()]
        assert len(lines) == 1
        assert "payload" not in lines[0]
        assert "TOP SECRET" not in json.dumps(lines[0])
        bus.shutdown()

    def test_live_capture_records_stay_sanitized(self):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        bus.subscribe("data.memory.search", lambda d: None)
        bus.publish("data.memory.search", {"query": "private note", "result_count": 2})
        assert wait_for(lambda: inspector.stats()["captured"] == 1)
        rec = inspector.records(limit=1)[0]
        assert "payload" not in rec
        assert "private note" not in json.dumps(rec)
        assert rec["metadata"] == {"query_len": 12, "result_count": 2}
        bus.shutdown()

    def test_api_records_never_leaks_payload(self, inspector_route_client):
        bus = EventBus()
        inspector = EventInspector(event_bus=bus)
        _inject(inspector, _poisoned_record("msg_api", "conversation_api"))
        with _patch_mai(inspector=inspector):
            r = inspector_route_client.get("/api/inspector/records")
            assert r.status_code == 200
            body = r.text
            assert "payload" not in body
            assert "TOP SECRET" not in body
            rec = inspector_route_client.get("/api/inspector/record/msg_api")
            assert rec.status_code == 200
            assert "payload" not in rec.text
            tr = inspector_route_client.get("/api/inspector/trace/conversation_api")
            assert tr.status_code == 200
            assert "payload" not in tr.text
        bus.shutdown()