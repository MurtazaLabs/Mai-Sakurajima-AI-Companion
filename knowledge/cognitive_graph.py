import logging
import time

logger = logging.getLogger(__name__)


class CognitiveGraph:
    """Read-only dashboard visualization helper.

    Reads directly from source subsystems (BeliefEngine, GoalManager, Brain)
    and formats data for frontend display.  Does *not* write through the
    KnowledgeGraph — eliminates triple-belief-storage drift.
    """

    def __init__(self, graph=None):
        self._cognitive_prefix = "cognitive:"

    def to_graph_data(self, belief_engine=None, goal_manager=None, brain=None):
        nodes = []
        edges = []
        seen = set()
        if belief_engine:
            try:
                beliefs = belief_engine.all_beliefs()
            except Exception as e:
                logger.warning("[CognitiveGraph] beliefs: %s", e)
                beliefs = []
            for b in beliefs:
                nid = self._belief_node(b)
                if nid in seen:
                    continue
                seen.add(nid)
                nodes.append(self._belief_node_dict(b, nid))
                if b.topic and b.topic != "unknown":
                    edges.append({"source": nid, "target": b.topic, "relation": "about", "weight": b.confidence})
                if b.object:
                    edges.append({"source": nid, "target": b.object.lower().strip(), "relation": "states", "weight": b.confidence})
        if goal_manager:
            try:
                goals = goal_manager.list()
            except Exception as e:
                logger.warning("[CognitiveGraph] goals: %s", e)
                goals = []
            for g in goals:
                nid = self._goal_node(g)
                if nid in seen:
                    continue
                seen.add(nid)
                nodes.append(self._goal_node_dict(g, nid))
                context = getattr(g, "context", {}) or {}
                for key, val in context.items():
                    if isinstance(val, str) and len(val) > 1:
                        edges.append({"source": nid, "target": val.lower().strip(), "relation": "context", "weight": 1.0})
        if brain:
            try:
                state_data = brain.state.emotion.model_dump() if hasattr(brain.state, "emotion") else {}
            except Exception as e:
                logger.warning("[CognitiveGraph] emotions: %s", e)
                state_data = {}
            if isinstance(state_data, dict):
                emotion_type = state_data.get("type", "neutral")
                intensity = state_data.get("intensity", 0.5)
                nid = self._emotion_node(emotion_type)
                if nid not in seen:
                    seen.add(nid)
                    nodes.append({
                        "id": nid, "name": nid, "type": "emotion",
                        "group": "cognitive", "created_at": time.time(),
                        "metadata": {"emotion_type": emotion_type, "intensity": intensity},
                    })
        return {"nodes": nodes, "edges": edges}

    def stats(self, belief_engine=None, goal_manager=None, brain=None):
        data = self.to_graph_data(belief_engine, goal_manager, brain)
        cognitive = [n for n in data["nodes"] if n["group"] == "cognitive"]
        return {
            "total_nodes": len(data["nodes"]),
            "cognitive_nodes": len(cognitive),
            "entity_nodes": len(data["nodes"]) - len(cognitive),
            "edges": len(data["edges"]),
        }

    def _belief_node(self, belief):
        obj = belief.object[:30].replace(" ", "_")
        return f"cognitive:belief:{belief.topic}:{obj}"

    def _belief_node_dict(self, belief, nid):
        return {
            "id": nid, "name": nid,
            "type": "belief", "group": "cognitive",
            "created_at": time.time(),
            "metadata": {
                "confidence": belief.confidence,
                "evidence_count": belief.evidence_count,
                "predicate": belief.predicate,
                "object": belief.object[:100],
            },
        }

    def _goal_node(self, goal):
        desc = goal.description[:30].replace(" ", "_")
        return f"cognitive:goal:{goal.id[:8]}:{desc}"

    def _goal_node_dict(self, goal, nid):
        return {
            "id": nid, "name": nid,
            "type": f"goal:{goal.status}", "group": "cognitive",
            "created_at": time.time(),
            "metadata": {
                "priority": goal.priority,
                "status": goal.status,
                "description": goal.description[:100],
            },
        }

    def _emotion_node(self, emotion_type):
        return f"cognitive:emotion:{emotion_type}"
