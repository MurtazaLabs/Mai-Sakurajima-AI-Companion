import logging
import threading
import time

logger = logging.getLogger(__name__)


class ProceduralRule:

    def __init__(self, rule, context, confidence=0.5, source="experience"):
        self.rule = str(rule).strip()
        self.context = str(context).strip().lower()
        self.confidence = max(0.0, min(1.0, float(confidence)))
        self.source = str(source)
        self.created_at = time.time()
        self.last_applied = 0.0
        self.apply_count = 0

    def to_dict(self):
        return {
            "rule": self.rule,
            "context": self.context,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at,
            "last_applied": self.last_applied,
            "apply_count": self.apply_count,
        }


class ProceduralMemory:
    """Store, retrieve, and reinforce procedural rules learned from experience.

    Supports deduplication with confidence reinforcement, cross-source retrieval
    (local + BrainGraph), apply-count tracking, and event publishing.
    """

    def __init__(self, event_bus=None, brain_graph=None):
        self._lock = threading.RLock()
        self._rules = []
        self.event_bus = event_bus
        self.brain_graph = brain_graph

    def learn(self, rule, context, confidence=0.5, source="experience"):
        if not rule or not context:
            return None
        with self._lock:
            existing = self._find(rule, context)
            if existing:
                existing.confidence = min(1.0, existing.confidence + 0.1)
                existing.apply_count += 1
                logger.info("[Procedural] Reinforced rule: %s", rule[:50])
                return existing
            pr = ProceduralRule(rule, context, confidence=confidence, source=source)
            self._rules.append(pr)
        if self.brain_graph:
            self.brain_graph.add_rule_node(
                rule=pr.rule,
                context=pr.context,
                confidence=pr.confidence,
                source=pr.source,
            )
        if self.event_bus:
            from core.event_specs import PROCEDURAL_LEARNED
            from core.mai_message import publish_event
            publish_event(self.event_bus, PROCEDURAL_LEARNED, pr.to_dict(), source="agency")
        return pr

    def retrieve(self, context, min_confidence=0.3):
        context = str(context).strip().lower()
        matches = []
        with self._lock:
            for r in self._rules:
                if r.confidence < min_confidence:
                    continue
                if context == r.context or context in r.context or r.context in context:
                    matches.append(r)
        if self.brain_graph:
            graph_rules = self.brain_graph.get_rules(context=context, min_confidence=min_confidence)
            local_text = {r.rule for r in matches}
            for n in graph_rules:
                r_text = n.metadata.get("rule", "")
                if r_text and r_text not in local_text:
                    pr = ProceduralRule(
                        rule=r_text,
                        context=n.metadata.get("context", context),
                        confidence=n.metadata.get("confidence", 0.5),
                        source=n.metadata.get("source", "brain_graph"),
                    )
                    matches.append(pr)
        matches.sort(key=lambda r: r.confidence, reverse=True)
        return matches

    def _find(self, rule, context):
        for r in self._rules:
            if r.rule == rule and r.context == context:
                return r
        return None

    def apply(self, rule, context):
        with self._lock:
            for r in self._rules:
                if r.rule == rule and (context == r.context or context in r.context or r.context in context):
                    r.apply_count += 1
                    r.last_applied = time.time()
                    return True
        return False

    def list(self, min_confidence=0.0):
        with self._lock:
            return [r for r in self._rules if r.confidence >= min_confidence]

    def stats(self):
        with self._lock:
            return {
                "total": len(self._rules),
                "avg_confidence": round(sum(r.confidence for r in self._rules) / max(1, len(self._rules)), 2),
            }
