# M6 · Emotional Experience store + schema integration tests.

import pytest

from memory.experience import EmotionExperience, ExperienceStore


@pytest.fixture
def store(tmp_path):
    return ExperienceStore(path=str(tmp_path / "experiences.jsonl"))


class TestEmotionExperience:
    def test_roundtrip_fields(self):
        exp = EmotionExperience(
            event="Mai felt joyful hearing the news",
            meaning="",
            emotion={"type": "joy", "intensity": 0.9},
            relationship_impact={"person": "senpai", "delta": 0.1},
            significance=0.8,
        )
        data = exp.to_dict()
        restored = EmotionExperience.from_dict(data)
        assert restored.id == exp.id
        assert restored.event == exp.event
        assert restored.emotion == exp.emotion
        assert restored.relationship_impact == exp.relationship_impact
        assert restored.significance == 0.8
        assert restored.timestamp == exp.timestamp

    def test_reflected_property_lazy(self):
        exp = EmotionExperience(event="e", significance=0.7)
        assert exp.reflected is False
        exp.reflection += 1
        assert exp.reflected is True

    def test_significance_clamped(self):
        assert EmotionExperience(event="e", significance=1.9).significance == 1.0
        assert EmotionExperience(event="e", significance=-1.0).significance == 0.0

    def test_empty_event_record_refused(self):
        store = ExperienceStore()
        exp = EmotionExperience(event="")
        assert store.record(exp) is exp
        assert store.count() == 0


class TestExperienceStore:
    def test_record_event_ingest(self, store):
        exp = store.record_event(
            "A warm conversation about the beach",
            emotion={"type": "warmth", "intensity": 0.8},
            significance=0.8,
        )
        assert exp.id
        assert store.count() == 1
        assert store.get(exp.id).event == "A warm conversation about the beach"

    def test_persistence_across_instances(self, tmp_path):
        path = str(tmp_path / "experiences.jsonl")
        s1 = ExperienceStore(path=path)
        s1.record_event("first", significance=0.9)
        s1.record_event("second", significance=0.4)
        s2 = ExperienceStore(path=path)
        assert s2.count() == 2
        events = [e.event for e in s2.recent(10)]
        assert events == ["first", "second"]

    def test_significant_filter(self, store):
        store.record_event("low", significance=0.3)
        store.record_event("high", significance=0.9)
        assert [e.event for e in store.significant(0.6)] == ["high"]

    def test_unreflected_filter_and_reflected(self, store):
        a = store.record_event("a", significance=0.9)
        b = store.record_event("b", significance=0.9)
        store.mark_reflected(a.id, meaning="done")
        unreflected = store.unreflected(0.6)
        assert [e.event for e in unreflected] == ["b"]
        assert store.get(a.id).reflected is True

    def test_mark_reflected_lazily_fills_and_persists(self, tmp_path):
        path = str(tmp_path / "experiences.jsonl")
        s1 = ExperienceStore(path=path)
        exp = s1.record_event("big moment", significance=0.9)
        assert s1.mark_reflected(exp.id, meaning="It mattered", lessons=["lesson1"],
                                 growth="Mai grew") is True
        assert s1.mark_reflected("nope") is False
        s2 = ExperienceStore(path=path)
        loaded = s2.get(exp.id)
        assert loaded.meaning == "It mattered"
        assert loaded.lessons == ["lesson1"]
        assert loaded.growth == "Mai grew"
        assert loaded.reflected is True

    def test_tolerates_bad_lines(self, tmp_path):
        path = tmp_path / "experiences.jsonl"
        path.write_text("{not json}\n", encoding="utf-8")
        store = ExperienceStore(path=str(path))
        store.record_event("good", significance=0.9)
        reloaded = ExperienceStore(path=str(path))
        assert [e.event for e in reloaded.recent(10)] == ["good"]

    def test_recent_and_stats(self, store):
        store.record_event("a", significance=0.9)
        store.record_event("b", significance=0.7)
        store.record_event("c", significance=0.2)
        exp = store.get([e.id for e in store.recent(3)][0])
        store.mark_reflected(exp.id)
        stats = store.stats()
        assert stats["count"] == 3
        assert stats["reflected"] == 1
        assert stats["significant"] == 2


class TestReplayDedup:
    """M8 — the same event replayed must not double-record (spec §9)."""

    def test_record_same_event_twice_deduped(self, store):
        exp = store.record_event("The best night of my life", significance=0.9)
        second = store.record_event("The best night of my life", significance=0.9)
        assert second is None
        assert store.count() == 1
        assert store.get(exp.id).event == "The best night of my life"
        assert store.stats()["deduped"] == 1

    def test_distinct_events_not_deduped(self, store):
        store.record_event("first", significance=0.9)
        store.record_event("second", significance=0.9)
        assert store.count() == 2
        assert store.stats()["deduped"] == 0

    def test_dedup_survives_reload(self, tmp_path):
        path = str(tmp_path / "experiences.jsonl")
        s1 = ExperienceStore(path=path)
        s1.record_event("replay me", significance=0.9)
        s2 = ExperienceStore(path=path)
        dup = s2.record_event("replay me", significance=0.9)
        assert dup is None
        assert s2.count() == 1

    def test_empty_event_unaffected_by_dedup(self):
        store = ExperienceStore()
        exp = EmotionExperience(event="")
        assert store.record(exp) is exp
        assert store.count() == 0

    def test_pipeline_replay_does_not_double_record(self):
        from unittest.mock import Mock

        from memory.pipeline import MemoryPipeline
        store = ExperienceStore()
        pipe = MemoryPipeline(experience_store=store, event_bus=Mock())
        pipe.emotion_analyzer = Mock(analyze=lambda t: {"type": "joy", "intensity": 0.9})
        pipe.tagger = Mock(extract_tags=lambda t: [])
        pipe.store("The best night of my life.", "I'm glad.")
        pipe.store("The best night of my life.", "I'm glad.")
        assert store.count() == 1
        assert store.stats()["deduped"] == 1


