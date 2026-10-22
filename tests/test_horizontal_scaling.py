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

    bus1.subscribe("test.topic", handler)
    time.sleep(0.1)  # Wait for subscription

    bus2.publish("test.topic", {"message": "hello from worker 2"})
    time.sleep(0.2)

    assert len(received) == 1
    assert received[0]["message"] == "hello from worker 2"