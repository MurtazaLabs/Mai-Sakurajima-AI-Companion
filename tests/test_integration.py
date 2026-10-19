import pathlib
import shutil
import tempfile
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _vector_store_patch():
    with patch("memory.memory.VectorStore") as mock:
        mock.return_value.add.return_value = "mock_vector_id"
        yield mock


@pytest.fixture
def temp_state():
    tmp = pathlib.Path(tempfile.mkdtemp())
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.integration
class TestKnowledgePipelineIntegration:

    def _make_state(self, state_dir=None):
        from core.state.shared_state import SharedState
        if state_dir is None:
            state_dir = pathlib.Path(tempfile.mkdtemp())
        return SharedState(persistence_dir=state_dir)

    def _make_memory(self):
        from core.event_bus import EventBus
        from memory.manager import MemoryManager
        from memory.memory import Memory
        from memory.pipeline import MemoryPipeline
        event_bus = EventBus()
        mem = Memory()
        pipeline = MemoryPipeline(event_bus=event_bus)
        manager = MemoryManager(
            memory=mem,
            pipeline=pipeline,
            event_bus=event_bus,
        )
        return manager, event_bus

    def test_think_populates_graph_retriever_and_beliefs(self, temp_state):
        from agency.agent import Agent
        from agency.registry import ToolRegistry
        from core.brain import Brain
        from core.event_bus import EventBus
        from knowledge.attention import AttentionSystem
        from knowledge.belief_engine import BeliefEngine
        from knowledge.consolidation import ConsolidationEngine
        from knowledge.extractor import EntityExtractor
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_manager import GraphManager
        from knowledge.retriever import AdvancedRetriever

        # --- Wire real knowledge subsystems ---
        event_bus = EventBus()
        belief_engine = BeliefEngine(event_bus=event_bus)
        knowledge_graph = KnowledgeGraph()
        attention_system = AttentionSystem(
            knowledge_graph=knowledge_graph,
            belief_engine=belief_engine,
        )

        extractor = EntityExtractor()
        graph_manager = GraphManager(
            graph=knowledge_graph,
            extractor=extractor,
            consolidation=ConsolidationEngine(),
            event_bus=event_bus,
        )

        retriever = AdvancedRetriever(
            vector_store=None,
            knowledge_graph=knowledge_graph,
            belief_engine=belief_engine,
            attention=attention_system,
            event_bus=event_bus,
        )

        tool_registry = ToolRegistry(event_bus=event_bus)
        agent = Agent(
            registry=tool_registry,
            event_bus=event_bus,
            max_steps=3,
        )

        # --- Wire memory ---
        memory_manager, _ = self._make_memory()
        memory_manager.configure_pipeline(graph=graph_manager)

        # --- Wire Brain ---
        state = self._make_state(temp_state)
        llm = MagicMock()
        llm.generate_with_tools.return_value = (
            "That's awesome! Python and ChromaDB are a great combo."
        )
        llm.is_available.return_value = True

        brain = Brain(
            llm=llm,
            memory=memory_manager,
            executor=MagicMock(),
            state=state,
            event_bus=event_bus,
            tool_registry=tool_registry,
            agent=agent,
            retriever=retriever,
            graph_manager=graph_manager,
        )

        # --- Act: run a conversation ---
        response = brain.think("I use Python and ChromaDB for my projects")
        assert response is not None
        assert len(response) > 0

        # --- Assert graph populated ---
        entities = knowledge_graph.all_entities()
        entity_names = [e.name for e in entities]
        assert "python" in entity_names, (
            f"Expected 'python' in graph entities, got {entity_names}"
        )

        relations = knowledge_graph.all_relations()
        assert len(relations) > 0, "Expected at least 1 relation in graph"

        # --- Assert retriever returns graph results ---
        results = retriever.retrieve("Python ChromaDB project", top_k=10)
        graph_results = [r for r in results if r.get("source") == "knowledge_graph"]
        assert len(graph_results) > 0, (
            f"Expected graph results from retriever, got {len(graph_results)} "
            f"(total results: {len(results)})"
        )

        # --- Assert belief engine populated (via graph sync) ---
        belief_engine.update_from_graph(graph_manager)
        all_beliefs = belief_engine.all_beliefs()
        assert len(all_beliefs) > 0, (
            f"Expected beliefs to be populated, got {len(all_beliefs)}"
        )

        # --- Assert graph stats are reasonable ---
        stats = knowledge_graph.stats()
        assert stats["nodes"] >= 2, f"Expected >= 2 nodes, got {stats['nodes']}"
        assert stats["edges"] >= 1, f"Expected >= 1 edges, got {stats['edges']}"

    def test_graph_manager_process_conversation_updates_everything(self):
        from core.event_bus import EventBus
        from knowledge.attention import AttentionSystem
        from knowledge.belief_engine import BeliefEngine
        from knowledge.consolidation import ConsolidationEngine
        from knowledge.extractor import EntityExtractor
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_manager import GraphManager
        from knowledge.retriever import AdvancedRetriever

        event_bus = EventBus()
        belief_engine = BeliefEngine(event_bus=event_bus)
        knowledge_graph = KnowledgeGraph()
        attention_system = AttentionSystem(
            knowledge_graph=knowledge_graph,
            belief_engine=belief_engine,
        )

        graph_manager = GraphManager(
            graph=knowledge_graph,
            extractor=EntityExtractor(),
            consolidation=ConsolidationEngine(),
            event_bus=event_bus,
        )

        retriever = AdvancedRetriever(
            vector_store=None,
            knowledge_graph=knowledge_graph,
            belief_engine=belief_engine,
            attention=attention_system,
            event_bus=event_bus,
        )

        # Process multiple conversations directly
        graph_manager.process_conversation(
            "I built Mai with Python", "Nice choice!"
        )
        graph_manager.process_conversation(
            "Mai uses ChromaDB for memory", "Yes it does"
        )
        graph_manager.process_conversation(
            "I switched Mai to Gemma", "Gemma is good"
        )

        # Verify graph
        stats = knowledge_graph.stats()
        assert stats["nodes"] >= 3
        assert stats["edges"] >= 3

        # Verify retriever sees graph
        results = retriever.retrieve("what does Mai use", top_k=10)
        graph_sources = {r["source"] for r in results}
        assert "knowledge_graph" in graph_sources

        # Verify belief engine populated via graph sync
        belief_engine.update_from_graph(graph_manager)
        all_beliefs = belief_engine.all_beliefs()
        assert len(all_beliefs) > 0

        # Verify beliefs reference known entities
        entity_names = {e.name for e in knowledge_graph.all_entities()}
        for b in all_beliefs:
            assert b.topic in entity_names or b.topic == "user", (
                f"Belief topic '{b.topic}' not in entities {entity_names}"
            )

    def test_empty_conversation_does_not_crash(self, temp_state):
        from core.brain import Brain
        from core.event_bus import EventBus
        from knowledge.attention import AttentionSystem
        from knowledge.belief_engine import BeliefEngine
        from knowledge.consolidation import ConsolidationEngine
        from knowledge.extractor import EntityExtractor
        from knowledge.graph import KnowledgeGraph
        from knowledge.graph_manager import GraphManager
        from knowledge.retriever import AdvancedRetriever

        event_bus = EventBus()
        belief_engine = BeliefEngine()
        kg = KnowledgeGraph()
        gm = GraphManager(
            graph=kg,
            extractor=EntityExtractor(),
            consolidation=ConsolidationEngine(),
        )
        retriever = AdvancedRetriever(
            vector_store=None,
            knowledge_graph=kg,
            belief_engine=belief_engine,
            attention=AttentionSystem(knowledge_graph=kg, belief_engine=belief_engine),
        )

        memory_manager, _ = self._make_memory()

        state = self._make_state(temp_state)
        llm = MagicMock()
        llm.generate_with_tools.return_value = "Hello!"
        llm.is_available.return_value = True

        brain = Brain(
            llm=llm,
            memory=memory_manager,
            executor=MagicMock(),
            state=state,
            event_bus=event_bus,
            retriever=retriever,
            graph_manager=gm,
        )

        response = brain.think("")
        assert response is not None
        assert kg.stats()["nodes"] == 0
        assert len(belief_engine.all_beliefs()) == 0
