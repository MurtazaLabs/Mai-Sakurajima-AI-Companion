import logging

import app.config_loader as cfg
from app.metadata import tag_service
from knowledge.retriever import AdvancedRetriever
from memory.hierarchy import MemoryHierarchy
from memory.manager import MemoryManager
from memory.memory import Memory
from memory.pipeline import MemoryPipeline
from memory.vector_store import VectorStore

logger = logging.getLogger("Mai")


def build(app):
    logger.info("    Building MemoryHierarchy...")
    app.memory_hierarchy = MemoryHierarchy(brain_graph=app.brain_graph, event_bus=app.event_bus)
    tag_service(app, "memory_hierarchy", "MemoryHierarchy", "Memory")
    logger.info("    ✓ MemoryHierarchy")
    app.health_registry.register("memory_hierarchy", component=app.memory_hierarchy)
    app.health_registry.heartbeat("memory_hierarchy")

    logger.info("    Building Memory pipeline...")
    app.raw_memory = Memory()
    tag_service(app, "raw_memory", "Memory", "Memory")
    app.memory_pipeline = MemoryPipeline(
        event_bus=app.event_bus,
        memory_hierarchy=app.memory_hierarchy,
        write_journal=app.write_journal,
    )
    tag_service(app, "memory_pipeline", "MemoryPipeline", "Memory")
    app.memory = MemoryManager.from_memory(
        memory=app.raw_memory,
        pipeline=app.memory_pipeline,
        event_bus=app.event_bus,
    )
    tag_service(app, "memory", "MemoryManager", "Memory")
    app.memory.intel.graph.brain_graph = app.brain_graph
    logger.info("    ✓ Memory pipeline")

    logger.info("    Building VectorStore...")
    try:
        app.vector_store = VectorStore()
        tag_service(app, "vector_store", "VectorStore", "Memory")
        app.memory.configure_pipeline(vector_store=app.vector_store)
        logger.info("    ✓ VectorStore")
    except Exception as e:
        logger.warning("    Vector store load failed: %s", e)
        app.vector_store = None

    app.health_registry.register("memory")
    app.health_registry.register("vector_store", component=app.vector_store)
    app.health_registry.heartbeat("memory")
    app.health_registry.heartbeat("vector_store")

    # ── Migrate any legacy (pre-Phase-3) vault folders to the canonical
    #    structure BEFORE replaying, so no historical data is lost. ──
    try:
        from knowledge.vault_migrator import migrate_vault
        migrate_summary = migrate_vault(cfg.OBSIDIAN_VAULT)
        logger.info("    Vault migration: %s", migrate_summary)
    except Exception as e:
        logger.warning("    Vault migration skipped: %s", e)

    # ── Phase 1 invariant: no legacy/duplicate vault folders may survive. ──
    try:
        from knowledge.vault_schema import assert_no_legacy_folders, scan_unknown_folders
        assert_no_legacy_folders(cfg.OBSIDIAN_VAULT)
        unknown = scan_unknown_folders(cfg.OBSIDIAN_VAULT)
        if unknown:
            logger.warning("    Vault: non-canonical folders present (review): %s", unknown)
    except FileExistsError as e:
        logger.error("    Vault schema invariant FAILED: %s", e)
        raise
    except Exception as e:
        logger.warning("    Vault schema check skipped: %s", e)

    # ── Replay persisted vault into in-memory stores so history survives
    #    restarts (MemoryHierarchy + VectorStore start empty on boot). ──
    try:
        from memory.vault_loader import load_vault_into_memory, verify_consistency
        load_vault_into_memory(
            reader=app.raw_memory.reader if hasattr(app.raw_memory, "reader") else None,
            memory_manager=app.memory,
            vector_store=app.vector_store,
            memory_hierarchy=app.memory_hierarchy,
            knowledge_graph=app.knowledge_graph,
        )
    except Exception as e:
        logger.warning("    Vault replay skipped: %s", e)

    # ── Advisory consistency check — vault vs in-memory stores. ──
    try:
        verify_consistency(
            reader=app.raw_memory.reader if hasattr(app.raw_memory, "reader") else None,
            vector_store=app.vector_store,
            knowledge_graph=app.knowledge_graph,
            memory_hierarchy=app.memory_hierarchy,
        )
    except Exception as e:
        logger.warning("    Vault consistency check skipped: %s", e)

    logger.info("    Building AdvancedRetriever...")
    app.retriever = AdvancedRetriever(
        vector_store=app.vector_store,
        knowledge_graph=app.knowledge_graph,
        belief_engine=app.belief_engine,
        attention=app.attention_system,
        event_bus=app.event_bus,
        graph_reasoning=None,  # wired in cognition builder
    )
    tag_service(app, "retriever", "AdvancedRetriever", "Memory")
    logger.info("    ✓ AdvancedRetriever")
    app.health_registry.register("retriever", component=app.retriever)
    app.health_registry.heartbeat("retriever")

    assert app.memory_hierarchy is not None
    assert app.raw_memory is not None
    assert app.memory_pipeline is not None
    assert app.memory is not None
    assert app.retriever is not None
