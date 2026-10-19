# knowledge/belief_engine.py
import logging
import re
import threading
import time

from core.utils import TTLCache

logger = logging.getLogger(__name__)


class Belief:

    def __init__(self, topic, predicate="is", object="", confidence=0.5, evidence_count=1):
        self.topic = str(topic).strip().lower()
        self.predicate = str(predicate).strip().lower()
        self.object = str(object).strip()
        self.confidence = max(0.0, min(1.0, float(confidence)))
        self.evidence_count = int(evidence_count)
        self.first_seen = time.time()
        self.last_updated = time.time()
        self.contradictions = 0

    def to_dict(self):
        return {
            "topic": self.topic,
            "predicate": self.predicate,
            "object": self.object,
            "confidence": self.confidence,
            "evidence_count": self.evidence_count,
            "first_seen": self.first_seen,
            "last_updated": self.last_updated,
            "contradictions": self.contradictions,
        }

    def __repr__(self):
        return (
            f"<Belief "
            f"{self.topic} {self.predicate} {self.object[:20]} "
            f"({round(self.confidence, 2)})>"
        )


class BeliefEngine:
    # ═══════════════════════════════════════════════════════════
    # SINGLE SOURCE OF TRUTH for all belief data.
    # BrainGraph and CognitiveGraph read from this class.
    # Do NOT add separate belief storage elsewhere.
    # ═══════════════════════════════════════════════════════════

    MAX_BELIEFS = 10000

    def __init__(self, event_bus=None, brain_graph=None):
        self._lock = threading.RLock()
        self._beliefs = {}
        self.event_bus = event_bus
        self.brain_graph = brain_graph
        self._last_relation_count = 0
        # Query cache for get_belief and query
        self._belief_cache = TTLCache(maxsize=1024, ttl=300.0)

    def _key(self, topic, predicate, object):
        return f"{topic}:{predicate}:{str(object).lower()}"

    def update(self, memory):
        from memory.schema import MemoryObject

        if not isinstance(memory, MemoryObject):
            return None

        content = memory.content
        mem_type = memory.type
        confidence = memory.confidence

        extracted = self._extract_beliefs(content, mem_type, confidence)

        results = []
        for belief_data in extracted:
            belief = self._merge(belief_data)
            results.append(belief)

        if results and self.brain_graph:
            for b in results:
                self.brain_graph.add_belief_node(
                    topic=b.topic,
                    predicate=b.predicate,
                    object_val=b.object,
                    confidence=b.confidence,
                    evidence_count=b.evidence_count,
                )

        if results and self.event_bus:
            from core.event_specs import BELIEF_UPDATED, STATE_BELIEF_UPDATED
            from core.mai_message import publish_event
            publish_event(self.event_bus, BELIEF_UPDATED, {
                "beliefs": [b.to_dict() for b in results],
                "source_memory_id": memory.id,
            }, source="knowledge")
            publish_event(self.event_bus, STATE_BELIEF_UPDATED, {
                "beliefs": [b.to_dict() for b in results],
            }, source="knowledge")

        return results

    def _extract_beliefs(self, text, mem_type, confidence):
        if not text:
            return []

        text_lower = text.lower()
        results = []

        patterns = [
            (r"\b(likes|enjoys|loves)\s+(\w+)", "likes"),
            (r"\b(dislikes|hates)\s+(\w+)", "dislikes"),
        ]

        for pattern, predicate in patterns:
            for match in re.finditer(pattern, text_lower):
                obj = match.group(2)
                results.append({
                    "topic": "user",
                    "predicate": predicate,
                    "object": obj,
                    "confidence": confidence,
                })

        if mem_type in ("preference", "preference_negative"):
            pred = "likes" if mem_type == "preference" else "dislikes"
            results.append({
                "topic": "user",
                "predicate": pred,
                "object": text,
                "confidence": confidence,
            })

        if mem_type == "identity":
            results.append({
                "topic": "user",
                "predicate": "is",
                "object": text,
                "confidence": confidence,
            })

        if mem_type == "employment":
            results.append({
                "topic": "user",
                "predicate": "works_at",
                "object": text,
                "confidence": confidence,
            })

        if mem_type == "location":
            results.append({
                "topic": "user",
                "predicate": "lives_in",
                "object": text,
                "confidence": confidence,
            })

        return results

    def _evict_if_needed(self):
        if len(self._beliefs) <= self.MAX_BELIEFS:
            return
        sorted_beliefs = sorted(
            self._beliefs.items(),
            key=lambda item: item[1].confidence,
        )
        to_remove = len(self._beliefs) - self.MAX_BELIEFS
        for k, _ in sorted_beliefs[:to_remove]:
            del self._beliefs[k]
        logger.info("[BeliefEngine] Evicted %d beliefs (cap=%d)", to_remove, self.MAX_BELIEFS)

    def _invalidate_belief_cache(self, topic: str):
        """Invalidate cache entries for a topic."""
        topic = topic.lower()
        # Invalidate get_belief and query cache entries
        self._belief_cache.clear()

    def _merge(self, belief_data):
        k = self._key(
            belief_data["topic"],
            belief_data["predicate"],
            belief_data["object"],
        )

        with self._lock:
            if k in self._beliefs:
                existing = self._beliefs[k]
                existing.evidence_count += 1
                existing.last_updated = time.time()
                confidence_boost = 0.1 * (1 - existing.confidence) * (1 / (1 + existing.contradictions))
                existing.confidence = min(1.0, existing.confidence + confidence_boost)
                # Invalidate cache
                self._invalidate_belief_cache(belief_data["topic"])
                return existing
            else:
                belief = Belief(
                    topic=belief_data["topic"],
                    predicate=belief_data["predicate"],
                    object=belief_data["object"],
                    confidence=belief_data["confidence"],
                )
                self._beliefs[k] = belief
                self._evict_if_needed()
                # Invalidate cache
                self._invalidate_belief_cache(belief_data["topic"])
                return belief

    def contradict(self, topic, predicate, object):
        k = self._key(topic, predicate, object)
        with self._lock:
            if k in self._beliefs:
                belief = self._beliefs[k]
                belief.contradictions += 1
                belief.confidence = max(0.1, belief.confidence * 0.7)
                belief.last_updated = time.time()
                if self.brain_graph:
                    self.brain_graph.add_belief_node(
                        topic=belief.topic,
                        predicate=belief.predicate,
                        object_val=belief.object,
                        confidence=belief.confidence,
                        evidence_count=belief.evidence_count,
                    )
                # Invalidate cache
                self._invalidate_belief_cache(topic)
                return belief
        return None

    def get_belief(self, topic, predicate=None, object=None):
        # Build cache key
        topic = topic.lower()
        predicate = predicate.lower() if predicate else None
        object = object.lower() if object else None
        cache_key = f"belief:{topic}:{predicate}:{object}"
        
        # Check cache first
        cached = self._belief_cache.get(cache_key)
        if cached is not None:
            return cached
        
        with self._lock:
            for k, belief in self._beliefs.items():
                if belief.topic == topic:
                    if predicate and belief.predicate != predicate:
                        continue
                    if object and belief.object.lower() != object:
                        continue
                    self._belief_cache.set(cache_key, belief)
                    return belief
        return None

    def query(self, topic):
        topic = topic.lower()
        cache_key = f"beliefs:{topic}"
        
        cached = self._belief_cache.get(cache_key)
        if cached is not None:
            return cached
        
        with self._lock:
            results = [
                b for b in self._beliefs.values()
                if b.topic == topic
            ]
            # Store copy to avoid modification issues
            self._belief_cache.set(cache_key, list(results))
            return results

    def all_beliefs(self):
        with self._lock:
            return sorted(
                self._beliefs.values(),
                key=lambda b: b.confidence,
                reverse=True,
            )

    def update_from_graph(self, graph_manager):
        if not graph_manager:
            return []
        try:
            all_edges = graph_manager.graph.all_relations()
            # Only process NEW relations since last call — breaks the
            # feedback loop where add_belief_node() adds relations that
            # would otherwise be re-processed on every cycle.
            new_count = len(all_edges) - self._last_relation_count
            if new_count <= 0:
                return []
            new_edges = all_edges[-new_count:]
            self._last_relation_count = len(all_edges)

            results = []
            seen = set()
            for edge in new_edges:
                src, tgt = str(edge.source).lower(), str(edge.target).lower()
                rel = edge.relation

                direct_key = f"{src}:{rel}:{tgt}"
                if direct_key not in seen:
                    seen.add(direct_key)
                    b = self._merge({
                        "topic": src,
                        "predicate": rel,
                        "object": tgt,
                        "confidence": max(0.3, edge.weight * 1.0),
                    })
                    results.append(b)

                rev_pred = f"related_to_{rel}"
                rev_key = f"{tgt}:{rev_pred}:{src}"
                if rev_key not in seen:
                    seen.add(rev_key)
                    b2 = self._merge({
                        "topic": tgt,
                        "predicate": rev_pred,
                        "object": src,
                        "confidence": max(0.3, edge.weight * 0.8),
                    })
                    results.append(b2)

            if results and self.brain_graph:
                for b in results:
                    self.brain_graph.add_belief_node(
                        topic=b.topic,
                        predicate=b.predicate,
                        object_val=b.object,
                        confidence=b.confidence,
                        evidence_count=b.evidence_count,
                    )

            if results and self.event_bus:
                from core.event_specs import BELIEF_UPDATED, STATE_BELIEF_UPDATED
                from core.mai_message import publish_event
                publish_event(self.event_bus, BELIEF_UPDATED, {
                    "beliefs": [b.to_dict() for b in results],
                    "source": "graph_sync",
                }, source="knowledge")
                publish_event(self.event_bus, STATE_BELIEF_UPDATED, {
                    "beliefs": [b.to_dict() for b in results],
                }, source="knowledge")
            return results
        except Exception as e:
            logger.error("[BeliefEngine] Graph sync error: %s", e)
            return []

    def count(self):
        with self._lock:
            return len(self._beliefs)
