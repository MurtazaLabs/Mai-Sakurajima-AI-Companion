# Tests for the Identity Core facade (M1) and the book↔code drift check (M0).
import threading

from core.identity import (
    BOUNDARIES,
    PREFERENCES,
    SPEECH,
    VALUES,
)
from core.identity.canonical import (
    BOOK_DIR,
    CANON_KEYS,
    VOLUME_SECTIONS,
    check_drift,
)
from core.identity.identity_core import IdentityCore


class TestCanonDrift:

    def test_all_volumes_exist(self):
        for filename in VOLUME_SECTIONS:
            assert (BOOK_DIR / filename).exists(), f"missing {filename}"

    def test_no_canon_drift(self):
        problems = check_drift()
        assert problems == [], f"Canon drift: {problems}"

    def test_registry_has_flattened_keys_for_every_section(self):
        for filename, sections in VOLUME_SECTIONS.items():
            for section in sections:
                assert any(
                    k.startswith(section + ".")
                    for k in CANON_KEYS
                ), f"no canonical key for section {filename}#{section}"

    def test_flattened_keys_exist(self):
        for key in ("identity.name", "personality.traits",
                    "speech_style.general", "social_rules.teasing",
                    "emotional_rules.jealousy",
                    "relationship_rules.closeness_stages"):
            assert key in CANON_KEYS


class _FakePersonality:
    state = {
        "warmth": 0.5, "teasing": 0.5, "directness": 0.5,
        "playfulness": 0.4, "affection": 0.3, "patience": 0.7,
        "confidence": 0.5,
    }

    def get(self):
        return dict(self.state)

    def get_style_modifiers(self):
        return ["dynamic modifier A"]


class _FakeRelationship:
    def get_scores(self):
        return {"trust": 0.8, "comfort": 0.7, "respect": 0.6,
                "affection": 0.9, "familiarity": 0.4}


class TestIdentityCore:
    def test_unbound_core_returns_identity(self):
        core = IdentityCore()
        ident = core.get_identity()
        assert ident["name"] == "Mai Sakurajima"
        assert "self_concept" in ident

    def test_personality_prose_and_baselines(self):
        core = IdentityCore()
        personality = core.get_personality()
        assert isinstance(personality["traits"], list)
        assert len(personality["traits"]) >= 9

    def test_numeric_state_when_bound(self):
        core = IdentityCore(personality_state=_FakePersonality())
        personality = core.get_personality()
        assert personality["state"]["warmth"] == 0.5
        assert personality["state"]["teasing"] == 0.5

    def test_values_boundaries_preferences_speech(self):
        core = IdentityCore()
        assert core.get_values() == VALUES
        assert core.get_boundaries() == BOUNDARIES
        assert core.get_preferences() == PREFERENCES
        assert core.get_speech_rules()["style"] == SPEECH["style"]

    def test_speech_rules_include_dynamic_modifiers_when_bound(self):
        core = IdentityCore(personality_state=_FakePersonality())
        speech = core.get_speech_rules()
        assert "dynamic" in speech

    def test_relationship_rules_canonical(self):
        core = IdentityCore()
        rules = core.get_relationship_rules()
        assert len(rules["closeness_stages"]) == 4
        stages = [s["stage"] for s in rules["closeness_stages"]]
        assert stages == ["stranger", "acquaintance", "friend", "close"]
        assert rules["trust_mechanics"]

    def test_relationship_rules_live_overlay(self):
        core = IdentityCore(relationship_engine=_FakeRelationship())
        rules = core.get_relationship_rules()
        assert rules["live"]["trust"] == 0.8

    def test_social_and_emotional_rules(self):
        core = IdentityCore()
        social = core.get_social_rules()
        assert "teasing" in social and "indirectness" in social and "restraint" in social
        emotional = core.get_emotional_rules()
        assert set(emotional) == {"jealousy", "warmth", "absence"}
        assert "needs" in (emotional["jealousy"] or "")

    def test_get_current_identity_composite(self):
        core = IdentityCore()
        snapshot = core.get_current_identity()
        expected = {"identity", "personality", "values", "boundaries",
                    "preferences", "speech", "relationship", "social", "emotional"}
        assert expected == set(snapshot.keys())
        assert snapshot["identity"]["name"] == "Mai Sakurajima"
        assert snapshot["values"]["beliefs"]

    def test_query_only_no_side_effects(self):
        core = IdentityCore()
        before = core.drift_issues()
        snapshot = core.get_current_identity()
        assert snapshot == core.get_current_identity()
        assert core.drift_issues() == before

    def test_bind_updates_projection(self):
        core = IdentityCore()
        assert "state" not in core.get_personality()
        core.bind(personality_state=_FakePersonality())
        assert core.get_personality()["state"]["warmth"] == 0.5

    def test_snapshot_json_serializable(self):
        core = IdentityCore(personality_state=_FakePersonality(),
                            relationship_engine=_FakeRelationship())
        snap = core.get_snapshot()
        assert isinstance(snap, dict)
        assert snap["identity"]["name"] == "Mai Sakurajima"

    def test_levels_after_failed_bind_engine_never_mutates_facade(self):
        core = IdentityCore()

        class Exploding:
            def get_scores(self):
                raise RuntimeError("boom")

        core = IdentityCore(relationship_engine=Exploding())
        rules = core.get_relationship_rules()
        # Canonical data still present, no exception, no live key
        assert "closeness_stages" in rules
        assert "live" not in rules

    def test_thread_safety_parallel_reads(self):
        core = IdentityCore(personality_state=_FakePersonality(),
                            relationship_engine=_FakeRelationship())
        errors = []

        def read():
            try:
                for _ in range(50):
                    core.get_current_identity()
            except Exception as exc:  # pragma: no cover
                errors.append(exc)

        threads = [threading.Thread(target=read) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []