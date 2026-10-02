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

    # Upper bound on the exported payload. The Canvas view renders 5,000 nodes
    # comfortably (see scripts/bench_graph.mjs); this cap only stops a runaway
    # graph from producing a multi-megabyte response.
    GRAPH_NODE_LIMIT = 5000
    GRAPH_EDGE_LIMIT = 20000

    def dashboard_graph(self):
        """Export the live knowledge graph for the Cognitive Desktop view.

        The node/edge payload and ``type_breakdown`` must come from the same
        store. An earlier version built a throwaway ``CognitiveGraph()`` here,
        which always came back empty while the breakdown counted the real
        graph, so the page rendered one node next to a 776-node summary.
        """
        nodes: list[dict] = []
        edges: list[dict] = []
        type_breakdown: dict = {}

        if self.brain_graph:
            try:
                kg = self.brain_graph.graph
                type_breakdown = kg.count_by_type()
                for entity in kg.all_entities()[: self.GRAPH_NODE_LIMIT]:
                    nodes.append({
                        "id": entity.name,
                        "name": entity.name,
                        "type": entity.type or "unknown",
                        "group": entity.type or "unknown",
                        "created_at": getattr(entity, "created_at", 0),
                        "metadata": dict(getattr(entity, "metadata", {}) or {}),
                    })
                known = {node["id"] for node in nodes}
                for relation in kg.all_relations()[: self.GRAPH_EDGE_LIMIT]:
                    if relation.source not in known or relation.target not in known:
                        continue
                    edges.append({
                        "source": relation.source,
                        "target": relation.target,
                        "type": relation.relation,
                        "label": relation.relation,
                        "weight": relation.weight,
                    })
            except Exception as e:
                logger.exception("[Dashboard] graph export: %s", e)
                nodes, edges = [], []

        # Beliefs, goals, and world entities are not part of the knowledge
        # graph; merge them so the view shows live cognition too.
        if self.world_model:
            try:
                known = {node["id"] for node in nodes}
                for ent in self.world_model.all_entities():
                    node_id = str(ent.get("name") or ent.get("id") or "")
                    if not node_id or node_id in known:
                        continue
                    known.add(node_id)
                    nodes.append({
                        "id": node_id,
                        "name": node_id,
                        "type": ent.get("category", "entity"),
                        "group": "entity",
                        "created_at": ent.get("created_at", 0),
                        "metadata": ent,
                    })
            except Exception as e:
                logger.exception("[Dashboard] world entity: %s", e)

        return {
            "nodes": nodes,
            "edges": edges,
            "type_breakdown": type_breakdown,
            "truncated": len(nodes) >= self.GRAPH_NODE_LIMIT,
        }

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
