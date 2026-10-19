from unittest.mock import MagicMock, patch


class TestBeliefEngine:

    def test_update_creates_belief_from_preference(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        engine = BeliefEngine(event_bus=event_bus)
        memory = MemoryObject(content="I like pizza", memory_type="preference", confidence=0.8)
        results = engine.update(memory)
        assert results is not None and len(results) >= 1
        assert results[0].topic == "user" and results[0].predicate == "likes"

    def test_update_creates_belief_from_identity(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        engine = BeliefEngine(event_bus=event_bus)
        results = engine.update(MemoryObject(content="John", memory_type="identity", confidence=0.9))
        assert results[0].predicate == "is"

    def test_update_creates_belief_from_location(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        engine = BeliefEngine(event_bus=event_bus)
        results = engine.update(MemoryObject(content="NYC", memory_type="location", confidence=0.7))
        assert results[0].predicate == "lives_in"

    def test_update_creates_belief_from_employment(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        engine = BeliefEngine(event_bus=event_bus)
        results = engine.update(MemoryObject(content="Acme", memory_type="employment", confidence=0.8))
        assert results[0].predicate == "works_at"

    def test_update_ignores_non_memory_object(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        assert BeliefEngine(event_bus=event_bus).update("not a memory object") is None

    def test_query_returns_beliefs_for_topic(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        engine = BeliefEngine(event_bus=event_bus)
        engine.update(MemoryObject(content="likes coding", memory_type="preference", confidence=0.9))
        assert all(b.topic == "user" for b in engine.query("user"))

    def test_query_returns_empty_for_unknown_topic(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        assert BeliefEngine(event_bus=event_bus).query("nonexistent") == []

    def test_all_beliefs_returns_sorted_by_confidence(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        engine = BeliefEngine(event_bus=event_bus)
        engine.update(MemoryObject(content="likes pizza", memory_type="preference", confidence=0.5))
        engine.update(MemoryObject(content="John", memory_type="identity", confidence=0.9))
        all_b = engine.all_beliefs()
        assert len(all_b) >= 2 and all_b[0].confidence >= all_b[-1].confidence

    def test_contradict_reduces_confidence(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        engine = BeliefEngine(event_bus=event_bus)
        engine.update(MemoryObject(content="likes pizza", memory_type="preference", confidence=0.9))
        engine.contradict("user", "likes", "likes pizza")
        assert engine.get_belief("user", "likes", "likes pizza").confidence < 0.9

    def test_contradict_returns_none_for_missing(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        assert BeliefEngine(event_bus=event_bus).contradict("unknown", "likes", "x") is None

    def test_get_belief_returns_none_when_not_found(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        assert BeliefEngine(event_bus=event_bus).get_belief("unknown") is None

    def test_count_returns_correct_number(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        engine = BeliefEngine(event_bus=event_bus)
        engine.update(MemoryObject(content="a", memory_type="preference", confidence=0.5))
        engine.update(MemoryObject(content="b", memory_type="identity", confidence=0.9))
        assert engine.count() >= 2

    def test_merge_increases_evidence_on_duplicate(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        engine = BeliefEngine(event_bus=event_bus)
        engine.update(MemoryObject(content="likes coding", memory_type="preference", confidence=0.6))
        r2 = engine.update(MemoryObject(content="likes coding", memory_type="preference", confidence=0.6))
        assert r2[0].evidence_count == 2

    def test_extract_beliefs_from_text_patterns(self, event_bus):
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        results = BeliefEngine(event_bus=event_bus).update(
            MemoryObject(content="User likes anime and enjoys music", memory_type="conversation", confidence=0.7))
        objects = {b.object for b in results}
        assert "anime" in objects and "music" in objects

    def test_event_published_on_update(self):
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        mock_bus = MagicMock()
        BeliefEngine(event_bus=mock_bus).update(MemoryObject(content="likes python", memory_type="preference", confidence=0.8))
        assert mock_bus.publish_message.called


class TestKnowledgeGraph:

    def test_add_entity_creates_and_returns(self):
        from knowledge.graph import KnowledgeGraph
        entity = KnowledgeGraph().add_entity("Python", entity_type="language")
        assert entity.name == "python" and entity.type == "language"

    def test_add_entity_updates_metadata_on_existing(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("Python", metadata={"version": "3"})
        kg.add_entity("Python", metadata={"paradigm": "OOP"})
        ent = kg.get_entity("Python")
        assert ent.metadata["version"] == "3" and ent.metadata["paradigm"] == "OOP"

    def test_get_entity_returns_none_for_missing(self):
        from knowledge.graph import KnowledgeGraph
        assert KnowledgeGraph().get_entity("missing") is None

    def test_add_relation_creates_entities_auto(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        rel = kg.add_relation("Python", "influenced", "Ruby", weight=0.8)
        assert rel.source == "python" and rel.target == "ruby" and rel.weight == 0.8
        assert kg.get_entity("python") and kg.get_entity("ruby")

    def test_query_depth_1(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_relation("A", "connects", "B")
        kg.add_relation("B", "connects", "C")
        assert len(kg.query("A", depth=1)) == 1

    def test_query_depth_2_returns_multi_hop(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_relation("A", "connects", "B")
        kg.add_relation("B", "connects", "C")
        assert len(kg.query("A", depth=2)) == 2

    def test_query_returns_reverse_relations(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_relation("A", "connects", "B")
        assert kg.query("B", depth=1)[0].target == "a"

    def test_get_relations_for_returns_all(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_relation("A", "connects", "B")
        kg.add_relation("C", "connects", "A")
        assert len(kg.get_relations_for("A")) == 2

    def test_all_entities_and_relations(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("A")
        kg.add_entity("B")
        kg.add_relation("A", "knows", "B")
        assert len(kg.all_entities()) == 2 and len(kg.all_relations()) == 1

    def test_to_dict_round_trip(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("Python", entity_type="language")
        kg.add_relation("Python", "influenced", "Ruby")
        d = kg.to_dict()
        assert "python" in d["entities"] and len(d["relations"]) == 1

    def test_save_and_load(self, tmp_path):
        from knowledge.graph import KnowledgeGraph
        path = str(tmp_path / "kg.json")
        kg = KnowledgeGraph()
        kg.add_entity("Test", entity_type="example")
        kg.add_relation("Test", "relates", "Other")
        kg.save(path)
        loaded = KnowledgeGraph.load(path)
        assert loaded.get_entity("test") and len(loaded.all_relations()) == 1

    def test_import_from_memory_graph(self):
        from knowledge.graph import KnowledgeGraph
        class MockNode:
            def __init__(self, text, memory_type, tags=None):
                self.text = text; self.memory_type = memory_type; self.tags = tags or []
        class MockGraph:
            nodes = [
                MockNode("John Doe", "identity", tags=["person", "engineer"]),
                MockNode("New York", "location"),
                MockNode("Acme", "employment"),
            ]
        kg = KnowledgeGraph()
        kg.import_from_memory_graph(MockGraph())
        assert kg.get_entity("person") and kg.get_entity("engineer") and kg.get_entity("user")


class TestAttentionSystem:

    def test_focus_creates_attention_focus(self):
        from knowledge.attention import AttentionSystem
        focus = AttentionSystem().focus("python")
        assert focus.topic == "python" and len(focus.areas) >= 1

    def test_focus_with_cognitive_state(self):
        from knowledge.attention import AttentionSystem
        focus = AttentionSystem().focus("music", cognitive_state={"energy": 0.8})
        assert "audio" in focus.areas or "songs" in focus.areas

    def test_focus_empty_topic(self):
        from knowledge.attention import AttentionSystem
        assert AttentionSystem().focus("").topic == ""

    def test_focus_with_knowledge_graph(self):
        from knowledge.attention import AttentionSystem
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_relation("python", "related_to", "machine_learning")
        assert "machine_learning" in AttentionSystem(knowledge_graph=kg).focus("python").areas

    def test_focus_with_belief_engine(self):
        from knowledge.attention import AttentionSystem
        from knowledge.belief_engine import BeliefEngine
        from memory.schema import MemoryObject
        be = BeliefEngine()
        be.update(MemoryObject(content="likes hiking", memory_type="preference", confidence=0.9))
        assert "hiking" in " ".join(AttentionSystem(belief_engine=be).focus("user").areas)

    def test_current_returns_latest_focus(self):
        from knowledge.attention import AttentionSystem
        attn = AttentionSystem()
        attn.focus("python")
        attn.focus("music")
        assert attn.current().topic == "music"

    def test_current_returns_none_before_any_focus(self):
        from knowledge.attention import AttentionSystem
        assert AttentionSystem().current() is None

    def test_history_tracks_topics(self):
        from knowledge.attention import AttentionSystem
        attn = AttentionSystem()
        attn.focus("python"); attn.focus("music"); attn.focus("anime")
        assert attn.history() == ["python", "music", "anime"]

    def test_history_respects_max(self):
        from knowledge.attention import AttentionSystem
        attn = AttentionSystem()
        attn._max_history = 2
        attn.focus("a"); attn.focus("b"); attn.focus("c")
        assert len(attn.history()) == 2

    def test_retrieve_uses_current_focus(self):
        from knowledge.attention import AttentionSystem
        attn = AttentionSystem()
        attn.focus("python")
        assert isinstance(attn.retrieve(), list)

    def test_retrieve_returns_empty_when_no_focus(self):
        from knowledge.attention import AttentionSystem
        assert AttentionSystem().retrieve() == []


class TestRetrievalStateProjections:
    """Retrieval must be observable as in-progress work on the state bus, not
    only as a post-hoc count on `data.*`."""

    def _types(self, bus):
        return [c[0][0].type for c in bus.publish_message.call_args_list]

    def _retriever(self, bus=None, results=None):
        from knowledge.retriever import AdvancedRetriever
        mock_vs = MagicMock()
        mock_vs.search.return_value = results if results is not None else [
            {"text": "Python is a language", "score": 0.9}
        ]
        return AdvancedRetriever(vector_store=mock_vs, event_bus=bus)

    def test_started_and_completed_bracket_the_retrieval(self):
        bus = MagicMock()
        self._retriever(bus).retrieve("python")
        types = self._types(bus)
        assert "state.retrieval.started" in types
        assert "state.retrieval.completed" in types
        assert types.index("state.retrieval.started") < types.index("state.retrieval.completed")

    def test_completed_carries_the_result_count(self):
        bus = MagicMock()
        self._retriever(bus).retrieve("python")
        msg = [c[0][0] for c in bus.publish_message.call_args_list
               if c[0][0].type == "state.retrieval.completed"][-1]
        assert msg.payload["count"] >= 1

    def test_payload_never_carries_the_query_or_content(self):
        """The projection exists to show that retrieval happened, not to move
        private memory content into the presentation layer."""
        bus = MagicMock()
        self._retriever(bus).retrieve("my private secret question")
        for c in bus.publish_message.call_args_list:
            msg = c[0][0]
            if not msg.type.startswith("state.retrieval"):
                continue
            assert "query" not in msg.payload
            assert "text" not in msg.payload
            assert "my private secret question" not in str(msg.payload)

    def test_empty_query_emits_no_state_projection(self):
        bus = MagicMock()
        self._retriever(bus).retrieve("")
        assert "state.retrieval.started" not in self._types(bus)

    def test_phatic_query_emits_no_state_projection(self):
        """A greeting must not make the entity flicker a retrieval."""
        from knowledge.retriever import AdvancedRetriever
        bus = MagicMock()
        AdvancedRetriever(event_bus=bus).retrieve("how are you")
        assert "state.retrieval.started" not in self._types(bus)

    def test_long_conversational_question_still_retrieves(self):
        """The phatic guard is word-bounded; a real question of similar tone
        must not be mistaken for small talk."""
        from knowledge.retriever import AdvancedRetriever
        assert AdvancedRetriever.is_phatic("how are you doing today my friend") is False

    def test_cache_hit_still_reports_completion(self):
        bus = MagicMock()
        retriever = self._retriever(bus)
        retriever.retrieve("python")
        bus.publish_message.reset_mock()
        retriever.retrieve("python")
        types = self._types(bus)
        assert "state.retrieval.started" in types
        assert "state.retrieval.completed" in types

    def test_no_bus_does_not_raise(self):
        busless = self._retriever(None)
        assert busless.retrieve("python")


class TestAdvancedRetriever:

    def test_retrieve_returns_empty_for_empty_query(self):
        from knowledge.retriever import AdvancedRetriever
        assert AdvancedRetriever().retrieve("") == []

    def test_retrieve_from_vector_store(self):
        from knowledge.retriever import AdvancedRetriever
        mock_vs = MagicMock()
        mock_vs.search.return_value = [{"text": "Python is a language", "score": 0.9}]
        results = AdvancedRetriever(vector_store=mock_vs).retrieve("python", top_k=5)
        assert results[0]["source"] == "vector"

    def test_retrieve_vector_content_key(self):
        from knowledge.retriever import AdvancedRetriever
        mock_vs = MagicMock()
        mock_vs.search.return_value = [{"content": "Some content", "relevance": 0.85}]
        assert len(AdvancedRetriever(vector_store=mock_vs).retrieve("query")) >= 1

    def test_retrieve_vector_fallback_string(self):
        from knowledge.retriever import AdvancedRetriever
        mock_vs = MagicMock()
        mock_vs.search.return_value = ["Plain string"]
        assert len(AdvancedRetriever(vector_store=mock_vs).retrieve("test")) >= 1

    def test_retrieve_vector_error_handled(self):
        from knowledge.retriever import AdvancedRetriever
        mock_vs = MagicMock()
        mock_vs.search.side_effect = Exception("DB error")
        assert isinstance(AdvancedRetriever(vector_store=mock_vs).retrieve("python"), list)

    def test_retrieve_from_beliefs(self):
        from knowledge.belief_engine import BeliefEngine
        from knowledge.retriever import AdvancedRetriever
        from memory.schema import MemoryObject
        be = BeliefEngine()
        be.update(MemoryObject(content="likes python", memory_type="preference", confidence=0.9))
        assert any(r["source"] == "belief" for r in AdvancedRetriever(belief_engine=be).retrieve("python", top_k=5))

    def test_retrieve_from_knowledge_graph(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.retriever import AdvancedRetriever
        kg = KnowledgeGraph()
        kg.add_relation("python", "used_for", "web_dev")
        assert any(r["source"] == "knowledge_graph" for r in AdvancedRetriever(knowledge_graph=kg).retrieve("python", top_k=5))

    def test_retrieve_with_attention_focus(self):
        from knowledge.attention import AttentionSystem
        from knowledge.graph import KnowledgeGraph
        from knowledge.retriever import AdvancedRetriever
        kg = KnowledgeGraph()
        kg.add_relation("python", "used_for", "data_science")
        attn = AttentionSystem(knowledge_graph=kg)
        attn.focus("python")
        assert isinstance(AdvancedRetriever(attention=attn, knowledge_graph=kg).retrieve("python", attention_focus=attn.current(), top_k=5), list)

    def test_dedup_by_content(self):
        from knowledge.retriever import AdvancedRetriever
        mock_vs = MagicMock()
        mock_vs.search.return_value = [{"text": "Same", "score": 0.9}, {"text": "Same", "score": 0.8}]
        results = AdvancedRetriever(vector_store=mock_vs).retrieve("test", top_k=5)
        assert len(results) == len(set(r["content"] for r in results))

    def test_diversify_by_source(self):
        from knowledge.retriever import AdvancedRetriever
        results = [{"source": "vector", "content": "A", "score": 0.9}, {"source": "belief", "content": "B", "score": 0.8}]
        diversified = AdvancedRetriever()._diversify(results, top_k=2)
        assert len(diversified) == 2 and diversified[0]["source"] != diversified[1]["source"]

    def test_retrieve_sorts_by_score(self):
        from knowledge.belief_engine import BeliefEngine
        from knowledge.retriever import AdvancedRetriever
        from memory.schema import MemoryObject
        be = BeliefEngine()
        be.update(MemoryObject(content="likes hiking", memory_type="preference", confidence=0.3))
        be.update(MemoryObject(content="John", memory_type="identity", confidence=0.9))
        scores = [r["score"] for r in AdvancedRetriever(belief_engine=be).retrieve("user", top_k=5)]
        assert scores == sorted(scores, reverse=True)

    def test_event_published_on_retrieve(self):
        from knowledge.retriever import AdvancedRetriever
        mock_bus = MagicMock()
        AdvancedRetriever(event_bus=mock_bus).retrieve("test")
        assert mock_bus.publish_message.called

    def test_multi_source_retrieval(self):
        from knowledge.belief_engine import BeliefEngine
        from knowledge.graph import KnowledgeGraph
        from knowledge.retriever import AdvancedRetriever
        from memory.schema import MemoryObject
        be = BeliefEngine()
        be.update(MemoryObject(content="likes python", memory_type="preference", confidence=0.9))
        kg = KnowledgeGraph()
        kg.add_relation("python", "used_for", "data_science")
        mock_vs = MagicMock()
        mock_vs.search.return_value = [{"text": "Python is great", "score": 0.95}]
        sources = {r["source"] for r in AdvancedRetriever(vector_store=mock_vs, belief_engine=be, knowledge_graph=kg).retrieve("python", top_k=10)}
        assert sources == {"vector", "belief", "knowledge_graph"}

    def test_enriched_graph_type_based_retrieval(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.reasoning import GraphReasoning
        from knowledge.retriever import AdvancedRetriever
        kg = KnowledgeGraph()
        kg.add_entity("OpenRouter", entity_type="technology")
        kg.add_entity("ChromaDB", entity_type="technology")
        gr = GraphReasoning(graph_manager=kg)
        retriever = AdvancedRetriever(
            knowledge_graph=kg, graph_reasoning=gr
        )
        results = retriever.retrieve("what type of technology", top_k=10)
        graph_items = [r for r in results if r["source"] == "knowledge_graph"]
        assert len(graph_items) >= 1

    def test_enriched_graph_neighbor_expansion(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.reasoning import GraphReasoning
        from knowledge.retriever import AdvancedRetriever
        gr = MagicMock(spec=GraphReasoning)
        gr.neighbors.return_value = [
            {"name": "data_science", "type": "field", "relation": "used_for",
             "weight": 0.9},
        ]
        kg = KnowledgeGraph()
        kg.add_relation("python", "used_for", "data_science")
        results = AdvancedRetriever(
            knowledge_graph=kg, graph_reasoning=gr
        ).retrieve("python", top_k=10)
        assert any(r["source"] == "knowledge_graph" for r in results)

    def test_enriched_graph_connection_path(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.reasoning import GraphReasoning
        from knowledge.retriever import AdvancedRetriever
        gr = MagicMock(spec=GraphReasoning)
        gr.what_connects.return_value = [
            "mai --[friend]--> syed",
        ]
        kg = KnowledgeGraph()
        kg.add_relation("mai", "friend", "syed")
        results = AdvancedRetriever(
            knowledge_graph=kg, graph_reasoning=gr
        ).retrieve("what connects mai and syed", top_k=10)
        assert any("mai --[friend]--> syed" in r["content"]
                    for r in results)

    def test_enriched_graph_fallback_when_graph_reasoning_unset(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.retriever import AdvancedRetriever
        kg = KnowledgeGraph()
        kg.add_relation("python", "used_for", "web_dev")
        results = AdvancedRetriever(knowledge_graph=kg).retrieve("python", top_k=5)
        assert any(r["source"] == "knowledge_graph" for r in results)

    def test_enriched_graph_reasoning_error_does_not_block(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.reasoning import GraphReasoning
        from knowledge.retriever import AdvancedRetriever
        gr = MagicMock(spec=GraphReasoning)
        gr.neighbors.side_effect = RuntimeError("graph unreachable")
        kg = KnowledgeGraph()
        kg.add_relation("python", "used_for", "data_science")
        results = AdvancedRetriever(
            knowledge_graph=kg, graph_reasoning=gr
        ).retrieve("python", top_k=5)
        # Should still get results via fallback
        assert any(r["source"] == "knowledge_graph" for r in results)


class TestTextChunker:

    def test_chunk_empty_text(self):
        from knowledge.chunker import TextChunker
        chunker = TextChunker()
        assert chunker.chunk_text("") == [] and chunker.chunk_text("   ") == []

    def test_chunk_small_text_single_chunk(self):
        from knowledge.chunker import TextChunker
        chunks = TextChunker(chunk_size=512, overlap=64).chunk_text("Hello world. Small text.", source="test")
        assert len(chunks) == 1 and "Hello world" in chunks[0].text

    def test_chunk_by_size_splits_large_text(self):
        from knowledge.chunker import TextChunker
        assert len(TextChunker(chunk_size=100, overlap=20).chunk_text("A. " * 50, source="test")) >= 2

    def test_chunk_paragraph_boundaries(self):
        from knowledge.chunker import TextChunker
        assert len(TextChunker(chunk_size=512).chunk_text("First.\n\nSecond.\n\nThird.", source="test")) >= 1

    def test_chunk_with_overlap_carryover(self):
        from knowledge.chunker import TextChunker
        chunks = TextChunker(chunk_size=100, overlap=30).chunk_text("word " * 100, source="test")
        if len(chunks) >= 2:
            assert len(set(chunks[0].text.split()) & set(chunks[1].text.split())) > 0

    def test_chunk_token_fallback(self):
        from knowledge.chunker import TextChunker
        assert len(TextChunker(chunk_size=50, overlap=10).chunk_text("a" * 200, source="test")) >= 2

    def test_chunk_assigns_correct_indices(self):
        from knowledge.chunker import TextChunker
        chunks = TextChunker(chunk_size=100, overlap=20).chunk_text("Sentence one. " * 20, source="test")
        assert all(c.index == i for i, c in enumerate(chunks))

    def test_chunk_source_and_metadata_propagated(self):
        from knowledge.chunker import TextChunker
        chunks = TextChunker().chunk_text("Hello world.", source="mysource", metadata={"type": "test"})
        assert chunks[0].source == "mysource" and chunks[0].metadata["type"] == "test"

    def test_chunk_token_estimate(self):
        from knowledge.chunker import TextChunker
        assert TextChunker().chunk_text("Hello world! Test.", source="test")[0].token_estimate >= 1

    def test_chunk_id_unique(self):
        from knowledge.chunker import TextChunker
        chunks = TextChunker(chunk_size=100, overlap=20).chunk_text("Sentence. " * 20, source="test")
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_paragraph_splitting(self):
        from knowledge.chunker import TextChunker
        assert len(TextChunker()._split_paragraphs("One\n\nTwo\n\nThree")) == 3

    def test_sentence_splitting(self):
        from knowledge.chunker import TextChunker
        assert len(TextChunker()._split_sentences("Hello. World! Test?")) == 3

    def test_semantic_chunker_initialization(self):
        from knowledge.chunker import TextChunker
        c = TextChunker(chunk_size=256, overlap=32, semantic_threshold=0.5)
        assert c.chunk_size == 256
        assert c.overlap == 32
        assert c.semantic_threshold == 0.5

    def test_semantic_chunker_fallback_without_embeddings(self):
        from knowledge.chunker import TextChunker
        c = TextChunker(chunk_size=100, overlap=20)
        chunks = c.chunk_text("Sentence. " * 30, source="test")
        assert len(chunks) >= 2

    def test_semantic_boundary_no_embeddings(self):
        from knowledge.chunker import TextChunker
        c = TextChunker()
        assert c._is_semantic_boundary("Hello world.", "Something else.", {}) is False

    def test_cosine_similarity(self):
        from knowledge.chunker import _cosine_similarity
        assert abs(_cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 0.001
        assert abs(_cosine_similarity([1, 0, 0], [-1, 0, 0]) + 1.0) < 0.001
        assert abs(_cosine_similarity([0, 0], [0, 0])) < 0.001

    def test_build_boundary_map_no_service(self):
        from knowledge.chunker import TextChunker
        c = TextChunker()
        assert c._build_boundary_map("Hello world. Test sentence.") == {}


class TestDocumentStore:

    def test_add_creates_record(self):
        from knowledge.document_store import DocumentStore
        record = DocumentStore().add("test.txt", "text", title="Test", chunk_count=5, total_tokens=100)
        assert record.source == "test.txt" and record.doc_type == "text"
        assert record.chunk_count == 5 and record.total_tokens == 100

    def test_get_by_source(self):
        from knowledge.document_store import DocumentStore
        store = DocumentStore()
        store.add("source.txt", "text")
        assert store.get_by_source("source.txt") is not None

    def test_get_by_source_missing(self):
        from knowledge.document_store import DocumentStore
        assert DocumentStore().get_by_source("missing") is None

    def test_remove_removes_record(self):
        from knowledge.document_store import DocumentStore
        store = DocumentStore()
        store.add("source.txt", "text")
        store.remove(store.get_by_source("source.txt").source_id)
        assert store.get_by_source("source.txt") is None

    def test_remove_missing(self):
        from knowledge.document_store import DocumentStore
        assert DocumentStore().remove("nonexistent") is False

    def test_list_all(self):
        from knowledge.document_store import DocumentStore
        store = DocumentStore()
        store.add("a.txt", "text"); store.add("b.txt", "text")
        assert len(store.list()) == 2

    def test_list_filter_by_type(self):
        from knowledge.document_store import DocumentStore
        store = DocumentStore()
        store.add("a.txt", "text"); store.add("b.py", "code")
        assert len(store.list(doc_type="text")) == 1

    def test_needs_reindex_new_source(self):
        from knowledge.document_store import DocumentStore
        assert DocumentStore().needs_reindex("unknown.txt") is True

    def test_needs_reindex_unchanged_file(self, tmp_path):
        from knowledge.document_store import DocumentStore
        f = tmp_path / "test.txt"; f.write_text("hello")
        store = DocumentStore()
        store.add(str(f), "text")
        assert store.needs_reindex(str(f)) is False

    def test_update_chunk_count(self):
        from knowledge.document_store import DocumentStore
        store = DocumentStore()
        store.add("src.txt", "text", chunk_count=5, total_tokens=100)
        store.update_chunk_count("src.txt", 10, 200)
        record = store.get_by_source("src.txt")
        assert record.chunk_count == 10 and record.total_tokens == 200

    def test_update_chunk_count_missing(self):
        from knowledge.document_store import DocumentStore
        assert DocumentStore().update_chunk_count("missing.txt", 1, 10) is False

    def test_count(self):
        from knowledge.document_store import DocumentStore
        store = DocumentStore()
        store.add("a.txt", "text"); store.add("b.py", "code")
        assert store.count() == 2 and store.count(doc_type="text") == 1

    def test_stats(self):
        from knowledge.document_store import DocumentStore
        store = DocumentStore()
        store.add("a.txt", "text", chunk_count=5, total_tokens=100)
        store.add("b.py", "code", chunk_count=3, total_tokens=60)
        s = store.stats()
        assert s["total_documents"] == 2 and s["total_chunks"] == 8 and s["total_tokens"] == 160

    def test_persistence(self, tmp_path):
        from knowledge.document_store import DocumentStore
        path = str(tmp_path / "store.json")
        DocumentStore(path=path).add("persist.txt", "text", chunk_count=3, total_tokens=60)
        store2 = DocumentStore(path=path)
        assert store2.count() == 1 and store2.get_by_source("persist.txt") is not None

    def test_needs_reindex_file_changed(self, tmp_path):
        import time

        from knowledge.document_store import DocumentStore
        f = tmp_path / "test.txt"; f.write_text("original")
        store = DocumentStore()
        store.add(str(f), "text")
        time.sleep(0.1)
        f.write_text("modified")
        assert store.needs_reindex(str(f)) is True


class TestIndexer:

    def test_index_text_empty_returns_error(self):
        from knowledge.indexer import Indexer
        assert Indexer(vector_store=MagicMock(), chunker=MagicMock()).index_text("")["error"] == "no_text"

    def test_reindex_drops_stale_chunks_by_metadata(self):
        from knowledge.chunker import TextChunker
        from knowledge.indexer import Indexer
        mock_vs = MagicMock()
        mock_vs.delete_by_metadata.return_value = True
        Indexer(vector_store=mock_vs, chunker=TextChunker(chunk_size=512)).index_text(
            "Hello world.", source="src.txt", doc_type="text"
        )
        mock_vs.delete_by_metadata.assert_called_once_with(source="src.txt", memory_type="knowledge")

    def test_index_text_chunks_and_stores(self):
        from knowledge.chunker import TextChunker
        from knowledge.indexer import Indexer
        mock_vs = MagicMock()
        result = Indexer(vector_store=mock_vs, chunker=TextChunker(chunk_size=512)).index_text("Hello world. Test.", source="test", doc_type="text")
        assert result["indexed"] >= 1 and mock_vs.add.called

    def test_index_text_with_document_store(self):
        from knowledge.chunker import TextChunker
        from knowledge.document_store import DocumentStore
        from knowledge.indexer import Indexer
        ds = DocumentStore()
        result = Indexer(vector_store=MagicMock(), chunker=TextChunker(chunk_size=512), document_store=ds).index_text("Some text.", source="src.txt", doc_type="text", title="Test")
        assert result["indexed"] >= 1 and ds.get_by_source("src.txt") is not None

    def test_index_text_updates_existing(self):
        from knowledge.chunker import TextChunker
        from knowledge.document_store import DocumentStore
        from knowledge.indexer import Indexer
        ds = DocumentStore(); ds.add("src.txt", "text", chunk_count=3, total_tokens=60)
        Indexer(vector_store=MagicMock(), chunker=TextChunker(chunk_size=512), document_store=ds).index_text("New text.", source="src.txt", doc_type="text")
        assert ds.get_by_source("src.txt").chunk_count >= 1

    def test_index_text_with_metadata(self):
        from knowledge.chunker import TextChunker
        from knowledge.indexer import Indexer
        result = Indexer(vector_store=MagicMock(), chunker=TextChunker(chunk_size=512)).index_text("Content.", source="src", doc_type="text", title="T", metadata={"source_type": "test"})
        assert result["indexed"] >= 1

    def test_index_file_not_found(self):
        from knowledge.indexer import Indexer
        result = Indexer(vector_store=MagicMock(), chunker=MagicMock()).index_file("/nonexistent/file.txt")
        assert "file_not_found" in result["error"]

    def test_index_file_auto_type(self, tmp_path):
        from knowledge.chunker import TextChunker
        from knowledge.indexer import Indexer
        f = tmp_path / "test.py"; f.write_text("print('hello')")
        assert Indexer(vector_store=MagicMock(), chunker=TextChunker(chunk_size=512)).index_file(str(f))["indexed"] >= 1

    def test_index_file_skip_up_to_date(self, tmp_path):
        from knowledge.chunker import TextChunker
        from knowledge.document_store import DocumentStore
        from knowledge.indexer import Indexer
        f = tmp_path / "test.txt"; f.write_text("content")
        ds = DocumentStore(); ds.add(str(f), "text")
        assert Indexer(vector_store=MagicMock(), chunker=TextChunker(chunk_size=512), document_store=ds).index_file(str(f))["error"] == "up_to_date"

    def test_index_directory(self, tmp_path):
        from knowledge.chunker import TextChunker
        from knowledge.indexer import Indexer
        d = tmp_path / "docs"; d.mkdir()
        (d / "a.txt").write_text("A"); (d / "b.txt").write_text("B")
        result = Indexer(vector_store=MagicMock(), chunker=TextChunker(chunk_size=512)).index_directory(str(d), pattern="*.txt")
        assert result["indexed"] >= 1 and result["files_processed"] == 2

    def test_index_directory_not_found(self):
        from knowledge.indexer import Indexer
        assert "directory_not_found" in Indexer(vector_store=MagicMock(), chunker=MagicMock()).index_directory("/nonexistent")["error"]

    def test_detect_type(self):
        from knowledge.indexer import Indexer
        idx = Indexer(vector_store=MagicMock(), chunker=MagicMock())
        assert idx._detect_type("file.py") == "code" and idx._detect_type("file.md") == "markdown"
        assert idx._detect_type("file.txt") == "text" and idx._detect_type("file.json") == "config"
        assert idx._detect_type("file.html") == "markup" and idx._detect_type("file.csv") == "data"
        assert idx._detect_type("file.unknown") == "text"

    def test_stats(self):
        from knowledge.indexer import Indexer
        assert Indexer(vector_store=MagicMock(), chunker=MagicMock()).stats() == {"total_indexed_chunks": 0}

    def test_index_text_publishes_event(self):
        from knowledge.chunker import TextChunker
        from knowledge.indexer import Indexer
        mock_bus = MagicMock()
        Indexer(vector_store=MagicMock(), chunker=TextChunker(chunk_size=512), event_bus=mock_bus).index_text("Hello.", source="src")
        assert mock_bus.publish_message.called

    def test_index_directory_publishes_event(self, tmp_path):
        from knowledge.chunker import TextChunker
        from knowledge.indexer import Indexer
        d = tmp_path / "docs"; d.mkdir(); (d / "a.txt").write_text("content")
        mock_bus = MagicMock()
        Indexer(vector_store=MagicMock(), chunker=TextChunker(chunk_size=512), event_bus=mock_bus).index_directory(str(d), pattern="*.txt")
        assert any(c[0][0].type == "data.indexer.completed" for c in mock_bus.publish_message.call_args_list)


class TestKnowledgeBaseBuilder:

    def test_build_from_text(self):
        from knowledge.builder import KnowledgeBaseBuilder
        mock_idx = MagicMock(); mock_idx.index_text.return_value = {"indexed": 2}
        result = KnowledgeBaseBuilder(indexer=mock_idx, document_store=MagicMock(), vector_store=MagicMock()).build_from_text("Hello.", source="test")
        assert result["success"] and result["indexed"] == 2

    def test_build_from_text_empty(self):
        from knowledge.builder import KnowledgeBaseBuilder
        result = KnowledgeBaseBuilder(indexer=MagicMock(), document_store=MagicMock(), vector_store=MagicMock()).build_from_text("", source="test")
        assert not result["success"] and result["error"] == "no_text"

    def test_build_from_file(self, tmp_path):
        from knowledge.builder import KnowledgeBaseBuilder
        f = tmp_path / "test.txt"; f.write_text("content")
        mock_idx = MagicMock(); mock_idx.index_file.return_value = {"indexed": 3}
        result = KnowledgeBaseBuilder(indexer=mock_idx, document_store=MagicMock(), vector_store=MagicMock()).build_from_file(str(f))
        assert result["success"] and result["indexed"] == 3

    def test_build_from_file_not_found(self):
        from knowledge.builder import KnowledgeBaseBuilder
        result = KnowledgeBaseBuilder(indexer=MagicMock(), document_store=MagicMock(), vector_store=MagicMock()).build_from_file("/nonexistent.txt")
        assert "file_not_found" in result["error"]

    def test_build_from_directory(self, tmp_path):
        from knowledge.builder import KnowledgeBaseBuilder
        d = tmp_path / "docs"; d.mkdir(); (d / "a.txt").write_text("content")
        mock_idx = MagicMock(); mock_idx.index_file.return_value = {"indexed": 2}
        with patch("os.path.isfile", return_value=True):
            result = KnowledgeBaseBuilder(indexer=mock_idx, document_store=MagicMock(), vector_store=MagicMock()).build_from_directory(str(d), pattern="*.*")
        assert result["success"]

    def test_rebuild_all(self):
        from knowledge.builder import KnowledgeBaseBuilder
        mock_doc = MagicMock(); mock_doc.source = "f.txt"
        mock_ds = MagicMock(); mock_ds.list.return_value = [mock_doc]
        mock_idx = MagicMock(); mock_idx.index_file.return_value = {"indexed": 2}
        with patch("os.path.isfile", return_value=True):
            result = KnowledgeBaseBuilder(indexer=mock_idx, document_store=mock_ds, vector_store=MagicMock()).rebuild_all()
        assert result["total_reindexed"] == 2

    def test_rebuild_all_skips_missing(self):
        from knowledge.builder import KnowledgeBaseBuilder
        mock_doc = MagicMock(); mock_doc.source = "missing.txt"
        mock_ds = MagicMock(); mock_ds.list.return_value = [mock_doc]
        with patch("os.path.isfile", return_value=False):
            result = KnowledgeBaseBuilder(indexer=MagicMock(), document_store=mock_ds, vector_store=MagicMock()).rebuild_all()
        assert result["total_reindexed"] == 0

    def test_search_passthrough(self):
        from knowledge.builder import KnowledgeBaseBuilder
        mock_vs = MagicMock(); mock_vs.search.return_value = [{"text": "result", "score": 0.9}]
        results = KnowledgeBaseBuilder(indexer=MagicMock(), document_store=MagicMock(), vector_store=mock_vs).search("query", top_k=3)
        assert len(results) == 1 and results[0]["text"] == "result"

    def test_history(self):
        from knowledge.builder import KnowledgeBaseBuilder
        mock_idx = MagicMock(); mock_idx.index_text.return_value = {"indexed": 1}
        builder = KnowledgeBaseBuilder(indexer=mock_idx, document_store=MagicMock(), vector_store=MagicMock())
        builder.build_from_text("T1", source="s1"); builder.build_from_text("T2", source="s2")
        hist = builder.history()
        assert len(hist) == 2 and hist[0]["source"] == "s1" and hist[1]["source"] == "s2"

    def test_history_limit(self):
        from knowledge.builder import KnowledgeBaseBuilder
        mock_idx = MagicMock(); mock_idx.index_text.return_value = {"indexed": 1}
        builder = KnowledgeBaseBuilder(indexer=mock_idx, document_store=MagicMock(), vector_store=MagicMock())
        for i in range(5): builder.build_from_text(f"T{i}", source=f"s{i}")
        assert len(builder.history(limit=3)) == 3

    def test_stats_aggregates(self):
        from knowledge.builder import KnowledgeBaseBuilder
        mock_idx = MagicMock(); mock_idx.stats.return_value = {"total_indexed_chunks": 10}
        mock_ds = MagicMock(); mock_ds.stats.return_value = {"total_documents": 3}
        mock_vs = MagicMock(); mock_vs.count.return_value = 42
        s = KnowledgeBaseBuilder(indexer=mock_idx, document_store=mock_ds, vector_store=mock_vs).stats()
        assert s["vector_store_count"] == 42 and s["indexer"]["total_indexed_chunks"] == 10

    def test_build_from_text_publishes_event(self):
        from knowledge.builder import KnowledgeBaseBuilder
        mock_idx = MagicMock(); mock_idx.index_text.return_value = {"indexed": 1}
        mock_bus = MagicMock()
        KnowledgeBaseBuilder(indexer=mock_idx, document_store=MagicMock(), vector_store=MagicMock(), event_bus=mock_bus).build_from_text("Hello", source="s")
        assert mock_bus.publish_message.called


class TestKnowledgeGraphExtension:

    def test_entity_count(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        assert kg.entity_count() == 0
        kg.add_entity("mai", entity_type="project")
        assert kg.entity_count() == 1

    def test_relation_count(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        assert kg.relation_count() == 0
        kg.add_relation("user", "builds", "mai")
        assert kg.relation_count() == 1

    def test_get_entity_by_type(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("mai", entity_type="project")
        kg.add_entity("murtaza", entity_type="person")
        results = kg.get_entity_by_type("project")
        assert len(results) == 1
        assert results[0].name == "mai"

    def test_most_connected(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_relation("a", "links", "b")
        kg.add_relation("a", "links", "c")
        kg.add_relation("b", "links", "d")
        top = kg.most_connected(limit=2)
        assert top[0][0] == "a"
        assert top[0][1] == 2

    def test_stats_empty(self):
        from knowledge.graph import KnowledgeGraph
        s = KnowledgeGraph().stats()
        assert s["nodes"] == 0 and s["edges"] == 0

    def test_stats_populated(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_relation("a", "links", "b")
        kg.add_relation("a", "links", "c")
        s = kg.stats()
        assert s["nodes"] == 3
        assert s["edges"] == 2
        assert s["avg_degree"] > 0

    def test_remove_entity(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("mai")
        kg.add_relation("user", "builds", "mai")
        assert kg.remove_entity("mai") is True
        assert kg.entity_count() == 1
        assert kg.remove_entity("nonexistent") is False

    def test_remove_relation(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_relation("a", "links", "b")
        assert kg.remove_relation("a", "links", "b") is True
        assert kg.relation_count() == 0
        assert kg.remove_relation("a", "links", "b") is False

    def test_search(self):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("OpenRouter")
        kg.add_entity("OpenAI")
        kg.add_entity("Whisper")
        results = kg.search("open")
        names = [e.name for e in results]
        assert "openrouter" in names
        assert "openai" in names
        assert "whisper" not in names

    def test_search_empty_query(self):
        from knowledge.graph import KnowledgeGraph
        assert KnowledgeGraph().search("") == []


class TestEntityExtractor:

    def test_extract_fallback_entities(self):
        from knowledge.extractor import EntityExtractor
        ee = EntityExtractor()
        result = ee.extract("I use OpenRouter and Whisper")
        entities = result["entities"]
        assert len(entities) >= 2

    def test_extract_fallback_relations(self):
        from knowledge.extractor import EntityExtractor
        ee = EntityExtractor()
        result = ee.extract("I use OpenRouter")
        relations = result["relations"]
        assert any(r["source"] == "user" and r["relation"] == "uses" for r in relations)

    def test_extract_liked_relation(self):
        from knowledge.extractor import EntityExtractor
        ee = EntityExtractor()
        result = ee.extract("I like Anime")
        relations = result["relations"]
        assert any(r["relation"] == "likes" for r in relations)

    def test_extract_switched_relation(self):
        from knowledge.extractor import EntityExtractor
        ee = EntityExtractor()
        result = ee.extract("I switched from Qwen to Gemma")
        relations = result["relations"]
        assert any(r["relation"] == "uses" for r in relations)

    def test_extract_from_conversation(self):
        from knowledge.extractor import EntityExtractor
        ee = EntityExtractor()
        result = ee.extract_from_conversation(
            "I use Python", "That is great"
        )
        assert len(result["entities"]) >= 1

    def test_llm_mode_valid_json(self):
        from unittest.mock import MagicMock

        from knowledge.extractor import EntityExtractor
        mock_llm = MagicMock()
        mock_llm.generate.return_value = (
            '{"entities": [{"name": "Python", "type": "skill"}],'
            '"relations": [{"source": "user", "relation": "uses", "target": "Python"}]}'
        )
        ee = EntityExtractor(llm=mock_llm)
        result = ee.extract("I use Python")
        assert len(result["entities"]) == 1
        assert result["entities"][0]["name"] == "Python"
        assert len(result["relations"]) == 1

    def test_llm_mode_invalid_json_falls_back_to_regex(self):
        from unittest.mock import MagicMock

        from knowledge.extractor import EntityExtractor
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "not json"
        ee = EntityExtractor(llm=mock_llm)
        result = ee.extract("I use Python")
        assert len(result["entities"]) >= 1

    def test_llm_mode_none_falls_back_to_regex(self):
        from unittest.mock import MagicMock

        from knowledge.extractor import EntityExtractor
        mock_llm = MagicMock()
        mock_llm.generate.return_value = None
        ee = EntityExtractor(llm=mock_llm)
        result = ee.extract("I use Python")
        assert len(result["entities"]) >= 1

    def test_llm_mode_typed_entities(self):
        from unittest.mock import MagicMock

        from knowledge.extractor import EntityExtractor
        mock_llm = MagicMock()
        mock_llm.generate.return_value = (
            '{"entities": [{"name": "Python", "type": "technology"},'
            '{"name": "ChromaDB", "type": "technology"}],'
            '"relations": [{"source": "user", "relation": "uses", "target": "Python"},'
            '{"source": "user", "relation": "uses", "target": "ChromaDB"}]}'
        )
        ee = EntityExtractor(llm=mock_llm)
        result = ee.extract("I use Python and ChromaDB for memory")
        types = {e["name"]: e["type"] for e in result["entities"]}
        assert types.get("Python") == "technology"
        assert types.get("ChromaDB") == "technology"
        assert len(result["relations"]) == 2


class TestConsolidationEngine:

    def test_normalize_name(self):
        from knowledge.consolidation import ConsolidationEngine
        ce = ConsolidationEngine()
        assert ce.normalize_name("  Open Router  ") == "open router"
        assert ce.normalize_name("the Open Router") == "open router"

    def test_merge_candidates_exact_match(self):
        from knowledge.consolidation import ConsolidationEngine
        ce = ConsolidationEngine()
        groups = ce.merge_candidates(["OpenRouter", "OpenRouter"])
        assert len(groups) == 1

    def test_merge_candidates_fuzzy_match(self):
        from knowledge.consolidation import ConsolidationEngine
        ce = ConsolidationEngine()
        groups = ce.merge_candidates(["OpenRouter", "open router", "Open Router"])
        assert len(groups) == 1

    def test_merge_candidates_no_match(self):
        from knowledge.consolidation import ConsolidationEngine
        ce = ConsolidationEngine()
        groups = ce.merge_candidates(["Python", "JavaScript"])
        assert len(groups) == 2

    def test_merge_candidates_empty(self):
        from knowledge.consolidation import ConsolidationEngine
        ce = ConsolidationEngine()
        assert ce.merge_candidates([]) == []

    def test_deduplicate_new_entities(self):

        from knowledge.consolidation import ConsolidationEngine
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        ce = ConsolidationEngine()
        entities = [{"name": "Python", "type": "skill"}]
        entities_out, _ = ce.deduplicate(kg, entities, [])
        assert len(entities_out) == 1

    def test_deduplicate_skips_duplicates(self):
        from knowledge.consolidation import ConsolidationEngine
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("Python", entity_type="skill")
        ce = ConsolidationEngine()
        entities = [{"name": "Python", "type": "skill"}, {"name": "JavaScript", "type": "skill"}]
        entities_out, _ = ce.deduplicate(kg, entities, [])
        assert len(entities_out) == 1
        assert entities_out[0]["name"] == "JavaScript"

    def test_deduplicate_remaps_relations(self):
        from knowledge.consolidation import ConsolidationEngine
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph()
        kg.add_entity("python", entity_type="skill")
        ce = ConsolidationEngine()
        entities = [{"name": "Python", "type": "skill"}]
        relations = [{"source": "user", "relation": "uses", "target": "Python"}]
        entities_out, relations_out = ce.deduplicate(kg, entities, relations)
        assert len(entities_out) == 0
        assert len(relations_out) == 1
        assert relations_out[0]["target"] == "python"

    def test_deduplicate_self_relation_skipped(self):
        from knowledge.consolidation import ConsolidationEngine
        from knowledge.graph import KnowledgeGraph
        ce = ConsolidationEngine()
        relations = [{"source": "x", "relation": "self", "target": "x"}]
        _, rels_out = ce.deduplicate(KnowledgeGraph(), [], relations)
        assert len(rels_out) == 0


class TestGraphManager:

    def test_process_conversation_adds_entities(self):
        from knowledge.extractor import EntityExtractor
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_manager import GraphManager
        gm = GraphManager(
            graph=KnowledgeGraph(),
            extractor=EntityExtractor(),
        )
        summary = gm.process_conversation("I use OpenRouter", "OK")
        assert summary["entities_added"] >= 1
        assert summary["relations_added"] >= 0

    def test_process_conversation_empty(self):
        from knowledge.graph_manager import GraphManager
        gm = GraphManager()
        summary = gm.process_conversation("", "")
        assert summary["entities_added"] == 0

    def test_facade_search(self):
        from knowledge.graph_manager import GraphManager
        gm = GraphManager()
        gm.graph.add_entity("ChromaDB", entity_type="technology")
        results = gm.graph.search("chroma")
        assert len(results) >= 1

    def test_facade_stats(self):
        from knowledge.graph_manager import GraphManager
        s = GraphManager().graph.stats()
        assert "nodes" in s

    def test_facade_add_and_count(self):
        from knowledge.graph_manager import GraphManager
        gm = GraphManager()
        gm.graph.add_entity("test_entity", entity_type="test")
        assert gm.graph.entity_count() == 1
        assert gm.graph.relation_count() == 0

    def test_facade_get_entity(self):
        from knowledge.graph_manager import GraphManager
        gm = GraphManager()
        gm.graph.add_entity("test_entity")
        assert gm.graph.get_entity("test_entity") is not None
        assert gm.graph.get_entity("nonexistent") is None

    def test_facade_get_entity_by_type(self):
        from knowledge.graph_manager import GraphManager
        gm = GraphManager()
        gm.graph.add_entity("mai", entity_type="project")
        results = gm.graph.get_entity_by_type("project")
        assert len(results) == 1

    def test_facade_most_connected(self):
        from knowledge.graph_manager import GraphManager
        gm = GraphManager()
        gm.graph.add_relation("a", "links", "b")
        top = gm.graph.most_connected(limit=5)
        assert len(top) >= 1

    def test_facade_remove_entity(self):
        from knowledge.graph_manager import GraphManager
        gm = GraphManager()
        gm.graph.add_entity("temp")
        assert gm.graph.remove_entity("temp") is True
        assert gm.graph.get_entity("temp") is None

    def test_facade_remove_relation(self):
        from knowledge.graph_manager import GraphManager
        gm = GraphManager()
        gm.graph.add_relation("a", "links", "b")
        assert gm.graph.remove_relation("a", "links", "b") is True

    def test_facade_query(self):
        from knowledge.graph_manager import GraphManager
        gm = GraphManager()
        gm.graph.add_relation("user", "builds", "mai")
        results = gm.graph.query("user", depth=1)
        assert len(results) >= 1

    def test_event_publishing(self):
        from unittest.mock import MagicMock

        from knowledge.graph_manager import GraphManager
        bus = MagicMock()
        gm = GraphManager(event_bus=bus)
        gm.process_conversation("hello", "hi")
        assert bus.publish_message.called


class _MockEntity:
    def __init__(self, name, type="person", created_at=1000):
        self.name = name
        self.type = type
        self.created_at = created_at


class _MockRelation:
    def __init__(self, source, target, relation="knows", weight=1.0):
        self.source = source
        self.target = target
        self.relation = relation
        self.weight = weight


class _MockGraph:
    def all_entities(self):
        return []


class TestGraphReasoning:

    def test_neighbors_returns_empty_without_graph_manager(self):
        from knowledge.reasoning import GraphReasoning
        gr = GraphReasoning()
        assert gr.neighbors("test") == []

    def _make_graph_mock(self):
        gm = MagicMock()
        gm.graph = MagicMock()
        return gm

    def test_neighbors_returns_related_entities(self):
        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()
        gm.graph.query.return_value = [
            _MockRelation("mai", "syed", "friend", 1.0),
            _MockRelation("mai", "haruki", "knows", 0.8),
        ]
        gm.graph.get_entity.side_effect = lambda n: _MockEntity(n)
        gr = GraphReasoning(gm)
        nbrs = gr.neighbors("mai")
        assert len(nbrs) == 2
        assert any(n["name"] == "syed" for n in nbrs)
        assert any(n["name"] == "haruki" for n in nbrs)

    def test_neighbors_returns_empty_on_error(self):
        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()
        gm.graph.query.side_effect = RuntimeError("fail")
        gr = GraphReasoning(gm)
        assert gr.neighbors("test") == []

    def test_shortest_path_same_source_target(self):
        from knowledge.reasoning import GraphReasoning
        gr = GraphReasoning(self._make_graph_mock())
        assert gr.shortest_path("a", "a") == ["a"]

    def test_shortest_path_direct_connection(self):
        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()
        gm.graph.query.return_value = [_MockRelation("mai", "syed", "friend")]
        gr = GraphReasoning(gm)
        path = gr.shortest_path("mai", "syed")
        assert path == ["mai", "syed"]

    def test_shortest_path_two_hops(self):
        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()
        call_count = [0]

        def query_side_effect(entity, depth=1):
            call_count[0] += 1
            if call_count[0] == 1:
                return [_MockRelation("mai", "akane", "friend")]
            return [_MockRelation("akane", "syed", "friend")]

        gm.graph.query.side_effect = query_side_effect
        gr = GraphReasoning(gm)
        path = gr.shortest_path("mai", "syed")
        assert path == ["mai", "akane", "syed"]

    def test_shortest_path_no_connection(self):
        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()
        gm.graph.query.return_value = [_MockRelation("mai", "akane", "friend")]
        gr = GraphReasoning(gm)
        path = gr.shortest_path("mai", "bob")
        assert path == []

    def test_query_by_type(self):
        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()
        gm.graph.get_entity_by_type.return_value = [
            _MockEntity("mai", "ai"),
            _MockEntity("akane", "ai"),
        ]
        gr = GraphReasoning(gm)
        ents = gr.query_by_type("ai")
        assert len(ents) == 2
        assert all(e["type"] == "ai" for e in ents)

    def test_recent_entities(self):
        import time

        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()
        now = time.time()
        ent_old = _MockEntity("old", "person", now - 7200)
        ent_new = _MockEntity("new", "person", now - 30)
        gm.graph.all_entities = lambda: [ent_old, ent_new]
        gr = GraphReasoning(gm)
        recent = gr.recent_entities(minutes=60)
        assert len(recent) == 1
        assert recent[0]["name"] == "new"

    def test_what_connects_returns_edges(self):
        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()
        gm.graph.query.side_effect = lambda e, depth=1: {
            "mai": [_MockRelation("mai", "akane", "friend")],
            "akane": [_MockRelation("akane", "syed", "friend")],
            "syed": [],
        }.get(e.lower(), [])
        gr = GraphReasoning(gm)
        edges = gr.what_connects("mai", "syed")
        assert len(edges) >= 1

    def test_answer_what_connects(self):
        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()
        gm.graph.query.return_value = [_MockRelation("mai", "syed", "friend")]
        gr = GraphReasoning(gm)
        result = gr.answer("what connects mai and syed")
        assert "Connection" in result

    def test_answer_what_is_related(self):
        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()
        gm.graph.query.return_value = [_MockRelation("mai", "syed", "friend")]
        gm.graph.get_entity.return_value = _MockEntity("syed")
        gr = GraphReasoning(gm)
        result = gr.answer("what is related to mai")
        assert "Entities related" in result

    def test_answer_path(self):
        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()

        def q(e, depth=1):
            if e.lower() == "mai":
                return [_MockRelation("mai", "syed", "friend")]
            return []

        gm.graph.query.side_effect = q
        gr = GraphReasoning(gm)
        result = gr.answer("path from mai to syed")
        assert "Path" in result

    def test_answer_unknown_returns_hint(self):
        from knowledge.reasoning import GraphReasoning
        gr = GraphReasoning(self._make_graph_mock())
        result = gr.answer("unknown query type")
        assert "Try:" in result

    def test_format_context_returns_empty_without_manager(self):
        from knowledge.reasoning import GraphReasoning
        gr = GraphReasoning()
        assert gr.format_context("test") == ""

    def test_format_context_returns_formatted_lines(self):
        from knowledge.reasoning import GraphReasoning
        gm = self._make_graph_mock()
        gm.graph.query.return_value = [
            _MockRelation("mai", "syed", "friend", 1.0),
            _MockRelation("mai", "haruki", "knows", 0.5),
        ]
        gm.graph.get_entity.side_effect = lambda n: _MockEntity(n)
        gr = GraphReasoning(gm)
        ctx = gr.format_context("mai")
        assert "[graph] syed" in ctx
        assert "[graph] haruki" in ctx

    def test_format_context_returns_empty_on_exception(self):
        from knowledge.reasoning import GraphReasoning
        gm = MagicMock()
        gm.query.side_effect = Exception("boom")
        gr = GraphReasoning(gm)
        assert gr.format_context("test") == ""

    def test_graph_query_tool_registers(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        from knowledge.reasoning import GraphReasoning
        reg = ToolRegistry()
        gm = MagicMock()
        gr = GraphReasoning(gm)
        register_builtin_tools(reg, graph_manager=gm, graph_reasoning=gr)
        assert reg.get("graph_query") is not None
        assert reg.get("graph_search") is not None
        assert reg.get("graph_reason") is not None

    def test_graph_tools_unregistered_without_manager(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        reg = ToolRegistry()
        register_builtin_tools(reg)
        assert reg.get("graph_query") is None
        assert reg.get("graph_search") is None
        assert reg.get("graph_reason") is None


class TestObsidianWriter:

    def test_sync_creates_markdown_files(self, tmp_path):
        from knowledge.graph import KnowledgeGraph
        from knowledge.obsidian_writer import ObsidianWriter
        gm = KnowledgeGraph()
        gm.add_entity("Mai", entity_type="character", metadata={"source": "test"})
        gm.add_entity("Syed", entity_type="person")
        gm.add_relation("Mai", "friend", "Syed")
        writer = ObsidianWriter(graph_manager=gm, vault_path=str(tmp_path), subdir="graph")
        stats = writer.sync()
        assert stats["written"] == 2
        assert stats["deleted"] == 0
        mai_path = tmp_path / "graph" / "mai.md"
        syed_path = tmp_path / "graph" / "syed.md"
        assert mai_path.exists()
        assert syed_path.exists()

    def test_markdown_contains_frontmatter_and_links(self, tmp_path):
        from knowledge.graph import KnowledgeGraph
        from knowledge.obsidian_writer import ObsidianWriter
        gm = KnowledgeGraph()
        gm.add_entity("Mai", entity_type="character", metadata={"source": "test"})
        gm.add_entity("Syed", entity_type="person")
        gm.add_relation("Mai", "friend", "Syed")
        writer = ObsidianWriter(graph_manager=gm, vault_path=str(tmp_path), subdir="graph")
        writer.sync()
        content = (tmp_path / "graph" / "mai.md").read_text(encoding="utf-8")
        assert "type: \"character\"" in content
        assert "friend" in content
        assert "[[syed]]" in content

    def test_delete_stale_entities(self, tmp_path):
        from knowledge.graph import KnowledgeGraph
        from knowledge.obsidian_writer import ObsidianWriter
        gm = KnowledgeGraph()
        gm.add_entity("Mai", entity_type="character")
        writer = ObsidianWriter(graph_manager=gm, vault_path=str(tmp_path), subdir="graph")
        writer.sync()
        gm.remove_entity("Mai")
        stats = writer.sync()
        assert stats["deleted"] == 1
        assert stats["written"] == 0

    def test_sanitize_handles_special_chars(self, tmp_path):
        from knowledge.graph import KnowledgeGraph
        from knowledge.obsidian_writer import ObsidianWriter
        gm = KnowledgeGraph()
        gm.add_entity("Test@Entity#1!", entity_type="test")
        writer = ObsidianWriter(graph_manager=gm, vault_path=str(tmp_path), subdir="graph")
        writer.sync()
        expected_file = tmp_path / "graph" / "testentity1.md"
        assert expected_file.exists()

    def test_backlinks_section(self, tmp_path):
        from knowledge.graph import KnowledgeGraph
        from knowledge.obsidian_writer import ObsidianWriter
        gm = KnowledgeGraph()
        gm.add_entity("Mai", entity_type="character")
        gm.add_entity("Syed", entity_type="person")
        gm.add_entity("Haruki", entity_type="character")
        gm.add_relation("Mai", "friend", "Syed")
        gm.add_relation("Haruki", "knows", "Mai")
        writer = ObsidianWriter(graph_manager=gm, vault_path=str(tmp_path), subdir="graph")
        writer.sync()
        mai_content = (tmp_path / "graph" / "mai.md").read_text(encoding="utf-8")
        assert "[[syed]]" in mai_content
        assert "Referenced By" in mai_content
        assert "[[haruki]]" in mai_content

    def test_empty_graph_produces_zero_writes(self, tmp_path):
        from knowledge.graph import KnowledgeGraph
        from knowledge.obsidian_writer import ObsidianWriter
        gm = KnowledgeGraph()
        writer = ObsidianWriter(graph_manager=gm, vault_path=str(tmp_path))
        stats = writer.sync()
        assert stats["written"] == 0
        assert stats["deleted"] == 0

    def test_obsidian_sync_tool_registers(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        reg = ToolRegistry()
        register_builtin_tools(reg, obsidian_writer=MagicMock())
        assert reg.get("obsidian_sync") is not None

    def test_obsidian_sync_tool_unregistered_without_writer(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        reg = ToolRegistry()
        register_builtin_tools(reg)
        assert reg.get("obsidian_sync") is None

    # ==================================================
    # 🧠 MERGED MEMORY WRITE METHODS
    # ==================================================

    def test_write_memory_creates_file(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        results = writer.write_memory(
            routes=["conversation"],
            user="hello", ai="hi",
            tags=["test"], emotion={"type": "happy", "intensity": 0.8},
            score=0.7,
        )
        assert results.get("conversation") is True
        conv_dir = tmp_path / "conversation"
        assert conv_dir.exists()
        files = list(conv_dir.iterdir())
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert "hello" in content
        assert "hi" in content

    def test_write_memory_dedup(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        writer.write_memory(["conversation"], "hello", "hi", [], {}, 0.5)
        result = writer.write_memory(["conversation"], "hello", "hi", [], {}, 0.5)
        assert result.get("conversation") is False

    def test_write_memory_unknown_folder_skipped(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        results = writer.write_memory(["nonexistent"], "hello", "hi", [], {}, 0.5)
        assert results == {}

    def test_raw_write_never_clobbers_compiler_owned_folder(self, tmp_path):
        """Regression: raw turn writes must not overwrite compiler-owned
        structured files (identity/preferences/relationship/knowledge/...).
        The compiled file keeps its facts; the raw turn goes to conversation/.
        """
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import IdentityFact, MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        state.identity.append(IdentityFact(fact="I am 25", category="age", timestamp="2026-01-01"))
        state.identity.append(IdentityFact(fact="I love python", category="interest", timestamp="2026-02-01"))
        writer.dump(state, "2026-06-01")
        identity_file = tmp_path / "identity" / "user.md"
        compiled = identity_file.read_text(encoding="utf-8")
        assert "I am 25" in compiled
        writer.write(folder="identity", user="raw turn only", ai="", tags=[], emotion={}, score=0.4)
        after = identity_file.read_text(encoding="utf-8")
        assert "I am 25" in after
        assert "I love python" in after
        assert "raw turn only" not in after
        conv_files = list((tmp_path / "conversation").glob("*.md"))
        assert len(conv_files) == 1
        assert "raw turn only" in conv_files[0].read_text(encoding="utf-8")

    def test_raw_write_to_relationship_redirected(self, tmp_path):
        """Relationship folder is compiler-owned (compile_relationship)."""
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        writer.write(folder="relationship", user="i trust you", ai="", tags=[], emotion={}, score=0.9)
        rel_file = tmp_path / "relationship" / "relationship.md"
        assert not rel_file.exists() or "i trust you" not in rel_file.read_text(encoding="utf-8", errors="replace")
        conv_files = list((tmp_path / "conversation").glob("*.md"))
        assert any("i trust you" in f.read_text(encoding="utf-8") for f in conv_files)

    # ── Fix 4: cross-day memory dedup ──

    def test_write_memory_cross_day_dedup(self, tmp_path):
        """Same user turn must not be duplicated into a new conversation file
        on a later day (the vault showed 10x 'machine learning' duplicates).
        """
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        assert writer.write_memory(["conversation"], "machine learning", "cool!", [], {}, 0.5)
        files = list((tmp_path / "conversation").glob("*.md"))
        assert len(files) == 1
        # simulate a fresh process (hash_cache reset) writing the same turn again
        writer.clear_cache()
        result = writer.write_memory(["conversation"], "machine learning", "cool!", [], {}, 0.5)
        assert result.get("conversation") is False
        files = list((tmp_path / "conversation").glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text(encoding="utf-8")
        assert content.count("machine learning") == 1

    def test_write_memory_cross_day_dedup_same_text_different_days(self, tmp_path):
        """Dedup must hit even when the daily file name changes (new date)."""
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        assert writer.write_memory(["conversation"], "i love python", "nice", [], {}, 0.5)
        first = list((tmp_path / "conversation").glob("*.md"))[0]
        first.rename(tmp_path / "conversation" / "1999-01-01.md")
        writer.clear_cache()
        result = writer.write_memory(["conversation"], "i love python", "nice", [], {}, 0.5)
        assert result.get("conversation") is False
        assert len(list((tmp_path / "conversation").glob("*.md"))) == 1

    def test_write_memory_cross_day_different_turn_not_deduped(self, tmp_path):
        """Different turns on different days must both be stored."""
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        assert writer.write_memory(["conversation"], "machine learning", "cool!", [], {}, 0.5)
        first = list((tmp_path / "conversation").glob("*.md"))[0]
        first.rename(tmp_path / "conversation" / "1999-01-01.md")
        writer.clear_cache()
        assert writer.write_memory(["conversation"], "python testing", "great", [], {}, 0.5)
        assert len(list((tmp_path / "conversation").glob("*.md"))) == 2

    def test_write_memory_reinforcement_bumps_existing(self, tmp_path):
        """Repeated turn should bump reinforcement_count on the canonical entry."""
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        writer.write_memory(
            ["conversation"], "hello", "hi",
            ["test"], {"type": "happy", "intensity": 0.8}, 0.7,
            metadata={"reinforcement_count": 1},
        )
        f = list((tmp_path / "conversation").glob("*.md"))[0]
        new_path = tmp_path / "conversation" / "1998-01-01.md"
        # move out of the current-day file so cross-day dedup path fires
        f.rename(new_path)
        writer.clear_cache()
        result = writer.write_memory(
            ["conversation"], "hello", "hi",
            ["test"], {"type": "happy", "intensity": 0.8}, 0.7,
            metadata={"reinforcement_count": 1},
        )
        assert result.get("conversation") is False
        content = new_path.read_text(encoding="utf-8")
        assert "reinforcement_count': 2" in content

    def test_write_memory_reinforcement_preserves_double_quote(self, tmp_path):
        """Bumping a double-quoted reinforcement_count must keep the quote style."""
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        writer.write_memory(
            ["conversation"], "hello", "hi",
            ["test"], {"type": "happy", "intensity": 0.8}, 0.7,
            metadata={"reinforcement_count": 3},
        )
        f = list((tmp_path / "conversation").glob("*.md"))[0]
        content = f.read_text(encoding="utf-8")
        # force double-quote style on the decision canonical entry
        content = content.replace("reinforcement_count': 3", 'reinforcement_count": 3')
        f.write_text(content, encoding="utf-8")
        new_path = tmp_path / "conversation" / "1998-01-01.md"
        f.rename(new_path)
        writer.clear_cache()
        result = writer.write_memory(
            ["conversation"], "hello", "hi",
            ["test"], {"type": "happy", "intensity": 0.8}, 0.7,
            metadata={"reinforcement_count": 3},
        )
        assert result.get("conversation") is False
        bumped = new_path.read_text(encoding="utf-8")
        assert 'reinforcement_count": 4' in bumped
        assert "reinforcement_count': 4" not in bumped

    # ── Fix 1: memory links only emitted for existing graph notes ──

    def test_write_memory_links_filtered_to_existing_notes(self, tmp_path):
        """Broken [[wiki]] links must not be written for absent graph notes."""
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        (tmp_path / "graph").mkdir(parents=True, exist_ok=True)
        (tmp_path / "graph" / "learning.md").write_text("# learning", encoding="utf-8")
        writer.write_memory(
            ["conversation"], "hello", "hi",
            tags=["learning", "nonexistent_tag"],
            emotion={"type": "happy", "intensity": 0.8}, score=0.7,
            entity_names=["learning", "ghost_entity"],
        )
        f = list((tmp_path / "conversation").glob("*.md"))[0]
        content = f.read_text(encoding="utf-8")
        assert "[[learning]]" in content
        assert "[[nonexistent_tag]]" not in content
        assert "[[ghost_entity]]" not in content

    def test_write_memory_no_broken_links_without_graph_dir(self, tmp_path):
        """With no graph/ dir, the Memory Links section must be empty."""
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        writer.write_memory(
            ["conversation"], "hello", "hi",
            tags=["learning"], emotion={}, score=0.5,
            entity_names=["learning"],
        )
        f = list((tmp_path / "conversation").glob("*.md"))[0]
        content = f.read_text(encoding="utf-8")
        assert "[[learning]]" not in content
        assert "### 🔗 Memory Links" in content

    def test_write_memory_entity_links_filtered(self, tmp_path):
        """Related Entities must only link existing graph notes."""
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        (tmp_path / "graph").mkdir(parents=True, exist_ok=True)
        (tmp_path / "graph" / "openrouter.md").write_text("# OpenRouter", encoding="utf-8")
        writer.write_memory(
            ["conversation"], "hello", "hi",
            tags=[], emotion={}, score=0.5,
            entity_names=["OpenRouter", "OpenRouter", "missing_thing"],
        )
        f = list((tmp_path / "conversation").glob("*.md"))[0]
        content = f.read_text(encoding="utf-8")
        assert "[[openrouter]]" in content or "[[OpenRouter]]" in content
        assert "[[missing_thing]]" not in content

    def test_write_important_creates_file(self, tmp_path):
        from datetime import datetime

        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        result = writer.write_important("important note")
        assert result is True
        today = datetime.now().strftime("%Y-%m-%d") + ".md"
        assert (tmp_path / "important" / today).exists()

    def test_write_reflection_creates_file(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        result = writer.write_reflection("deep thought")
        assert result is True
        assert (tmp_path / "reflections" / "reflections.md").exists()

    def test_archive_creates_file(self, tmp_path):
        from datetime import datetime

        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        result = writer.archive("old data")
        assert result is True
        today = datetime.now().strftime("%Y-%m-%d") + ".md"
        assert (tmp_path / "archive" / today).exists()

    def test_clear_cache_works(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        writer.write("conversation", "hello", "hi", [], {}, 0.5)
        assert len(writer.hash_cache) > 0
        writer.clear_cache()
        assert len(writer.hash_cache) == 0

    def test_stats_contains_memory_keys(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        stats = writer.stats()
        assert "vault" in stats
        assert "cached_hashes" in stats
        assert "memory_writes" in stats

    def test_sync_without_graph_returns_empty(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        writer = ObsidianWriter(vault_path=str(tmp_path))
        stats = writer.sync()
        assert stats["written"] == 0

    def test_dump_identity_creates_file(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import IdentityFact, MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        state.identity.append(IdentityFact(fact="I am 25", category="age", timestamp="2026-07-17"))
        state.likes.append("coding")
        writer.dump(state, "2026-07-17")
        identity_file = tmp_path / "identity" / "user.md"
        assert identity_file.exists()
        content = identity_file.read_text(encoding="utf-8")
        assert "I am 25" in content

    def test_dump_preferences_creates_file(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        state.likes.append("coding")
        state.dislikes.append("bugs")
        writer.dump(state, "2026-07-17")
        pref_file = tmp_path / "preferences" / "preferences.md"
        assert pref_file.exists()
        content = pref_file.read_text(encoding="utf-8")
        assert "coding" in content
        assert "bugs" in content

    def test_dump_knowledge_creates_file(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import KnowledgeEntry, MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        state.knowledge.append(KnowledgeEntry(topic="Python", fact="a language", timestamp="2026-07-17"))
        writer.dump(state, "2026-07-17")
        know_file = tmp_path / "knowledge" / "knowledge.md"
        assert know_file.exists()
        content = know_file.read_text(encoding="utf-8")
        assert "Python" in content

    def test_dump_dreams_creates_file(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        state.dreams.append("travel to Japan")
        writer.dump(state, "2026-07-17")
        dream_file = tmp_path / "dreams" / "dreams.md"
        assert dream_file.exists()
        content = dream_file.read_text(encoding="utf-8")
        assert "travel to Japan" in content

    def test_dump_entities_creates_files(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        state.people.append({"name": "Alice", "confidence": 0.9, "last_seen": "2026-07-17"})
        state.places.append({"name": "Tokyo", "confidence": 0.8, "last_seen": "2026-07-17"})
        writer.dump(state, "2026-07-17")
        assert (tmp_path / "people" / "people.md").exists()
        assert (tmp_path / "places" / "places.md").exists()

    def test_dump_statistics_creates_file(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        state.entity_count = 10
        state.relation_count = 5
        state.interaction_count = 42
        writer.dump(state, "2026-07-17")
        stats_file = tmp_path / "statistics" / "stats.md"
        assert stats_file.exists()
        content = stats_file.read_text(encoding="utf-8")
        assert "total_entities: 10" in content
        assert "total_relations: 5" in content
        assert "total_conversations: 42" in content

    def test_dump_empty_state_does_not_create_empty_files(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        writer.dump(state, "2026-07-17")
        assert (tmp_path / "statistics" / "stats.md").exists()
        assert not (tmp_path / "people" / "people.md").exists()

    def test_dump_entity_with_multiple(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        state.people.append({"name": "Alice", "confidence": 0.9, "last_seen": "2026-07-17"})
        state.people.append({"name": "Bob", "confidence": 0.7, "last_seen": "2026-07-16"})
        writer.dump(state, "2026-07-17")
        content = (tmp_path / "people" / "people.md").read_text(encoding="utf-8")
        assert "Alice" in content
        assert "Bob" in content


class TestStatsBackfill:

    def _make_conversation(self, root, date_str, turns, filename=None):
        conv_dir = root / "conversation"
        conv_dir.mkdir(parents=True, exist_ok=True)
        lines = []
        for i, user_line in enumerate(turns):
            lines.append("---")
            lines.append("id: abc")
            lines.append(f"timestamp: {date_str}")
            lines.append("---")
            lines.append(f"## Turn {i}")
            lines.append("")
            lines.append("### 👤 User")
            lines.append(user_line)
            lines.append("")
            lines.append("### 🌸 Mai")
            lines.append("hi!")
            lines.append("")
        (conv_dir / (filename or f"{date_str}.md")).write_text(
            "\n".join(lines), encoding="utf-8")
        return conv_dir

    def test_first_met_derived_from_earliest_conversation(self, tmp_path):
        """Fix 2: stats first_met must come from the vault, not today."""
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import MemoryState
        self._make_conversation(tmp_path, "2026-07-15", ["hello"])
        self._make_conversation(tmp_path, "2026-07-20", ["hello again"])
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        writer.dump(state, "2026-08-06")
        content = (tmp_path / "statistics" / "stats.md").read_text(encoding="utf-8")
        assert "first_met: 2026-07-15" in content

    def test_total_conversations_uses_real_turns_not_counter(self, tmp_path):
        """Fix the false 674 total: count actual conversation turns."""
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import MemoryState
        self._make_conversation(tmp_path, "2026-07-15", ["turn one", "turn two"])
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        state.interaction_count = 674  # inflated boot counter
        state.entity_count = 10
        writer.dump(state, "2026-08-06")
        content = (tmp_path / "statistics" / "stats.md").read_text(encoding="utf-8")
        assert "total_conversations: 2" in content
        assert "total_messages: 4" in content

    def test_interaction_counter_fallback_when_vault_empty(self, tmp_path):
        """No conversation files -> fall back to interaction_count."""
        from knowledge.obsidian_writer import ObsidianWriter
        from memory.state import MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        state = MemoryState()
        state.interaction_count = 42
        writer.dump(state, "2026-07-17")
        content = (tmp_path / "statistics" / "stats.md").read_text(encoding="utf-8")
        assert "total_conversations: 42" in content


class TestGraphJunkGate:

    def test_unknown_low_confidence_entity_skipped(self):
        """Fix 3: unknown entities at fallback confidence 0.2 must be refused."""
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_manager import GraphManager

        class FakeExtractor:
            def extract_from_conversation(self, user_message, ai_response):
                return {"entities": [
                    {"name": "siad", "type": "unknown", "confidence": 0.2},
                    {"name": "Python", "type": "technology", "confidence": 0.95},
                ], "relations": []}

        graph = KnowledgeGraph()
        gm = GraphManager(graph=graph, extractor=FakeExtractor())
        summary = gm.process_conversation("siad Python", "ok")
        assert summary["junk_skipped"] == 1
        assert graph.get_entity("siad") is None
        assert graph.get_entity("python") is not None

    def test_capitalized_fallback_entity_kept(self):
        """Unknown entities at confidence 0.3 (capitalized) are still kept."""
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_manager import GraphManager

        class FakeExtractor:
            def extract_from_conversation(self, user_message, ai_response):
                return {"entities": [
                    {"name": "OpenRouter", "type": "unknown", "confidence": 0.3},
                ], "relations": []}

        graph = KnowledgeGraph()
        gm = GraphManager(graph=graph, extractor=FakeExtractor())
        summary = gm.process_conversation("OpenRouter", "ok")
        assert summary["junk_skipped"] == 0
        assert graph.get_entity("openrouter") is not None


class TestVaultJanitor:

    def _graph_with_junk(self):
        from knowledge.graph import KnowledgeGraph
        graph = KnowledgeGraph()
        graph.add_entity("siad", "unknown", {"confidence": 0.2})
        graph.add_entity("pormise", "unknown", {"confidence": 0.2})
        graph.add_entity("messing", "unknown", {"confidence": 0.2})
        graph.add_entity("Machine", "unknown", {"confidence": 0.3})
        graph.add_entity("python", "technology", {"confidence": 0.9})
        return graph

    def test_find_junk_entities(self, tmp_path):
        from knowledge.vault_janitor import VaultJanitor
        graph = self._graph_with_junk()
        janitor = VaultJanitor(graph=graph)
        junk = janitor.find_junk_entities()
        names = {e.name for e in junk}
        assert "siad" in names and "pormise" in names and "messing" in names
        assert "python" not in names

    def test_sweep_dry_run_does_not_remove(self, tmp_path):
        from knowledge.vault_janitor import VaultJanitor
        graph = self._graph_with_junk()
        janitor = VaultJanitor(graph=graph)
        result = janitor.sweep_entities(dry_run=True)
        assert result["removed"] >= 3
        assert graph.get_entity("siad") is not None

    def test_sweep_apply_removes_from_graph(self, tmp_path):
        from knowledge.vault_janitor import VaultJanitor
        graph = self._graph_with_junk()
        janitor = VaultJanitor(graph=graph)
        result = janitor.sweep_entities(dry_run=False)
        assert result["removed"] >= 3
        assert graph.get_entity("siad") is None
        assert graph.get_entity("python") is not None

    def test_sweep_note_files_removes_orphan_junk_notes(self, tmp_path):
        from knowledge.vault_janitor import VaultJanitor
        graph = self._graph_with_junk()
        graph_dir = tmp_path / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / "siad.md").write_text("# siad", encoding="utf-8")
        (graph_dir / "learning.md").write_text("# learning", encoding="utf-8")
        (graph_dir / "mem-abc.md").write_text("# mem", encoding="utf-8")
        janitor = VaultJanitor(graph=graph, vault_root=tmp_path)
        result = janitor.sweep_note_files(dry_run=False)
        assert "siad.md" in result["files"]
        assert "learning.md" not in result["files"]
        assert "mem-abc.md" not in result["files"]

    def test_sweep_entity_from_graph_deletes_via_exporter(self, tmp_path):
        """Removed entities leave orphan notes which the janitor can purge."""
        from knowledge.vault_janitor import VaultJanitor
        graph = self._graph_with_junk()
        graph_dir = tmp_path / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        for name in ("siad", "pormise", "messing"):
            (graph_dir / f"{name}.md").write_text(f"# {name}", encoding="utf-8")
        janitor = VaultJanitor(graph=graph, vault_root=tmp_path)
        janitor.sweep_entities(dry_run=False)
        result = janitor.sweep_note_files(dry_run=False)
        for name in ("siad", "pormise", "messing"):
            assert f"{name}.md" in result["files"]

    def test_uppercase_acronym_entities_kept(self, tmp_path):
        """Two-letter uppercase acronyms (AI, JS) are not junk."""
        from knowledge.vault_janitor import VaultJanitor
        assert VaultJanitor._is_junk_name("AI") is False
        assert VaultJanitor._is_junk_name("JS") is False
        assert VaultJanitor._is_junk_name("C") is True
        assert VaultJanitor._is_junk_name("go") is True

        from knowledge.graph import KnowledgeGraph
        graph = KnowledgeGraph()
        graph.add_entity("AI", "technology", {"confidence": 0.8})
        graph.add_entity("siad", "unknown", {"confidence": 0.2})
        janitor = VaultJanitor(graph=graph)
        names = {e.name for e in janitor.find_junk_entities()}
        assert "siad" in names
        assert "AI" not in names
        janitor.sweep_entities(dry_run=False)
        assert graph.get_entity("AI") is not None

    def test_sweep_note_files_keeps_living_acronym_note(self, tmp_path):
        """Note files for living entities are never removed as junk."""
        from knowledge.graph import KnowledgeGraph
        from knowledge.vault_janitor import VaultJanitor
        graph = KnowledgeGraph()
        graph.add_entity("AI", "technology", {"confidence": 0.8})
        graph_dir = tmp_path / "graph"
        graph_dir.mkdir(parents=True, exist_ok=True)
        (graph_dir / "ai.md").write_text("# AI", encoding="utf-8")
        janitor = VaultJanitor(graph=graph, vault_root=tmp_path)
        result = janitor.sweep_note_files(dry_run=False)
        assert "ai.md" not in result["files"]
        assert (graph_dir / "ai.md").exists()


class TestVaultPostProcessor:

    def test_process_no_vault(self):
        from knowledge.vault_compiler import VaultCompiler
        from knowledge.vault_post_processor import VaultPostProcessor
        writer = MagicMock()
        writer.vault_root = None
        pp = VaultPostProcessor(compiler=VaultCompiler(writer))
        pp.process("hello", "hi", [], {})
        writer.dump.assert_not_called()

    def test_process_calls_dump(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from knowledge.vault_compiler import VaultCompiler
        from knowledge.vault_post_processor import VaultPostProcessor
        writer = ObsidianWriter(vault_path=str(tmp_path))
        pp = VaultPostProcessor(compiler=VaultCompiler(writer))
        pp.process("I am a software engineer named Rida", "That's great!", ["greeting"], {"type": "happy", "intensity": 0.5})
        assert (tmp_path / "identity" / "user.md").exists()

    def test_populate_from_regex_identity(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from knowledge.vault_compiler import VaultCompiler
        from knowledge.vault_post_processor import VaultPostProcessor
        from memory.state import MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        pp = VaultPostProcessor(compiler=VaultCompiler(writer))
        state = MemoryState()
        pp._populate_from_regex(state, "I am a software engineer and my name is Rida", "", [], {})
        assert any("software engineer" in f.fact for f in state.identity)
        assert any("rida" in f.fact.lower() for f in state.identity)

    def test_populate_from_regex_preferences(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from knowledge.vault_compiler import VaultCompiler
        from knowledge.vault_post_processor import VaultPostProcessor
        from memory.state import MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        pp = VaultPostProcessor(compiler=VaultCompiler(writer))
        state = MemoryState()
        pp._populate_from_regex(state, "I like coding. I dislike meetings.", "", [], {})
        assert any("coding" in l.lower() for l in state.likes)
        assert any("meetings" in d.lower() for d in state.dislikes)

    def test_populate_from_regex_dreams(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from knowledge.vault_compiler import VaultCompiler
        from knowledge.vault_post_processor import VaultPostProcessor
        from memory.state import MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        pp = VaultPostProcessor(compiler=VaultCompiler(writer))
        state = MemoryState()
        pp._populate_from_regex(state, "I dream to travel to Japan!", "", [], {})
        assert any("japan" in d.lower() for d in state.dreams)

    def test_populate_from_llm_identity(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from knowledge.vault_compiler import VaultCompiler
        from knowledge.vault_post_processor import VaultPostProcessor
        from memory.state import MemoryState
        writer = ObsidianWriter(vault_path=str(tmp_path))
        pp = VaultPostProcessor(compiler=VaultCompiler(writer))
        state = MemoryState()
        pp._populate_from_llm(state, {
            "identity": [{"fact": "I am a programmer", "category": "work"}],
            "preferences": {"likes": ["Python"], "dislikes": ["Java"]},
            "dreams": ["build an AI"],
            "knowledge": [{"topic": "Python", "fact": "Python is a language"}],
        })
        assert any("programmer" in f.fact for f in state.identity)
        assert "Python" in state.likes
        assert "build an AI" in state.dreams
        assert any(k.topic == "Python" for k in state.knowledge)

    def test_process_with_graph_entities(self, tmp_path):
        from knowledge.graph import KnowledgeGraph
        from knowledge.obsidian_writer import ObsidianWriter
        from knowledge.vault_compiler import VaultCompiler
        from knowledge.vault_post_processor import VaultPostProcessor
        gm = KnowledgeGraph()
        gm.add_entity("Alice", entity_type="person", metadata={"confidence": 0.9})
        gm.add_entity("Tokyo", entity_type="place", metadata={"confidence": 0.8})
        writer = ObsidianWriter(graph_manager=gm, vault_path=str(tmp_path))
        pp = VaultPostProcessor(compiler=VaultCompiler(writer), graph_manager=gm)
        pp.process("hello", "hi there", [], {})
        people_file = tmp_path / "people" / "people.md"
        places_file = tmp_path / "places" / "places.md"
        assert people_file.exists()
        assert places_file.exists()
        people_content = people_file.read_text(encoding="utf-8")
        places_content = places_file.read_text(encoding="utf-8")
        assert "alice" in people_content.lower()
        assert "tokyo" in places_content.lower()

    def test_llm_extract_parses_json(self, tmp_path):
        from knowledge.obsidian_writer import ObsidianWriter
        from knowledge.vault_compiler import VaultCompiler
        from knowledge.vault_post_processor import VaultPostProcessor
        writer = ObsidianWriter(vault_path=str(tmp_path))
        llm = MagicMock()
        llm.generate.return_value = '{"identity": [{"fact": "I am a coder", "category": "work"}], "preferences": {"likes": ["Python"]}, "knowledge": [{"topic": "AI", "fact": "AI is cool"}]}'
        llm.is_available.return_value = True
        pp = VaultPostProcessor(compiler=VaultCompiler(writer), llm=llm)
        result = pp._llm_extract("I code in Python", "That's great")
        assert result is not None
        assert "identity" in result
        assert "preferences" in result


class TestObsidianReader:

    def test_load_memories_empty_vault(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        memories = reader.load_memories()
        assert memories == []

    def test_read_entity_nonexistent(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        assert reader.read_entity("nonexistent") is None

    def test_list_entities_empty(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        assert reader.list_entities() == []

    def test_get_all_returns_dict_with_keys(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        data = reader.get_all()
        assert "identity" in data
        assert "preferences" in data
        assert "relationship" in data
        assert "reflections" in data
        assert "statistics" in data

    def test_read_and_list_entity(self, tmp_path):
        from knowledge.graph import KnowledgeGraph
        from knowledge.obsidian_reader import ObsidianReader
        from knowledge.obsidian_writer import ObsidianWriter
        gm = KnowledgeGraph()
        gm.add_entity("TestEntity", entity_type="test")
        writer = ObsidianWriter(graph_manager=gm, vault_path=str(tmp_path))
        writer.sync()
        reader = ObsidianReader(vault_path=str(tmp_path))
        result = reader.read_entity("testentity")
        assert result is not None
        assert "testentity" in result["content"]
        entities = reader.list_entities()
        assert "testentity" in entities

    def test_clear_cache_reader(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        reader.cache["test"] = "value"
        reader.clear_cache()
        assert len(reader.cache) == 0

    def test_stats_reader(self, tmp_path):
        from knowledge.obsidian_reader import ObsidianReader
        reader = ObsidianReader(vault_path=str(tmp_path))
        stats = reader.stats()
        assert "vault" in stats
        assert "cached_files" in stats
        assert "tracked_hashes" in stats


class TestCognitiveGraph:

    def test_to_graph_data_includes_beliefs(self):
        from knowledge.cognitive_graph import CognitiveGraph
        cg = CognitiveGraph()
        be = MagicMock()
        be.all_beliefs.return_value = [
            MagicMock(topic="user", predicate="likes", object="pizza",
                      confidence=0.8, evidence_count=3),
            MagicMock(topic="user", predicate="works_at", object="Acme",
                      confidence=0.9, evidence_count=5),
        ]
        data = cg.to_graph_data(belief_engine=be)
        assert len(data["nodes"]) >= 2
        assert any("belief" in n["type"] for n in data["nodes"])

    def test_to_graph_data_empty_without_sources(self):
        from knowledge.cognitive_graph import CognitiveGraph
        cg = CognitiveGraph()
        data = cg.to_graph_data()
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_to_graph_data_includes_goals(self):
        from knowledge.cognitive_graph import CognitiveGraph
        cg = CognitiveGraph()
        gm = MagicMock()
        g1 = MagicMock(id="abc123", description="learn Python", priority="high",
                       status="active", context={"topic": "python"})
        gm.list.return_value = [g1]
        data = cg.to_graph_data(goal_manager=gm)
        assert len(data["nodes"]) >= 1

    def test_to_graph_data_includes_emotions(self):
        from knowledge.cognitive_graph import CognitiveGraph
        cg = CognitiveGraph()
        brain = MagicMock()
        emotion_data = {"type": "happy", "intensity": 0.8}
        brain.state.emotion.model_dump.return_value = emotion_data
        data = cg.to_graph_data(brain=brain)
        assert len(data["nodes"]) >= 1
        assert any("emotion" in n["type"] for n in data["nodes"])

    def test_to_graph_data_handles_none_sources(self):
        from knowledge.cognitive_graph import CognitiveGraph
        cg = CognitiveGraph()
        data = cg.to_graph_data(None, None, None)
        assert data["nodes"] == []

    def test_stats_returns_counts(self):
        from knowledge.cognitive_graph import CognitiveGraph
        cg = CognitiveGraph()
        stats = cg.stats()
        assert "total_nodes" in stats
        assert "cognitive_nodes" in stats
        assert "entity_nodes" in stats
        assert "edges" in stats


class TestGraphReflection:

    def test_identify_clusters_single(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_reflection import GraphReflection
        kg = KnowledgeGraph()
        kg.add_entity("A", entity_type="test")
        kg.add_entity("B", entity_type="test")
        kg.add_relation("A", "connects", "B")
        gr = GraphReflection(kg)
        clusters = gr.identify_clusters()
        assert len(clusters) == 1
        assert "a" in clusters[0]
        assert "b" in clusters[0]

    def test_identify_clusters_multiple(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_reflection import GraphReflection
        kg = KnowledgeGraph()
        kg.add_entity("A", entity_type="test")
        kg.add_entity("B", entity_type="test")
        kg.add_relation("A", "connects", "B")
        kg.add_entity("C", entity_type="test")
        kg.add_entity("D", entity_type="test")
        kg.add_relation("C", "connects", "D")
        gr = GraphReflection(kg)
        clusters = gr.identify_clusters()
        assert len(clusters) == 2

    def test_identify_clusters_empty(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_reflection import GraphReflection
        gr = GraphReflection(KnowledgeGraph())
        assert gr.identify_clusters() == []

    def test_isolated_entities(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_reflection import GraphReflection
        kg = KnowledgeGraph()
        kg.add_entity("Connected", entity_type="test")
        kg.add_entity("Alone", entity_type="test")
        kg.add_relation("Connected", "self", "Connected")
        gr = GraphReflection(kg)
        isolated = gr.isolated_entities()
        names = [e.name for e in isolated]
        assert "alone" in names

    def test_suggest_new_relations_empty_when_one_cluster(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_reflection import GraphReflection
        kg = KnowledgeGraph()
        kg.add_entity("A", entity_type="test")
        gr = GraphReflection(kg)
        assert gr.suggest_new_relations() == []

    def test_suggest_new_relations_returns_suggestions(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_reflection import GraphReflection
        kg = KnowledgeGraph()
        kg.add_entity("A", entity_type="test")
        kg.add_entity("B", entity_type="test")
        kg.add_relation("A", "connects", "B")
        kg.add_entity("C", entity_type="test")
        kg.add_entity("D", entity_type="test")
        kg.add_relation("C", "connects", "D")
        gr = GraphReflection(kg)
        suggestions = gr.suggest_new_relations(max_suggestions=2)
        assert len(suggestions) >= 1

    def test_summary_contains_keys(self):
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_reflection import GraphReflection
        kg = KnowledgeGraph()
        kg.add_entity("A", entity_type="test")
        gr = GraphReflection(kg)
        s = gr.summary()
        assert "total_entities" in s
        assert "total_relations" in s
        assert "clusters" in s
        assert "isolated_count" in s
        assert "suggested_new_relations" in s

    def test_recent_activity(self):

        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_reflection import GraphReflection
        kg = KnowledgeGraph()
        kg.add_entity("Old", entity_type="test")  # created now
        gr = GraphReflection(kg)
        activity = gr.recent_activity(minutes=60)
        assert activity["recent_entities"] >= 1


class TestRelationshipUpdaterGuard:

    def test_empty_file_resets_to_baseline(self, tmp_path):
        """Zeroed-interactions file must not pin Trust=0. Fronts the boot-time
        blank relationship.md drift (Fix 2 relationship metrics)."""
        from memory.relationship_updater import RelationshipUpdater
        path = tmp_path / "relationship.md"
        path.write_text(
            "Closeness: 0.00\nTrust: 0.00\nInteractions: 0\n", encoding="utf-8")
        updater = RelationshipUpdater(str(path))
        assert updater.state.closeness == 0.5
        assert updater.state.trust == 0.5

    def test_real_values_are_preserved(self, tmp_path):
        """Non-degenerate files load as-is (no baseline reset)."""
        from memory.relationship_updater import RelationshipUpdater
        path = tmp_path / "relationship.md"
        path.write_text(
            "Closeness: 0.80\nTrust: 0.60\nInteractions: 42\n", encoding="utf-8")
        updater = RelationshipUpdater(str(path))
        assert updater.state.closeness == 0.8
        assert updater.state.trust == 0.6
        assert updater.state.interactions == 42

    def test_fresh_state_uses_defaults(self, tmp_path):
        from memory.relationship_updater import RelationshipUpdater
        path = tmp_path / "relationship.md"
        if path.exists():
            path.unlink()
        updater = RelationshipUpdater(str(path))
        assert updater.state.closeness == 0.5
        assert updater.state.trust == 0.5


class TestGraphExporterLongNames:
    """A memory dump used as an entity name must not abort the graph export.

    Live failure (2026-10-03 boot): an entity named after an entire pasted
    memory (~1,900 chars) produced a filename past Windows MAX_PATH, so
    write_entity raised, and because sync() called it unguarded the exception
    escaped to VaultCompiler.compile_graph -> {"written": 0}. Every other
    entity note was silently skipped.
    """

    LONG = ("theres_more_when_i_was_7_years_old " * 60).strip()

    def _exporter(self, tmp_path, names):
        from knowledge.graph_exporter import GraphExporter

        class _Ent:
            def __init__(self, name):
                self.name = name
                self.type = "person"
                self.created_at = 1000.0
                self.metadata = {}

        class _Graph:
            def all_entities(self):
                return [_Ent(n) for n in names]

            def get_relations_for(self, name):
                return []

        return GraphExporter(graph_manager=_Graph(), vault_path=str(tmp_path / "vault"))

    def test_long_name_filename_stays_within_path_limits(self, tmp_path):
        exp = self._exporter(tmp_path, [self.LONG])
        stem = exp._sanitize(self.LONG)
        assert len(stem) <= 96
        assert (exp.entity_dir / f"{stem}.md").parent == exp.entity_dir

    def test_sync_writes_the_note_instead_of_raising(self, tmp_path):
        exp = self._exporter(tmp_path, [self.LONG])
        stats = exp.sync()
        assert stats["written"] == 1
        assert stats["failed"] == 0
        assert len(list(exp.entity_dir.glob("*.md"))) == 1

    def test_one_bad_entity_does_not_zero_out_the_export(self, tmp_path):
        exp = self._exporter(tmp_path, ["murtaza", self.LONG, "karachi"])
        original = exp.write_entity

        def exploding(entity):
            if len(entity.name) > 500:
                raise OSError(2, "No such file or directory")
            return original(entity)

        exp.write_entity = exploding
        stats = exp.sync()
        assert stats["written"] == 2
        assert stats["failed"] == 1
        assert stats["total"] == 3

    def test_long_names_sharing_a_prefix_do_not_collide(self, tmp_path):
        exp = self._exporter(tmp_path, [])
        assert exp._sanitize(self.LONG + "alpha") != exp._sanitize(self.LONG + "beta")
        assert exp._sanitize("Murtaza") == "murtaza"

