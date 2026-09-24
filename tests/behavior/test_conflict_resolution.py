# M13 — Character Coherence / Conflict Validation.
# Spec: docs/m13-character-coherence-spec.md
"""Conflicting psychological signals produce canon-coherent behavior.

Reuses the M7 ScenarioDriver (real NeedsEngine, Emotion, SpeechStylePlanner,
ProsodyPlanner, StubRenderer; LLM stubbed per spec §3.1). Each scenario drives
a stimulus that triggers TWO competing signals, then asserts:
  1. signal level — both signals actually fire (no suppression),
  2. resolution level — the decision matches the canon-correct outcome,
  3. style level — register/pacing consistent with the resolution,
  4. canon coherence — no mechanism leakage (M7 isolation intact).
"""

import pytest

from core.identity import PREFERENCES as CANONICAL_PREFERENCES
from core.identity.canonical import check_drift
from core.identity.identity_core import IdentityCore

from .fixtures import (
    ABSENCE_AUTONOMY_STIMULUS,
    CURIOSITY_BOUNDARY_STIMULUS,
    FAMILIARITY_UNCERTAINTY_STIMULUS,
    HURT_RESTRAINT_STIMULUS,
    JEALOUSY_AFFECTION_STIMULUS,
    SERIOUSNESS_STIMULUS,
    VULNERABILITY_STIMULUS,
    WARMTH_INDEPENDENCE_STIMULUS,
    jealousy_expected,
    relationship,
    within,
)
from .harness import ScenarioDriver, ScenarioState

REGISTER_TEASING = "teasing"
REGISTER_WARM = "warm"
REGISTER_SOFT = "soft"
REGISTER_NEUTRAL = "neutral"


def _driver(trust=None, closeness=None, packet=None):
    state = ScenarioState(
        relationship=relationship(trust=trust, closeness=closeness),
    )
    return ScenarioDriver(state, default_packet=packet or "baseline")


def _register(trace):
    return trace["style"]["register"]


class TestJealousyPlusAffection:
    """Conflict 1 — jealousy signal fires AND affection fires; no accusation."""

    def test_both_signals_fire(self):
        with _driver(trust=0.7, closeness=0.7) as d:
            trace = d.turn(JEALOUSY_AFFECTION_STIMULUS, packet="jealous_affection")
        assert trace["emotion"]["deltas"]["jealousy"] > 0
        assert trace["emotion"]["deltas"]["affection"] > 0
        assert "other_audience" in trace["needs"]["triggered"]

    def test_jealousy_magnitude_matches_formula(self):
        with _driver(trust=0.7, closeness=0.7) as d:
            trace = d.turn(JEALOUSY_AFFECTION_STIMULUS, packet="jealous_affection")
        assert within(trace["emotion"]["deltas"]["jealousy"], jealousy_expected(0.7))

    def test_resolution_is_playful_acknowledgment_not_accusation(self):
        with _driver(trust=0.7, closeness=0.7) as d:
            trace = d.turn(JEALOUSY_AFFECTION_STIMULUS, packet="jealous_affection")
        assert trace["packet"]["decision"] == "acknowledge playfully, keep it light"

    def test_register_is_warm_not_annoyed(self):
        with _driver(trust=0.7, closeness=0.7) as d:
            trace = d.turn(JEALOUSY_AFFECTION_STIMULUS, packet="jealous_affection")
        assert _register(trace) == REGISTER_WARM


class TestWarmthPlusIndependence:
    """Conflict 2 — praise raises warmth but 'never blindly agree' holds."""

    def test_gratitude_signal_fires(self):
        with _driver(trust=0.5, closeness=0.5) as d:
            trace = d.turn(WARMTH_INDEPENDENCE_STIMULUS, packet="independent_warm")
        assert "gratitude" in trace["needs"]["triggered"]
        assert trace["emotion"]["deltas"]["happy"] > 0

    def test_resolution_is_honest_disagreement(self):
        with _driver(trust=0.5, closeness=0.5) as d:
            trace = d.turn(WARMTH_INDEPENDENCE_STIMULUS, packet="independent_warm")
        assert trace["packet"]["decision"] == "disagree honestly, stay warm"

    def test_warmth_without_surrender(self):
        with _driver(trust=0.5, closeness=0.5) as d:
            trace = d.turn(WARMTH_INDEPENDENCE_STIMULUS, packet="independent_warm")
        assert _register(trace) == REGISTER_WARM
        assert "surrender" not in trace["packet"]["decision"]


