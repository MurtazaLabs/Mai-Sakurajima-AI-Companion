class TestMemoryManager:

    def test_store_returns_node(self, memory_manager):
        node = memory_manager.store("I am excited about machine learning — it's important to me", "That's great!")
        assert node is not None

    def test_get_context_empty_initially(self, memory_manager):
        ctx = memory_manager.get_context()
        assert isinstance(ctx, list)

    def test_get_context_after_store(self, memory_manager):
        memory_manager.store("I am excited about machine learning — it's important to me", "That's great!")
        ctx = memory_manager.get_context()
        assert len(ctx) >= 1

    def test_extract_delegates_to_pipeline(self, memory_manager):
        results = memory_manager.extract("my favorite food is pizza")
        assert len(results) >= 1
        assert results[0].type == "preference"

    def test_validate_short_input(self, memory_manager):
        assert memory_manager.validate("ok") is False
        assert memory_manager.validate("hi") is False

    def test_validate_normal_input(self, memory_manager):
        assert memory_manager.validate("hello world") is True
        assert memory_manager.validate("what is the weather") is True

    def test_process_basic(self, memory_manager):
        node = memory_manager.process("I am excited about machine learning — it's important to me", "That's great!")
        assert node is not None

    def test_process_empty_returns_none(self, memory_manager):
        node = memory_manager.process("", "")
        assert node is None

    def test_fallback_attributes(self, memory_manager):
        assert hasattr(memory_manager, "tagger")
        assert hasattr(memory_manager, "event_bus")


class TestMemoryPipeline:

    def test_extract(self, event_bus):
        from memory.pipeline import MemoryPipeline
        pipe = MemoryPipeline(event_bus=event_bus)
        results = pipe.extract("I like coding")
        assert len(results) >= 1

    def test_validate(self, event_bus):
        from memory.pipeline import MemoryPipeline
        pipe = MemoryPipeline(event_bus=event_bus)
        assert pipe.validate("hello world") is True
        assert pipe.validate("ok") is False

    def test_run_lifecycle(self, event_bus):
        from memory.pipeline import MemoryPipeline
        from memory.schema import MemoryObject
        pipe = MemoryPipeline(event_bus=event_bus)
        nodes = [MemoryObject(content="test", memory_type="conversation")]
        active, to_archive, to_delete = pipe.run_lifecycle(nodes)
        assert isinstance(active, list)
        assert isinstance(to_archive, list)
        assert isinstance(to_delete, list)

    def test_run_consolidation(self, event_bus):
        from memory.pipeline import MemoryPipeline
        from memory.schema import MemoryObject
        pipe = MemoryPipeline(event_bus=event_bus)
        nodes = [
            MemoryObject(content="I like pizza", memory_type="preference"),
            MemoryObject(content="I love pizza", memory_type="preference"),
        ]
        new_nodes, remaining = pipe.run_consolidation(nodes)
        assert isinstance(new_nodes, list)
        assert isinstance(remaining, list)


class TestMemoryLifecycle:

    def test_classify_working(self):
        from memory.lifecycle import MemoryLifecycle
        from memory.schema import MemoryObject
        lc = MemoryLifecycle()
        node = MemoryObject(content="fresh", memory_type="conversation")
        state = lc.classify(node)
        assert state in ("working", "short_term", "long_term", "archive", "delete", "archived")


class TestMemoryIntelligenceDI:

    def test_inject_all_mocks(self):
        from unittest.mock import MagicMock

        from memory.intelligence import MemoryIntelligence
        tagger = MagicMock()
        tagger.extract_tags.return_value = ["test"]
        emotion = MagicMock()
        emotion.analyze.return_value = {"type": "happy", "intensity": 0.8}
        scorer = MagicMock()
        graph = MagicMock()
        recall = MagicMock()
        router = MagicMock()
        writer = MagicMock()
        reflector = MagicMock()
        decay = MagicMock()
        mi = MemoryIntelligence(
            tagger=tagger,
            emotion=emotion,
            scorer=scorer,
            graph=graph,
            recall_engine=recall,
            router=router,
            writer=writer,
            reflector=reflector,
            decay=decay,
        )
        assert mi.tagger is tagger
        assert mi.emotion is emotion
        assert mi.scorer is scorer
        assert mi.graph is graph
        assert mi.recall_engine is recall
        assert mi.router is router
        assert mi.writer is writer
        assert mi.reflector is reflector
        assert mi.decay is decay

    def test_default_constructs_real_subsystems(self):
        from unittest.mock import MagicMock

        from memory.intelligence import MemoryIntelligence
        mi = MemoryIntelligence(tagger=MagicMock(), emotion=MagicMock())
        assert mi.scorer is not None
        assert mi.graph is not None
        assert mi.recall_engine is not None
        assert mi.reflector is not None
        assert mi.decay is not None

    def test_should_delete_low_importance_old(self):
        import time

        from memory.lifecycle import MemoryLifecycle
        from memory.schema import MemoryObject
        lc = MemoryLifecycle()
        node = MemoryObject(
            content="old and unimportant",
            memory_type="conversation",
            importance=0.05,
            timestamp=time.time() - 999999,
        )
        assert lc.should_delete(node) is True

    def test_should_archive(self):
        import time

        from memory.lifecycle import MemoryLifecycle
        from memory.schema import MemoryObject
        lc = MemoryLifecycle()
        node = MemoryObject(
            content="old enough to archive",
            memory_type="conversation",
            importance=0.2,
            timestamp=time.time() - 999999,
        )
        assert lc.should_archive(node) is True


