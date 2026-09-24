import logging

import app.config_loader as cfg
from app.metadata import tag_service
from core.brain import Brain
from agency.evolution import PersonalityEvolution
from knowledge.cognitive_graph import CognitiveGraph
from knowledge.graph_reflection import GraphReflection
from knowledge.reasoning import GraphReasoning
from core.emotion import Emotion

logger = logging.getLogger("Mai")


def build(app):
    logger.info("    Building CognitiveGraph...")
    app.cognitive_graph = CognitiveGraph()
    tag_service(app, "cognitive_graph", "CognitiveGraph", "Cognition")
    logger.info("    ✓ CognitiveGraph")

    logger.info("    Building GraphReflection...")
    app.graph_reflection = GraphReflection(app.knowledge_graph)
    tag_service(app, "graph_reflection", "GraphReflection", "Cognition")
    logger.info("    ✓ GraphReflection")

    logger.info("    Building GraphReasoning...")
    app.graph_reasoning = GraphReasoning(app.graph_manager)
    tag_service(app, "graph_reasoning", "GraphReasoning", "Cognition")
    logger.info("    ✓ GraphReasoning")

    # Wire graph into memory pipeline and retriever
    app.memory.configure_pipeline(graph=app.graph_manager)
    app.retriever.graph_reasoning = app.graph_reasoning

    # Wire VaultPostProcessor into the pipeline
    from knowledge.vault_post_processor import VaultPostProcessor
    app.vault_post_processor = VaultPostProcessor(
        compiler=app.vault_compiler,
        graph_manager=app.graph_manager,
        llm=app.llm,
        relationship_updater=app.memory.memory.rel_updater,
    )
    app.memory.configure_pipeline(vault_post_processor=app.vault_post_processor)
    logger.info("    ✓ VaultPostProcessor")

    # Phase 2: point RelationshipUpdater at the VaultCompiler so relationship.md
    # is a compile output, not a direct-write store.
    try:
        app.memory.memory.rel_updater.compiler = app.vault_compiler
    except Exception as e:
        logger.warning("    RelationshipUpdater compiler wiring skipped: %s", e)

    from core.brain import BrainDeps

    logger.info("    Building Brain...")
    app.brain = Brain(
        llm=app.llm, memory=app.memory, executor=app.safe_executor,
        state=app.shared_state,
        deps=BrainDeps(
            event_bus=app.event_bus,
            tool_registry=app.tool_registry, agent=app.agent,
            retriever=app.retriever, reasoning_engine=app.reasoning_engine,
            thought_journal=app.thought_journal, reflection_engine=app.reflection_engine,
            learning_engine=app.learning_engine, goal_manager=app.goal_manager,
            world_model=app.world_model, procedural_memory=app.procedural_memory,
            dream_engine=app.dream_engine, graph_manager=app.graph_manager,
            graph_reasoning=app.graph_reasoning, obsidian_writer=app.obsidian_writer,
            memory_hierarchy=app.memory_hierarchy,
            relationship_engine=app.relationship_engine,
            session_manager=app.session_manager,
        ),
    )
    tag_service(app, "brain", "Brain", "Cognition")
    logger.info("    ✓ Brain")

    # Create Emotion for wake generator and emotional responses
    app.emotion = Emotion(shared_state=app.shared_state, event_bus=app.event_bus)
    tag_service(app, "emotion", "Emotion", "Cognition")
    logger.info("    ✓ Emotion")

    # Bind IdentityCore to owning engines (read-only projection hooks).
    try:
        app.identity.bind(
            personality_state=app.brain.personality_state,
            relationship_engine=app.relationship_engine,
        )
        app.brain.identity_core = app.identity
        logger.info("    ✓ IdentityCore bound (personality_state, relationship_engine)")
    except Exception as e:
        logger.warning("    IdentityCore bind skipped: %s", e)

    # M2 — Psychological core: NeedsEngine evaluates needs each turn and feeds
    # the state.* projection bus. Brain pulls the live relationship context.
    from core.needs_engine import NeedsEngine
    app.needs_engine = NeedsEngine(event_bus=app.event_bus)
    app.brain.needs_engine = app.needs_engine
    tag_service(app, "needs_engine", "NeedsEngine", "Cognition")
    logger.info("    ✓ NeedsEngine")

    # M6 — Preference evolution is built in the Agency layer; expose it on the
    # brain so the scheduler's weekly preference_apply task can reach it.
    app.brain.preference_evolution = getattr(app, "preference_evolution", None)

    # M8 — Experience proxy: the memory coordinator exposes reflected
    # experiences to next-turn context assembly (EXPERIENTIAL MEMORIES).
    mc = getattr(app.brain, "memory_coordinator", None)
    if mc is not None:
        mc.experience_store = getattr(app, "experience_store", None)

    logger.info("    Building PersonalityEvolution...")
    app.personality_evolution = PersonalityEvolution(
        personality_state=app.brain.personality_state,
        event_bus=app.event_bus,
    )
    tag_service(app, "personality_evolution", "PersonalityEvolution", "Cognition")
    app.brain.post_think_hooks.personality_evolution = app.personality_evolution
    app.brain.post_think_hooks.brain_graph = app.brain_graph
    logger.info("    ✓ PersonalityEvolution")

    # Phase 3: generate the proposed-layout vault artifacts (index.md, schema.md,
    # graph/ export) once at boot. These are compiler outputs, not live stores.
    try:
        app.vault_compiler.compile_schema()
        app.vault_compiler.compile_graph(app.graph_manager)
        app.vault_compiler.compile_index()
        logger.info("    ✓ VaultCompiler layout artifacts (index/schema/graph)")
    except Exception as e:
        logger.warning("    VaultCompiler layout artifacts skipped: %s", e)

    # Import existing memory nodes into the knowledge graph so named entities
    # and relations appear in graph/entities.md and graph/relations.md.
    try:
        memory_graph = getattr(app.memory.memory, "intel", None)
        if memory_graph is not None and hasattr(memory_graph, "graph"):
            mg = memory_graph.graph
            if mg and hasattr(mg, "nodes") and mg.nodes:
                imported = app.knowledge_graph.import_from_memory_graph(mg)
                logger.info("    ✓ Imported %d memory nodes into knowledge graph", len(mg.nodes))
    except Exception as e:
        logger.warning("    Memory graph import skipped: %s", e)

    assert app.cognitive_graph is not None
    assert app.graph_reflection is not None
    assert app.graph_reasoning is not None
    assert app.brain is not None
    assert app.personality_evolution is not None
