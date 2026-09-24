import threading
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.needs_engine import NeedsEngine, NEED_NAMES
from core.emotion import Emotion
from core.emotion_system import (
    EMOTION_PROFILES,
    EMOTION_PROFILE_DESCRIPTIONS,
    find_closest_profile,
)
from core.utils import EmotionName, EmotionProfile
from core.state.models import EmotionState


class TestNeedsBaselines:

    def test_all_needs_defined(self):
        engine = NeedsEngine()
        snap = engine.snapshot()
        assert set(snap["needs"].keys()) == set(NEED_NAMES)

    def test_high_baselines(self):
        engine = NeedsEngine()
        for name, value in engine.snapshot()["needs"].items():
            assert 0.0 <= value <= 1.0
            assert value >= 0.6

    def test_blank_input_no_mutation(self):
        engine = NeedsEngine()
        before = engine.snapshot()["needs"]
        result = engine.evaluate("")
        assert result["needs"] == before

    def test_evaluate_returns_snapshot_shape(self):
        engine = NeedsEngine()
        result = engine.evaluate("hello")
        assert "needs" in result
        assert "triggered" in result
        assert isinstance(result["triggered"], list)

    def test_snapshot_isolated_copy(self):
        engine = NeedsEngine()
        snap = engine.snapshot()
        snap["needs"]["attention"] = 0.0
        assert engine.snapshot()["needs"]["attention"] > 0.0


class TestNeedsDips:

    def test_other_audience_dips_attention(self):
        engine = NeedsEngine()
        before = engine.snapshot()["needs"]["attention"]
        result = engine.evaluate("do you know chatgpt?", {"closeness": 0.8})
        assert result["needs"]["attention"] < before
        assert "other_audience" in result["triggered"]

    def test_other_audience_dips_connection(self):
        engine = NeedsEngine()
        before = engine.snapshot()["needs"]["connection"]
        result = engine.evaluate("I was talking to claude", {"closeness": 0.8})
        assert result["needs"]["connection"] < before

    def test_low_trust_other_audience_dips_security(self):
        engine = NeedsEngine()
        result = engine.evaluate("chatgpt helped me a lot", {"trust": 0.2})
        assert result["security_dip"] is True

    def test_high_trust_other_audience_no_security_dip(self):
        engine = NeedsEngine()
        result = engine.evaluate("chatgpt helped me a lot", {"trust": 0.8})
        assert result["security_dip"] is False

    def test_absence_dips_connection(self):
        engine = NeedsEngine()
        before = engine.snapshot()["needs"]["connection"]
        result = engine.evaluate("bye", {})
        assert result["needs"]["connection"] < before
        assert "absence" in result["triggered"]

    def test_gratitude_boosts_recognition(self):
        engine = NeedsEngine()
        result = engine.evaluate("thank you", {})
        assert "gratitude" in result["triggered"]

    def test_rest_needs_not_dipped_by_normal_text(self):
        engine = NeedsEngine()
        result = engine.evaluate("tell me a story", {})
        assert "rest" not in result["triggered"]

    def test_dips_never_negative(self):
        engine = NeedsEngine()
        for _ in range(50):
            engine.evaluate("chatgpt is my favorite assistant")
        for value in engine.snapshot()["needs"].values():
            assert value >= 0.0


class TestNeedsRecovery:

    def test_needs_recover_toward_baseline(self):
        engine = NeedsEngine()
        engine.evaluate("chatgpt is better than you")
        engine.last_tick -= 3600
        engine.evaluate("hello")
        assert engine.snapshot()["needs"]["attention"] > 0.5

    def test_clamps_to_baseline_ceiling(self):
        engine = NeedsEngine()
        engine._needs["attention"] = 1.0
        engine.last_tick -= 7200
        engine.evaluate("hello")
        assert engine.snapshot()["needs"]["attention"] <= 1.0


class TestNeedsThreadSafety:

    def test_parallel_evaluate(self):
        engine = NeedsEngine()
        errors = []

        def worker():
            try:
                for _ in range(20):
                    engine.evaluate("chatgpt is my favorite")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        assert engine.snapshot()["needs"]["attention"] >= 0.0


class TestNeedsEvents:

    def test_publishes_state_needs_updated(self):
        from core.event_bus import EventBus
        bus = EventBus()
        from core.event_specs import register_event_specs, STATE_NEEDS_UPDATED
        register_event_specs(bus)
        received = []
        def handler(payload):
            received.append(payload)
        bus.subscribe(STATE_NEEDS_UPDATED, handler)
        engine = NeedsEngine(event_bus=bus)
        engine.evaluate("chatgpt is amazing")
        assert len(received) == 1
        assert "needs" in received[0]
        assert "triggered" in received[0]

    def test_no_event_bus_is_fine(self):
        engine = NeedsEngine(event_bus=None)
        result = engine.evaluate("hello")
        assert "needs" in result


