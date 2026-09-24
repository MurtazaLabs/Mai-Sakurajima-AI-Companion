# core/prompt_coordinator.py
"""
PromptCoordinator - Builds system prompts from various context sources.

Extracted from Brain to decouple prompt construction logic.
"""
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from app.config_loader import LLM_MAX_CONTEXT, CHARACTER_MONOLOGUE_ENABLED
from core.prompt_builder import build_system_prompt
from core.identity import get_identity
from core.event_specs import STATE_REASONING_BUSY, STATE_REASONING_COMPLETE
from core.mai_message import publish_event

logger = logging.getLogger(__name__)


@dataclass
class PromptContext:
    """Container for all prompt-building context."""
    user_input: str
    user_id: str = ""
    memory_data: Optional[Dict[str, Any]] = None
    identity_data: Optional[Dict[str, Any]] = None
    monologue: Optional[bool] = None
    monologue_enabled: bool = CHARACTER_MONOLOGUE_ENABLED


@dataclass
class PromptComponents:
    """Pre-computed prompt components."""
    context: str = ""
    structured: Dict[str, Any] = field(default_factory=dict)
    recall_text: str = ""
    knowledge_text: str = ""
    graph_text: str = ""
    experiences_text: str = ""
    system_notes_str: Optional[str] = None
    identity_data: Optional[Dict[str, Any]] = None
    emotion_export: Dict[str, Any] = field(default_factory=dict)
    mood: Dict[str, Any] = field(default_factory=dict)
    personality_dynamic: Dict[str, Any] = field(default_factory=dict)
    behavior_rules: Dict[str, Any] = field(default_factory=dict)
    cognitive_export: Dict[str, Any] = field(default_factory=dict)
    tool_defs: List[Dict[str, Any]] = field(default_factory=list)
    tool_defs_str: str = ""
    system_notes_str: Optional[str] = None
    relationship_str: Optional[str] = None
    context_state: Dict[str, Any] = field(default_factory=dict)
    monologue_enabled: bool = True


