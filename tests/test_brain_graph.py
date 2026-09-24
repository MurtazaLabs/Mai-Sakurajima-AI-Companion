"""Integration tests for BRAIN_GRAPH_PLAN — wiring graph pipeline into conversation flow."""

from unittest.mock import MagicMock, patch

import pytest


class TestMemoryPipelineGraphWiring:

    def _make_pipeline(self, **kwargs):
        from memory.pipeline import MemoryPipeline
        pipeline = MemoryPipeline(**kwargs)
        pipeline.tagger = MagicMock()
        pipeline.tagger.extract_tags.return_value = ["test"]
        pipeline.emotion_analyzer = MagicMock()
        pipeline.emotion_analyzer.analyze.return_value = {"type": "neutral", "intensity": 0.5}
        pipeline.vector_store = MagicMock()
        pipeline.vector_store.add.return_value = "vec_id"
        pipeline.event_bus = MagicMock()
        return pipeline

    def test_pipeline_calls_process_conversation_when_graph_set(self):
        graph = MagicMock()
        graph.process_conversation.return_value = {
            "entities_added": 2, "relations_added": 1, "duplicates_skipped": 0,
        }
        pipeline = self._make_pipeline(graph=graph)
        pipeline.vector_store.add.return_value = "vec_id"

        node = pipeline.store("hello world", "hi there")
        assert node is not None
        graph.process_conversation.assert_called_once_with("hello world", "hi there")

    def test_pipeline_skips_graph_when_not_set(self):
        pipeline = self._make_pipeline()
        pipeline.vector_store.add.return_value = "vec_id"

        node = pipeline.store("Hello world", "hi")
        assert node is not None

    def test_pipeline_graph_error_does_not_crash(self):
        graph = MagicMock()
        graph.process_conversation.side_effect = RuntimeError("graph crash")
        pipeline = self._make_pipeline(graph=graph)
        pipeline.vector_store.add.return_value = "vec_id"

        node = pipeline.store("Hello world", "hi")
        assert node is not None


class TestMemoryPipelineJournalEntityLinks:

    def test_journal_graph_batch_adds_entity_links(self):
        """Journaled knowledge_graph entries must enrich vault notes with
        entity links, matching the synchronous path (M-5)."""
        from types import SimpleNamespace
        from core.write_journal import WriteJournal
        from memory.pipeline import MemoryPipeline

        graph = MagicMock()
        graph.process_conversation.return_value = {"entities_added": 1}
        entity = SimpleNamespace(name="pipeline_entity")
        graph.graph.all_entities.side_effect = [[], [entity]]

        writer = MagicMock()
        obsidian_writer = MagicMock()
        obsidian_writer._memory_writer = writer

        wj = WriteJournal()
        pipeline = MemoryPipeline(graph=graph, obsidian_writer=obsidian_writer,
                                  write_journal=wj)
        pipeline.tagger = MagicMock()
        pipeline.tagger.extract_tags.return_value = ["test"]
        pipeline.emotion_analyzer = MagicMock()
        pipeline.emotion_analyzer.analyze.return_value = {"type": "neutral", "intensity": 0.5}
        pipeline.vector_store = MagicMock()
        pipeline.vector_store.add.return_value = "vec_id"
        pipeline.event_bus = MagicMock()

        node = pipeline.store("hello pipeline_entity", "hi there")
        assert node is not None
        wj.drain()

        graph.process_conversation.assert_called_once_with(
            "hello pipeline_entity", "hi there")
        writer.add_entity_links.assert_called_once_with(
            folder="conversation",
            user="hello pipeline_entity",
            ai="hi there",
            entity_names=["pipeline_entity"],
        )


