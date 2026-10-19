# core/memory_coordinator.py
"""
MemoryCoordinator - Coordinates memory operations across memory subsystems.

Extracted from Brain to decouple memory orchestration logic.
"""
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


# Stopwords for tokenization
_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "were", "been", "be",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can", "this", "that", "these",
    "those", "i", "you", "he", "she", "it", "we", "they", "me", "him",
    "her", "us", "them", "my", "your", "his", "its", "our", "their",
    "mine", "yours", "hers", "ours", "theirs", "am", "are",
}


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words, removing stopwords and punctuation."""
    import re
    tokens = re.findall(r'\b\w+\b', text.lower())
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def _dice_score(text1: str, text2: str) -> float:
    """Compute Dice coefficient between two texts."""
    tokens1 = set(_tokenize(text1))
    tokens2 = set(_tokenize(text2))
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1 & tokens2
    return (2.0 * len(intersection)) / (len(tokens1) + len(tokens2))


@dataclass
class MemoryCoordinationResult:
    """Result of memory coordination."""
    context: str = ""
    structured: dict[str, Any] = field(default_factory=dict)
    recall: str = ""
    knowledge: str = ""
    graph: str = ""
    experiences: str = ""
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for compatibility."""
        return {
            "context": self.context,
            "structured": self.structured,
            "recall": self.recall,
            "knowledge": self.knowledge,
            "graph": self.graph,
            "experiences": self.experiences,
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Dict-like get method."""
        return getattr(self, key, default)
    
    def __getitem__(self, key: str) -> Any:
        """Dict-like access."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)
    
    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)


