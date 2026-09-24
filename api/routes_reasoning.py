"""Reasoning domain logic for the Mai API (thoughts, reflections).

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for how this is composed.
"""
import logging
from typing import Any
from api.errors import safe_error

logger = logging.getLogger("api.server")


class ReasoningMixin:
    """Thought journal + reflection handlers."""

    # Set by MaiAPI at runtime — declared here for type checker
    thought_journal: Any = None
    reflection_engine: Any = None
    brain: Any = None

    def reasoning_thoughts(self, limit=50):
        if not self.thought_journal:
            return {"error": "thought_journal_not_available"}
        try:
            entries = self.thought_journal.recent(n=limit)
            return {"thoughts": entries, "count": self.thought_journal.count()}
        except Exception as e:
            return {"error": safe_error(e)}

    def reasoning_reflect(self):
        if not self.reflection_engine:
            return {"error": "reflection_engine_not_available"}
        try:
            memories = []
            thoughts = []
            if self.thought_journal:
                thoughts = self.thought_journal.recent(n=20)
            if hasattr(self, 'brain') and self.brain and hasattr(self.brain, 'memory'):
                try:
                    mem = self.brain.memory
                    if hasattr(mem, 'short'):
                        memories = list(mem.short)
                except Exception as e:
                    logger.exception("[Reasoning] memories: %s", e)
            reflection = self.reflection_engine.daily_reflection(
                memories=memories, thoughts=thoughts, force=True)
            result = reflection.to_dict()
            if not hasattr(self, '_reflection_history'):
                self._reflection_history = []
            self._reflection_history.append(result)
            return {"reflection": result}
        except Exception as e:
            return {"error": safe_error(e)}

    def reasoning_reflect_history(self):
        if not hasattr(self, '_reflection_history'):
            self._reflection_history = []
        return {"history": list(self._reflection_history)}