class TestPostThinkHooksGraphCall:

    def test_post_think_calls_graph_manager(self):
        from core.post_think_hooks import PostThinkHooks
        graph = MagicMock()
        graph.process_conversation.return_value = {
            "entities_added": 3, "relations_added": 1, "duplicates_skipped": 0,
        }
        event_bus = MagicMock()

        hooks = PostThinkHooks(graph_manager=graph)
        hooks.run(
            user_input="I love Python",
            response="Python is great!",
            thought_journal=MagicMock(),
            memory=MagicMock(),
            event_bus=event_bus,
        )
        hooks.shutdown(timeout=2.0)

        graph.process_conversation.assert_called_once_with(
            "I love Python", "Python is great!"
        )

    def test_post_think_publishes_graph_event(self):
        from core.post_think_hooks import PostThinkHooks
        graph = MagicMock()
        graph.process_conversation.return_value = {
            "entities_added": 2, "relations_added": 1, "duplicates_skipped": 0,
        }
        event_bus = MagicMock()

        hooks = PostThinkHooks(graph_manager=graph)
        hooks.run(
            user_input="I like anime",
            response="What's your favorite anime?",
            thought_journal=MagicMock(),
            memory=MagicMock(),
            event_bus=event_bus,
        )
        hooks.shutdown(timeout=2.0)

        events = [call[0][0].payload for call in event_bus.publish_message.call_args_list
                  if call[0][0].type == "data.graph.updated"]
        assert len(events) >= 1
        assert events[0]["entities_added"] == 2

    def test_post_think_skips_graph_when_no_entities(self):
        from core.post_think_hooks import PostThinkHooks
        graph = MagicMock()
        graph.process_conversation.return_value = {
            "entities_added": 0, "relations_added": 0, "duplicates_skipped": 0,
        }
        event_bus = MagicMock()

        hooks = PostThinkHooks(graph_manager=graph)
        hooks.run(
            user_input="ok",
            response="Alright!",
            thought_journal=MagicMock(),
            memory=MagicMock(),
            event_bus=event_bus,
        )
        hooks.shutdown(timeout=2.0)

        # Should not publish event when no entities added
        graph_events = [call for call in event_bus.publish_message.call_args_list
                        if call[0][0].type == "data.graph.updated"]
        assert len(graph_events) == 0

    def test_post_think_export_graph_string_vault_root(self):
        from pathlib import Path
        from core.post_think_hooks import PostThinkHooks
        graph = MagicMock()
        graph.process_conversation.return_value = {
            "entities_added": 2, "relations_added": 1, "duplicates_skipped": 0,
        }
        obsidian_writer = MagicMock()
        hooks = PostThinkHooks(
            graph_manager=graph,
            obsidian_writer=obsidian_writer,
            vault_root="E:/MaiMemory",
        )
        for _ in range(3):
            hooks.run(
                user_input="trip to Shibuya",
                response="Shibuya is in Tokyo",
                thought_journal=MagicMock(),
                memory=MagicMock(),
                event_bus=MagicMock(),
            )
        hooks.shutdown(timeout=2.0)
        assert obsidian_writer.export_graph.call_count == 1
        graph_dir = obsidian_writer.export_graph.call_args[0][0]
        assert isinstance(graph_dir, Path)
        assert graph_dir == Path("E:/MaiMemory") / "graph"

    def test_post_think_no_graph_manager(self):
        from core.post_think_hooks import PostThinkHooks
        hooks = PostThinkHooks()
        hooks.run(
            user_input="hello",
            response="hi",
            thought_journal=MagicMock(),
            memory=MagicMock(),
            event_bus=MagicMock(),
        )
        hooks.shutdown(timeout=1.0)
        # No crash


class TestGraphManagerIntegration:

    def test_graph_manager_process_conversation_extracts_entities(self):
        from knowledge.graph_manager import GraphManager
        from knowledge.graph import KnowledgeGraph
        from knowledge.extractor import EntityExtractor
        from knowledge.consolidation import ConsolidationEngine

        graph = KnowledgeGraph()
        mgr = GraphManager(
            graph=graph,
            extractor=EntityExtractor(),
            consolidation=ConsolidationEngine(),
        )

        summary = mgr.process_conversation(
            "I love Python and building AI with Gemma",
            "That's cool! Python is great for ML.",
        )

        assert summary["entities_added"] >= 1

    def test_graph_stats_after_conversation(self):
        from knowledge.graph_manager import GraphManager
        from knowledge.graph import KnowledgeGraph
        from knowledge.extractor import EntityExtractor
        from knowledge.consolidation import ConsolidationEngine

        graph = KnowledgeGraph()
        mgr = GraphManager(
            graph=graph,
            extractor=EntityExtractor(),
            consolidation=ConsolidationEngine(),
        )

        mgr.process_conversation(
            "I built Mai with Gemma and ChromaDB",
            "That's a great tech stack!",
        )

        stats = mgr.graph.stats()
        assert stats["nodes"] > 0

    def test_empty_conversation_does_not_crash(self):
        from knowledge.graph_manager import GraphManager
        from knowledge.graph import KnowledgeGraph

        mgr = GraphManager(graph=KnowledgeGraph())
        summary = mgr.process_conversation("", "")
        assert summary["entities_added"] == 0
        assert summary["relations_added"] == 0
