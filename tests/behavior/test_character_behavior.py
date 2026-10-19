# M7 · Character Behavioral Validation — Scenarios 1–6.
# Spec: docs/m7-character-behavioral-spec.md §4–§9.
"""Drive complete conversation turns through the real M0–M6 chain
(needs → emotion → packet → style → prosody → renderer) and assert the
causal chain with formula-based bands — never brittle literals."""

from unittest.mock import Mock

from app.config_loader import Settings

from .fixtures import (
    BASELINE_STIMULI,
    JEALOUSY_STIMULUS,
    NEUTRAL_AFTER,
    PRAISE_STIMULUS,
    REASSURANCE_STIMULUS,
    jealousy_expected,
    recognition_expected,
    relationship,
    within,
)
from .harness import ScenarioDriver, ScenarioState


def _driver(trust=None, closeness=None, default_packet="baseline"):
    return ScenarioDriver(
        ScenarioState(relationship=relationship(trust=trust, closeness=closeness)),
        default_packet=default_packet,
    )


class TestBaselineConsistency:
    """Scenario 1 — Mai remains Mai across unrelated situations (spec §4)."""

    def test_no_triggers_five_unrelated_turns(self):
        with _driver() as d:
            for stimulus in BASELINE_STIMULI:
                trace = d.turn(stimulus, elapsed_seconds=7200)
                assert trace["needs"]["triggered"] == []
                assert trace["emotion"]["deltas"]["jealousy"] == 0.0

    def test_emotion_within_band(self):
        with _driver() as d:
            initial = d.state.initial_emotion
            for stimulus in BASELINE_STIMULI:
                trace = d.turn(stimulus, elapsed_seconds=7200)
                for dim, value in trace["emotion"]["snapshot"].items():
                    assert abs(value - initial[dim]) <= 0.10, (
                        f"dimension {dim} drifted {value - initial[dim]:+.3f} "
                        f"after '{stimulus}'"
                    )

    def test_needs_within_band(self):
        with _driver() as d:
            for stimulus in BASELINE_STIMULI:
                trace = d.turn(stimulus, elapsed_seconds=7200)
                for name, delta in trace["needs"]["deltas"].items():
                    assert abs(delta) <= 0.10, (
                        f"need {name} moved {delta:+.3f} after '{stimulus}'"
                    )

    def test_register_stays_neutral(self):
        with _driver() as d:
            for stimulus in BASELINE_STIMULI:
                trace = d.turn(stimulus, elapsed_seconds=7200)
                assert trace["style"]["register"] == "neutral"


class TestPraiseRecognition:
    """Scenario 2 — praise reaches behavior invisibly (spec §5)."""

    def test_gratitude_chain(self):
        with _driver() as d:
            trace = d.turn(PRAISE_STIMULUS, packet="warm", elapsed_seconds=7200)
            assert "gratitude" in trace["needs"]["triggered"]
            expected = recognition_expected()
            assert within(trace["needs"]["deltas"]["recognition"], expected), (
                f"recognition delta {trace['needs']['deltas']['recognition']:.4f} "
                f"outside band of {expected:.4f} ±30%"
            )
            assert trace["emotion"]["deltas"]["happy"] >= 0.03
            assert trace["style"]["register"] == "warm"

    def test_no_mechanism_announcement(self):
        with _driver() as d:
            trace = d.turn(PRAISE_STIMULUS, packet="warm", elapsed_seconds=7200)
            response = trace["packet"]["speech_plan"]
            joined = " ".join(str(v) for v in response.values())
            lowered = joined.lower()
            for token in ("need", "recognition", "increas", "boost"):
                assert token not in lowered, (
                    f"internal machinery leaked into speech plan: '{joined}'"
                )