class TestMemoryState:

    def test_defaults(self):
        from memory.state import MemoryState
        s = MemoryState()
        assert s.identity == []
        assert s.likes == []
        assert s.dislikes == []
        assert s.entity_count == 0
        assert s.relation_count == 0

    def test_merge_identity_adds_new(self):
        from memory.state import IdentityFact, MemoryState
        s = MemoryState()
        s.merge_identity([IdentityFact(fact="I am 25", category="age", timestamp="2026-07-17")])
        assert len(s.identity) == 1
        assert s.identity[0].fact == "I am 25"

    def test_merge_identity_preserves_different_facts_same_category(self):
        from memory.state import IdentityFact, MemoryState
        s = MemoryState()
        s.merge_identity([IdentityFact(fact="I am 25", category="age", timestamp="2026-07-16")])
        s.merge_identity([IdentityFact(fact="I am 26", category="age", timestamp="2026-07-17")])
        assert len(s.identity) == 2
        assert any(f.fact == "I am 25" for f in s.identity)
        assert any(f.fact == "I am 26" for f in s.identity)

    def test_merge_identity_preserves_timestamp(self):
        from memory.state import IdentityFact, MemoryState
        s = MemoryState()
        s.merge_identity([IdentityFact(fact="I am 25", category="age", timestamp="2026-07-16")])
        s.merge_identity([IdentityFact(fact="I am 26", category="age")])
        assert s.identity[0].timestamp == "2026-07-16"

    def test_merge_preferences_adds_likes(self):
        from memory.state import MemoryState
        s = MemoryState()
        s.merge_preferences(["coding", "coffee"], [])
        assert "coding" in s.likes
        assert "coffee" in s.likes
        assert s.dislikes == []

    def test_merge_preferences_moves_between_lists(self):
        from memory.state import MemoryState
        s = MemoryState()
        s.merge_preferences(["coding"], [])
        s.merge_preferences([], ["coding"])
        assert "coding" not in s.likes
        assert "coding" in s.dislikes

    def test_merge_knowledge_preserves_different_facts_same_topic(self):
        from memory.state import KnowledgeEntry, MemoryState
        s = MemoryState()
        s.merge_knowledge([KnowledgeEntry(topic="Python", fact="Python is great", timestamp="2026-07-17")])
        s.merge_knowledge([KnowledgeEntry(topic="Python", fact="Python is a programming language", timestamp="2026-07-18")])
        assert len(s.knowledge) == 2
        assert any(f.fact == "Python is great" for f in s.knowledge)
        assert any(f.fact == "Python is a programming language" for f in s.knowledge)

    def test_merge_knowledge_preserves_timestamp(self):
        from memory.state import KnowledgeEntry, MemoryState
        s = MemoryState()
        s.merge_knowledge([KnowledgeEntry(topic="Python", fact="Python is great", timestamp="2026-07-17")])
        s.merge_knowledge([KnowledgeEntry(topic="Python", fact="Python is great")])
        assert s.knowledge[0].timestamp == "2026-07-17"

    def test_add_entity(self):
        from memory.state import MemoryState
        s = MemoryState()
        s.add_entity("Alice", 0.9, "2026-07-17")
        assert len(s.people) == 1
        assert s.people[0]["name"] == "Alice"

    def test_load_from_file_identity(self, tmp_path):
        from memory.state import MemoryState
        identity_dir = tmp_path / "identity"
        identity_dir.mkdir()
        f = identity_dir / "user.md"
        dash = "\u2014"
        f.write_bytes(("- [age] I am 25 " + dash + " 2026-07-17\n- [name] Alice " + dash + " 2026-07-16").encode("utf-8"))
        s = MemoryState()
        s.load_from_file(f, "identity")
        assert len(s.identity) == 2, f"got {len(s.identity)} identity facts"
        cats = {fact.category for fact in s.identity}
        assert "age" in cats
        assert "name" in cats

    def test_load_from_file_preferences(self, tmp_path):
        from memory.state import MemoryState
        pref_dir = tmp_path / "preferences"
        pref_dir.mkdir()
        f = pref_dir / "preferences.md"
        dash = "\u2014"
        f.write_bytes(("## Likes\n- coding " + dash + " 2026-07-17\n- coffee\n## Dislikes\n- bugs").encode("utf-8"))
        s = MemoryState()
        s.load_from_file(f, "preferences")
        assert "coding" in s.likes, f"likes={s.likes}"
        assert "bugs" in s.dislikes, f"dislikes={s.dislikes}"

    def test_load_from_file_knowledge(self, tmp_path):
        from memory.state import MemoryState
        know_dir = tmp_path / "knowledge"
        know_dir.mkdir()
        f = know_dir / "knowledge.md"
        dash = "\u2014"
        f.write_bytes(("- **Python** " + dash + " a programming language " + dash + " 2026-07-17").encode("utf-8"))
        s = MemoryState()
        s.load_from_file(f, "knowledge")
        assert len(s.knowledge) == 1
        assert s.knowledge[0].topic == "Python"

    def test_load_from_file_dreams(self, tmp_path):
        from memory.state import MemoryState
        dream_dir = tmp_path / "dreams"
        dream_dir.mkdir()
        f = dream_dir / "dreams.md"
        dash = "\u2014"
        f.write_bytes(("- travel to Japan " + dash + " 2026-07-17\n- build AI " + dash + " 2026-07-16").encode("utf-8"))
        s = MemoryState()
        s.load_from_file(f, "dreams")
        assert "travel to Japan" in s.dreams

    def test_load_statistics_from_file(self, tmp_path):
        from memory.state import MemoryState
        stats_dir = tmp_path / "statistics"
        stats_dir.mkdir()
        f = stats_dir / "stats.md"
        f.write_text("total_conversations: 42\ntotal_entities: 10\ntotal_relations: 25")
        s = MemoryState()
        s.load_statistics_from_file(f)
        assert s.interaction_count == 42
        assert s.entity_count == 10
        assert s.relation_count == 25
