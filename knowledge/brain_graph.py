# NOTE: P2-16 — consider collapsing BrainGraph/GraphManager/KnowledgeGraph into 2 layers
import logging
import threading
import time

logger = logging.getLogger(__name__)

NODE_TYPE_BELIEF = "belief"
NODE_TYPE_MEMORY = "memory"
NODE_TYPE_GOAL = "goal"
NODE_TYPE_THOUGHT = "thought"
NODE_TYPE_RULE = "rule"
NODE_TYPE_ENTITY = "entity"
NODE_TYPE_EMOTION = "emotion"
EDGE_BELIEF = "believes"
EDGE_RELATED = "related_to"
EDGE_HAS_SUBGOAL = "has_subgoal"
EDGE_REFERS_TO = "refers_to"
EDGE_APPLIES_TO = "applies_to"
EDGE_FOLLOWED_BY = "followed_by"

class BrainGraph:

    def __init__(self, graph=None, event_bus=None, belief_engine=None):
        from knowledge.graph import KnowledgeGraph
        self.graph = graph or KnowledgeGraph()
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self.belief_engine = belief_engine

    def add_belief_node(self, topic, predicate, object_val, confidence=0.5, evidence_count=1):
        # Single source of truth is BeliefEngine._beliefs — no longer stored in graph
        if not self.belief_engine:
            raise RuntimeError("BrainGraph.add_belief_node called without BeliefEngine wired. "
                               "BeliefEngine must be set before using belief operations.")
        self.belief_engine._merge({
            "topic": topic,
            "predicate": predicate,
            "object": object_val,
            "confidence": confidence,
        })
        return f"belief:{topic}:{predicate}:{object_val}"

    def get_beliefs(self, topic=None):
        # Single source of truth is BeliefEngine._beliefs
        if not self.belief_engine:
            raise RuntimeError("BrainGraph.get_beliefs called without BeliefEngine wired. "
                               "BeliefEngine must be set before using belief operations.")
        all_b = self.belief_engine.all_beliefs()
        if topic:
            topic = topic.lower()
            return [b for b in all_b if b.topic == topic]
        return all_b

    def add_memory_node(self, memory_id, text, memory_type="conversation",
                        score=0.5, tags=None, emotion=None, importance=0.5, source="user"):
        self.graph.add_entity(
            f"mem:{memory_id}",
            entity_type=NODE_TYPE_MEMORY,
            metadata={
                "memory_id": memory_id,
                "text": text,
                "memory_type": memory_type,
                "score": score,
                "tags": tags or [],
                "emotion": emotion or {},
                "importance": importance,
                "source": source,
                "created_at": time.time(),
            },
        )
        return memory_id

    def add_memory_link(self, from_id, to_id, weight=0.5):
        self.graph.add_relation(
            f"mem:{from_id}",
            EDGE_RELATED,
            f"mem:{to_id}",
            weight=weight,
        )

    def get_memories(self, memory_type=None, limit=None):
        nodes = self.graph.get_entity_by_type(NODE_TYPE_MEMORY)
        if memory_type:
            nodes = [n for n in nodes if n.metadata.get("memory_type") == memory_type]
        nodes.sort(key=lambda n: n.metadata.get("score", 0), reverse=True)
        if limit:
            nodes = nodes[:limit]
        return nodes

    def add_goal_node(self, goal_id, description, priority="normal",
                      status="active", context=None):
        self.graph.add_entity(
            f"goal:{goal_id}",
            entity_type=NODE_TYPE_GOAL,
            metadata={
                "goal_id": goal_id,
                "description": description,
                "priority": priority,
                "status": status,
                "context": context or {},
                "created_at": time.time(),
                "turn_count": 0,
            },
        )
        return goal_id

    def update_goal_node(self, goal_id, status=None, turn_count=None, progress=None):
        node = self.graph.get_entity(f"goal:{goal_id}")
        if node:
            if status:
                node.metadata["status"] = status
            if turn_count is not None:
                node.metadata["turn_count"] = turn_count
            if progress is not None:
                node.metadata["progress"] = progress
            node.metadata["updated_at"] = time.time()

    def get_goals(self, status=None):
        nodes = self.graph.get_entity_by_type(NODE_TYPE_GOAL)
        if status:
            nodes = [n for n in nodes if n.metadata.get("status") == status]
        nodes.sort(key=lambda n: n.metadata.get("turn_count", 0), reverse=True)
        return nodes

    def add_thought_node(self, thought_id, query="", conclusion="",
                         confidence=0.5, reasoning_steps=None):
        self.graph.add_entity(
            f"thought:{thought_id}",
            entity_type=NODE_TYPE_THOUGHT,
            metadata={
                "thought_id": thought_id,
                "query": query,
                "conclusion": conclusion,
                "confidence": confidence,
                "reasoning_steps": reasoning_steps or [],
                "created_at": time.time(),
            },
        )
        return thought_id

    def get_thoughts(self, limit=None):
        nodes = self.graph.get_entity_by_type(NODE_TYPE_THOUGHT)
        nodes.sort(key=lambda n: n.metadata.get("created_at", 0), reverse=True)
        if limit:
            nodes = nodes[:limit]
        return nodes

    def add_rule_node(self, rule, context, confidence=0.5, source="experience"):
        rule_id = f"rule:{hash(rule)}:{hash(context)}"
        self.graph.add_entity(
            rule_id,
            entity_type=NODE_TYPE_RULE,
            metadata={
                "rule": rule,
                "context": context,
                "confidence": confidence,
                "source": source,
                "apply_count": 0,
                "created_at": time.time(),
            },
        )
        self.graph.add_relation(rule_id, EDGE_APPLIES_TO, context, weight=confidence)
        return rule_id

    def get_rules(self, context=None, min_confidence=0.0):
        nodes = self.graph.get_entity_by_type(NODE_TYPE_RULE)
        nodes = [n for n in nodes if n.metadata.get("confidence", 0) >= min_confidence]
        if context:
            context = context.lower()
            nodes = [
                n for n in nodes
                if context in n.metadata.get("context", "").lower()
            ]
        nodes.sort(key=lambda n: n.metadata.get("confidence", 0), reverse=True)
        return nodes

    def add_world_entity(self, name, category="person", attributes=None):
        self.graph.add_entity(
            name,
            entity_type=category,
            metadata=dict(attributes or {}),
        )

    def get_world_entities(self, category=None):
        if category:
            return self.graph.get_entity_by_type(category)
        return self.graph.all_entities()

    def connect(self, source, relation, target, weight=1.0):
        self.graph.add_relation(source, relation, target, weight=weight)

    def add_emotion_snapshot(self, snapshot_id, state, profile, dominant):
        self.graph.add_entity(
            f"emotion:{snapshot_id}",
            entity_type=NODE_TYPE_EMOTION,
            metadata={
                "snapshot_id": snapshot_id,
                "state": dict(state),
                "profile": profile,
                "dominant": dominant,
                "created_at": time.time(),
            },
        )
        prev = self.graph.get_entity_by_type(NODE_TYPE_EMOTION)
        if len(prev) >= 2:
            self.graph.add_relation(
                f"emotion:{prev[-2].name.split(':')[-1]}",
                EDGE_FOLLOWED_BY,
                f"emotion:{snapshot_id}",
                weight=0.5,
            )
        return snapshot_id

    def get_emotion_history(self, limit=20):
        nodes = self.graph.get_entity_by_type(NODE_TYPE_EMOTION)
        nodes.sort(key=lambda n: n.metadata.get("created_at", 0), reverse=True)
        return nodes[:limit]

    def stats(self):
        base = self.graph.stats()
        type_counts = self.graph.count_by_type()
        base["by_type"] = type_counts
        return base

    def all_entities(self):
        return self.graph.all_entities()

    def all_relations(self):
        return self.graph.all_relations()

    def search(self, query):
        return self.graph.search(query)

    def search_entities(self, query, node_type=None):
        return self.graph.search_entities(query, node_type=node_type)

    def get_entity(self, name):
        return self.graph.get_entity(name)

    def get_relations_for(self, entity):
        return self.graph.get_relations_for(entity)

    def query(self, entity, depth=1):
        return self.graph.query(entity, depth=depth)

    def most_connected(self, limit=10):
        return self.graph.most_connected(limit=limit)

    def save(self, path):
        return self.graph.save(path)

    @classmethod
    def load(cls, path):
        from knowledge.graph import KnowledgeGraph
        kg = KnowledgeGraph.load(path)
        return cls(graph=kg)
