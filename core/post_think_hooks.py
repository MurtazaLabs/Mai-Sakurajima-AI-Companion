import logging
import threading
import time

logger = logging.getLogger(__name__)

_MAX_BG_THREADS = 16


class PostThinkHooks:

    def __init__(self, goal_manager=None, reflection_engine=None,
                 learning_engine=None, dream_engine=None,
                 personality_evolution=None, belief_engine=None,
                 graph_manager=None, procedural_memory=None,
                 brain_graph=None, reasoning_engine=None,
                 memory_hierarchy=None, prune_interval=10,
                 obsidian_writer=None, vault_root=None,
                 relationship_engine=None):
        self.goal_manager = goal_manager
        self.reflection_engine = reflection_engine
        self.learning_engine = learning_engine
        self.dream_engine = dream_engine
        self.personality_evolution = personality_evolution
        self.belief_engine = belief_engine
        self.graph_manager = graph_manager
        self.procedural_memory = procedural_memory
        self.brain_graph = brain_graph
        self.reasoning_engine = reasoning_engine
        self.memory_hierarchy = memory_hierarchy
        self.obsidian_writer = obsidian_writer
        self.vault_root = vault_root
        self.relationship_engine = relationship_engine
        self.prune_interval = prune_interval
        self._lock = threading.RLock()
        self._threads = []
        self._reflection_count = 0
        self._decay_count = 0
        self._prune_cycle_count = 0
        self._graph_export_count = 0

    def _prune_finished_threads(self):
        with self._lock:
            self._threads[:] = [t for t in self._threads if t.is_alive()]

    def run(self, user_input, response, thought_journal, memory, event_bus, obsidian_writer=None):
        # -- Relationship dynamics: synchronous, deterministic, no LLM/db.
        # Runs before the background cycle so the NEXT turn's prompt and
        # behavior rules already read the updated scores (M10).
        if self.relationship_engine:
            try:
                self.relationship_engine.analyze_turn(user_input, response)
            except Exception as e:
                logger.warning("[PostThink] relationship_engine: %s", e)

        if not any([self.reflection_engine, self.learning_engine,
                    self.goal_manager, self.dream_engine,
                    self.belief_engine, self.graph_manager,
                    self.personality_evolution, self.procedural_memory,
                    self.brain_graph, self.reasoning_engine,
                    self.memory_hierarchy, self.relationship_engine]):
            return

        self._prune_finished_threads()
        with self._lock:
            if len(self._threads) >= _MAX_BG_THREADS:
                logger.debug("[PostThink] Max bg threads reached, skipping")
                return

        def run_bg():
            with self._lock:
                rc = self._reflection_count

            # -- GoalManager --
            if self.goal_manager:
                try:
                    self.goal_manager.increment_turns()
                    from core.event_specs import GOAL_TURNS_INCREMENTED
                    from core.mai_message import publish_event
                    publish_event(event_bus, GOAL_TURNS_INCREMENTED, {}, source="cognition")
                except Exception as e:
                    logger.warning("[PostThink] goal_manager: %s", e)

            # -- ReflectionEngine + beliefs + goals + procedural --
            reflection = None
            if self.reflection_engine and thought_journal:
                try:
                    recent_thoughts = thought_journal.recent(5)
                    reflection = self.reflection_engine.daily_reflection(
                        thoughts=recent_thoughts,
                    )
                except Exception as e:
                    logger.warning("[PostThink] reflection_engine: %s", e)

                if reflection:
                    try:
                        with self._lock:
                            self._reflection_count += 1
                        from core.event_specs import (
                            REFLECTION_GENERATED,
                            STATE_REASONING_REFLECTION,
                        )
                        from core.mai_message import publish_event
                        publish_event(event_bus, REFLECTION_GENERATED, {
                            "type": "daily",
                            "summary": reflection.summary,
                            "topics": reflection.topics,
                            "patterns": reflection.patterns,
                        }, source="cognition")
                        publish_event(event_bus, STATE_REASONING_REFLECTION, {
                            "summary": reflection.summary,
                            "topics": reflection.topics,
                            "patterns": reflection.patterns,
                        }, source="cognition")
                        # skip — reflection is published via event_bus, no need to store as conversation
                    except Exception as e:
                        logger.warning("[PostThink] reflection store: %s", e)

                    try:
                        if self.belief_engine:
                            for topic in reflection.topics:
                                self.belief_engine._merge({
                                    "topic": topic, "predicate": "is",
                                    "object": "frequently discussed", "confidence": 0.6,
                                })
                        if self.goal_manager and reflection.topics:
                            beliefs = [{"topic": t, "predicate": "is", "object": "frequently discussed"} for t in reflection.topics]
                            self.goal_manager.check_goals(beliefs)
                    except Exception as e:
                        logger.warning("[PostThink] belief merge: %s", e)

                    try:
                        if self.procedural_memory and reflection.patterns:
                            for pattern in reflection.patterns:
                                self.procedural_memory.learn(
                                    rule=pattern, context="reflection",
                                    confidence=0.5, source="reflection_engine",
                                )
                    except Exception as e:
                        logger.warning("[PostThink] procedural learn: %s", e)

            # -- LearningEngine + personality --
            if self.learning_engine and thought_journal:
                try:
                    recent = thought_journal.recent(10)
                    if recent:
                        adjustments = self.learning_engine.adjust_behavior(
                            [t.get("conclusion", "") for t in recent]
                        )
                        if adjustments:
                            from core.event_specs import BEHAVIOR_ADJUSTED
                            from core.mai_message import publish_event
                            publish_event(event_bus, BEHAVIOR_ADJUSTED, adjustments, source="cognition")
                            if self.personality_evolution:
                                self.personality_evolution.evolve(behavior_adjustments=adjustments)
                except Exception as e:
                    logger.warning("[PostThink] learning_engine: %s", e)

            # -- BeliefEngine graph sync --
            if self.belief_engine and self.graph_manager:
                try:
                    beliefs = self.belief_engine.update_from_graph(self.graph_manager)
                    if beliefs:
                        from core.event_specs import BELIEF_GRAPH_SYNCED
                        from core.mai_message import publish_event
                        publish_event(event_bus, BELIEF_GRAPH_SYNCED, {"count": len(beliefs)}, source="cognition")
                except Exception as e:
                    logger.warning("[PostThink] belief graph_sync: %s", e)

            # -- GraphManager conversation processing --
            if self.graph_manager:
                try:
                    summary = self.graph_manager.process_conversation(user_input, response)
                    if summary and summary.get("entities_added", 0):
                        from core.event_specs import GRAPH_UPDATED
                        from core.mai_message import publish_event
                        publish_event(event_bus, GRAPH_UPDATED, summary, source="cognition")
                        with self._lock:
                            self._graph_export_count += 1
                            gc = self._graph_export_count
                        if gc % 3 == 0 and self.obsidian_writer and self.vault_root:
                            try:
                                from pathlib import Path
                                graph_dir = Path(self.vault_root) / "graph"
                                self.obsidian_writer.export_graph(graph_dir)
                            except Exception as e:
                                logger.warning("[PostThink] graph export: %s", e)
                except Exception as exc:
                    logger.warning("[PostThink] Graph processing: %s", exc)

            # -- BrainGraph thought nodes --
            with self._lock:
                rc = self._reflection_count
            if self.brain_graph and thought_journal and rc % 3 == 0:
                try:
                    recent = thought_journal.recent(20)
                    if recent:
                        for t in recent:
                            topic = t.get("query", "")[:80]
                            if topic:
                                self.brain_graph.add_thought_node(
                                    thought_id=t.get("id", str(time.time())),
                                    query=t.get("query", ""),
                                    conclusion=t.get("conclusion", ""),
                                    confidence=t.get("confidence", 0.5),
                                )
                except Exception as e:
                    logger.warning("[PostThink] brain_graph thought_node: %s", e)

            # -- MemoryHierarchy decay --
            if self.memory_hierarchy:
                with self._lock:
                    self._decay_count += 1
                    dc = self._decay_count
                if dc % 5 == 0:
                    try:
                        self.memory_hierarchy.apply_decay(elapsed_hours=0.1)
                    except Exception as e:
                        logger.warning("[PostThink] MemoryHierarchy decay: %s", e)

            # -- VectorStore prune --
            with self._lock:
                self._prune_cycle_count += 1
                pc = self._prune_cycle_count
            if pc % self.prune_interval == 0:
                try:
                    vec = getattr(memory, 'vector', None)
                    if vec is not None and hasattr(vec, 'prune'):
                        pruned = vec.prune()
                        if pruned:
                            logger.info("[PostThink] Auto-pruned %d memories", pruned)
                except Exception as e:
                    logger.warning("[PostThink] VectorStore prune: %s", e)

        thread = threading.Thread(target=run_bg, daemon=True)
        thread.start()
        with self._lock:
            self._threads.append(thread)

    def shutdown(self, timeout=5.0):
        with self._lock:
            pending = list(self._threads)
            self._threads.clear()
        if pending:
            per_thread = max(timeout / len(pending), 0.5)
            for t in pending:
                t.join(timeout=per_thread)
        return len(pending)