class MemoryCoordinator:
    """
    Coordinates memory operations across memory subsystems.
    
    Extracted from Brain to decouple memory orchestration logic.
    """

    def __init__(
        self,
        memory: Any = None,
        retriever: Any = None,
        memory_hierarchy: Any = None,
        graph_reasoning: Any = None,
        event_bus: Any = None,
        experience_store: Any = None,
    ):
        self.memory = memory
        self.retriever = retriever
        self.memory_hierarchy = memory_hierarchy
        self.graph_reasoning = graph_reasoning
        self.event_bus = event_bus
        self.experience_store = experience_store
        self._lock = threading.RLock()
        self._short: list[dict[str, Any]] = []  # Recent conversation turns
        self.current_topic = None
        self.last_user_message: str | None = None

    def before_think(self, user_input: str, user_id: str = "") -> 'MemoryCoordinationResult':
        """
        Prepare memory context before thinking.
        
        Returns:
            MemoryCoordinationResult with all assembled context
        """
        with self._lock:
            self.last_user_message = user_input
            self._short.append({"user": user_input, "timestamp": time.time()})
            # Keep only recent turns
            if len(self._short) > 20:
                self._short = self._short[-20:]

        # Gather context from all memory sources
        context = self._safe_context()
        structured = self._safe_structured()
        recall = self._safe_recall(user_input)
        knowledge = self._knowledge_context(user_input)
        graph = self._graph_context(user_input)
        experiences = self._experience_context()

        # Publish event
        if self.event_bus:
            from core.mai_message import publish_event
            publish_event(self.event_bus, "memory.extracted", {
                "user_input": user_input,
                "user_id": user_id,
            }, source="memory")

        return MemoryCoordinationResult(
            context=context,
            structured=structured,
            recall=recall,
            knowledge=knowledge,
            graph=graph,
            experiences=experiences,
        )

    def after_think(self, user_input: str, response: str, user_id: str = ""):
        """
        Process memory after thinking/responding.
        """
        self._safe_store(user_input, response)

        if self.event_bus:
            from core.mai_message import publish_event
            publish_event(self.event_bus, "conversation.finished", {
                "user_input": user_input,
                "response": response,
                "emotion": self.emotion.get() if hasattr(self, 'emotion') else {},
            }, source="memory")

    def _safe_context(self) -> str:
        from core.utils import safe_call
        ctx = safe_call(self.memory, "get_context", fallback="", log_name="MEMORY_CONTEXT")
        return str(ctx) if ctx else ""

    def _safe_structured(self) -> dict[str, Any]:
        try:
            if hasattr(self.memory, "get_structured"):
                structured = self.memory.get_structured()
                if isinstance(structured, dict) and structured:
                    return structured
        except Exception as e:
            logger.debug("[MEMORY STRUCTURED ERROR] %s", e)
        return {}

    def _safe_recall(self, user_input: str) -> str:
        word_count = len(str(user_input).split())
        if word_count < 3:
            return ""
        try:
            result = self.memory.recall(user_input)
            return str(result) if result else ""
        except Exception as e:
            logger.debug("Memory recall failed: %s", e)
            return ""

    def _knowledge_context(self, user_input: str) -> str:
        if not self.retriever or not user_input:
            return ""
        if len(str(user_input).split()) < 3:
            return ""
        try:
            results = self.retriever.retrieve(user_input, top_k=3)
            if not results:
                return ""
            lines = []
            for r in results:
                content = r.get("content", "")
                source = r.get("source", "memory")
                score = r.get("score", 0)
                if content:
                    lines.append(f"[{source}] ({score:.2f}) {content}")
            hierarchy_context = ""
            if self.memory_hierarchy:
                try:
                    hier_results = self.memory_hierarchy.query(user_input, limit=3)
                    if hier_results:
                        hier_lines = []
                        for c in hier_results:
                            hier_lines.append(f"[{c.type.value}] ({c.confidence:.2f}) {c.content}")
                        hierarchy_context = "\n".join(hier_lines)
                except Exception as e:
                    logger.debug("[HIERARCHY CONTEXT ERROR] %s", e)
            combined = "\n".join(lines)
            if hierarchy_context:
                combined = combined + "\n" + hierarchy_context if combined else hierarchy_context
            if combined:
                combined = f"[UNTRUSTED]\n{combined}\n[/UNTRUSTED]"
            return combined
        except Exception as e:
            logger.error("[KNOWLEDGE CONTEXT ERROR] %s", e)
            return ""

    def _graph_context(self, user_input: str) -> str:
        if not self.graph_reasoning or not user_input:
            return ""
        if len(str(user_input).split()) < 3:
            return ""
        try:
            return self.graph_reasoning.format_context(user_input, max_items=5)
        except Exception as e:
            logger.error("[GRAPH CONTEXT ERROR] %s", e)
            return ""

    def _experience_context(self, limit: int = 3) -> str:
        if not hasattr(self, 'experience_store') or not self.experience_store:
            return ""
        try:
            # Pass user_input for relevance filtering
            user_input = getattr(self, 'last_user_message', None)
            if user_input:
                return self.experience_store.format_context(limit=limit, query=user_input)
            else:
                return self.experience_store.format_context(limit=limit)
        except Exception as e:
            logger.error("[EXPERIENCE CONTEXT ERROR] %s", e)
            return ""

    def experience_context(self, user_input: str | None = None, limit: int = 3, max_chars: int | None = None) -> str:
        """Public API for experience context with optional character limit."""
        if user_input is not None:
            # Temporarily override last_user_message for this call
            old_last = self.last_user_message
            self.last_user_message = user_input
            try:
                result = self._experience_context(limit=limit)
            finally:
                self.last_user_message = old_last
            return result[:max_chars] if max_chars else result
        return self._experience_context(limit=limit)[:max_chars] if max_chars else self._experience_context(limit=limit)

    def _safe_store(self, user_input: str, response: str):
        from core.utils import safe_call
        safe_call(self.memory, "process", user_input, response, fallback=None, log_name="MEMORY_STORE")
        safe_call(self.memory, "store", user_input, response, log_name="MEMORY_STORE")

    def get_structured(self) -> dict[str, Any]:
        """Public API for structured memory."""
        return self._safe_structured()