class PromptCoordinator:
    """
    Builds system prompts from various context sources.
    
    Decoupled from Brain - receives all dependencies via constructor.
    """

    def __init__(
        self,
        memory: Any,
        state: Any,
        event_bus: Any,
        emotion: Any,
        personality_state: Any,
        behavior: Any,
        cognitive: Any,
        memory_coordinator: Any,
        retriever: Any,
        graph_reasoning: Any,
        tool_registry: Any,
        tool_manager: Any,
        llm: Any,
        identity_core: Optional[Any] = None,
    ):
        self.memory = memory
        self.state = state
        self.event_bus = event_bus
        self.emotion = emotion
        self.personality_state = personality_state
        self.behavior = behavior
        self.cognitive = cognitive
        self.memory_coordinator = memory_coordinator
        self.retriever = retriever
        self.graph_reasoning = graph_reasoning
        self.tool_registry = tool_registry
        self.tool_manager = tool_manager
        self.llm = llm
        self.identity_core = identity_core

    def build(self, context: PromptContext) -> str:
        """Build complete system prompt from context."""
        components = self._gather_components(context)
        system = self._assemble_prompt(components, context)
        return self._trim_system_prompt(system)

    def _gather_components(self, context: PromptContext) -> PromptComponents:
        """Gather all prompt components from various sources."""
        comps = PromptComponents()
        
        # Memory context
        if context.memory_data:
            comps.context = context.memory_data.get("context", "")
            comps.structured = context.memory_data.get("structured", {})
            comps.recall_text = context.memory_data.get("recall", "")
            comps.knowledge_text = context.memory_data.get("knowledge", "")
            comps.graph_text = context.memory_data.get("graph", "")
            comps.experiences_text = context.memory_data.get("experiences", "")
        else:
            comps.context = self._safe_context()
            comps.structured = self._safe_structured()
            comps.recall_text = self._safe_recall(context.user_input)
            comps.knowledge_text = self._knowledge_context(context.user_input)
            comps.graph_text = self._graph_context(context.user_input)
            comps.experiences_text = self._experience_context()

        # Identity data
        if context.identity_data is None:
            try:
                candidate = self._identity_data()
                if isinstance(candidate, dict) and "identity" in candidate:
                    comps.identity_data = candidate
            except Exception as e:
                logger.debug("[PromptCoordinator] identity_data fallback failed: %s", e)
        else:
            comps.identity_data = context.identity_data

        # Structured notes
        structured_notes = comps.structured.get("system", {})
        comps.system_notes_str = str(structured_notes) if structured_notes else None

        # Relationship & emotion state (requires state lock)
        with self.state.lock:
            live_relationship = self.state.relationship_scores.model_dump()
            # Sync persisted emotion state into Emotion object's internal dict
            if hasattr(self.emotion, "state") and isinstance(self.emotion.state, dict):
                for k, v in self.state.emotion.model_dump().items():
                    try:
                        self.emotion.state[k] = float(v)
                    except (TypeError, ValueError):
                        self.emotion.state[k] = v

            self.personality_state.update_from_relationship(live_relationship)
            self.personality_state.update_from_preferences(self.structured.get("preferences", {}))
            self.personality_state.update_from_reflections(self.structured.get("reflections", {}))

        comps.personality_dynamic = self.personality_state.get()

        with self.state.lock:
            comps.emotion_export = self.state.emotion.model_dump()
            comps.mood = self.emotion.get()

        # Context state
        comps.context_state = {
            "time_of_day": self._time_of_day(),
            "user_mood": self._infer_user_mood(""),  # Will be updated with actual input
        }

        # Behavior rules
        comps.behavior_rules = self.behavior.build(
            structured=comps.structured,
            emotion=comps.emotion_export,
            context=comps.context_state,
        )

        # Tool definitions
        comps.tool_defs = self._tool_defs_for_prompt()
        comps.tool_defs_str = self._format_tool_defs(comps.tool_defs)

        # Cognitive state
        comps.cognitive_export = self.cognitive.get()

        if self.thought_journal:
            recent = self.thought_journal.recent(5)
            comps.cognitive_export["recent_thoughts"] = [
                {"query": t.get("query", ""), "conclusion": t.get("conclusion", "")}
                for t in recent
            ]

        if self.goal_manager:
            active = self.goal_manager.list(status="active")
            if active:
                comps.cognitive_export["current_goal"] = active[0].description
                comps.cognitive_export["active_task"] = active[0].description

        if self.state:
            with self.state.lock:
                comps.cognitive_export["current_speaker"] = self.state.runtime.current_speaker_name or ""

        return comps

    def _assemble_prompt(self, comps: PromptComponents, context: PromptContext) -> str:
        """Assemble final system prompt using prompt_builder."""
        # Determine monologue setting
        monologue = context.monologue
        if monologue is None:
            monologue_enabled = True
        else:
            monologue_enabled = bool(monologue)

        system = build_system_prompt(
            context=comps.context,
            emotion=comps.mood,
            behavior=comps.behavior_rules,
            personality=comps.personality_dynamic,
            relationship=comps.relationship_str,
            recall=comps.recall_text,
            knowledge=comps.knowledge_text,
            graph=comps.graph_text,
            experiences=comps.experiences_text or None,
            tool_defs=comps.tool_defs,
            system_notes=comps.system_notes_str,
            cognitive_state=comps.cognitive_export,
            identity_data=comps.identity_data,
            monologue_enabled=monologue_enabled,
        )

        return system

    def _trim_system_prompt(self, system: str) -> str:
        """Trim system prompt to fit within context budget."""
        MAX_SYSTEM_CHARS = int(LLM_MAX_CONTEXT * 0.5 * 4)
        if len(system) > MAX_SYSTEM_CHARS:
            marker = "\n\nRELEVANT MEMORIES"
            if marker in system:
                parts = system.split(marker)
                system = parts[0] + marker + "\n[Memories trimmed for length]"
            if len(system) > MAX_SYSTEM_CHARS:
                system = system[:MAX_SYSTEM_CHARS]
        return system

    # --- Helper methods (delegated from Brain) ---

    def _safe_context(self) -> str:
        from core.utils import safe_call
        ctx = safe_call(self.memory, "get_context", fallback="", log_name="MEMORY_CONTEXT")
        return str(ctx) if ctx else ""

    def _safe_structured(self) -> Dict[str, Any]:
        try:
            if hasattr(self.memory, "get_structured"):
                structured = self.memory.get_structured()
                if isinstance(structured, dict) and structured:
                    return structured
        except Exception as e:
            logger.debug("[MEMORY STRUCTURED ERROR] %s", e)
        return {}

    def _safe_recall(self, user_input: str) -> str:
        from core.utils import safe_call
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
            # Add hierarchy context
            hierarchy_context = ""
            if self.graph_reasoning:
                try:
                    hier_results = self.graph_reasoning.query(query, limit=3)
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

    def _experience_context(self) -> str:
        if not hasattr(self, 'experience_store') or not self.experience_store:
            return ""
        try:
            return self.experience_store.format_context(limit=3)
        except Exception as e:
            logger.error("[EXPERIENCE CONTEXT ERROR] %s", e)
            return ""

    def _identity_data(self) -> Optional[Dict[str, Any]]:
        identity_core = getattr(self, "identity_core", None)
        if identity_core is not None:
            try:
                data = identity_core.get_current_identity()
                if isinstance(data, dict) and "identity" in data:
                    return data
            except Exception as exc:
                logger.debug("[PromptCoordinator] identity_core query failed, falling back: %s", exc)
        return get_identity()

    def _time_of_day(self):
        from core.brain_router import BrainRouter
        return BrainRouter.time_of_day()

    def _infer_user_mood(self, text: str):
        from core.brain_router import BrainRouter
        return BrainRouter.infer_user_mood(text)

    def _tool_defs_for_prompt(self):
        from core.tool_manager import ToolManager
        return self.tool_manager.definitions_for_prompt() if self.tool_manager else []

    def _format_tool_defs(self, tool_defs):
        # Simple formatting for prompt
        return "\n".join([f"- {t.get('name', '')}: {t.get('description', '')}" for t in tool_defs])

    def _safe_recall(self, user_input: str) -> str:
        return self._safe_recall(user_input)

    def _safe_context(self) -> str:
        return self._safe_context()

    def _safe_structured(self) -> Dict[str, Any]:
        return self._safe_structured()

    # Properties for external dependencies (set by BrainFacade)
    thought_journal: Optional[Any] = None
    goal_manager: Optional[Any] = None
    graph_reasoning: Optional[Any] = None