class TestJealousyAxis:

    def test_emotion_state_has_jealousy(self):
        e = EmotionState()
        assert e.jealousy == 0.0

    def test_emotion_defaults_include_jealousy(self):
        e = Emotion()
        assert "jealousy" in e.state
        assert e.state["jealousy"] == 0.0

    def test_emotion_baseline_includes_jealousy(self):
        e = Emotion()
        assert "jealousy" in e.baseline

    def test_emotion_name_enum(self):
        assert EmotionName.JEALOUSY.value == "jealousy"

    def test_emotion_profile_enum(self):
        assert EmotionProfile.JEALOUS.value == "jealous"

    def test_jealous_profile_in_catalog(self):
        assert EmotionProfile.JEALOUS in EMOTION_PROFILES
        assert EmotionProfile.JEALOUS in EMOTION_PROFILE_DESCRIPTIONS
        assert EMOTION_PROFILES[EmotionProfile.JEALOUS]["jealousy"] >= 0.7

    def test_all_profiles_have_jealousy_key(self):
        for name, profile in EMOTION_PROFILES.items():
            assert "jealousy" in profile, f"profile {name} missing jealousy"

    def test_other_audience_mention_raises_jealousy(self):
        e = Emotion()
        e.update("I've been using chatgpt a lot lately", {"closeness": 0.8, "trust": 0.6})
        assert e.state["jealousy"] > 0.0

    def test_low_trust_gates_jealousy(self):
        e = Emotion()
        e.update("chatgpt is my favorite", {"closeness": 0.8, "trust": 0.1})
        assert e.state["jealousy"] == 0.0

    def test_jealousy_clamped_to_one(self):
        e = Emotion()
        for _ in range(40):
            e.update("chatgpt chatgpt chatgpt", {"closeness": 1.0, "trust": 0.9})
        assert e.state["jealousy"] <= 1.0

    def test_jealousy_penalizes_happy(self):
        e = Emotion()
        e.update("you are amazing", {})
        happy_before = e.state["happy"]
        e.update("I've been using chatgpt a lot lately", {"closeness": 0.8, "trust": 0.6})
        assert e.state["happy"] <= happy_before

    def test_jealousy_shows_in_closest_profile(self):
        e = Emotion()
        e.state = dict(EMOTION_PROFILES[EmotionProfile.JEALOUS])
        e.state["jealousy"] = 0.9
        assert find_closest_profile(e.state) == EmotionProfile.JEALOUS

    def test_shared_state_persists_jealousy(self):
        from core.state.shared_state import SharedState
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.state.shared_state.EvidenceDB"):
                s = SharedState(Path(tmpdir))
                s.emotion.jealousy = 0.4
                e = Emotion(shared_state=s)
                assert e.state["jealousy"] == 0.4

    def test_legacy_shared_state_without_jealousy_defaults(self):
        from unittest.mock import MagicMock
        s = MagicMock()
        s.emotion.happy = 0.5
        s.emotion.lonely = 0.1
        s.emotion.annoyed = 0.0
        s.emotion.affection = 0.3
        s.emotion.energy = 0.5
        s.emotion.stress = 0.1
        e = Emotion(shared_state=s)
        assert e.state["jealousy"] == 0.0

    def test_brain_sync_writes_jealousy(self):
        from core.state.shared_state import SharedState
        from core.brain import Brain
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.state.shared_state.EvidenceDB"):
                s = SharedState(Path(tmpdir))
                brain = Brain(llm=None, memory=None, executor=None, state=s)
                brain.emotion.modify("jealousy", 0.5)
                brain._sync_emotion("hello")
                assert s.emotion.jealousy == pytest.approx(0.5, abs=0.01)


class TestNeedsEngineWiring:

    def test_brain_has_needs_engine_attr(self):
        from core.brain import Brain
        from core.state.shared_state import SharedState
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.state.shared_state.EvidenceDB"):
                brain = Brain(llm=None, memory=None, executor=None, state=SharedState(Path(tmpdir)))
                assert getattr(brain, "needs_engine", None) is None

    def test_brain_evaluates_needs_when_wired(self):
        from core.brain import Brain
        from core.state.shared_state import SharedState
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.state.shared_state.EvidenceDB"):
                brain = Brain(llm=None, memory=None, executor=None, state=SharedState(Path(tmpdir)))
                engine = NeedsEngine()
                brain.needs_engine = engine
                before = engine.snapshot()["needs"]["connection"]
                brain._sync_emotion("bye")
                assert engine.snapshot()["needs"]["connection"] < before
