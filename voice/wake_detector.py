import time
import logging
import numpy as np

logger = logging.getLogger(__name__)


class WakeDetector:
    def __init__(self, wake_words=None, stt=None, cooldown=2.0):
        from app.config_loader import WAKE_WORDS as DEFAULT_WAKE_WORDS
        self.wake_words = [w.lower().strip() for w in (wake_words or DEFAULT_WAKE_WORDS)]
        # Build word-level keys from multi-word phrases (e.g. "wake up mai" → {"wake", "mai"})
        self._key_words = set()
        stop_words = {"the", "a", "an", "in", "on", "at", "to", "for", "of", "and", "is", "it", "up"}
        for phrase in self.wake_words:
            for word in phrase.split():
                if word not in stop_words:
                    self._key_words.add(word)
        # Phonetic-close words — Whisper often hears "wait" for "wake", "make" for "wake", etc.
        self._key_words.update({"wait", "make", "wake"})
        self.stt = stt
        self.cooldown = cooldown
        self._last_trigger = 0.0

    def is_wake(self, audio, transcribed_text=""):
        now = time.time()
        if now - self._last_trigger < self.cooldown:
            return False, ""

        text = transcribed_text
        if not text and self.stt and audio is not None:
            try:
                text = self.stt.transcribe(audio)
            except Exception as e:
                logger.warning("[WakeDetector] STT error: %s", e)
                return False, ""

        text_lower = text.lower()
        matched = self._match(text_lower)
        if matched:
            self._last_trigger = now
            logger.info("[WakeDetector] Triggered: %s", matched)
            return True, text

        return False, text

    def detect_in_text(self, text):
        now = time.time()
        if now - self._last_trigger < self.cooldown:
            return False
        text_lower = text.lower()
        matched = self._match(text_lower)
        if matched:
            self._last_trigger = now
            logger.info("[WakeDetector] Triggered (text): %s", matched)
            return True
        return False

    def _match(self, text_lower):
        """Try full phrase match first, then word-level fallback, then substring."""
        for wake in self.wake_words:
            if wake in text_lower:
                return wake
        # Word-level fallback: any key word present? (e.g. "wake" in "certainly the wake")
        words_in_text = set(text_lower.split())
        hits = words_in_text & self._key_words
        if hits:
            logger.debug("[WakeDetector] Partial match: %s in '%s'", hits, text_lower)
            return next(iter(hits))
        # Substring fallback: key word within a transcribed word (e.g. "make" in "makeup")
        for word in words_in_text:
            for kw in self._key_words:
                if kw in word:
                    logger.debug("[WakeDetector] Substring match: '%s' in '%s'", kw, word)
                    return kw
        return None

    def reset(self):
        self._last_trigger = 0.0
