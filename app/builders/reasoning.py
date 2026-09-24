import logging

import app.config_loader as cfg
from app.metadata import tag_service
from reasoning.engine import ReasoningEngine
from reasoning.journal import ThoughtJournal
from reasoning.reflection import ReflectionEngine
from reasoning.learning import LearningEngine

logger = logging.getLogger("Mai")


def build(app):
    logger.info("    Building ThoughtJournal...")
    app.thought_journal = ThoughtJournal(
        path=str(cfg.CACHE_DIR / "thought_journal.json"),
        brain_graph=app.brain_graph,
    )
    tag_service(app, "thought_journal", "ThoughtJournal", "Reasoning")
    logger.info("    ✓ ThoughtJournal")

    logger.info("    Building ReasoningEngine...")
    app.reasoning_engine = ReasoningEngine(
        retriever=app.retriever,
        journal=app.thought_journal,
        event_bus=app.event_bus,
    )
    tag_service(app, "reasoning_engine", "ReasoningEngine", "Reasoning")
    logger.info("    ✓ ReasoningEngine")

    logger.info("    Building ReflectionEngine...")
    app.reflection_engine = ReflectionEngine(
        journal=app.thought_journal,
        event_bus=app.event_bus,
        enforce_cadence=True,
    )
    tag_service(app, "reflection_engine", "ReflectionEngine", "Reasoning")
    logger.info("    ✓ ReflectionEngine")

    logger.info("    Building LearningEngine...")
    app.learning_engine = LearningEngine(
        belief_engine=app.belief_engine,
        event_bus=app.event_bus,
    )
    tag_service(app, "learning_engine", "LearningEngine", "Reasoning")
    logger.info("    ✓ LearningEngine")

    app.health_registry.register("reasoning_engine", component=app.reasoning_engine)
    app.health_registry.register("reflection_engine", component=app.reflection_engine)
    app.health_registry.register("learning_engine", component=app.learning_engine)
    app.health_registry.heartbeat("reasoning_engine")
    app.health_registry.heartbeat("reflection_engine")
    app.health_registry.heartbeat("learning_engine")

    assert app.thought_journal is not None
    assert app.reasoning_engine is not None
    assert app.reflection_engine is not None
    assert app.learning_engine is not None
