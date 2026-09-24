"""Tests for the MaiMessage envelope and correlation propagation."""
import threading

import pytest

from core.mai_message import (
    MaiMessage,
    Priority,
    clear_correlation,
    correlation_scope,
    current_correlation_id,
    ensure_correlation,
    legacy_message,
    new_correlation_id,
    new_message_id,
    set_correlation,
)


class TestMaiMessage:

    def test_round_trip(self):
        msg = MaiMessage(
            type="control.memory.store",
            payload={"content": "hello"},
            version=1,
            source="reasoning",
            target="memory",
            priority=Priority.HIGH,
            correlation_id="conversation_abc",
            causation_id="msg_parent",
        )
        restored = MaiMessage.from_dict(msg.to_dict())
        assert restored.type == msg.type
        assert restored.payload == msg.payload
        assert restored.version == msg.version
        assert restored.source == msg.source
        assert restored.target == msg.target
        assert restored.priority == Priority.HIGH
        assert restored.correlation_id == "conversation_abc"
        assert restored.causation_id == "msg_parent"
        assert restored.id == msg.id
        assert restored.timestamp == msg.timestamp

    def test_auto_ids_and_timestamp(self):
        msg = MaiMessage(type="data.x")
        assert msg.id.startswith("msg_")
        assert msg.timestamp > 0
        assert msg.correlation_id is None

    def test_priority_resolution(self):
        assert MaiMessage(type="t", priority="critical").priority is Priority.CRITICAL
        assert MaiMessage(type="t", priority="HIGH").priority is Priority.HIGH
        assert MaiMessage(type="t", priority=4).priority is Priority.BACKGROUND
        assert MaiMessage(type="t", priority="bogus").priority is Priority.NORMAL
        assert MaiMessage(type="t", priority=None).priority is Priority.NORMAL
        assert MaiMessage(type="t", priority=True).priority is Priority.NORMAL

    def test_type_required(self):
        with pytest.raises(ValueError):
            MaiMessage(type="")

    def test_non_dict_payload_wrapped(self):
        msg = MaiMessage(type="t", payload=42)
        assert msg.payload == {"value": 42}

    def test_namespace_classification(self):
        assert MaiMessage(type="control.x").namespace == "control"
        assert MaiMessage(type="data.x.y").namespace == "data"
        assert MaiMessage(type="state.x").namespace == "state"
        assert MaiMessage(type="legacy.topic").namespace == "legacy"

    def test_is_legacy_flag(self):
        assert legacy_message("some.topic").is_legacy is True
        assert MaiMessage(type="control.x").is_legacy is False

    def test_legacy_wrapper(self):
        data = {"a": 1}
        msg = legacy_message("some.topic", data, source="core")
        assert msg.type == "some.topic"
        assert msg.payload is data
        assert msg.version == 0
        assert msg.source == "core"
        assert msg.metadata["legacy"] is True

    def test_reply_links_causation(self):
        parent = MaiMessage(type="data.q", source="brain", target="memory",
                            correlation_id="conversation_1")
        reply = parent.reply({"answer": 42}, type="state.a", target="brain")
        assert reply.causation_id == parent.id
        assert reply.correlation_id == "conversation_1"
        assert reply.source == "memory"
        assert reply.target == "brain"
        assert reply.payload == {"answer": 42}

    def test_new_ids_are_unique(self):
        ids = {new_message_id() for _ in range(100)}
        assert len(ids) == 100
        cids = {new_correlation_id() for _ in range(100)}
        assert len(cids) == 100
        assert all(c.startswith("conversation_") for c in cids)


class TestCorrelation:

    def setup_method(self):
        clear_correlation()

    def teardown_method(self):
        clear_correlation()

    def test_set_get_clear(self):
        assert current_correlation_id() is None
        set_correlation("conversation_x")
        assert current_correlation_id() == "conversation_x"
        clear_correlation()
        assert current_correlation_id() is None

    def test_scope_sets_and_restores(self):
        set_correlation("outer")
        with correlation_scope("inner"):
            assert current_correlation_id() == "inner"
        assert current_correlation_id() == "outer"
        clear_correlation()

    def test_scope_without_value_generates_when_none(self):
        with correlation_scope() as cid:
            assert cid.startswith("conversation_")
            assert current_correlation_id() == cid
        assert current_correlation_id() is None

    def test_scope_inherits_outer_when_not_provided(self):
        set_correlation("outer")
        with correlation_scope() as cid:
            assert cid == "outer"
        assert current_correlation_id() == "outer"
        clear_correlation()

    def test_message_inherits_thread_local(self):
        with correlation_scope("conversation_tl"):
            msg = MaiMessage(type="data.inherit")
        assert msg.correlation_id == "conversation_tl"

    def test_scope_is_thread_local(self):
        results = {}
        set_correlation("main_thread")
        barrier = threading.Barrier(2)

        def worker():
            with correlation_scope("worker_cid"):
                results["worker"] = current_correlation_id()
            barrier.wait()

        t = threading.Thread(target=worker)
        t.start()
        barrier.wait()
        t.join()
        assert results["worker"] == "worker_cid"
        assert current_correlation_id() == "main_thread"
        clear_correlation()

    def test_ensure_correlation_reuses_active(self):
        set_correlation("conversation_x")
        with ensure_correlation("memory") as cid:
            assert cid == "conversation_x"
            assert current_correlation_id() == "conversation_x"
        assert current_correlation_id() == "conversation_x"
        clear_correlation()

    def test_ensure_correlation_seeds_when_none(self):
        clear_correlation()
        with ensure_correlation("voice") as cid:
            assert cid.startswith("voice_")
            assert current_correlation_id() == cid
        assert current_correlation_id() is None

    def test_ensure_correlation_restores_on_exit(self):
        clear_correlation()
        with ensure_correlation("memory"):
            assert current_correlation_id() is not None
        assert current_correlation_id() is None
