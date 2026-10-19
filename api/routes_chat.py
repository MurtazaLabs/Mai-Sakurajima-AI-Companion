"""Chat + wake + status domain logic for the Mai API.

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for how this is composed.
"""
import logging
from typing import Any

from api.errors import safe_error
from config.ai import WAKE_WORDS

logger = logging.getLogger("api.server")


class ChatMixin:
    """Conversation, wake-greeting, and runtime status handlers."""

    # Set by MaiAPI at runtime — declared here for type checker
    _ready: bool = False
    brain: Any = None
    goal_manager: Any = None
    world_model: Any = None
    dream_engine: Any = None
    _last_dream_report: dict = {}

    def chat(self, message, _stream=False, user_id=""):
        if not self._ready or not self.brain:
            return {"error": "system_not_ready"}
        try:
            msg_lower = message.strip().lower()
            is_wake = any(ww in msg_lower for ww in WAKE_WORDS)
            if is_wake:
                return self._do_wake_greeting()
            response = self.brain.think(message, user_id=user_id)
            return {"response": str(response), "status": "ok"}
        except Exception as e:
            logger.error("[API] Chat error: %s", e)
            return {"error": safe_error(e)}

    def chat_wake(self):
        if not self._ready or not self.brain:
            return {"error": "system_not_ready"}
        try:
            return self._do_wake_greeting()
        except Exception as e:
            logger.error("[API] Wake greeting error: %s", e)
            return {"error": safe_error(e)}

    def _do_wake_greeting(self):
        from core.wake_generator import WakeGenerator

        brain = self.brain
        identity = {}
        try:
            from app.config_loader import AI_NAME, AI_PERSONALITY
            identity = {"name": AI_NAME, "personality": AI_PERSONALITY}
        except Exception as e:
            logger.exception("[Chat] identity: %s", e)
        wg = WakeGenerator(
            identity=identity,
            personality_state=brain.personality_state if hasattr(brain, "personality_state") else None,
            emotion=brain.emotion if hasattr(brain, "emotion") else None,
        )
        context = {
            "identity": identity,
            "personality_state": brain.personality_state if hasattr(brain, "personality_state") else None,
            "emotion": brain.emotion.get() if hasattr(brain, "emotion") and hasattr(brain.emotion, "get") else {},
            "cognitive_state": brain.cognitive.get() if hasattr(brain, "cognitive") and hasattr(brain.cognitive, "get") else {},
            "time_of_day": "day",
        }
        try:
            if hasattr(brain, "_time_of_day"):
                context["time_of_day"] = brain._time_of_day()
        except Exception as e:
            logger.exception("[Chat] time_of_day: %s", e)
        greeting = wg.generate(context=context)
        return {"response": greeting, "status": "ok", "wake": True}

    def status(self):
        if not self._ready:
            return {"ready": False}
        info: dict = {"ready": True}
        try:
            if self.brain:
                info["emotion"] = self.brain.emotion.get() if hasattr(self.brain, "emotion") else {}
        except Exception as e:
            logger.exception("[Status] emotion: %s", e)
        try:
            if self.goal_manager:
                info["goals"] = self.goal_manager.stats()
        except Exception as e:
            logger.exception("[Status] goals: %s", e)
        try:
            if self.world_model:
                info["world"] = self.world_model.stats()
        except Exception as e:
            logger.exception("[Status] world: %s", e)
        try:
            if self.dream_engine:
                info["dream"] = {
                    "is_dreaming": bool(getattr(self.dream_engine, "is_dreaming", False)),
                    "last_report": self._last_dream_report,
                }
        except Exception as e:
            logger.exception("[Status] dream: %s", e)
        return info

    def _on_dream_completed(self, data=None):
        try:
            data = data or {}
            self._last_dream_report = {
                "level": data.get("level"),
                "duration": data.get("duration"),
                "tasks": data.get("tasks", []),
                "errors": data.get("errors", []),
            }
        except Exception as e:
            logger.exception("[Chat] dream completed: %s", e)
