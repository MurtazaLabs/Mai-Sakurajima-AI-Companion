import logging
import os
import time
import threading
from pathlib import Path

import app.config_loader as cfg
from app.metadata import tag_service
from core.os_kernel import AIOSKernel
from core.plugin_system import HookRegistry, PluginLoader
from core.wake_generator import WakeGenerator
from plugins.lifecycle import create_plugin_lifecycle_manager
from knowledge.chunker import TextChunker
from knowledge.document_store import DocumentStore
from knowledge.indexer import Indexer
from knowledge.builder import KnowledgeBaseBuilder
from knowledge.watcher import DirectoryWatcher

logger = logging.getLogger("Mai")


def build(app):
    logger.info("    Building AIOSKernel...")
    # Create WakeGenerator for greeting-first mode
    wake_generator = WakeGenerator(
        identity={"name": "Mai"},
        personality_state=app.brain.personality_state,
        emotion=app.emotion,
    )
    app.kernel = AIOSKernel(
        brain=app.brain, voice=app.voice, wake=app.wake, stt=app.stt,
        state=app.shared_state, relationship_engine=app.relationship_engine,
        speaker_manager=app.speaker_manager,
        per_person_relationship=app.per_person_relationship,
        wake_generator=wake_generator,
    )
    tag_service(app, "kernel", "AIOSKernel", "Runtime", active=True)
    app.kernel.voice_manager = app.voice_manager
    logger.info("    [OK] AIOSKernel")
    assert app.kernel is not None

    logger.info("    Building HookRegistry and PluginLoader...")
    app.hook_registry = HookRegistry()
    plugin_loader = PluginLoader(hooks=app.hook_registry)
    app.plugin_loader = plugin_loader
    logger.info("    [OK] HookRegistry + PluginLoader")

    logger.info("    Building PluginLifecycleManager...")
    plugin_dir = Path(cfg.ROOT_DIR) / "plugins"
    app.lifecycle_manager = create_plugin_lifecycle_manager(
        plugin_dir=plugin_dir,
        hook_registry=app.hook_registry,
        event_bus=app.event_bus,
        brain=app.brain,
    )
    # Hand the app-wired manager to the plugin API routes — without this the
    # routes fall back to a disconnected temp-dir manager (Phase 2d).
    try:
        from api.routes_plugins import set_lifecycle_manager
        set_lifecycle_manager(app.lifecycle_manager)
    except Exception as exc:
        logger.warning("    [WARN] Could not wire lifecycle manager to API routes: %s", exc)
    tag_service(app, "lifecycle_manager", "PluginLifecycleManager", "Runtime", active=True)
    logger.info("    [OK] PluginLifecycleManager")

    logger.info("    Building ModelLifecycleCoordinator...")
    try:
        from core.model_lifecycle import ModelLifecycleCoordinator, init_coordinator
        app.model_lifecycle = init_coordinator(db_path=str(Path(cfg.ROOT_DIR) / "data" / "models.db"))
        tag_service(app, "model_lifecycle", "ModelLifecycleCoordinator", "Runtime", active=True)
        logger.info("    [OK] ModelLifecycleCoordinator")
    except Exception as e:
        logger.warning("    ModelLifecycleCoordinator failed to load: %s", e)
        app.model_lifecycle = None

    logger.info("    Loading plugins...")
    try:
        results = app.plugin_loader.load_all(brain=app.brain, event_bus=app.event_bus)
        loaded = sum(1 for r in results if r["success"])
        for r in results:
            if not r["success"]:
                logger.warning("    Plugin failed: %s", r['name'])
        logger.info("    [OK] Plugins: %s/%s loaded", loaded, len(results))
        if app.brain is not None:
            app.brain.hook_registry = app.hook_registry
    except Exception as e:
        logger.warning("    Plugin loading skipped: %s", e)
        app.plugin_loader = None
        app.hook_registry = None

    logger.info("    Building KnowledgeBaseBuilder...")
    try:
        embedding_service = getattr(app, "embedding_service", None) or getattr(app, "vector_store", None)
        if embedding_service is not None and hasattr(embedding_service, "_embed_service"):
            embedding_service = embedding_service._embed_service
        chunker = TextChunker(embedding_service=embedding_service)
        doc_store = DocumentStore()
        indexer = Indexer(
            vector_store=app.vector_store,
            chunker=chunker,
            document_store=doc_store,
            event_bus=app.event_bus,
        )
        app.knowledge_builder = KnowledgeBaseBuilder(
            indexer=indexer,
            document_store=doc_store,
            vector_store=app.vector_store,
            event_bus=app.event_bus,
        )
        tag_service(app, "knowledge_builder", "KnowledgeBaseBuilder", "Runtime")
        logger.info("    [OK] KnowledgeBaseBuilder")
    except Exception as e:
        logger.warning("    Knowledge base builder failed to load: %s", e)
        app.knowledge_builder = None
        indexer = None

    logger.info("    Building DirectoryWatcher...")
    app.directory_watcher = None
    try:
        if app.knowledge_builder is not None:
            directories = []
            try:
                from config.paths import OBSIDIAN_VAULT
                directories.append(OBSIDIAN_VAULT)
            except Exception:
                pass
            watcher = DirectoryWatcher(builder=app.knowledge_builder, directories=directories)
            app.directory_watcher = watcher
            tag_service(app, "directory_watcher", "DirectoryWatcher", "Runtime", active=False)
            logger.info("    [OK] DirectoryWatcher (dirs=%s)", directories or "none")
    except Exception as e:
        logger.warning("    DirectoryWatcher failed to load: %s", e)
    app.directory_watcher = None
