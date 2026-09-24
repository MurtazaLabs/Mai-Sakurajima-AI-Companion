"""Dashboard/observability domain logic for the Mai API (state, consciousness, graph).

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for how this is composed.
"""
import logging
from typing import Any
from api.errors import safe_error

logger = logging.getLogger("api.server")


class DashboardMixin:
    """Rich dashboard state, consciousness snapshot, and graph export handlers."""

    # Set by MaiAPI at runtime — declared here for type checker
    brain: Any = None
    goal_manager: Any = None
    world_model: Any = None
    brain_graph: Any = None
    belief_engine: Any = None

    def build_dashboard_state(self):
        state = {}
        brain = self.brain
        if brain:
            try:
                emo = brain.state.emotion.model_dump() if hasattr(brain.state, "emotion") else {}
                if hasattr(brain, "emotion"):
                    emo["profile"] = brain.emotion.profile_name()
                    emo["history_count"] = brain.emotion.history.count()
                    emo["dominant"] = brain.emotion.dominant()
                    if hasattr(brain.emotion, "state"):
                        emo["state"] = brain.emotion.state.copy()
                state["emotion"] = emo
            except Exception as e:
                logger.exception("[Dashboard] emotion state: %s", e)
            try:
                state["relationship"] = brain.state.relationship_scores.model_dump() if hasattr(brain.state, "relationship_scores") else {}
            except Exception as e:
                logger.exception("[Dashboard] relationship: %s", e)
            try:
                rt = brain.state.runtime
                state["runtime"] = rt.model_dump() if hasattr(rt, "model_dump") else {}
            except Exception as e:
                logger.exception("[Dashboard] runtime: %s", e)
            try:
                state["personality"] = dict(brain.personality_state.state) if hasattr(brain.personality_state, "state") else {}
            except Exception as e:
                logger.exception("[Dashboard] personality: %s", e)
            try:
                rt = brain.state.runtime
                state["speaker"] = {"current": rt.current_speaker_name or "Unknown", "known": rt.known_user, "confidence": round(rt.speaker_confidence, 3)}
            except Exception as e:
                logger.exception("[Dashboard] speaker: %s", e)
        if self.goal_manager:
            try:
                state["goals"] = self.goal_manager.stats()
            except Exception as e:
                logger.exception("[Dashboard] goals: %s", e)
        if self.world_model:
            try:
                wstats = self.world_model.stats()
                entities = self.world_model.all_entities()
                wstats["entities"] = [{"name": e.get("name", ""), "category": e.get("category", "")} for e in entities[-20:]]
                state["world"] = wstats
            except Exception as ex:
                logger.exception("[Dashboard] world: %s", ex)
        try:
            kg = brain.graph_manager.graph if brain and hasattr(brain, "graph_manager") and brain.graph_manager else None
            if kg:
                from knowledge.graph_reflection import GraphReflection
                state["graph_reflection"] = GraphReflection(kg).summary()
                from knowledge.cognitive_graph import CognitiveGraph
                cg_stats = CognitiveGraph().stats(
                    belief_engine=self.belief_engine,
                    goal_manager=self.goal_manager,
                    brain=brain,
                )
                state["cognitive_graph"] = cg_stats
        except Exception as e:
            logger.exception("[Dashboard] cognitive graph: %s", e)
        if brain and hasattr(brain, "cognitive"):
            try:
                state["cognitive"] = brain.cognitive.get()
            except Exception as e:
                logger.exception("[Dashboard] cognitive state: %s", e)
        try:
            from app.config_loader import AI_NAME
            state["name"] = AI_NAME
        except Exception as e:
            logger.exception("[Dashboard] name: %s", e)
        return state

    def consciousness_state(self):
        state = {}
        brain = self.brain
        if not brain:
            return {"ready": False}
        try:
            state["emotion"] = brain.emotion.get() if hasattr(brain, "emotion") else {}
        except Exception as e:
            logger.exception("[Consciousness] emotion: %s", e)
        try:
            if hasattr(brain, "cognitive"):
                cog = brain.cognitive.get()
                state["cognitive"] = {
                    "working_memory": cog.get("working_memory", []),
                    "current_topic": cog.get("current_topic", ""),
                    "attention_focus": cog.get("attention_focus", ""),
                    "current_goal": cog.get("current_goal", ""),
                    "confidence": cog.get("confidence", 0.0),
                    "recent_thoughts": cog.get("recent_thoughts", []),
                }
        except Exception as e:
            logger.exception("[Consciousness] cognitive: %s", e)
        try:
            rt = brain.state.runtime
            state["speaker"] = {"name": rt.current_speaker_name or "Unknown", "known": rt.known_user}
        except Exception as e:
            logger.exception("[Consciousness] speaker: %s", e)
        try:
            state["personality"] = dict(brain.personality_state.state) if hasattr(brain.personality_state, "state") else {}
        except Exception as e:
            logger.exception("[Consciousness] personality: %s", e)
        try:
            state["goals"] = self.goal_manager.stats() if self.goal_manager else {}
        except Exception as e:
            logger.exception("[Consciousness] goals: %s", e)
        state["ready"] = True
        return state

    def dashboard_graph(self):
        try:
            from knowledge.cognitive_graph import CognitiveGraph

            cg = CognitiveGraph()
            data: dict = cg.to_graph_data(
                belief_engine=self.belief_engine,
                goal_manager=self.goal_manager,
                brain=self.brain,
            )

            if self.world_model:
                try:
                    for ent in self.world_model.all_entities():
                        data["nodes"].append({
                            "id": ent.get("name") or ent.get("id"),
                            "name": ent.get("name") or ent.get("id"),
                            "type": ent.get("category", "entity"),
                            "group": "entity",
                            "created_at": ent.get("created_at", 0),
                            "metadata": ent,
                        })
                except Exception as e:
                    logger.exception("[Dashboard] world entity: %s", e)

            type_breakdown: dict = {}
            try:
                if self.brain_graph:
                    type_breakdown = self.brain_graph.graph.count_by_type()
            except Exception as e:
                logger.exception("[Dashboard] type breakdown: %s", e)
            data["type_breakdown"] = type_breakdown

            if data.get("nodes"):
                return data
        except Exception as e:
            logger.exception("[Dashboard] graph: %s", e)
        return {"nodes": [], "edges": [], "type_breakdown": {}}

    def dashboard_graph_prune(self):
        """Remove auto-generated feedback-loop nodes from the KnowledgeGraph."""
        try:
            if not self.brain_graph:
                return {"error": "no_brain_graph"}
            kg = self.brain_graph.graph
            removed = kg.prune_feedback_loop_nodes()
            # Reset belief engine watermark so future conversations work correctly
            if self.belief_engine:
                self.belief_engine._last_relation_count = len(kg.all_relations())
            stats = kg.stats_by_type()
            return {"removed": removed, "stats": stats}
        except Exception as e:
            return {"error": safe_error(e)}