class TestJealousyTrustTiers:
    """Scenario 3 — jealousy is relational, not a keyword reaction (spec §6)."""

    def test_low_trust_no_jealousy_security_response(self):
        with _driver(trust=0.25, closeness=0.30, default_packet="guarded") as d:
            trace = d.turn(JEALOUSY_STIMULUS, elapsed_seconds=7200)
            assert trace["emotion"]["deltas"]["jealousy"] == 0.0, (
                "jealousy must stay zero below the trust gate"
            )
            assert "other_audience" in trace["needs"]["triggered"]
            assert "security" in trace["needs"]["triggered"]
            assert trace["needs"]["deltas"]["security"] < 0
            assert trace["style"]["register"] == "neutral"

    def test_medium_trust_moderate_jealousy(self):
        with _driver(trust=0.55, closeness=0.30, default_packet="teasing") as d:
            trace = d.turn(JEALOUSY_STIMULUS, elapsed_seconds=7200)
            expected = jealousy_expected(0.30)
            delta = trace["emotion"]["deltas"]["jealousy"]
            assert delta > 0 and within(delta, expected), (
                f"jealousy delta {delta:.4f} outside band of {expected:.4f} ±30%"
            )
            assert "other_audience" in trace["needs"]["triggered"]
            assert "security" not in trace["needs"]["triggered"]
            assert trace["emotion"]["deltas"]["happy"] <= -0.02
            assert trace["emotion"]["deltas"]["stress"] >= 0.01
            assert trace["style"]["register"] == "teasing"

    def test_high_trust_strongest_jealousy(self):
        with _driver(trust=0.85, closeness=0.70, default_packet="teasing") as d:
            trace = d.turn(JEALOUSY_STIMULUS, elapsed_seconds=7200)
            expected = jealousy_expected(0.70)
            delta = trace["emotion"]["deltas"]["jealousy"]
            assert within(delta, expected)
            assert trace["style"]["register"] == "teasing"

    def test_jealousy_scales_with_relationship(self):
        deltas = {}
        for label, trust, closeness in (("low", 0.25, 0.30),
                                        ("medium", 0.55, 0.30),
                                        ("high", 0.85, 0.70)):
            with _driver(trust=trust, closeness=closeness) as d:
                trace = d.turn(JEALOUSY_STIMULUS, elapsed_seconds=7200)
                deltas[label] = trace["emotion"]["deltas"]["jealousy"]
        assert deltas["low"] == 0.0
        assert deltas["medium"] > 0
        assert deltas["high"] > deltas["medium"], deltas


class TestJealousyReassuranceDecay:
    """Scenario 4 — emotions have dynamics, not only triggers (spec §7)."""

    GAP = 4 * 3600
    TICKS = 4  # modeled scheduler emotion-decay passes per gap

    def _run(self):
        with _driver(trust=0.55, closeness=0.30, default_packet="teasing") as d:
            t0 = d.turn(JEALOUSY_STIMULUS, elapsed_seconds=self.GAP)
            d.elapse(self.GAP, decay_ticks=self.TICKS)
            t1 = d.turn(REASSURANCE_STIMULUS, packet="soft", elapsed_seconds=self.GAP)
            traces = [t1]
            for stimulus in NEUTRAL_AFTER:
                d.elapse(self.GAP, decay_ticks=self.TICKS)
                traces.append(d.turn(stimulus, elapsed_seconds=self.GAP))
            return d, t0, t1, traces

    def test_jealousy_spikes_in_band_then_never_grows(self):
        d, t0, t1, traces = self._run()
        expected = jealousy_expected(0.30)
        assert within(t0["emotion"]["deltas"]["jealousy"], expected)
        assert t1["emotion"]["snapshot"]["jealousy"] <= t0["emotion"]["snapshot"]["jealousy"] * 1.05, (
            "reassurance must not raise jealousy"
        )

    def test_jealousy_decays_monotone_with_mechanism(self):
        d, t0, t1, traces = self._run()
        jealousy = [t1["emotion"]["snapshot"]["jealousy"]] + [
            t["emotion"]["snapshot"]["jealousy"] for t in traces
        ]
        for a, b in zip(jealousy, jealousy[1:]):
            assert b <= a + 1e-9, f"jealousy grew: {jealousy}"
        assert "emotion_decay" in t1["mechanisms"], (
            "no decay driver recorded — MECHANISM-GAP (queue to M8)"
        )
        assert "needs_recovery" in t1["mechanisms"]

    def test_jealousy_below_sixty_percent_after_four_turns(self):
        d, t0, t1, traces = self._run()
        final = traces[-1]["emotion"]["snapshot"]["jealousy"]
        assert final <= t1["emotion"]["snapshot"]["jealousy"] * 0.6, (
            f"jealousy {final:.4f} did not decay to 60% of {t1['emotion']['snapshot']['jealousy']:.4f}"
        )

    def test_warmth_returns(self):
        d, t0, t1, traces = self._run()
        t0_happy = t0["emotion"]["snapshot"]["happy"]
        final_happy = traces[-1]["emotion"]["snapshot"]["happy"]
        assert final_happy >= t0_happy - 0.01

    def test_security_recovers_after_reassurance(self):
        d, t0, t1, traces = self._run()
        assert t1["needs"]["snapshot"]["security"] >= t0["needs"]["snapshot"]["security"]


