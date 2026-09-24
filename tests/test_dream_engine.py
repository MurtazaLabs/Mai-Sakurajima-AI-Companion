import pytest
from unittest.mock import MagicMock


class TestDreamReport:

    def test_dream_report_defaults(self):
        from agency.dreaming import DreamReport
        r = DreamReport(level=1)
        assert r.level == 1
        assert r.tasks_run == []
        assert r.orphans_found == 0
        assert r.duration == 0.0
        assert r.errors == []


class TestDreamEngine:

    def test_should_dream_not_enough_idle(self):
        from agency.dreaming import DreamEngine
        engine = DreamEngine()
        engine._min_idle_seconds = 300
        assert engine.should_dream(10) is False

    def test_should_dream_recently_dreamed(self):
        from agency.dreaming import DreamEngine
        import time
        engine = DreamEngine()
        engine._min_idle_seconds = 10
        engine._last_dream = time.time()
        assert engine.should_dream(600) is False

    def test_should_dream_ready(self):
        from agency.dreaming import DreamEngine
        import time
        engine = DreamEngine()
        engine._min_idle_seconds = 10
        engine._last_dream = time.time() - 7200
        assert engine.should_dream(600) is True

    def test_level_1_tasks_run(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("mai", entity_type="character")
        engine = DreamEngine(knowledge_graph=kg)
        state = MemoryState()
        state.people.append({"name": "Alice", "confidence": 0.9, "last_seen": "2026-07-17"})
        report = engine.run(state, level=1)
        assert "orphans" in report.tasks_run
        assert report.duration >= 0

    def test_level_5_experience_reflection(self):
        from agency.dreaming import DreamEngine
        from agency.dream_report import DreamReport
        from agency.dream_tasks import experience_reflection
        from memory.state import MemoryState
        from memory.experience import ExperienceStore
        store = ExperienceStore()
        store.record_event("An intense talk about loss", emotion={"type": "sadness", "intensity": 0.9},
                           significance=0.9)
        store.record_event("A quiet walk", significance=0.2)  # below dream threshold
        engine = DreamEngine(experience_store=store)
        state = MemoryState()
        assert experience_reflection(engine, state, DreamReport(level=5)) == 1
        reflected = [e for e in store.unreflected(0.6)]
        assert len(reflected) == 0
        kept = store.get([e.id for e in store.recent(10)][0])
        assert kept.reflected is True
        assert kept.meaning  # deterministic fallback meaning filled
        assert any("experience" in getattr(k, "fact", str(k))
                   for k in state.knowledge)

    def test_experience_reflection_no_store_noop(self):
        from agency.dreaming import DreamEngine
        from agency.dream_report import DreamReport
        from agency.dream_tasks import experience_reflection
        from memory.state import MemoryState
        engine = DreamEngine()
        state = MemoryState()
        assert experience_reflection(engine, state, DreamReport(level=5)) == 0

    def test_experience_reflection_metric_mapped(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        from memory.experience import ExperienceStore
        store = ExperienceStore()
        store.record_event("Win at chess", significance=0.9)
        engine = DreamEngine(experience_store=store)
        report = engine.run(MemoryState(), level=5)
        assert report.experiences_reflected == 1


    def test_level_1_merge_duplicates(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        engine = DreamEngine()
        state = MemoryState()
        state.people.append({"name": "Alice", "confidence": 0.9, "last_seen": "2026-07-17"})
        state.people.append({"name": "alice", "confidence": 0.7, "last_seen": "2026-07-16"})
        state.people.append({"name": "Bob", "confidence": 0.8, "last_seen": "2026-07-17"})
        report = engine.run(state, level=1)
        assert "merge_duplicates" in report.tasks_run
        assert len(state.people) == 2

    def test_level_1_merge_knowledge(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState, KnowledgeEntry
        engine = DreamEngine()
        state = MemoryState()
        state.knowledge.append(KnowledgeEntry(topic="Python", fact="Python is great", timestamp="2026-07-17"))
        state.knowledge.append(KnowledgeEntry(topic="Python", fact="Python is great", timestamp="2026-07-17"))
        report = engine.run(state, level=1)
        assert "merge_knowledge" in report.tasks_run
        assert len(state.knowledge) == 1

    def test_level_1_link_notes(self):
        from agency.dreaming import DreamEngine, DreamReport
        from memory.state import MemoryState
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("alice", entity_type="person")
        kg.add_entity("tokyo", entity_type="place")
        engine = DreamEngine(knowledge_graph=kg)
        state = MemoryState()
        state.people.append({"name": "Alice", "confidence": 0.9, "last_seen": "2026-07-17"})
        state.places.append({"name": "Tokyo", "confidence": 0.8, "last_seen": "2026-07-17"})
        state.places.append({"name": "Tokyo", "confidence": 0.8, "last_seen": "2026-07-17"})
        state.places.append({"name": "Tokyo", "confidence": 0.8, "last_seen": "2026-07-17"})
        state.places.append({"name": "Tokyo", "confidence": 0.8, "last_seen": "2026-07-17"})
        state.places.append({"name": "Tokyo", "confidence": 0.8, "last_seen": "2026-07-17"})
        report = DreamReport(level=1)
        links = engine._run_task("link_notes", state, report)
        assert links >= 1

    def test_level_2_importance_task(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        engine = DreamEngine()
        state = MemoryState()
        report = engine.run(state, level=2)
        assert "importance" in report.tasks_run

    def test_level_2_relationship_building(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("alice", entity_type="person")
        kg.add_entity("bob", entity_type="person")
        engine = DreamEngine(knowledge_graph=kg)
        state = MemoryState()
        state.people.append({"name": "Alice", "confidence": 0.9, "last_seen": "2026-07-17"})
        state.people.append({"name": "Bob", "confidence": 0.8, "last_seen": "2026-07-17"})
        report = engine.run(state, level=2)
        assert "relationship_building" in report.tasks_run

    def test_level_3_knowledge_discovery_via_llm(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        llm = MagicMock()
        llm.generate.return_value = '[{"trait": "Enjoys building AI systems", "confidence": 0.9}]'
        llm.is_available.return_value = True
        engine = DreamEngine(llm=llm)
        state = MemoryState()
        state.likes.append("Python")
        state.likes.append("AI")
        report = engine.run(state, level=3)
        assert "knowledge_discovery" in report.tasks_run
        assert report.knowledge_discovered >= 1

    def test_level_3_knowledge_discovery_low_confidence_skipped(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        llm = MagicMock()
        llm.generate.return_value = '[{"trait": "Maybe likes tea", "confidence": 0.5}]'
        llm.is_available.return_value = True
        engine = DreamEngine(llm=llm)
        state = MemoryState()
        state.likes.append("Coffee")
        report = engine.run(state, level=3)
        assert report.knowledge_discovered == 0

    def test_level_3_reflections_task_without_llm(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        engine = DreamEngine()
        state = MemoryState()
        report = engine.run(state, level=3)
        assert "reflections" in report.tasks_run
        assert report.reflections_generated == 0

    def test_level_4_optimize_graph(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("a", entity_type="test")
        kg.add_entity("b", entity_type="test")
        kg.add_relation("a", "relates_to", "b", weight=0.05)
        engine = DreamEngine(knowledge_graph=kg)
        state = MemoryState()
        report = engine.run(state, level=4)
        assert "graph_optimization" in report.tasks_run
        assert report.graph_optimized is True

    def test_level_4_archive_stale_task(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        engine = DreamEngine()
        state = MemoryState()
        report = engine.run(state, level=4)
        assert "archive_stale" in report.tasks_run

    def test_error_isolation(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        kg = MagicMock()
        kg.get_entity.return_value = None
        kg.get_relations_for.side_effect = RuntimeError("graph down")
        kg.all_relations.return_value = []
        engine = DreamEngine(knowledge_graph=kg)
        state = MemoryState()
        state.people.append({"name": "Alice", "confidence": 0.9, "last_seen": "2026-07-17"})
        state.places.append({"name": "Tokyo", "confidence": 0.8, "last_seen": "2026-07-17"})
        report = engine.run(state, level=1)
        assert len(report.errors) > 0
        assert report.duration >= 0

    def test_event_bus_publish(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        from core.event_bus import EventBus
        from core.event_specs import register_event_specs
        bus = EventBus()
        register_event_specs(bus)
        received = []
        bus.subscribe("data.dream.completed", lambda e: received.append(e))
        engine = DreamEngine(event_bus=bus)
        state = MemoryState()
        engine.run(state, level=1)
        assert len(received) >= 1
        data = received[0]
        assert data["level"] == 1
        assert "duration" in data

    def test_weekly_digest_task(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        engine = DreamEngine()
        state = MemoryState()
        report = engine.run(state, level=4)
        assert "weekly_digest" in report.tasks_run

    def test_importance_full_task(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        engine = DreamEngine()
        state = MemoryState()
        report = engine.run(state, level=4)
        assert "importance_full" in report.tasks_run

    def test_importance_recalculation_adds_importance_field(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        from datetime import datetime, timedelta
        engine = DreamEngine()
        state = MemoryState()
        recent = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        state.people.append({"name": "Alice", "confidence": 0.9, "last_seen": recent})
        engine._run_task("importance", state, None)
        assert "importance" in state.people[0]
        assert state.people[0]["importance_source"] == "fresh"

    def test_importance_decay_over_time(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        from datetime import datetime, timedelta
        engine = DreamEngine()
        state = MemoryState()
        recent = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        state.people.append({"name": "Old", "confidence": 0.9, "last_seen": "2025-01-01"})
        state.people.append({"name": "Recent", "confidence": 0.9, "last_seen": recent})
        engine._run_task("importance", state, None)
        old_imp = state.people[0].get("importance", 1.0)
        recent_imp = state.people[1].get("importance", 1.0)
        assert old_imp < recent_imp
        assert state.people[0]["importance_source"] == "decayed"

    def test_full_importance_updates_kg_entities(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("test_entity", entity_type="test", metadata={"confidence": 0.8})
        engine = DreamEngine(knowledge_graph=kg)
        state = MemoryState()
        engine._run_task("importance_full", state, None)
        ent = kg.get_entity("test_entity")
        assert ent is not None
        assert "importance" in ent.metadata

    def test_compress_conversations_injects_summary(self, tmp_path):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        conv_dir = tmp_path / "conversation"
        conv_dir.mkdir()
        f = conv_dir / "2026-07-17.md"
        f.write_text("---\nid: test\ntimestamp: 2026-07-17\nemotion: happy\n---\n\n# Conversation\n\nUser said hello. Mai replied. They discussed Python programming and AI systems.")
        engine = DreamEngine(vault_root=tmp_path)
        compressed =         engine._run_task("conversation_compression", None, None)
        assert compressed >= 1
        content = f.read_text(encoding="utf-8")
        assert "summary:" in content

    def test_compress_skips_already_summarized(self, tmp_path):
        from agency.dreaming import DreamEngine
        conv_dir = tmp_path / "conversation"
        conv_dir.mkdir()
        f = conv_dir / "2026-07-17.md"
        f.write_text("---\nsummary: \"already done\"\ntimestamp: 2026-07-17\n---\n\nContent here")
        engine = DreamEngine(vault_root=tmp_path)
        compressed =         engine._run_task("conversation_compression", None, None)
        assert compressed == 0

    def test_extract_keywords_filters_stopwords(self):
        from agency.dreaming import DreamEngine
        from agency.dream_tasks import _extract_keywords
        result = _extract_keywords("Python programming and AI systems are great for development", top_n=3)
        assert "python" in result.lower() or "programming" in result.lower()

    def test_generate_reflections_via_llm(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState, IdentityFact
        llm = MagicMock()
        llm.generate.return_value = '{"reflections": [{"observation": "User enjoys coding", "confidence": 0.95, "category": "interest_change"}]}'
        llm.is_available.return_value = True
        engine = DreamEngine(llm=llm)
        state = MemoryState()
        state.identity.append(IdentityFact(fact="I am a programmer", category="work", timestamp="2026-07-17"))
        state.likes.append("Python")
        count = engine._run_task("reflections", state, None)
        assert count >= 1

    def test_generate_reflections_low_confidence_skipped(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState, IdentityFact
        llm = MagicMock()
        llm.generate.return_value = '{"reflections": [{"observation": "Maybe likes tea", "confidence": 0.5, "category": "habit"}]}'
        llm.is_available.return_value = True
        engine = DreamEngine(llm=llm)
        state = MemoryState()
        state.identity.append(IdentityFact(fact="I am a programmer", category="work", timestamp="2026-07-17"))
        count = engine._run_task("reflections", state, None)
        assert count == 0

    def test_weekly_digest_creates_entry(self, tmp_path):
        from datetime import datetime, timedelta

        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        conv_dir = tmp_path / "conversation"
        conv_dir.mkdir()
        recent_day = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        f = conv_dir / f"{recent_day}.md"
        f.write_text("User discussed AI projects and learning Python.")
        llm = MagicMock()
        llm.generate.return_value = '{"digest": "This week the user focused on AI and Python.", "key_topics": ["AI", "Python"], "mood": "positive", "new_information": []}'
        llm.is_available.return_value = True
        engine = DreamEngine(llm=llm, vault_root=tmp_path)
        state = MemoryState()
        result = engine._run_task("weekly_digest", state, None)
        assert result is True

    def test_weekly_digest_no_files_returns_false(self, tmp_path):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        conv_dir = tmp_path / "conversation"
        conv_dir.mkdir()
        llm = MagicMock()
        llm.is_available.return_value = True
        engine = DreamEngine(llm=llm, vault_root=tmp_path)
        state = MemoryState()
        result = engine._run_task("weekly_digest", state, None)
        assert result is False

    def test_archive_stale_removes_old_low_importance(self):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        engine = DreamEngine()
        state = MemoryState()
        state.people.append({"name": "Stale", "confidence": 0.3, "last_seen": "2025-01-01", "importance": 0.1})
        state.people.append({"name": "Recent", "confidence": 0.9, "last_seen": "2026-07-17", "importance": 0.9})
        archived = engine._run_task("archive_stale", state, None)
        assert archived == 1
        assert len(state.people) == 1
        assert state.people[0]["name"] == "Recent"

    def test_emotional_reflection_detects_stress(self, tmp_path):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        conv_dir = tmp_path / "conversation"
        conv_dir.mkdir()
        for day in range(17, 22):
            f = conv_dir / f"2026-07-{day}.md"
            f.write_text(f"---\nid: {day}\nemotion: anxious\n---\n\nContent")
        engine = DreamEngine(vault_root=tmp_path)
        state = MemoryState()
        count = engine._run_task("emotional_reflection", state, None)
        assert count >= 1
        assert any("[emotion]" in k.fact for k in state.knowledge)

    def test_emotional_reflection_requires_3_emotions(self, tmp_path):
        from agency.dreaming import DreamEngine
        from memory.state import MemoryState
        conv_dir = tmp_path / "conversation"
        conv_dir.mkdir()
        f = conv_dir / "2026-07-17.md"
        f.write_text("---\nemotion: happy\n---\n\nContent")
        engine = DreamEngine(vault_root=tmp_path)
        state = MemoryState()
        count = engine._run_task("emotional_reflection", state, None)
        assert count == 0
