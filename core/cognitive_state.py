# core/cognitive_state.py
import logging
import threading
import time

logger = logging.getLogger(__name__)


class CognitiveState:

    def __init__(self):
        self.lock = threading.RLock()

        self.current_topic = ""
        self.attention_focus = ""
        self.emotion = {
            "type": "neutral",
            "intensity": 0.5,
            "valence": 0.5,
        }
        self.working_memory = []
        self.current_goal = None
        self.current_reasoning = ""
        self.current_speaker = ""
        self.active_task = ""
        self.conversation_intent = ""
        self.confidence = 0.5
        self.current_thought = None
        self.recent_thoughts = []
        self.conversation_state = {
            "turn_count": 0,
            "session_duration": 0.0,
            "user_mood": "neutral",
        }

    def get(self):
        with self.lock:
            return {
                "current_topic": self.current_topic,
                "attention_focus": self.attention_focus,
                "emotion": dict(self.emotion),
                "working_memory": list(self.working_memory),
                "current_goal": self.current_goal,
                "current_reasoning": self.current_reasoning,
                "current_speaker": self.current_speaker,
                "active_task": self.active_task,
                "conversation_intent": self.conversation_intent,
                "confidence": self.confidence,
                "current_thought": self.current_thought,
                "recent_thoughts": list(self.recent_thoughts),
                "conversation_state": dict(self.conversation_state),
            }

    def update(self, **kwargs):
        with self.lock:
            for key, value in kwargs.items():
                if key == "conversation_state" and isinstance(value, dict):
                    self.conversation_state.update(value)
                elif key == "emotion" and isinstance(value, dict):
                    self.emotion.update(value)
                elif key == "working_memory" and isinstance(value, list):
                    self.working_memory = value[-5:]
                elif key == "recent_thoughts" and isinstance(value, list):
                    self.recent_thoughts = value[-10:]
                elif hasattr(self, key):
                    current = getattr(self, key, None)
                    # Preserve the declared attribute's type; reject mismatched
                    # types so dynamic setattr can't corrupt state shape.
                    if isinstance(value, type(current)) or (
                        current is None and not isinstance(value, dict)
                    ):
                        if isinstance(current, float) and isinstance(value, (int, float)):
                            setattr(self, key, max(0.0, min(1.0, float(value))))
                        else:
                            setattr(self, key, value)

    def push_turn(self, user_message, ai_message):
        with self.lock:
            self.conversation_state["turn_count"] += 1
            turn = {
                "role": "user",
                "content": str(user_message),
                "timestamp": time.time(),
            }
            self.working_memory.append(turn)
            turn = {
                "role": "assistant",
                "content": str(ai_message),
                "timestamp": time.time(),
            }
            self.working_memory.append(turn)
            self.working_memory = self.working_memory[-5:]