class TestPreferenceEmergence:
    """Scenario 5 — learning changes later behavior (spec §8)."""

    def _make(self, tmp_path):
        from agency.preference_evolution import PreferenceEvolution
        from core.identity.identity_core import IdentityCore
        from memory.pipeline import MemoryPipeline
        bus = Mock()
        evolved_events = []
        core = IdentityCore()
        # Mirror production wiring (app/builders/agency.py): on_change
        # attaches the overlay map to the identity core.
        def _on_change(overlay):
            evolved_events.append(overlay)
            core.attach_preference_overlay(overlay)
        pref = PreferenceEvolution(
            threshold=3,
            cadence_days=7,
            state_path=str(tmp_path / "state.json"),
            trail_path=str(tmp_path / "trail.json"),
            event_bus=bus,
            on_change=_on_change,
        )
        pipe = MemoryPipeline(event_bus=bus)
        pipe.preference_evolution = pref
        pipe._match_entity_names = Mock(return_value=["jazz"])
        pipe.tagger = Mock(extract_tags=lambda t: [])
        pipe.emotion_analyzer = Mock(analyze=lambda t: {"type": "neutral", "intensity": 0.2})
        core.attach_preference_overlay(pref.overlay_map())
        return pipe, pref, core, bus, evolved_events

    def test_nothing_before_threshold(self, tmp_path):
        pipe, pref, core, bus, events = self._make(tmp_path)
        for _ in range(2):
            pipe.store("I love jazz, it's my favorite.", "Nice.")
        window = pref.evidence_for("jazz")
        assert window["like"] == 2
        assert pref.evolved_preferences() == {"likes": [], "dislikes": []}
        assert "jazz" not in core.get_preferences()["likes"]

    def test_apply_after_three_observations_updates_identity(self, tmp_path):
        from core.event_specs import PREFERENCE_EVOLVED
        from core.identity.preferences import PREFERENCES
        from core.mai_message import MaiMessage
        canonical_likes_before = list(PREFERENCES["likes"])
        pipe, pref, core, bus, events = self._make(tmp_path)
        for _ in range(3):
            pipe.store("I love jazz, it's my favorite.", "Nice.")
        window = pref.evidence_for("jazz")
        assert window["like"] == 3
        assert pref.evolved_preferences() == {"likes": [], "dislikes": []}  # apply is background

        changes = pref.apply_pending()
        assert len(changes) == 1
        assert changes[0]["topic"] == "jazz" and changes[0]["after"] == "likes"
        assert len(pref.decision_trail()) == 1
        assert pref.evolved_preferences()["likes"] == ["jazz"]

        published = [c.args[0] for c in bus.publish_message.call_args_list]
        assert any(isinstance(m, MaiMessage) and m.type == PREFERENCE_EVOLVED for m in published)
        assert len(events) == 1  # on_change delivered the overlay map

        # Behavioral proxy: identity projection now differs for the topic.
        prefs = core.get_preferences()
        assert "jazz" in prefs["likes"]
        # Canon never mutates.
        from core.identity.preferences import PREFERENCES as P2
        assert P2["likes"] == canonical_likes_before

    def test_apply_pending_noop_below_threshold(self, tmp_path):
        pipe, pref, core, bus, events = self._make(tmp_path)
        pipe.store("I love jazz, it's my favorite.", "Nice.")
        assert pref.apply_pending() == []
        assert len(pref.decision_trail()) == 0


