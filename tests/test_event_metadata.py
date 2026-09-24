"""Payload-safe metadata extraction (Event Inspector Phase 3)."""
import time

import pytest

from core.event_metadata import (
    MetadataExtractorRegistry,
    extract_metadata,
    register_extractor,
)
from core.event_bus import EventBus
from core.mai_message import MaiMessage, Priority


def _capture_record(bus, type_, wait_ms=2000):
    deadline = time.time() + wait_ms / 1000
    while time.time() < deadline:
        for rec in bus.traces():
            if rec["type"] == type_:
                return rec
        time.sleep(0.01)
    raise AssertionError(f"no record captured for {type_}")


class TestRegistry:

    def test_unknown_type_no_metadata(self):
        assert extract_metadata("unknowable.thing", {"query": "secret"}) == {}

    def test_exact_type_match(self):
        meta = extract_metadata("data.memory.search", {"query": "garden", "result_count": 4})
        assert meta == {"query_len": 6, "result_count": 4}

    def test_prefix_match_highest_segment(self):
        reg = MetadataExtractorRegistry()
        reg.register("data", lambda p: {"any": True})
        reg.register("data.memory", lambda p: {"specialized": True})
        assert reg.extract("data.memory.search", {}) == {"specialized": True}

    def test_register_replaces_extractor(self):
        reg = MetadataExtractorRegistry()
        assert reg.known_prefixes()
        reg.register("data.memory", lambda p: {"x": 1})
        assert reg.extract("data.memory.search", {}) == {"x": 1}
        reg.unregister("data.memory")
        assert reg.extract("data.memory.search", {}) == {}

    def test_non_dict_payload_ignored(self):
        assert extract_metadata("data.tool.executed", "nope") == {}
        assert extract_metadata("data.tool.executed", None) == {}
        assert extract_metadata("data.tool.executed", ["x"]) == {}

    def test_extractor_error_safe(self):
        reg = MetadataExtractorRegistry()
        reg.register("boom", lambda p: 1 / 0)
        assert reg.extract("boom.x", {}) == {}


class TestDefaultExtractors:

    def test_speech_text_len_and_emotion(self):
        meta = extract_metadata(
            "control.speech.speak",
            {"text": "good morning", "emotion": "happy"},
        )
        assert meta["text_len"] == 12
        assert meta["emotion"] == "happy"

    def test_speech_unknown_emotion_rejected(self):
        meta = extract_metadata(
            "control.speech.speak", {"emotion": "suspicious-user-text"}
        )
        assert "emotion" not in meta

    def test_tool_name_allowlist(self):
        meta = extract_metadata(
            "data.tool.executed",
            {"name": "get_brain_state", "duration": 12, "success": True},
        )
        assert meta["tool_name"] == "get_brain_state"
        assert meta["duration_ms"] == 12
        assert meta["success"] is True

    def test_tool_unknown_name_rejected(self):
        meta = extract_metadata("data.tool.executed", {"name": "evil_exec"})
        assert "tool_name" not in meta

    def test_memory_query_len_and_type(self):
        meta = extract_metadata(
            "data.memory.store",
            {"query": "who am i", "memory_type": "semantic"},
        )
        assert meta["query_len"] == 8
        assert meta["memory_type"] == "semantic"

    def test_memory_non_allowlisted_type_rejected(self):
        meta = extract_metadata("data.memory.store", {"memory_type": "whatever"})
        assert "memory_type" not in meta

    def test_knowledge_result_count(self):
        meta = extract_metadata("data.knowledge.query", {"result_count": 7})
        assert meta["result_count"] == 7

    def test_reasoning_steps(self):
        meta = extract_metadata("control.reasoning.think", {"step_count": 3})
        assert meta["step_count"] == 3

    def test_dream_level_bounds(self):
        assert extract_metadata("dream.completed", {"level": 3}) == {"level": 3}
        assert extract_metadata("dream.completed", {"level": 9}) == {}
        assert extract_metadata("dream.completed", {"level": "3"}) == {}

    def test_system_action_allowlist(self):
        meta = extract_metadata("control.system.action", {"action": "open_app"})
        assert meta["action"] == "open_app"
        assert extract_metadata("control.system.action", {"action": "rm -rf /"}) == {}


