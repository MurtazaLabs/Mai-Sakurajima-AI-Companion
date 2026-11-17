"""
Horizontal scaling tests for the Redis-backed shared-state layer.

Multiple Mai processes must be able to observe the same emotion state and the
same event stream without sticky sessions, so that any worker can serve any
request. That property lives entirely in RedisSharedState and RedisEventBus.

These tests skip when no Redis server is reachable rather than reporting a
pass, so the suite never overstates horizontal-scaling coverage.
"""
import sys
import time
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.event_bus_redis import RedisEventBus
from core.state.models import EmotionState
from core.state.redis_state import RedisConfig, RedisSharedState


def _make_state(name: str, base: Path) -> RedisSharedState:
    return RedisSharedState(
        persistence_dir=base / name,
        redis_config=RedisConfig(host="localhost", port=6379, max_connections=5),
    )


def test_emotion_state_roundtrip(tmp_path):
    """Emotion state survives a set/get cycle through the shared-state layer."""
    state = _make_state("test_redis_fallback", tmp_path)
    state.set_emotion(EmotionState(
        happy=0.8, sad=0.1, angry=0.05, anxious=0.1, neutral=0.05
    ))
    emotion = state.get_emotion()
    assert emotion.happy == pytest.approx(0.8)
    assert emotion.sad == pytest.approx(0.1)


def test_redis_state_sharing(tmp_path):
    """State written by one worker is visible to a different worker instance."""
    writer = _make_state("test_redis_fallback", tmp_path)
    if not writer.is_available():
        pytest.skip("Redis unavailable; cross-instance sharing cannot be verified")

    writer.set_emotion(EmotionState(
        happy=0.8, sad=0.1, angry=0.05, anxious=0.1, neutral=0.05
    ))

    # Separate instance, same Redis server.
    reader = _make_state("test_redis_fallback2", tmp_path)
    emotion = reader.get_emotion()
    assert emotion.happy == pytest.approx(0.8)


def test_event_bus_pubsub():
    """Events published by one worker reach a subscriber on another instance."""
    bus1 = RedisEventBus(worker_count=2, max_queue=100)
    bus2 = RedisEventBus(worker_count=2, max_queue=100)

    if not bus1._redis_available:
        pytest.skip("Redis unavailable; pub/sub across workers cannot be verified")

    received = []

    def handler(msg):
        received.append(msg.payload)

    # receive_message=True: the handler consumes the MaiMessage envelope, which
    # is what a cross-worker subscriber gets on the fabric path.
    bus1.subscribe("test.topic", handler, receive_message=True)
    time.sleep(0.1)  # Wait for subscription

    bus2.publish("test.topic", {"message": "hello from worker 2"})
    time.sleep(0.2)

    assert len(received) == 1
    assert received[0]["message"] == "hello from worker 2"
    bus1.shutdown()
    bus2.shutdown()


def test_registered_event_reaches_another_worker():
    """Semantic events (publish_event) must cross workers too, not just the
    legacy publish path — otherwise state.* / data.* fan-out dies the moment a
    second worker joins."""
    from core.event_specs import PARTNER_BRIEFING, register_event_specs
    from core.mai_message import publish_event

    bus1 = RedisEventBus(worker_count=1, max_queue=50)
    bus2 = RedisEventBus(worker_count=1, max_queue=50)
    if not bus1._redis_available:
        pytest.skip("Redis unavailable; cross-worker fan-out cannot be verified")
    register_event_specs(bus1)
    register_event_specs(bus2)

    received = []
    bus1.subscribe(
        PARTNER_BRIEFING,
        lambda msg: received.append(msg.payload),
        receive_message=True,
    )
    time.sleep(0.1)

    publish_event(bus2, PARTNER_BRIEFING, {"ritual": "morning", "text": "hi"}, source="partner")
    deadline = time.time() + 3
    while time.time() < deadline and not received:
        time.sleep(0.02)

    assert received == [{"ritual": "morning", "text": "hi"}]
    bus1.shutdown()
    bus2.shutdown()