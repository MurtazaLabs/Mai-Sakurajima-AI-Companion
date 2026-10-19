# Mai_ai/voice/prosody.py
# M4 · ProsodyPlanner — applies a SpeechStyle to the spoken text. Pure text
# layer: inserts pause/hesitation punctuation, trims to the target sentence
# length, and normalizes spacing. No TTS, no LLM.

import logging
import re

logger = logging.getLogger("Mai.Prosody")

_WS = re.compile(r"\s+")
_SPLITTERS = re.compile(r"(?<=[.!?…])\s+")


class ProsodyPlan:

    __slots__ = ("pause_points", "rate", "sentence_length", "text")

    def __init__(self, text, pause_points=0, rate=1.0, sentence_length="balanced"):
        self.text = text
        self.pause_points = pause_points
        self.rate = rate
        self.sentence_length = sentence_length

    def as_dict(self):
        return {
            "text": self.text,
            "pause_points": self.pause_points,
            "rate": self.rate,
            "sentence_length": self.sentence_length,
        }


def _sentences(text):
    parts = [p.strip() for p in _SPLITTERS.split(text)]
    return [p for p in parts if p]


class ProsodyPlanner:

    def plan(self, text, style):
        if not text:
            return ProsodyPlan("", rate=style.rate, sentence_length=style.sentence_length)

        text = _WS.sub(" ", text.strip())
        sentences = _sentences(text)
        if not sentences:
            sentences = [text]

        text = self._apply_length(sentences, style)
        text = self._apply_hesitation(text, style.hesitation)

        return ProsodyPlan(
            text=text,
            pause_points=text.count("…"),
            rate=style.rate,
            sentence_length=style.sentence_length,
        )

    def _apply_length(self, sentences, style):
        target = {"short": 12, "balanced": 28, "long": 60}[style.sentence_length]
        out = []
        for sentence in sentences:
            pieces = self._split_to(sentence, target)
            out.extend(pieces)
        # Join short/long style:
        if style.sentence_length == "long":
            return " ".join(out)
        return " ".join(out)

    def _split_to(self, sentence, target):
        words = sentence.split()
        if len(words) <= target:
            return [sentence]
        chunks, chunk, count = [], [], 0
        for word in words:
            chunk.append(word)
            count += 1
            if count >= target:
                count = 0
                chunks.append(" ".join(chunk))
                chunk = []
        if chunk:
            chunks.append(" ".join(chunk))
        return chunks

    def _apply_hesitation(self, text, hesitation):
        if hesitation == "none":
            return text
        if hesitation == "heavy":
            text = re.sub(r"(?<=[.!?…])\s+(?=[A-Z])", "\u2026 ", text)
            return text.replace(" but ", "… but ").replace(" because ", "… because ")
        # light
        return text.replace(", ", ", … ").replace("…, ", "… ")