import logging

from app.config_loader import CHARACTER_MONOLOGUE_ENABLED, LLM_MAX_CONTEXT
from core.prompt_builder import build_system_prompt

logger = logging.getLogger(__name__)


class PromptOrchestrator:

    def __init__(self, brain):
        self._brain = brain

    def build(self, user_input, memory_data=None, identity_data=None, monologue=None):
        brain = self._brain

        if memory_data:
            context = memory_data.get("context", "")
            structured = memory_data.get("structured", {})
            recall_text = memory_data.get("recall", "")
            knowledge_text = memory_data.get("knowledge", "")
            graph_text = memory_data.get("graph", "")
            experiences_text = memory_data.get("experiences", "")
        else:
            context = brain._safe_context()
            structured = brain._safe_structured()
            recall_text = brain._safe_recall(user_input)
            knowledge_text = brain._knowledge_context(user_input)
            graph_text = brain._graph_context(user_input)
            experiences_text = brain._experience_context()

        if identity_data is None:
            try:
                candidate = brain._identity_data()
                if isinstance(candidate, dict) and "identity" in candidate:
                    identity_data = candidate
            except Exception as e:
                logger.debug("[PromptOrchestrator] identity_data fallback failed: %s", e)

        structured_notes = structured.get("system", {})
        system_notes_str = str(structured_notes) if structured_notes else None

        try:
            with brain.state.lock:
                live_relationship = brain.state.relationship_scores.model_dump()
                # Sync persisted emotion state into the live Emotion object's
                # internal dict (its source of truth) — NOT via setattr, which
                # would create unused attributes and bypass the real state.
                if hasattr(brain.emotion, "state") and isinstance(brain.emotion.state, dict):
                    for k, v in brain.state.emotion.model_dump().items():
                        try:
                            brain.emotion.state[k] = float(v)
                        except (TypeError, ValueError):
                            brain.emotion.state[k] = v

            brain.personality_state.update_from_relationship(live_relationship)
            brain.personality_state.update_from_preferences(structured.get("preferences", {}))
            brain.personality_state.update_from_reflections(structured.get("reflections", {}))
        except Exception as e:
            logger.error("[PERSONALITY STATE ERROR] %s", e)

        personality_dynamic = brain.personality_state.get()

        with brain.state.lock:
            emotion_export = brain.state.emotion.model_dump()
            mood = brain.emotion.get()

        context_state = {
            "time_of_day": brain._time_of_day(),
            "user_mood": brain._infer_user_mood(user_input),
        }

        behavior_rules = brain.behavior.build(
            structured=structured,
            emotion=emotion_export,
            context=context_state,
        )

        tool_defs = brain._tool_defs_for_prompt()

        cognitive_export = brain.cognitive.get()

        if brain.thought_journal:
            recent = brain.thought_journal.recent(5)
            cognitive_export["recent_thoughts"] = [
                {"query": t.get("query", ""), "conclusion": t.get("conclusion", "")}
                for t in recent
            ]

        if brain.goal_manager:
            active = brain.goal_manager.list(status="active")
            if active:
                cognitive_export["current_goal"] = active[0].description
                cognitive_export["active_task"] = active[0].description

        if brain.state:
            with brain.state.lock:
                cognitive_export["current_speaker"] = brain.state.runtime.current_speaker_name or ""

        system = build_system_prompt(
            context=context,
            emotion=mood,
            behavior=behavior_rules,
            personality=personality_dynamic,
            relationship=str(live_relationship) if live_relationship else None,
            recall=recall_text,
            knowledge=knowledge_text,
            graph=graph_text,
            experiences=experiences_text or None,
            tool_defs=tool_defs,
            system_notes=system_notes_str,
            cognitive_state=cognitive_export,
            identity_data=identity_data,
            monologue_enabled=bool(CHARACTER_MONOLOGUE_ENABLED) if monologue is None else bool(monologue),
        )

        MAX_SYSTEM_CHARS = int(LLM_MAX_CONTEXT * 0.5 * 4)
        if len(system) > MAX_SYSTEM_CHARS:
            marker = "\n\nRELEVANT MEMORIES"
            if marker in system:
                parts = system.split(marker)
                system = parts[0] + marker + "\n[Memories trimmed for length]"
            if len(system) > MAX_SYSTEM_CHARS:
                system = system[:MAX_SYSTEM_CHARS]

        return system
