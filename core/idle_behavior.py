# core/idle_behavior.py
import logging
import random
import time

logger = logging.getLogger(__name__)


class IdleBehavior:
    def __init__(self, emotion=None):
        self.emotion = emotion

        self.last_idle_time = 0

        self.cooldown_range = (45, 120)

    # 🧠 Main idle generation
    def generate(self, cognition, context=None):
        if not cognition:
            return None

        if context is None:
            context = {}

        if not self._can_speak():
            return None

        if not self._passes_filters(cognition):
            return None

        emotion_state = self._emotion_state()

        chance = self._calculate_speak_chance(
            emotion_state,
            context
        )

        if random.random() > chance:
            return None

        message = self._transform_thought(
            cognition,
            emotion_state,
            context
        )

        if not message:
            return None

        self.last_idle_time = time.time()

        return {
            "type": "idle_speech",
            "content": message,
            "source_thought": cognition["thought"],
            "timestamp": time.time()
        }

    # ⏱️ cooldown system
    def _can_speak(self):
        now = time.time()

        required = random.randint(
            self.cooldown_range[0],
            self.cooldown_range[1]
        )

        return now - self.last_idle_time > required

    # 🚫 filter weird/repetitive thoughts
    def _passes_filters(self, cognition):
        thought = cognition.get("thought", "").lower()

        blocked = [
            "language model",
            "ai assistant",
            "system prompt",
            "i am thinking"
        ]

        for phrase in blocked:
            if phrase in thought:
                return False

        if len(thought.strip()) < 4:
            return False

        return True

    # 🎲 dynamic speech chance
    def _calculate_speak_chance(
        self,
        emotion,
        context
    ):
        base = 0.15

        lonely = emotion.get("lonely", 0.0)
        affection = emotion.get("affection", 0.0)
        energy = emotion.get("energy", 0.5)

        base += lonely * 0.25
        base += affection * 0.15
        base += energy * 0.10

        if not context.get("user_active", True):
            base -= 0.10

        if context.get("time_of_day") == "night":
            base -= 0.05

        return max(0.05, min(base, 0.7))

    # 🗣️ convert thought → natural speech
    def _transform_thought(
        self,
        cognition,
        emotion,
        context
    ):
        thought = cognition.get("thought", "")

        dominant = max(
            emotion,
            key=emotion.get
        )

        # affectionate tone
        if dominant == "affection":
            return self._soften(thought)

        # lonely tone
        if dominant == "lonely":
            return self._attention_seek(thought)

        # playful tone
        if dominant == "happy":
            return self._playful(thought)

        return self._neutral(thought)

    # 💕 styles
    def _soften(self, thought):
        return f"...{thought}"

    def _attention_seek(self, thought):
        return f"You've been quiet lately. {thought}"

    def _playful(self, thought):
        return f"Heh. {thought}"

    def _neutral(self, thought):
        return thought

    # 😊 emotion helper
    def _emotion_state(self):
        if not self.emotion:
            return {
                "happy": 0.5,
                "lonely": 0.0,
                "affection": 0.3,
                "energy": 0.5
            }
        try:
            if isinstance(self.emotion, dict):
                state = self.emotion
            else:
                raw = self.emotion.get()
                if isinstance(raw, dict) and isinstance(raw.get("state"), dict):
                    state = raw["state"]
                else:
                    raise TypeError("emotion.get() returned unexpected shape")
            return {
                "happy": float(state.get("happy", 0.5)),
                "lonely": float(state.get("lonely", 0.0)),
                "affection": float(state.get("affection", 0.3)),
                "energy": float(state.get("energy", 0.5)),
            }
        except Exception as e:
            logger.warning("[IdleBehavior] Emotion get failed: %s", e)
            return {
                "happy": 0.5,
                "lonely": 0.0,
                "affection": 0.3,
                "energy": 0.5
            }