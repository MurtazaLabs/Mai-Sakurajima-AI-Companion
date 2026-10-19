# reasoning/engine.py
import logging
import time

logger = logging.getLogger(__name__)


class ReasoningTrace:

    def __init__(self, query, evidence=None, known=None, unknowns=None,
                 steps=None, confidence=0.5, conclusion=""):
        self.query = str(query).strip()
        self.retrieved_evidence = list(evidence or [])
        self.known_facts = list(known or [])
        self.unknowns = list(unknowns or [])
        self.reasoning_steps = list(steps or [])
        self.confidence = max(0.0, min(1.0, float(confidence)))
        self.conclusion = str(conclusion).strip()
        self.timestamp = time.time()

    def to_dict(self):
        return {
            "query": self.query,
            "retrieved_evidence": list(self.retrieved_evidence),
            "known_facts": list(self.known_facts),
            "unknowns": list(self.unknowns),
            "reasoning_steps": list(self.reasoning_steps),
            "confidence": self.confidence,
            "conclusion": self.conclusion,
            "timestamp": self.timestamp,
        }


class ReasoningEngine:

    def __init__(self, retriever=None, journal=None, event_bus=None):
        self.retriever = retriever
        self.journal = journal
        self.event_bus = event_bus

    def reason(self, query, context=None):
        if not query:
            return ReasoningTrace(query="", conclusion="No query provided.", confidence=0.0)

        query = str(query).strip()
        context = context or {}

        evidence = self._retrieve_evidence(query, context)

        known_facts = self._extract_known(evidence)
        unknowns = self._identify_unknowns(query, known_facts)

        steps = self._build_steps(query, known_facts, unknowns)
        confidence = self._compute_confidence(evidence, steps, unknowns)
        conclusion = self._build_conclusion(query, known_facts, steps, confidence)

        trace = ReasoningTrace(
            query=query,
            evidence=evidence,
            known=known_facts,
            unknowns=unknowns,
            steps=steps,
            confidence=confidence,
            conclusion=conclusion,
        )

        if self.journal:
            self.journal.store(trace.to_dict())

        if self.event_bus:
            from core.event_specs import REASONING_COMPLETED
            from core.mai_message import publish_event
            publish_event(self.event_bus, REASONING_COMPLETED, {
                "query": query,
                "confidence": confidence,
                "step_count": len(steps),
            }, source="reasoning")

        return trace

    def _retrieve_evidence(self, query, context):
        evidence = []
        if self.retriever:
            try:
                results = self.retriever.retrieve(
                    query,
                    attention_focus=context.get("attention_focus"),
                    top_k=5,
                )
                for r in results:
                    evidence.append({
                        "content": r.get("content", ""),
                        "source": r.get("source", "unknown"),
                        "score": r.get("score", 0.5),
                    })
            except Exception as e:
                logger.error("[ReasoningEngine] Retrieve error: %s", e)

        return evidence

    def _extract_known(self, evidence):
        known = []
        for e in evidence:
            content = e.get("content", "").strip()
            if content and content not in known:
                known.append(content)
        return known[:8]

    def _identify_unknowns(self, query, known):
        unknowns = []
        question_words = {"what", "why", "how", "when", "where", "who", "which"}

        words = query.lower().split()
        for w in words:
            if w in question_words:
                topic = query.lower().replace(w, "").strip().rstrip("?").strip()
                if topic and not any(topic in k.lower() for k in known):
                    unknowns.append(f"I don't have direct evidence about {topic}.")
                break

        return unknowns

    def _build_steps(self, query, known, unknowns):
        steps = []

        if known:
            steps.append(f"Retrieved {len(known)} pieces of evidence.")
            for i, k in enumerate(known[:3], 1):
                steps.append(f"Evidence {i}: {k[:80]}")
        else:
            steps.append("No direct evidence found in memory or knowledge.")

        if unknowns:
            for u in unknowns:
                steps.append(f"Gap: {u}")

        if known and not unknowns:
            steps.append("Evidence appears sufficient to form a conclusion.")
        elif known:
            steps.append("Partial evidence available. Confidence is limited.")

        return steps

    def _compute_confidence(self, evidence, steps, unknowns):
        if not evidence:
            return 0.1

        avg_score = sum(
            e.get("score", 0.5) for e in evidence
        ) / len(evidence)

        gap_penalty = 0.2 * len(unknowns)

        step_quality = min(1.0, len(steps) * 0.15)

        confidence = avg_score * 0.6 + step_quality * 0.4 - gap_penalty
        return max(0.0, min(1.0, confidence))

    def _build_conclusion(self, query, known, steps, confidence):
        if not known:
            return (
                f"I don't have enough information to answer '{query}'. "
                "I'd need to learn more about this."
            )

        conclusion_parts = ["Based on what I know:"]
        for k in known[:2]:
            conclusion_parts.append(f"- {k[:100]}")

        if confidence > 0.7:
            conclusion_parts.append("I'm fairly confident about this.")
        elif confidence > 0.4:
            conclusion_parts.append("I have some evidence but I'm not completely sure.")
        else:
            conclusion_parts.append("This is based on limited evidence.")

        return " ".join(conclusion_parts)
