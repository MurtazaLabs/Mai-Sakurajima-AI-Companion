import logging

logger = logging.getLogger("Mai")


def _check_infrastructure(app):
    ok = True
    if app.event_bus is None:
        logger.error("  ✗ EventBus: MISSING"); ok = False
    if app.shared_state is None:
        logger.error("  ✗ SharedState: MISSING"); ok = False
    if app.llm is None:
        logger.error("  ✗ LLM: MISSING"); ok = False
    if app.health_registry is None:
        logger.error("  ✗ HealthRegistry: MISSING"); ok = False
    return ok


def _check_knowledge(app):
    ok = True
    if app.knowledge_graph is None:
        logger.error("  ✗ KnowledgeGraph: MISSING"); ok = False
    if app.brain_graph is None:
        logger.error("  ✗ BrainGraph: MISSING"); ok = False
    if app.belief_engine is None:
        logger.error("  ✗ BeliefEngine: MISSING"); ok = False
    return ok


def _check_memory(app):
    ok = True
    if app.memory is None:
        logger.error("  ✗ Memory: MISSING"); ok = False
    if app.memory_hierarchy is None:
        logger.error("  ✗ MemoryHierarchy: MISSING"); ok = False
    if app.retriever is None:
        logger.error("  ✗ Retriever: MISSING"); ok = False
    return ok


def _check_reasoning(app):
    ok = True
    if app.thought_journal is None:
        logger.error("  ✗ ThoughtJournal: MISSING"); ok = False
    if app.reasoning_engine is None:
        logger.error("  ✗ ReasoningEngine: MISSING"); ok = False
    if app.reflection_engine is None:
        logger.error("  ✗ ReflectionEngine: MISSING"); ok = False
    if app.learning_engine is None:
        logger.error("  ✗ LearningEngine: MISSING"); ok = False
    return ok


def _check_agency(app):
    ok = True
    if app.tool_registry is None:
        logger.error("  ✗ ToolRegistry: MISSING"); ok = False
    if app.agent is None:
        logger.error("  ✗ Agent: MISSING"); ok = False
    if app.goal_manager is None:
        logger.error("  ✗ GoalManager: MISSING"); ok = False
    if app.world_model is None:
        logger.error("  ✗ WorldModel: MISSING"); ok = False
    if app.safe_executor is None:
        logger.error("  ✗ SafeExecutor: MISSING"); ok = False
    return ok


def _check_brain(app):
    ok = True
    if app.brain is None:
        logger.error("  ✗ Brain: MISSING"); ok = False
    if app.personality_evolution is None:
        logger.error("  ✗ PersonalityEvolution: MISSING"); ok = False
    if app.needs_engine is None:
        logger.error("  ✗ NeedsEngine: MISSING"); ok = False
    return ok


def _check_voice(app):
    ok = True
    if app.voice is None:
        logger.error("  ✗ Voice: MISSING"); ok = False
    if app.stt is None:
        logger.error("  ✗ STT: MISSING"); ok = False
    if app.wake is None:
        logger.error("  ✗ WakeWord: MISSING"); ok = False
    return ok


def _check_runtime(app):
    ok = True
    if app.kernel is None:
        logger.error("  ✗ Kernel: MISSING"); ok = False
    return ok


VALIDATION_ORDER = [
    ("Infrastructure", _check_infrastructure),
    ("Knowledge",       _check_knowledge),
    ("Memory",          _check_memory),
    ("Reasoning",       _check_reasoning),
    ("Agency",          _check_agency),
    ("Cognition",       _check_brain),
    ("Voice",           _check_voice),
    ("Runtime",         _check_runtime),
]


def validate(app):
    logger.info("  Validation...")
    for layer_name, check_fn in VALIDATION_ORDER:
        if not check_fn(app):
            logger.error("  ✗ Layer FAILED: %s", layer_name)
            return False
        logger.info("    ✓ %s", layer_name)
    return True
