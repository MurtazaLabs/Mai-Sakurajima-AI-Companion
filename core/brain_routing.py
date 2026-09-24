import json
import logging
from typing import Optional, Any

from core.utils import TimeOfDay, UserMood

logger = logging.getLogger(__name__)


class BrainRouter:
    """Task routing decisions extracted from Brain.

    Stores a reference to the parent Brain (``_brain``) so that attributes
    mutated after construction (e.g. ``brain.reasoning_engine = X``) are
    visible without an explicit sync step.
    """

    def __init__(self, brain=None, agent=None, reasoning_engine=None,
                 thought_journal=None, tool_manager=None, tool_registry=None,
                 executor=None, emotion_getter=None, cognitive=None,
                 memory_coordinator=None, post_think_hooks=None, llm=None,
                 response_pipeline=None, event_bus=None):
        self._brain = brain
        self._agent = agent
        self._reasoning_engine = reasoning_engine
        self._thought_journal = thought_journal
        self.tool_manager = tool_manager
        self.tool_registry = tool_registry
        self.executor = executor
        self.emotion_getter = emotion_getter
        self.cognitive = cognitive
        self.memory_coordinator = memory_coordinator
        self.post_think_hooks = post_think_hooks
        self.llm = llm
        self.response_pipeline = response_pipeline
        self.event_bus = event_bus

    @property
    def reasoning_engine(self):
        if self._brain is not None:
            return self._brain.reasoning_engine
        return self._reasoning_engine

    @property
    def agent(self):
        if self._brain is not None:
            return self._brain.agent
        return self._agent

    @agent.setter
    def agent(self, value):
        self._agent = value

    @property
    def thought_journal(self):
        if self._brain is not None:
            return self._brain.thought_journal
        return self._thought_journal

    @thought_journal.setter
    def thought_journal(self, value):
        self._thought_journal = value

    def is_complex_task(self, user_input):
        if not self.agent and not self.reasoning_engine:
            return False
        t = user_input.lower().strip()
        complex_patterns = ["research", "investigate", "find out", "look into",
                            "multi-step", "do several", "in order to"]
        for pat in complex_patterns:
            if pat in t:
                return True
        return False

    def is_analytical_query(self, user_input):
        if not self.reasoning_engine:
            return False
        t = user_input.lower().strip()
        analytical_starters = ("why", "how", "what do you think", "analyze",
                               "explain", "should i", "is it a good idea")
        for starter in analytical_starters:
            if t.startswith(starter):
                return True
        return False

    def run_reasoning(self, query):
        if not self.reasoning_engine:
            return None
        try:
            trace = self.reasoning_engine.reason(query)
            if trace and trace.conclusion:
                logger.info("[REASONING] confidence=%.2f, steps=%d", trace.confidence, len(trace.reasoning_steps))
                if self.thought_journal:
                    self.thought_journal.store(trace.to_dict())
                return trace
        except Exception as e:
            logger.error("[REASONING ERROR] %s", e)
        return None

    def delegate_to_agent(self, user_input):
        if not self.agent:
            return None
        try:
            result = self.agent.run(user_input)
            if result and result.get("success"):
                conclusion = result.get("result", {})
                if isinstance(conclusion, dict):
                    return conclusion.get("conclusion", str(conclusion))
                return str(conclusion)
        except Exception as e:
            logger.error("[AGENT ERROR] %s", e)
        return None

    def handle_agent_path(self, user_input, agent_result, system, user_id=""):
        self.cognitive.push_turn(user_input, f"[AGENT] {agent_result}")
        from core.event_specs import CONVERSATION_FINISHED, STATE_REASONING_COMPLETE
        from core.mai_message import publish_event
        publish_event(self.event_bus, CONVERSATION_FINISHED, {
            "user_input": user_input,
            "response": agent_result,
            "emotion": self.emotion_getter(),
            "mode": "agent",
        }, source="cognition")
        publish_event(self.event_bus, STATE_REASONING_COMPLETE, {
            "user_input": user_input,
            "response": agent_result,
            "mode": "agent",
        }, source="cognition")
        self.post_think_hooks(user_input, agent_result, self.memory_coordinator.get_structured())
        from core.style_filter import apply_style
        from core.brain import Brain
        generation_input = (
            f"{Brain._delimit_user_input(user_input)}\n\n"
            f"[Agent task completed — summarize the outcome naturally in your own voice]\n"
            f"{agent_result}"
        )
        raw = self.llm.generate_with_tools(system, generation_input)
        if raw is None:
            return self._fallback_response(user_input)
        raw = str(raw).strip()
        logger.debug("[LLM RAW AGENT] %s", raw)
        result = self.response_pipeline.process(
            raw, user_input, self.emotion_getter, self.cognitive,
            self.memory_coordinator, self.post_think_hooks,
            tool_registry=self.tool_registry, executor=self.executor,
            user_id=user_id,
        )
        if result.handled:
            return apply_style(result.response)
        self.memory_coordinator.after_think(user_input, f"[AGENT] {raw}", user_id=user_id)
        return apply_style(raw)

    def infer_user_mood(self, text):
        t = str(text).lower()
        sad_words = ["sad", "hurt", "cry", "lonely", "depressed"]
        if any(x in t for x in sad_words):
            return UserMood.SAD
        happy_words = ["happy", "excited", "good news", "love"]
        if any(x in t for x in happy_words):
            return UserMood.HAPPY
        angry_words = ["angry", "annoyed", "mad"]
        if any(x in t for x in angry_words):
            return UserMood.ANGRY
        return UserMood.NEUTRAL

    @staticmethod
    def time_of_day():
        from datetime import datetime
        hour = datetime.now().hour
        if hour < 6:
            return TimeOfDay.LATE_NIGHT
        if hour < 12:
            return TimeOfDay.MORNING
        if hour < 18:
            return TimeOfDay.DAY
        if hour < 22:
            return TimeOfDay.EVENING
        return TimeOfDay.NIGHT

    def _fallback_response(self, user_input):
        try:
            ctx = self.memory_coordinator.memory.get_context(limit=3) if hasattr(self.memory_coordinator, "memory") else []
            if ctx:
                last = ctx[-1] if isinstance(ctx, list) else str(ctx)
                return f"I'm having trouble connecting right now. Based on our last conversation: {last}"
        except Exception as e:
            logger.debug("Fallback response failed: %s", e)
        return "I'm having trouble connecting right now. Please try again in a moment."
