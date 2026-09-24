import logging

import app.config_loader as cfg
from app.metadata import tag_service
from agency.registry import ToolRegistry
from agency.agent import Agent
from agency.goals import GoalManager
from agency.procedural import ProceduralMemory
from agency.world import WorldModel
from agency.dreaming import DreamEngine
from execution.task_executor import TaskExecutor
from execution.safe_executor import SafeExecutor

logger = logging.getLogger("Mai")


def build(app):
    logger.info("    Building ToolRegistry...")
    app.tool_registry = ToolRegistry(event_bus=app.event_bus)
    tag_service(app, "tool_registry", "ToolRegistry", "Agency")
    app.health_registry.register("tool_registry", component=app.tool_registry)
    app.health_registry.heartbeat("tool_registry")
    logger.info("    ✓ ToolRegistry")

    logger.info("    Building Agent...")
    app.agent = Agent(registry=app.tool_registry, event_bus=app.event_bus, max_steps=10)
    tag_service(app, "agent", "Agent", "Agency")
    app.health_registry.register("agent", component=app.agent)
    app.health_registry.heartbeat("agent")
    logger.info("    ✓ Agent")

    logger.info("    Building GoalManager...")
    app.goal_manager = GoalManager(
        event_bus=app.event_bus,
        brain_graph=app.brain_graph,
        learning_engine=app.learning_engine,
    )
    tag_service(app, "goal_manager", "GoalManager", "Agency")
    app.health_registry.register("goal_manager", component=app.goal_manager)
    app.health_registry.heartbeat("goal_manager")
    logger.info("    ✓ GoalManager")

    logger.info("    Building ProceduralMemory...")
    app.procedural_memory = ProceduralMemory(event_bus=app.event_bus, brain_graph=app.brain_graph)
    tag_service(app, "procedural_memory", "ProceduralMemory", "Agency")
    app.health_registry.register("procedural_memory", component=app.procedural_memory)
    app.health_registry.heartbeat("procedural_memory")
    logger.info("    ✓ ProceduralMemory")

    logger.info("    Building WorldModel...")
    app.world_model = WorldModel(event_bus=app.event_bus, brain_graph=app.brain_graph)
    tag_service(app, "world_model", "WorldModel", "Agency")
    app.health_registry.register("world_model", component=app.world_model)
    app.health_registry.heartbeat("world_model")
    logger.info("    ✓ WorldModel")

    logger.info("    Building DreamEngine...")
    app.dream_engine = DreamEngine(
        knowledge_graph=app.knowledge_graph,
        llm=getattr(app, "llm", None),
        event_bus=app.event_bus,
        vault_root=app.vault_root,
        obsidian_writer=app.obsidian_writer,
        vault_compiler=app.vault_compiler,
        experience_store=getattr(app, "experience_store", None),
    )
    tag_service(app, "dream_engine", "DreamEngine", "Agency")
    app.health_registry.register("dream_engine", component=app.dream_engine)
    app.health_registry.heartbeat("dream_engine")
    logger.info("    ✓ DreamEngine")

    # M6 · Emotional experience + growth — ExperienceStore and
    # PreferenceEvolution are built after memory exists, wired here.
    try:
        from memory.experience import ExperienceStore
        from config.paths import ROOT_DIR
        data_dir = ROOT_DIR / "data"
        data_dir.mkdir(exist_ok=True)
        app.experience_store = ExperienceStore(
            path=str(data_dir / "experiences.jsonl")
        )
        tag_service(app, "experience_store", "ExperienceStore", "Agency")
        logger.info("    ✓ ExperienceStore")
        app.dream_engine.experience_store = app.experience_store
        if getattr(app, "memory_pipeline", None) is not None:
            app.memory_pipeline.experience_store = app.experience_store
    except Exception as e:
        logger.warning("    ExperienceStore failed to load: %s", e)
        app.experience_store = None

    try:
        from agency.preference_evolution import PreferenceEvolution
        from config.character import (
            PREFERENCE_EVOLUTION_EVIDENCE_THRESHOLD,
            PREFERENCE_EVOLUTION_CADENCE_DAYS,
        )
        data_dir = ROOT_DIR / "data"
        data_dir.mkdir(exist_ok=True)
        def _refresh_overlay(overlay):
            core = getattr(app, "identity", None)
            if core is not None and hasattr(core, "attach_preference_overlay"):
                core.attach_preference_overlay(overlay)
        app.preference_evolution = PreferenceEvolution(
            threshold=PREFERENCE_EVOLUTION_EVIDENCE_THRESHOLD,
            cadence_days=PREFERENCE_EVOLUTION_CADENCE_DAYS,
            state_path=str(data_dir / "preference_evolution.json"),
            trail_path=str(data_dir / "preference_trail.json"),
            event_bus=app.event_bus,
            on_change=_refresh_overlay,
        )
        _refresh_overlay(app.preference_evolution.overlay_map())
        tag_service(app, "preference_evolution", "PreferenceEvolution", "Agency")
        logger.info("    ✓ PreferenceEvolution")
        if getattr(app, "memory_pipeline", None) is not None:
            app.memory_pipeline.preference_evolution = app.preference_evolution
    except Exception as e:
        logger.warning("    PreferenceEvolution failed to load: %s", e)
        app.preference_evolution = None

    logger.info("    Building Executors...")
    app.executor = TaskExecutor()
    tag_service(app, "executor", "TaskExecutor", "Agency")
    # Use config manager override for EXECUTOR_MODE if available
    executor_mode = cfg.SAFE_MODE
    if app.config_manager:
        override = app.config_manager.get("EXECUTOR_MODE")
        if override:
            executor_mode = override
    app.safe_executor = SafeExecutor(app.executor, mode=executor_mode)
    tag_service(app, "safe_executor", "SafeExecutor", "Agency")
    logger.info("    ✓ Executors")

    assert app.tool_registry is not None
    assert app.agent is not None
    assert app.goal_manager is not None
    assert app.procedural_memory is not None
    assert app.world_model is not None
    assert app.dream_engine is not None
    assert app.executor is not None
    assert app.safe_executor is not None
