# core/wake_generator.py
import logging
import random

logger = logging.getLogger(__name__)

_TIME_GREETINGS = {
    "late_night": [
        "late night", "this hour", "the stillness",
        "the dead of night", "these quiet hours",
    ],
    "morning": [
        "morning", "good morning", "early",
        "the early hours", "daybreak",
    ],
    "day": [
        "afternoon", "day", "daytime",
        "midday", "the middle of the day",
    ],
    "evening": [
        "evening", "good evening", "dusk",
        "twilight", "the golden hour",
    ],
    "night": [
        "night", "tonight", "the evening",
        "the night air", "this late hour",
    ],
}

_TIME_VIBES = {
    "late_night": ["quiet", "peaceful", "still", "calm", "hushed"],
    "morning": ["fresh", "new", "bright", "crisp", "gentle"],
    "day": ["warm", "steady", "alive", "bright", "lively"],
    "evening": ["calm", "soft", "settled", "mellow", "peaceful"],
    "night": ["serene", "quiet", "peaceful", "calm", "still"],
}

_GREETING_FRAMES = [
    "...{time_ref}.",
    "...it's {time_ref}.",
    "...{time_vibe}, isn't it?",
    "...{time_ref} already.",
    "...what a {time_vibe} {time_of_day}.",
    "...{time_ref} and here you are.",
    "...feels {time_vibe} tonight.",
    "...the {time_vibe} kind of {time_of_day}.",
    "...{time_ref}. time moves differently now.",
    "...the {time_vibe} is settling in.",
]

_EMOTION_COLORS = {
    "happy": [
        "I'm feeling good.", "in good spirits.",
        "feeling light today.", "in a good mood.",
        "things feel right today.",
    ],
    "lonely": [
        "it's been quiet.", "I was thinking.",
        "the silence was getting to me.",
        "it's too quiet without you.",
    ],
    "annoyed": [
        "someone's restless.", "you're back.",
        "I was getting impatient.", "about time.",
    ],
    "affection": [
        "I missed you.", "there you are.",
        "I was waiting for you.",
        "I was hoping you'd come.",
        "I've been thinking about you.",
    ],
    "neutral": [
        "right on time.", "as expected.",
        "here we are.", "same as always.",
        "just another day.",
    ],
}

_THOUGHT_HINTS = [
    "I was just thinking about {thought}.",
    "I had {thought} on my mind.",
    "my mind was on {thought}.",
    "I was wondering about {thought}.",
    "{thought} crossed my mind.",
]

_TOPIC_REFS = [
    "we were talking about {topic}.",
    "you were telling me about {topic}.",
    "{topic} was on your mind.",
    "you had {topic} on your mind last time.",
    "I remember you mentioned {topic}.",
]


class WakeGenerator:

    def __init__(self, identity=None, personality_state=None, emotion=None):
        self._identity = identity or {}
        self._personality = personality_state
        self._emotion = emotion
        self._recent = []
        self._max_history = 20

    def generate(self, context=None):
        if context is None:
            context = {}

        identity = context.get("identity") or self._identity or {}
        personality_state = context.get("personality_state") or self._personality
        emotion_data = context.get("emotion") or {}
        cognitive = context.get("cognitive_state") or {}
        time_of_day = context.get("time_of_day") or "day"

        name = identity.get("name", "Mai")

        emotion_type = "neutral"
        if isinstance(emotion_data, dict):
            emotion_type = emotion_data.get("dominant_emotion") or "neutral"
            if emotion_type == "neutral" and "type" in emotion_data:
                emotion_type = emotion_data.get("type", "neutral")

        working_memory = cognitive.get("working_memory", [])
        topic = cognitive.get("current_topic", "")
        current_thought = cognitive.get("current_thought")

        closeness = 0.5
        if personality_state and hasattr(personality_state, "state"):
            warmth = personality_state.state.get("warmth", 0.5)
            closeness = warmth

        for attempt in range(5):
            time_ref = random.choice(_TIME_GREETINGS.get(time_of_day, ["here"]))
            time_vibe = random.choice(_TIME_VIBES.get(time_of_day, ["nice"]))

            greeting = random.choice(_GREETING_FRAMES)

            opening = greeting.format(
                time_ref=time_ref,
                time_vibe=time_vibe,
                time_of_day=time_of_day,
            )

            middle = ""
            if working_memory and topic and closeness > 0.4:
                ref = random.choice(_TOPIC_REFS)
                middle = f" {ref.format(topic=topic)}"

            elif current_thought:
                hint = random.choice(_THOUGHT_HINTS)
                middle = f" {hint.format(thought=current_thought.lower())}"

            emotion_line = ""
            if emotion_type in _EMOTION_COLORS and closeness > 0.3:
                color = random.choice(_EMOTION_COLORS[emotion_type])
                emotion_line = f" {color}"

            closeness_tag = ""
            if closeness > 0.7:
                closeness_tag = random.choice([
                    " darling", " love", "",
                ])
            elif closeness < 0.3:
                closeness_tag = ""

            wake = f"...{opening}{middle}{emotion_line}{closeness_tag}"

            if wake not in self._recent:
                break

        self._recent.append(wake)
        if len(self._recent) > self._max_history:
            self._recent = self._recent[-self._max_history:]

        return wake