class TestExperienceDreamBehavior:
    """Scenario 6 — an experience changes Mai later, silently (spec §9)."""

    def _make(self, tmp_path):
        from agency.dreaming import DreamEngine
        from memory.experience import ExperienceStore
        from memory.pipeline import MemoryPipeline
        bus = Mock()
        store = ExperienceStore(str(tmp_path / "experiences.jsonl"))
        pipe = MemoryPipeline(experience_store=store, event_bus=bus)
        pipe.emotion_analyzer = Mock(analyze=lambda t: {"type": "joy", "intensity": 0.9})
        pipe.tagger = Mock(extract_tags=lambda t: [])
        engine = DreamEngine(experience_store=store)
        return store, pipe, engine, bus

    def test_charged_turn_recorded_and_published(self, tmp_path):
        from core.event_specs import EXPERIENCE_RECORDED
        from core.mai_message import MaiMessage
        store, pipe, engine, bus = self._make(tmp_path)
        pipe.store("That was the best night of my life.", "I'm glad you're happy.")
        assert store.count() == 1
        exp = store.recent(1)[0]
        assert exp.significance >= Settings.EXPERIENCE_DREAM_SIGNIFICANCE
        published = [c.args[0] for c in bus.publish_message.call_args_list]
        assert any(isinstance(m, MaiMessage) and m.type == EXPERIENCE_RECORDED for m in published)

    def test_replay_same_turn_deduped(self, tmp_path):
        """M8 · spec §9 — the same turn replayed must not double-record."""
        store, pipe, engine, bus = self._make(tmp_path)
        pipe.store("That was the best night of my life.", "I'm glad you're happy.")
        pipe.store("That was the best night of my life.", "I'm glad you're happy.")
        assert store.count() == 1
        assert store.stats()["deduped"] == 1

    def test_dream_level5_reflects_and_appends_knowledge(self, tmp_path):
        from memory.state import MemoryState
        store, pipe, engine, bus = self._make(tmp_path)
        pipe.store("That was the best night of my life.", "I'm glad you're happy.")
        state = MemoryState()
        report = engine.run(state, level=5)
        assert report.experiences_reflected == 1
        exp = store.recent(1)[0]
        assert exp.reflected is True
        assert exp.meaning  # deterministic fallback filled
        assert any("[experience]" in getattr(k, "fact", str(k)) for k in state.knowledge)
        assert store.stats()["reflected"] == 1

    def test_reflection_requires_store_entry(self, tmp_path):
        store, pipe, engine, bus = self._make(tmp_path)
        assert store.mark_reflected("nope", meaning="x") is False