class TestSafetyFilter:

    def test_no_free_text_values(self):
        meta = extract_metadata("data.memory.search", {"query": "x", "hit": "user's private note"})
        assert set(meta) == {"query_len"}

    def test_value_length_capped(self):
        meta = extract_metadata("data.memory.search", {"query": "y"})
        big = {"result_count": 1, "payload_text": "z" * 500}
        reg = MetadataExtractorRegistry()
        reg.register("x", lambda p: big)
        out = reg.extract("x.y", {})
        assert len(out) == 1
        assert "payload_text" not in out

    def test_key_count_capped(self):
        reg = MetadataExtractorRegistry()
        reg.register("noisy", lambda p: {f"k{i}": i for i in range(50)})
        out = reg.extract("noisy.x", {})
        assert len(out) <= 6

    def test_non_primitive_values_dropped(self):
        reg = MetadataExtractorRegistry()
        reg.register("obj", lambda p: {"blob": {"a": 1}, "arr": [1, 2], "ok": 3})
        out = reg.extract("obj.x", {})
        assert out == {"ok": 3}


class TestBusIntegration:

    def test_bus_trace_includes_metadata(self):
        bus = EventBus()
        bus.subscribe("data.memory.search", lambda d: None)
        bus.publish("data.memory.search", {"query": "garden", "result_count": 2})
        rec = _capture_record(bus, "data.memory.search")
        assert rec["metadata"] == {"query_len": 6, "result_count": 2}
        bus.shutdown()

    def test_bus_telemetry_carries_metadata(self):
        bus = EventBus()
        captured = []
        bus.subscribe("telemetry.inspector.record", lambda m: captured.append(m.payload), receive_message=True)
        bus.publish("data.tool.executed", {"name": "reason", "success": True})
        for _ in range(400):
            if any(r.get("type") == "data.tool.executed" for r in captured):
                break
            time.sleep(0.01)
        rec = next(r for r in captured if r.get("type") == "data.tool.executed")
        assert rec["metadata"]["tool_name"] == "reason"
        assert rec["metadata"]["success"] is True
        bus.shutdown()

    def test_telemetry_itself_has_no_metadata(self):
        bus = EventBus()
        bus.subscribe("t", lambda d: None)
        bus.publish("t", {"query": "zz"})
        assert _capture_record(bus, "t")["metadata"] == {}
        bus.shutdown()

    def test_default_metadata_never_contains_query_content(self):
        bus = EventBus()
        bus.subscribe("data.memory.search", lambda d: None)
        bus.publish("data.memory.search", {"query": "TOP SECRET", "result_count": 1})
        rec = _capture_record(bus, "data.memory.search")
        assert "TOP SECRET" not in json_safe(rec["metadata"])
        bus.shutdown()

    def test_register_extractor_runtime(self):
        register_extractor("data.custom", lambda p: {"n": int(p.get("n", 0))})
        bus = EventBus()
        bus.subscribe("data.custom.item", lambda d: None)
        bus.publish("data.custom.item", {"n": 5})
        rec = _capture_record(bus, "data.custom.item")
        assert rec["metadata"] == {"n": 5}
        bus.shutdown()


class TestPerfBudget:

    def test_extract_under_100us_average(self):
        registry = MetadataExtractorRegistry()
        payloads = [
            ("data.memory.search", {"query": "garden house", "result_count": 3}),
            ("control.speech.speak", {"text": "hi there", "emotion": "happy"}),
            ("data.tool.executed", {"name": "reason", "success": True}),
            ("some.unregistered.type", {"query": "secret"}),
        ]
        # warm-up
        for t, p in payloads * 200:
            registry.extract(t, p)
        start = time.perf_counter()
        n = 10000
        for _ in range(n):
            for t, p in payloads:
                registry.extract(t, p)
        elapsed = time.perf_counter() - start
        avg_us = elapsed / (n * len(payloads)) * 1e6
        assert avg_us < 100, f"extract avg {avg_us:.1f}us exceeded 100us budget"


def json_safe(obj):
    import json
    return json.dumps(obj)