class TestMemoryObjectExperienceField:
    def test_additive_field_roundtrip(self):
        from memory.schema import MemoryObject
        exp = EmotionExperience(event="moment", significance=0.8)
        obj = MemoryObject(content="hi", memory_type="conversation",
                           emotion_experience=exp.to_dict())
        assert obj.emotion_experience["event"] == "moment"
        restored = MemoryObject.from_dict(obj.to_dict())
        assert restored.emotion_experience["significance"] == 0.8

    def test_absent_field_backward_compat(self):
        from memory.schema import MemoryObject
        obj = MemoryObject.from_dict({"content": "x", "memory_type": "conversation"})
        assert getattr(obj, "emotion_experience", None) is None


class TestPipelineIngestHook:
    def test_emotional_turn_recorded_cheaply(self):
        from unittest.mock import Mock

        from memory.experience import ExperienceStore
        from memory.pipeline import MemoryPipeline
        store = ExperienceStore()
        pipe = MemoryPipeline(experience_store=store, event_bus=Mock())
        pipe.emotion_analyzer = Mock(analyze=lambda t: {"type": "joy", "intensity": 0.9})
        pipe.tagger = Mock(extract_tags=lambda t: [])
        pipe.store("I love this moment so much!", "That warms me.")
        assert store.count() == 1
        assert store.stats()["significant"] == 1
        assert store.recent(1)[0].emotion["type"] == "joy"

    def test_low_intensity_turn_not_recorded(self):
        from unittest.mock import Mock

        from memory.experience import ExperienceStore
        from memory.pipeline import MemoryPipeline
        store = ExperienceStore()
        pipe = MemoryPipeline(experience_store=store, event_bus=Mock())
        pipe.emotion_analyzer = Mock(analyze=lambda t: {"type": "neutral", "intensity": 0.3})
        pipe.tagger = Mock(extract_tags=lambda t: [])
        pipe.store("It is fine, nothing special.", "I see.")
        assert store.count() == 0

    def test_trivial_turn_skipped_by_validation(self):
        from unittest.mock import Mock

        from memory.experience import ExperienceStore
        from memory.pipeline import MemoryPipeline
        store = ExperienceStore()
        pipe = MemoryPipeline(experience_store=store, event_bus=Mock())
        pipe.emotion_analyzer = Mock(analyze=lambda t: {"type": "joy", "intensity": 0.9})
        pipe.tagger = Mock(extract_tags=lambda t: [])
        pipe.store("ok", "fine")
        assert store.count() == 0

    def test_no_store_noop(self):
        from unittest.mock import Mock

        from memory.pipeline import MemoryPipeline
        pipe = MemoryPipeline(event_bus=Mock())
        pipe.emotion_analyzer = Mock(analyze=lambda t: {"type": "joy", "intensity": 0.9})
        pipe.tagger = Mock(extract_tags=lambda t: [])
        pipe.store("I love this moment so much!", "That warms me.")  # must not raise


class TestPreferenceEvidenceHook:
    def _pipe(self, pref=None):
        from unittest.mock import Mock

        from memory.pipeline import MemoryPipeline
        pipe = MemoryPipeline(event_bus=Mock())
        pipe.emotion_analyzer = Mock(analyze=lambda t: {"type": "neutral", "intensity": 0.5})
        pipe.tagger = Mock(extract_tags=lambda t: ["music"])
        pipe._match_entity_names = Mock(return_value=["jazz"])
        pipe.preference_evolution = pref
        return pipe

    def test_evidence_recorded_from_turn(self):
        from unittest.mock import Mock

        from agency.preference_evolution import PreferenceEvolution
        pref = PreferenceEvolution(threshold=3)
        pref.scan_turn = Mock(wraps=pref.scan_turn)
        pipe = self._pipe(pref)
        pipe.store("I love jazz, it's my favorite", "That's lovely.")
        pref.scan_turn.assert_called_once()
        assert pref.evidence_for("jazz")["like"] == 1

    def test_evidence_skipped_when_unwired(self):
        pipe = self._pipe(None)
        pipe.store("I love jazz", "Nice.")  # must not raise

    def test_experience_recorded_event_published(self):
        from unittest.mock import Mock

        from core.mai_message import MaiMessage
        from memory.experience import ExperienceStore
        from memory.pipeline import MemoryPipeline
        bus = Mock()
        store = ExperienceStore()
        pipe = MemoryPipeline(experience_store=store, event_bus=bus)
        pipe.emotion_analyzer = Mock(analyze=lambda t: {"type": "joy", "intensity": 0.9})
        pipe.tagger = Mock(extract_tags=lambda t: [])
        pipe.store("I love this moment so much!", "That warms me.")
        assert store.count() == 1
        assert bus.publish_message.call_count >= 1
        published = [c.args[0] for c in bus.publish_message.call_args_list]
        assert any(
            isinstance(m, MaiMessage) and m.type == "data.experience.recorded"
            for m in published
        )