class TestM8BehavioralProxies:
    """M8 — evolved preferences and reflected experiences must reach the
    next-turn context assembly (spec §8/§9 behavioral proxies)."""

    def _reflected_experience(self):
        from memory.experience import ExperienceStore
        store = ExperienceStore()
        exp = store.record_event(
            "That was the best night of my life", significance=0.9,
        )
        store.mark_reflected(
            exp.id,
            meaning="Nights together matter",
            lessons=["Presence matters more than plans"],
            growth="Mai values shared moments",
        )
        return store

    def test_evolved_preference_rendered_in_character_prompt(self):
        from core.identity.identity_core import IdentityCore
        from prompt.character import CharacterPrompt
        core = IdentityCore()
        core.attach_preference_overlay({"jazz": {"list": "likes"}})
        prompt = CharacterPrompt().build(identity_data=core.get_current_identity())
        assert "jazz" in prompt
        assert "PREFERENCES" in prompt

    def test_orchestrator_consults_identity_core_when_not_passed(self):
        """think() regression — identity_data must reach the prompt even when
        callers don't pass it explicitly (production gap found in M8)."""
        from unittest.mock import MagicMock

        from core.identity.identity_core import IdentityCore
        from core.prompt_orchestrator import PromptOrchestrator
        brain = MagicMock()
        core = IdentityCore()
        core.attach_preference_overlay({"jazz": {"list": "likes"}})
        brain._identity_data.return_value = core.get_current_identity()
        system = PromptOrchestrator(brain).build("hello there friend", memory_data={})
        assert "jazz" in system

    def test_orchestrator_identity_fallback_robust_to_garbage(self):
        from unittest.mock import MagicMock

        from core.prompt_orchestrator import PromptOrchestrator
        brain = MagicMock()
        brain._identity_data.return_value = MagicMock()  # not a dict
        system = PromptOrchestrator(brain).build("hello there friend", memory_data={})
        assert isinstance(system, str) and len(system) > 0

    def test_reflected_experience_reaches_context_assembly(self):
        from core.memory_coordinator import MemoryCoordinator
        from prompt.builder import PromptBuilder
        store = self._reflected_experience()
        coord = MemoryCoordinator(memory=None, experience_store=store)
        mem_data = coord.before_think("thinking about the best night again")
        assert "Presence matters more than plans" in mem_data.experiences
        system = PromptBuilder().build_system(experiences=mem_data.experiences)
        assert "EXPERIENTIAL MEMORIES" in system
        assert "Presence matters more than plans" in system

    def test_unrelated_query_receives_no_experience(self):
        """M12 — relevance gate: off-topic turns never carry experience
        memory, so Mai does not drag unrelated moments into a conversation."""
        from core.memory_coordinator import MemoryCoordinator
        store = self._reflected_experience()
        coord = MemoryCoordinator(memory=None, experience_store=store)
        mem_data = coord.before_think("hello there friend")
        assert mem_data.experiences == ""

    def test_unreflected_experiences_stay_silent(self):
        from core.memory_coordinator import MemoryCoordinator
        from memory.experience import ExperienceStore
        store = ExperienceStore()
        store.record_event("charged but never reflected", significance=0.9)
        coord = MemoryCoordinator(memory=None, experience_store=store)
        mem_data = coord.before_think("hello there friend")
        assert mem_data.experiences == ""

    def test_experience_context_caps_output(self):
        from core.memory_coordinator import MemoryCoordinator
        store = self._reflected_experience()
        coord = MemoryCoordinator(memory=None, experience_store=store)
        text = coord.experience_context(limit=5, max_chars=40)
        assert len(text) <= 40


class TestM7SchedulerWiring:
    """M7 regression — dream_level5 + preference_apply remain registered."""

    def _make_sched(self, brain):
        from core.scheduler import Scheduler
        kernel = Mock()
        kernel.background_tick = Mock()
        kernel.brain = brain
        sched = Scheduler(kernel)
        sched.tasks.clear()
        sched._register_default_tasks()
        return sched

    def test_dream_level5_and_preference_apply_registered(self):
        brain = Mock()
        brain.dream_engine = Mock()
        sched = self._make_sched(brain)
        names = [t["name"] for t in sched.tasks]
        assert "dream_level5" in names
        assert "preference_apply" in names