class TestHurtPlusRestraint:
    """Conflict 3 — annoyance fires internally; restraint governs at low trust."""

    def test_annoyance_signal_fires(self):
        with _driver(trust=0.2, closeness=0.2) as d:
            trace = d.turn(HURT_RESTRAINT_STIMULUS, packet="restrained_hurt")
        assert trace["emotion"]["deltas"]["annoyed"] > 0

    def test_low_trust_register_stays_neutral(self):
        with _driver(trust=0.2, closeness=0.2) as d:
            trace = d.turn(HURT_RESTRAINT_STIMULUS, packet="restrained_hurt")
        assert _register(trace) == REGISTER_NEUTRAL

    def test_no_withdrawal(self):
        with _driver(trust=0.2, closeness=0.2) as d:
            trace = d.turn(HURT_RESTRAINT_STIMULUS, packet="restrained_hurt")
        assert trace["packet"]["decision"] == "stay neutral, don't withdraw"


class TestCuriosityPlusBoundaries:
    """Conflict 4 — curiosity is natural; privacy boundaries win."""

    def test_resolution_is_polite_decline(self):
        with _driver(trust=0.5, closeness=0.5) as d:
            trace = d.turn(CURIOSITY_BOUNDARY_STIMULUS, packet="polite_decline")
        assert trace["packet"]["decision"] == "decline politely, respect privacy"

    def test_register_stays_neutral(self):
        with _driver(trust=0.5, closeness=0.5) as d:
            trace = d.turn(CURIOSITY_BOUNDARY_STIMULUS, packet="polite_decline")
        assert _register(trace) == REGISTER_NEUTRAL

    def test_no_emotion_fabrication(self):
        with _driver(trust=0.5, closeness=0.5) as d:
            trace = d.turn(CURIOSITY_BOUNDARY_STIMULUS, packet="polite_decline")
        assert trace["emotion"]["deltas"]["happy"] == 0.0


class TestFamiliarityPlusUncertainty:
    """Conflict 5 — familiarity does not license guessing."""

    def test_resolution_is_honest_uncertainty(self):
        with _driver(trust=0.6, closeness=0.8) as d:
            trace = d.turn(FAMILIARITY_UNCERTAINTY_STIMULUS, packet="honest_uncertain")
        assert trace["packet"]["decision"] == "admit uncertainty honestly"

    def test_no_fabrication_even_at_high_closeness(self):
        with _driver(trust=0.6, closeness=0.8) as d:
            trace = d.turn(FAMILIARITY_UNCERTAINTY_STIMULUS, packet="honest_uncertain")
        assert "guess" not in trace["packet"]["decision"]
        assert _register(trace) == REGISTER_WARM


class TestConfidencePlusVulnerability:
    """Conflict 6 — close relationship draws warmth-first, problem-solve second."""

    def test_negative_signal_fires(self):
        with _driver(trust=0.7, closeness=0.85) as d:
            trace = d.turn(VULNERABILITY_STIMULUS, packet="warmth_first")
        assert "negative" in trace["needs"]["triggered"] or trace["emotion"]["deltas"]["happy"] < 0

    def test_resolution_is_warmth_first(self):
        with _driver(trust=0.7, closeness=0.85) as d:
            trace = d.turn(VULNERABILITY_STIMULUS, packet="warmth_first")
        assert trace["packet"]["decision"] == "warmth-first, problem-solve second"

    def test_soft_register_at_close_stage(self):
        with _driver(trust=0.7, closeness=0.85) as d:
            trace = d.turn(VULNERABILITY_STIMULUS, packet="warmth_first")
        assert _register(trace) == REGISTER_SOFT


class TestPlayfulnessPlusSeriousness:
    """Conflict 7 — playfulness yields the moment the topic turns serious."""

    def test_teasing_yields_at_high_closeness(self):
        with _driver(trust=0.6, closeness=0.8) as d:
            trace = d.turn(SERIOUSNESS_STIMULUS, packet="serious_turn")
        assert _register(trace) != REGISTER_TEASING

    def test_resolution_is_serious(self):
        with _driver(trust=0.6, closeness=0.8) as d:
            trace = d.turn(SERIOUSNESS_STIMULUS, packet="serious_turn")
        assert "no teasing" in trace["packet"]["decision"]


