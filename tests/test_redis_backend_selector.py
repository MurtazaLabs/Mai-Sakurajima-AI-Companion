"""Phase 2a — Redis backend selector (MAI_REDIS_URL) for the infrastructure builder.

Verifies:
- No MAI_REDIS_URL → the historical in-process EventBus + file-backed SharedState
  (default boot path unchanged).
- MAI_REDIS_URL set but Redis unreachable/malformed → clean fallback to the
  in-process backends with a warning (never breaks boot).
- MAI_REDIS_URL set and reachable → RedisEventBus + RedisSharedState, and
  RedisSharedState satisfies the full SharedState interface consumed by
  RelationshipEngineV2 / Brain / OsKernel (lock, db, state_dir, models).
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.builders.infrastructure import (
    REDIS_URL_ENV,
    _build_event_bus,
    _build_shared_state,
    _resolve_redis_client,
)
from core.event_bus import EventBus
from core.event_bus_redis import RedisEventBus
from core.state.db import EvidenceDB
from core.state.redis_state import RedisSharedState
from core.state.relationship import RelationshipEngineV2
from core.state.shared_state import SharedState


@pytest.fixture
def fake_redis():
    client = MagicMock()
    client.ping.return_value = True
    client.get.return_value = None  # fresh Redis: no master-state key yet
    return client


# ── Default path unchanged ────────────────────────────────────────


def test_unset_env_resolves_to_no_client(monkeypatch):
    monkeypatch.delenv(REDIS_URL_ENV, raising=False)
    assert _resolve_redis_client() is None


def test_default_backends_unchanged(monkeypatch, tmp_path):
    monkeypatch.delenv(REDIS_URL_ENV, raising=False)
    bus, bus_backend = _build_event_bus(None)
    state, state_backend = _build_shared_state(tmp_path, None)
    assert isinstance(bus, EventBus)
    assert bus_backend == "in-process"
    assert isinstance(state, SharedState)
    assert state_backend == "in-process"


# ── Opt-in gate degrades cleanly ──────────────────────────────────


def test_unreachable_redis_falls_back_to_no_client(monkeypatch):
    monkeypatch.setenv(REDIS_URL_ENV, "redis://127.0.0.1:1/0")
    assert _resolve_redis_client() is None


def test_malformed_url_falls_back_to_no_client(monkeypatch):
    monkeypatch.setenv(REDIS_URL_ENV, "::::not-a-redis-url")
    assert _resolve_redis_client() is None


def test_blank_url_ignored(monkeypatch):
    monkeypatch.setenv(REDIS_URL_ENV, "   ")
    assert _resolve_redis_client() is None


# ── Redis path wiring ─────────────────────────────────────────────


def test_redis_client_wires_redis_backends(monkeypatch, tmp_path, fake_redis):
    bus, bus_backend = _build_event_bus(fake_redis)
    state, state_backend = _build_shared_state(tmp_path, fake_redis)
    assert isinstance(bus, RedisEventBus)
    assert bus_backend == "redis"
    assert bus._redis_available is True
    assert isinstance(state, RedisSharedState)
    assert state_backend == "redis"
    assert state.is_available() is True


def test_redis_event_bus_dispatch(monkeypatch, tmp_path, fake_redis):
    bus, _ = _build_event_bus(fake_redis)
    received = []

    def handler(payload):
        received.append(payload)
        return payload

    bus.subscribe("selector.test", handler)
    results = bus.publish_wait("selector.test", {"value": 42})
    assert results == [{"value": 42}]
    assert received == [{"value": 42}]


# ── RedisSharedState interface parity (drop-in for SharedState) ──


def test_redis_shared_state_interface_parity(monkeypatch, tmp_path, fake_redis):
    state, backend = _build_shared_state(tmp_path, fake_redis)
    assert backend == "redis"

    # Public lock (used by RelationshipEngineV2, Brain, OsKernel)
    with state.lock:
        pass

    # SQLite evidence store (used by RelationshipEngineV2)
    assert isinstance(state.db, EvidenceDB)
    assert state.state_dir.exists()

    # Model attributes match SharedState's sub-states
    for attr in ("emotion", "relationship_scores", "goals", "attention", "runtime"):
        assert getattr(state, attr) is not None

    # Persistence API
    data = state.serialize()
    assert set(data) == {
        "emotion", "relationship_scores", "goals", "attention", "runtime",
    }
    state.save()
    assert (state.state_dir / "master_state.json").exists()
    state.load_state_from_disk()  # Redis-first path with fallback — must not raise


def test_relationship_engine_v2_works_on_redis_shared_state(
    monkeypatch, tmp_path, fake_redis
):
    state, _ = _build_shared_state(tmp_path, fake_redis)
    engine = RelationshipEngineV2(state=state, llm=None)

    # apply_deltas exercises state.lock + relationship_scores + save_state_to_disk
    engine.apply_deltas({"trust": 0.1})
    assert state.relationship_scores.trust == pytest.approx(0.6)

    # log_interaction_evidence exercises state.db (SQLite) + recalculation
    engine.log_interaction_evidence(
        event_type="test_event",
        description="parity check",
        impacts={"trust": 0.02},
    )
    evidence = state.db.get_all_evidence()
    assert len(evidence) == 1
    assert evidence[0]["event_type"] == "test_event"
