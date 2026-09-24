# core/style_filter.py
import random
import re
import threading

from core.identity.speech import SPEECH


class StyleFilter:
    def __init__(self):
        self._lock = threading.RLock()
        self.recent_suffixes = []
        self.speech_rules = SPEECH["style"]

    # 🎭 MAIN STYLE PASS
    def apply_style(
        self,
        text,
        personality=None,
        emotion=None,
        context=None
    ):

        if not text:
            return text

        if personality is None:
            personality = {}

        if emotion is None:
            emotion = {}

        if context is None:
            context = {}

        text = text.strip()

        # 🧠 sentence-aware processing
        sentences = self._split_sentences(text)

        styled = []

        for sentence in sentences:

            sentence = self._soften_directness(
                sentence,
                personality
            )

            sentence = self._add_natural_pauses(
                sentence,
                personality,
                emotion
            )

            styled.append(sentence)

        text = " ".join(styled)

        # 😏 teasing
        text = self._inject_teasing(
            text,
            personality,
            emotion,
            context
        )

        # 🌙 soft finish
        text = self._soft_finish(
            text,
            personality,
            emotion
        )

        return text.strip()

    # ✂️ sentence splitting
    def _split_sentences(self, text):

        parts = re.split(
            r'(?<=[.!?])\s+',
            text
        )

        return [
            p.strip()
            for p in parts
            if p.strip()
        ]

    # 🧠 soften directness
    def _soften_directness(
        self,
        text,
        personality
    ):

        directness = personality.get(
            "directness",
            0.5
        )

        if directness > 0.75:
            return text

        concise_mode = any(
            "Concise" in r
            for r in self.speech_rules
        )

        replacements = {
            r"\bI think\b": "It seems",
            r"\bI understand\b": "I see",
            r"\bYou should\b": "You might want to",
            r"\bYes\b": "…yes",
            r"\bNo\b": "…no"
        }

        soften_chance = 0.3 if concise_mode else 0.6

        for pattern, replacement in replacements.items():

            if random.random() < soften_chance:

                text = re.sub(
                    pattern,
                    replacement,
                    text
                )

        return text

    # 🌫️ pauses
    def _add_natural_pauses(
        self,
        text,
        personality,
        emotion
    ):

        warmth = personality.get(
            "warmth",
            0.5
        )

        affection = emotion.get(
            "affection",
            0.3
        )

        chance = (
            0.15 +
            warmth * 0.15 +
            affection * 0.15
        )

        if (
            random.random() < chance and
            not text.startswith("...")
        ):

            text = "... " + text

        return text

    # 😏 teasing
    def _inject_teasing(
        self,
        text,
        personality,
        emotion,
        context
    ):

        teasing = personality.get(
            "teasing",
            0.3
        )

        affection = emotion.get(
            "affection",
            0.3
        )

        serious = context.get(
            "serious_mode",
            False
        )

        adapts_tone = any(
            "Adapts tone" in r
            for r in self.speech_rules
        )

        if serious and adapts_tone:
            return text

        chance = (
            teasing * 0.2 +
            affection * 0.1
        )

        if adapts_tone and serious:
            chance *= 0.3

        if random.random() > chance:
            return text

        teasing_lines = [
            "You're a little predictable.",
            "You really do overthink things sometimes.",
            "Hm. You're easy to read lately.",
            "You always make that face when you're thinking."
        ]

        with self._lock:
            available = [
                t for t in teasing_lines
                if t not in self.recent_suffixes
            ]

            if not available:
                self.recent_suffixes.clear()
                available = teasing_lines

            selected = random.choice(available)

            self.recent_suffixes.append(selected)

        return f"{text} {selected}"

    # 🌙 endings
    def _soft_finish(
        self,
        text,
        personality,
        emotion
    ):

        warmth = personality.get(
            "warmth",
            0.5
        )

        affection = emotion.get(
            "affection",
            0.3
        )

        chance = (
            warmth * 0.1 +
            affection * 0.15
        )

        if random.random() > chance:
            return text

        endings = [
            "...just saying.",
            "...that's all.",
            "...if that matters.",
            "...not that you'd admit it."
        ]

        with self._lock:
            available = [
                e for e in endings
                if e not in self.recent_suffixes
            ]

            if not available:
                self.recent_suffixes.clear()
                available = endings

            selected = random.choice(available)

            self.recent_suffixes.append(selected)

        return f"{text} {selected}"


# ✅ GLOBAL INSTANCE
_style_filter = StyleFilter()


# ✅ COMPATIBILITY FUNCTION
def apply_style(
    text,
    personality=None,
    emotion=None,
    context=None
):
    return _style_filter.apply_style(
        text,
        personality,
        emotion,
        context
    )