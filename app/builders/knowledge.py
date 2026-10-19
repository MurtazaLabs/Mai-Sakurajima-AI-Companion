import logging

import app.config_loader as cfg
from app.metadata import tag_service
from knowledge.attention import AttentionSystem
from knowledge.belief_engine import BeliefEngine
from knowledge.brain_graph import BrainGraph
from knowledge.consolidation import ConsolidationEngine
from knowledge.extractor import EntityExtractor
from knowledge.graph import KnowledgeGraph
from knowledge.graph_manager import GraphManager
from knowledge.obsidian_writer import ObsidianWriter
from knowledge.vault_compiler import VaultCompiler

logger = logging.getLogger("Mai")


def build(app):
    logger.info("    Building KnowledgeGraph...")
    app.knowledge_graph = KnowledgeGraph()
    tag_service(app, "knowledge_graph", "KnowledgeGraph", "Knowledge")
    logger.info("    ✓ KnowledgeGraph")

    logger.info("    Building BrainGraph...")
    app.brain_graph = BrainGraph(graph=app.knowledge_graph, event_bus=app.event_bus)
    tag_service(app, "brain_graph", "BrainGraph", "Knowledge")
    logger.info("    ✓ BrainGraph")

    logger.info("    Building BeliefEngine...")
    app.belief_engine = BeliefEngine(event_bus=app.event_bus, brain_graph=app.brain_graph)
    tag_service(app, "belief_engine", "BeliefEngine", "Knowledge")
    logger.info("    ✓ BeliefEngine")

    # Wire single source of truth — BrainGraph reads belief data from BeliefEngine
    app.brain_graph.belief_engine = app.belief_engine

    logger.info("    Building AttentionSystem...")
    app.attention_system = AttentionSystem(
        knowledge_graph=app.knowledge_graph,
        belief_engine=app.belief_engine,
    )
    tag_service(app, "attention_system", "AttentionSystem", "Knowledge")
    logger.info("    ✓ AttentionSystem")

    # Build vault/persistence layer here so it's available before Agency phase
    logger.info("    Building GraphManager...")
    extractor = EntityExtractor(llm=app.llm if cfg.EXTRACTOR_USE_LLM else None)
    consolidation = ConsolidationEngine()
    app.graph_manager = GraphManager(
        graph=app.knowledge_graph,
        extractor=extractor,
        consolidation=consolidation,
        event_bus=app.event_bus,
    )
    tag_service(app, "graph_manager", "GraphManager", "Knowledge")
    logger.info("    ✓ GraphManager")

    logger.info("    Building ObsidianWriter...")
    app.obsidian_writer = ObsidianWriter(graph_manager=app.graph_manager)
    tag_service(app, "obsidian_writer", "ObsidianWriter", "Knowledge")
    logger.info("    ✓ ObsidianWriter")

    app.vault_root = app.obsidian_writer.vault_root

    logger.info("    Building VaultCompiler...")
    app.vault_compiler = VaultCompiler(app.obsidian_writer)
    tag_service(app, "vault_compiler", "VaultCompiler", "Knowledge")
    logger.info("    ✓ VaultCompiler")

    app.health_registry.register("belief_engine", component=app.belief_engine)
    app.health_registry.register("knowledge_graph", component=app.knowledge_graph)
    app.health_registry.register("brain_graph", component=app.brain_graph)
    app.health_registry.register("graph_manager", component=app.graph_manager)
    app.health_registry.heartbeat("belief_engine")
    app.health_registry.heartbeat("knowledge_graph")
    app.health_registry.heartbeat("brain_graph")
    app.health_registry.heartbeat("graph_manager")

    assert app.knowledge_graph is not None
    assert app.brain_graph is not None
    assert app.belief_engine is not None
    assert app.attention_system is not None
    assert app.graph_manager is not None
    assert app.obsidian_writer is not None
    assert app.vault_compiler is not None
