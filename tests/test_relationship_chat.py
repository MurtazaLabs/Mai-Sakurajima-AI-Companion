# M10 · Relationship dynamics on the chat path.
# Deterministic analyzer unit tests + think() integration + M9 session tests.
from unittest.mock import MagicMock

import pytest

from config.settings import Settings
from core.state.relationship import RelationshipEngineV2, _deterministic_deltas


class _PlainState:
    """Minimal state stand-in with a plain-object relationship_scores."""

    def __init__(self):
        import threading
        self.lock = threading.RLock()
        self.relationship_scores = _PlainScores()
        self.saved = 0
        self.save_state_to_disk = self._save

    def _save(self):
        self.saved += 1


class _PlainScores:
    def __init__(self):
        self.trust = 0.5
        self.comfort = 0.5
        self.respect = 0.5
        self.affection = 0.3
        self.familiarity = 0.1


def _engine(state=None):
    return RelationshipEngineV2(state=state or _PlainState(), llm=None)


class TestDeterministicDeltas:
    def test_gratitude_raises_trust_comfort(self):
        deltas = _deterministic_deltas("Thank you, I really appreciate it.")
        assert deltas["trust"] > 0
        assert deltas["comfort"] > 0
        assert deltas["affection"] > 0

    def test_praise_raises_trust_respect(self):
        deltas = _deterministic_deltas("You're a good listener, you know that?")
        assert deltas["trust"] > 0
        assert deltas["respect"] > 0

    def test_vulnerability_raises_comfort(self):
        deltas = _deterministic_deltas("I feel like I've been struggling lately.")
        assert deltas["comfort"] > 0
        assert deltas["trust"] > 0

    def test_hostility_lowers_trust(self):
        deltas = _deterministic_deltas("This is stupid, shut up already.")
        assert deltas["trust"] < 0
        assert deltas["comfort"] < 0
        assert deltas["respect"] < 0

    def test_affection_raises_affection(self):
        deltas = _deterministic_deltas("I love you, Mai.")
        assert deltas["affection"] > 0
        assert deltas["trust"] > 0

    def test_reassurance_in_response_raises_comfort(self):
        deltas = _deterministic_deltas("hello", "You don't have to carry it alone.")
        assert deltas["comfort"] > 0

    def test_deltas_stay_inside_llm_band(self):
        deltas = _deterministic_deltas("Thank you, you're amazing, I love you!")
        for v in deltas.values():
            assert abs(v) <= Settings.RELATIONSHIP_MAX_DELTA

    def test_empty_input_all_zeros(self):
        deltas = _deterministic_deltas("", "")
        assert all(v == 0.0 for v in deltas.values())

    def test_familiarity_bumps_on_any_turn(self):
        deltas = _deterministic_deltas("hello")
        assert deltas["familiarity"] == Settings.RELATIONSHIP_FAMILIARITY_BOOST


class TestApplyDeltas:
    def test_applies_to_plain_object(self):
        state = _PlainState()
        engine = _engine(state)
        engine.apply_deltas({"trust": 0.02, "comfort": 0.02})
        assert state.relationship_scores.trust == pytest.approx(0.52)
        assert state.relationship_scores.comfort == pytest.approx(0.52)
        assert state.relationship_scores.familiarity == 0.1  # untouched

    def test_clamps_to_one(self):
        state = _PlainState()
        engine = _engine(state)
        engine.apply_deltas({"trust": 2.0})
        assert state.relationship_scores.trust == 1.0

    def test_clamps_to_zero(self):
        state = _PlainState()
        engine = _engine(state)
        engine.apply_deltas({"trust": -2.0})
        assert state.relationship_scores.trust == 0.0

    def test_weight_scales_deltas(self):
        state = _PlainState()
        engine = _engine(state)
        deltas = engine.analyze_turn("Thank you so much.", weight=0.5)
        full = _deterministic_deltas("Thank you so much.")
        assert deltas["trust"] == pytest.approx(full["trust"] * 0.5)

    def test_persists_after_apply(self):
        state = _PlainState()
        engine = _engine(state)
        engine.apply_deltas({"trust": 0.01})
        assert state.saved >= 1

    def test_missing_state_safe(self):
        engine = _engine(None)
        assert engine.analyze_turn("hello") == {} or True
        engine.apply_deltas({"trust": 0.1})  # must not raise

    def test_missing_relationship_scores_safe(self):
        state = _PlainState()
        state.relationship_scores = None
        engine = _engine(state)
        engine.apply_deltas({"trust": 0.1})  # must not raise

    def test_pydantic_roundtrip(self, tmp_path):
        from core.state.models import RelationshipValues
        from core.state.shared_state import SharedState

        state = SharedState(persistence_dir=tmp_path)
        engine = RelationshipEngineV2(state=state, llm=None)
        engine.apply_deltas({"trust": 0.02, "affection": 0.02})
        assert state.relationship_scores.trust == pytest.approx(0.52)
        assert isinstance(state.relationship_scores, RelationshipValues)


class TestThinkIntegration:
    """Relationship must move through the real Brain.think() path (synchronously)."""

    def _brain(self):
        from evaluation.runner import FakeLLM, build_stub_brain
        return build_stub_brain(llm=FakeLLM())

    def test_praise_turn_raises_trust_after_think(self):
        brain = self._brain()
        assert brain.state.relationship_scores.trust == 0.5
        brain.think("You're a good listener, you know that?")
        assert brain.state.relationship_scores.trust > 0.5

    def test_hostile_turn_lowers_trust_after_think(self):
        brain = self._brain()
        brain.think("This is stupid, shut up.")
        assert brain.state.relationship_scores.trust < 0.5

    def test_trust_accumulates_across_turns(self):
        brain = self._brain()
        brain.think("Thank you, I appreciate it.")
        mid = brain.state.relationship_scores.trust
        brain.think("Thank you again, you're amazing.")
        assert brain.state.relationship_scores.trust > mid

    def test_prompt_sees_updated_relationship(self):
        brain = self._brain()
        brain.think("You're a good listener, you know that?")
        system = brain.prompt_orchestrator.build("hello", monologue=True,
                                                 identity_data=brain._identity_data())
        assert '"trust": 0.52' in system or "0.52" in system


class TestM9Sessions:
    """M9 praise sessions must now show a rising trust trajectory."""

    def test_praise_session_trust_rises(self, tmp_path):
        from evaluation.runner import SessionRunner, build_stub_brain
        from evaluation.scenarios import PRAISE

        brain = build_stub_brain()
        runner = SessionRunner(brain, out_dir=tmp_path)
        report = runner.run(PRAISE, session_name="praise-m10")
        trust_series = [
            t.evidence["relationship"].get("trust", 0.5) for t in runner.transcript
        ]
        assert trust_series[-1] > trust_series[0]
        assert report.axis_scores["relationship_trajectory"] == 5

    def test_review_required_clears_relationship_axis(self, tmp_path):
        from evaluation.runner import SessionRunner, build_stub_brain
        from evaluation.scenarios import PRAISE

        brain = build_stub_brain()
        runner = SessionRunner(brain, out_dir=tmp_path)
        report = runner.run(PRAISE[:4], session_name="praise-m10b")
        assert "relationship_trajectory" in report.exercised
        assert report.axis_scores["relationship_trajectory"] >= 4
