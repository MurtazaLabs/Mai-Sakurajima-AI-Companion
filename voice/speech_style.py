# Mai_ai/voice/speech_style.py
# M4 · Character speech decisions — generates a SpeechStyle from the
# character pipeline's speech_plan (ThoughtPacket) + live relationship
# context. Pure decision layer: no LLM, no TTS calls.

import logging

logger = logging.getLogger("Mai.SpeechStyle")

# Register labels are intentionally aligned with the feature-service emotion
# vocabulary so a renderer can map them 1:1 (e.g. Kokoro emotion label).
REGISTER_NEUTRAL = "neutral"
REGISTER_TEASING = "teasing"
REGISTER_SOFT = "soft"
REGISTER_WARM = "warm"
REGISTER_ANNOYED = "annoyed"
REGISTER_SAD = "sad"

PACE_FAST = 1.08
PACE_BRISK = 1.02
PACE_NORMAL = 1.0
PACE_SLOW = 0.92
PACE_RELAXED = 0.85


class SpeechStyle:

    __slots__ = ("closeness", "hesitation", "rate", "register", "sentence_length")

    def __init__(
        self,
        register=REGISTER_NEUTRAL,
        rate=PACE_NORMAL,
        hesitation="light",
        sentence_length="balanced",
        closeness=0.5,
    ):
        self.register = register if register in {
            REGISTER_NEUTRAL, REGISTER_TEASING, REGISTER_SOFT,
            REGISTER_WARM, REGISTER_ANNOYED, REGISTER_SAD,
        } else REGISTER_NEUTRAL
        self.rate = max(0.7, min(1.25, float(rate)))
        self.hesitation = hesitation if hesitation in {"none", "light", "heavy"} else "light"
        self.sentence_length = sentence_length if sentence_length in {
            "short", "balanced", "long",
        } else "balanced"
        self.closeness = max(0.0, min(1.0, float(closeness)))

    def as_dict(self):
        return {
            "register": self.register,
            "rate": self.rate,
            "hesitation": self.hesitation,
            "sentence_length": self.sentence_length,
            "closeness": self.closeness,
        }

    def __eq__(self, other):
        if not isinstance(other, SpeechStyle):
            return NotImplemented
        return self.as_dict() == other.as_dict()

    def __repr__(self):
        return f"SpeechStyle({self.as_dict()!r})"


class SpeechStylePlanner:

    """Turns a speech_plan (ThoughtPacket's optional 5-field schema) + context
    into a pure SpeechStyle. Every layer (rate, register, hesitation,
    sentence length) degrades gracefully when the model emits no plan."""

    _INTENTION_HESITATION = {
        "tease": "light",
        "reassure": "heavy",
        "apologize": "heavy",
        "comfort": "heavy",
        "explain": "none",
        "report": "none",
        "banter": "light",
    }

    _REGISTER_BY_TONE = {
        "teasing": REGISTER_TEASING,
        "playful": REGISTER_TEASING,
        "soft": REGISTER_SOFT,
        "warm": REGISTER_WARM,
        "affectionate": REGISTER_WARM,
        "annoyed": REGISTER_ANNOYED,
        "irritated": REGISTER_ANNOYED,
        "sad": REGISTER_SAD,
        "sincere": REGISTER_NEUTRAL,
        "neutral": REGISTER_NEUTRAL,
    }

    _PACE_BY_LABEL = {
        "fast": PACE_FAST,
        "brisk": PACE_BRISK,
        "neutral": PACE_NORMAL,
        "balanced": PACE_NORMAL,
        "slow": PACE_SLOW,
        "relaxed": PACE_RELAXED,
    }

    def plan(self, speech_plan=None, context=None):
        """

        :param speech_plan: dict from ThoughtPacket.speech_plan (intention,
            tone, pacing, sentence_length, register) — any subset.
        :param context: optional dict ({"closeness": float}) from the
            relationship engine; used for "distance/affect" shaping.
        :return: SpeechStyle
        """
        plan = speech_plan or {}
        ctx = context or {}
        closeness = float(ctx.get("closeness") or 0.5) or 0.5

        register = self._register_from(plan.get("register"), plan.get("tone"))
        register = self._warm_if_close(register, closeness)
        rate = self._rate_from(plan.get("pacing"))
        hesitation = self._hesitation_from(plan.get("intention"), register)
        sentence_length = plan.get("sentence_length") or "balanced"
        if sentence_length not in {"short", "balanced", "long"}:
            sentence_length = "balanced"

        return SpeechStyle(
            register=register,
            rate=rate,
            hesitation=hesitation,
            sentence_length=sentence_length,
            closeness=closeness,
        )

    def _register_from(self, register, tone):
        if register:
            return self._REGISTER_BY_TONE.get(register, REGISTER_NEUTRAL)
        if tone:
            return self._REGISTER_BY_TONE.get(tone, REGISTER_NEUTRAL)
        return REGISTER_NEUTRAL

    def _warm_if_close(self, register, closeness):
        if closeness >= 0.65 and register == REGISTER_NEUTRAL:
            return REGISTER_WARM
        return register

    def _hesitation_from(self, intention, register):
        seeded = self._INTENTION_HESITATION.get(intention or "")
        if seeded == "none":
            return "none"
        if seeded == "heavy":
            return "heavy"
        if register == REGISTER_TEASING:
            return "light"
        if register == REGISTER_SOFT or register == REGISTER_SAD:
            return "light"
        if register == REGISTER_ANNOYED:
            return "none"
        return "light"

    def _rate_from(self, pacing):
        if pacing is None:
            return PACE_NORMAL
        if isinstance(pacing, (int, float)):
            return max(0.7, min(1.25, float(pacing)))
        return self._PACE_BY_LABEL.get(str(pacing).lower(), PACE_NORMAL)