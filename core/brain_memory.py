import logging
from core.utils import safe_call, safe_attr

logger = logging.getLogger(__name__)


class BrainMemory:
    """Memory lifecycle helpers extracted from Brain.

    Stores a reference to the parent Brain (``_brain``) so that attributes
    mutated after construction (e.g. ``brain.retriever = X``) are visible.
    """

    def __init__(self, brain=None, memory=None, retriever=None,
                 memory_hierarchy=None, graph_reasoning=None):
        self._brain = brain
        self._memory = memory
        self._retriever = retriever
        self._memory_hierarchy = memory_hierarchy
        self._graph_reasoning = graph_reasoning

    @property
    def memory(self):
        if self._brain is not None:
            return self._brain.memory
        return self._memory

    @property
    def retriever(self):
        if self._brain is not None:
            return self._brain.retriever
        return self._retriever

    @property
    def memory_hierarchy(self):
        if self._brain is not None:
            return self._brain.memory_hierarchy
        return self._memory_hierarchy

    @property
    def graph_reasoning(self):
        if self._brain is not None:
            return self._brain.graph_reasoning
        return self._graph_reasoning

    def safe_context(self):
        ctx = safe_call(self.memory, "get_context", fallback="", log_name="MEMORY_CONTEXT")
        if not ctx:
            return ""
        return str(ctx)

    def safe_structured(self):
        try:
            if hasattr(self.memory, "get_structured"):
                structured = self.memory.get_structured()
                if isinstance(structured, dict) and structured:
                    return structured
        except Exception as e:
            logger.debug("[MEMORY STRUCTURED ERROR] %s", e)
        reader = safe_attr(self.memory, "reader", fallback=None)
        if reader is not None:
            reader_data = safe_call(reader, "get_all", fallback=None, log_name="MEMORY_READER")
            if isinstance(reader_data, dict):
                return reader_data
        return {}

    def safe_recall(self, user_input):
        word_count = len(str(user_input).split())
        if word_count < 3:
            return ""
        try:
            result = self.memory.recall(user_input)
            if result is None:
                return ""
            return str(result)
        except Exception as e:
            logger.debug("Memory recall failed: %s", e)
            return ""

    def safe_store(self, user_input, response):
        stored = safe_call(self.memory, "process", user_input, response, fallback=None, log_name="MEMORY_STORE")
        if stored is not None:
            return
        safe_call(self.memory, "store", user_input, response, log_name="MEMORY_STORE")

    def knowledge_context(self, user_input):
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

    def graph_context(self, user_input):
        if not self.graph_reasoning or not user_input:
            return ""
        if len(str(user_input).split()) < 3:
            return ""
        try:
            return self.graph_reasoning.format_context(user_input, max_items=5)
        except Exception as e:
            logger.error("[GRAPH CONTEXT ERROR] %s", e)
            return ""