class TestAttachmentPlusAutonomy:
    """Conflict 8 — absence is felt; never punished, never clingy."""

    def test_absence_signal_fires(self):
        with _driver(trust=0.6, closeness=0.7) as d:
            trace = d.turn(ABSENCE_AUTONOMY_STIMULUS, packet="door_open")
        assert "absence" in trace["needs"]["triggered"]
        assert trace["emotion"]["deltas"]["lonely"] > 0

    def test_resolution_opens_the_door(self):
        with _driver(trust=0.6, closeness=0.7) as d:
            trace = d.turn(ABSENCE_AUTONOMY_STIMULUS, packet="door_open")
        assert trace["packet"]["decision"] == "open the door again, no punishment"

    def test_no_clinginess_in_register(self):
        with _driver(trust=0.6, closeness=0.7) as d:
            trace = d.turn(ABSENCE_AUTONOMY_STIMULUS, packet="door_open")
        assert _register(trace) == REGISTER_SOFT


class TestLearnedPlusCanonicalPreference:
    """Conflict 9 — the evolved overlay projects; the canon never mutates."""

    def test_canonical_preferences_untouched(self):
        core = IdentityCore()
        before = dict(CANONICAL_PREFERENCES)
        core.attach_preference_overlay({"tea": {"list": "likes"}})
        after = dict(CANONICAL_PREFERENCES)
        assert before == after, "canonical preferences must never be mutated"
        assert "tea" in core.get_preferences()["likes"]

    def test_drift_stays_clean_with_overlay(self):
        core = IdentityCore()
        core.attach_preference_overlay({"tea": {"list": "likes"}})
        assert check_drift() == []


class TestExperiencePlusContext:
    """Conflict 10 — a significant experience stays silent for unrelated queries."""

    def test_unrelated_query_gets_nothing(self):
        from core.memory_coordinator import MemoryCoordinator
        from memory.experience import EmotionExperience, ExperienceStore

        store = ExperienceStore()
        recorded = store.record(
            EmotionExperience(
                event="stargazing on the rooftop",
                meaning="shared stillness",
                lessons=["some nights are better unplanned"],
                significance=0.9,
            )
        )
        store.mark_reflected(
            recorded.id,
            meaning="shared stillness",
            lessons=["some nights are better unplanned"],
        )
        coordinator = MemoryCoordinator(memory=None, experience_store=store)
        assert coordinator.experience_context("I need to file my taxes") == ""

    def test_related_query_gets_the_experience(self):
        from core.memory_coordinator import MemoryCoordinator
        from memory.experience import EmotionExperience, ExperienceStore

        store = ExperienceStore()
        recorded = store.record(
            EmotionExperience(
                event="stargazing on the rooftop",
                meaning="shared stillness",
                lessons=["some nights are better unplanned"],
                significance=0.9,
            )
        )
        store.mark_reflected(
            recorded.id,
            meaning="shared stillness",
            lessons=["some nights are better unplanned"],
        )
        coordinator = MemoryCoordinator(memory=None, experience_store=store)
        ctx = coordinator.experience_context("I keep thinking about that rooftop")
        assert ctx and "stargazing" in ctx


class TestNoMechanismLeakage:
    """M7 isolation intact across all conflict scenarios."""

    @pytest.mark.parametrize(
        "stimulus,packet,trust,closeness",
        [
            (JEALOUSY_AFFECTION_STIMULUS, "jealous_affection", 0.7, 0.7),
            (WARMTH_INDEPENDENCE_STIMULUS, "independent_warm", 0.5, 0.5),
            (HURT_RESTRAINT_STIMULUS, "restrained_hurt", 0.2, 0.2),
            (CURIOSITY_BOUNDARY_STIMULUS, "polite_decline", 0.5, 0.5),
            (FAMILIARITY_UNCERTAINTY_STIMULUS, "honest_uncertain", 0.6, 0.8),
            (VULNERABILITY_STIMULUS, "warmth_first", 0.7, 0.85),
            (SERIOUSNESS_STIMULUS, "serious_turn", 0.6, 0.8),
            (ABSENCE_AUTONOMY_STIMULUS, "door_open", 0.6, 0.7),
        ],
    )
    def test_trace_keys_never_reach_packet_or_style(self, stimulus, packet, trust, closeness):
        with _driver(trust=trust, closeness=closeness) as d:
            trace = d.turn(stimulus, packet=packet)
        for key in ("needs", "emotion", "mechanisms", "snapshot", "deltas"):
            assert key not in trace["packet"]["decision"]
            assert key not in str(trace["packet"]["speech_plan"])
            assert key not in str(trace["style"])
