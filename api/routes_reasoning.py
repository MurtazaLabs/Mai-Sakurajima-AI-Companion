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
            return {
                "thoughts": [_public_thought(entry) for entry in entries if isinstance(entry, dict)],
                "count": self.thought_journal.count(),
            }
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
            return {"reflection": _public_reflection(result)}
        except Exception as e:
            return {"error": safe_error(e)}

    def reasoning_reflect_history(self):
        if not hasattr(self, '_reflection_history'):
            self._reflection_history = []
        return {"history": [_public_reflection(item) for item in self._reflection_history]}


def _public_text(value, limit=500):
    if value is None:
        return ""
    text = str(value).strip()
    return text[:limit]


def _public_list(value, limit=8):
    if not isinstance(value, list):
        return []
    result = []
    for item in value[:limit]:
        if isinstance(item, dict):
            text = item.get("text") or item.get("content") or item.get("summary") or item.get("description")
        else:
            text = item
        text = _public_text(text)
        if text:
            result.append(text)
    return result


def _public_thought(entry):
    confidence = entry.get("confidence")
    if not isinstance(confidence, (int, float)):
        confidence = None
    return {
        "id": _public_text(entry.get("id"), 120),
        "query": _public_text(entry.get("query") or "Reasoning trace"),
        "conclusion": _public_text(entry.get("conclusion")),
        "reasoning_steps": _public_list(entry.get("reasoning_steps")),
        "retrieved_evidence": _public_list(entry.get("retrieved_evidence")),
        "known_facts": _public_list(entry.get("known_facts")),
        "unknowns": _public_list(entry.get("unknowns")),
        "confidence": confidence,
        "timestamp": entry.get("timestamp"),
    }


def _public_reflection(item):
    if not isinstance(item, dict):
        return {}
    confidence = item.get("confidence")
    if not isinstance(confidence, (int, float)):
        confidence = None
    return {
        "period": _public_text(item.get("period") or "reflection", 32),
        "summary": _public_text(item.get("summary")),
        "patterns": _public_list(item.get("patterns")),
        "topics": _public_list(item.get("topics")),
        "confidence": confidence,
        "timestamp": item.get("timestamp"),
    }
