import logging
import time

from app.config_loader import (
    VOICE_COOLDOWN,
    WAKE_WORDS,
)

logger = logging.getLogger(__name__)


class WakeWord:
    """Thin coordinator for wake-word detection.

    No longer owns a microphone or uses speech_recognition.
    Instead it monitors the VoiceManager's wake detection via a shared flag
    set by the VoiceManager's background wake-detection thread.

    The listen() method is kept for backward compatibility with the kernel's
    main loop, but it now polls a shared flag rather than opening its own mic.
    """

    def __init__(self, wake_words=None, voice_manager=None, cooldown=None):
        self.cooldown = cooldown or VOICE_COOLDOWN
        self.last_trigger = 0
        self.wake_words = wake_words or WAKE_WORDS

        # VoiceManager reference — set externally after both are constructed
        self._voice_manager = voice_manager

        logger.info("[WakeWord] Initialized (delegates to VoiceManager)")

    def bind_voice_manager(self, vm):
        self._voice_manager = vm
        logger.debug("[WakeWord] Bound to VoiceManager")

    def listen(self):
        """Non-blocking wake check. Returns True once if wake was detected
        since the last call, then resets. This lets the kernel's polling
        loop react to events without requiring event subscriptions."""
        # Cooldown check
        if time.time() - self.last_trigger < self.cooldown:
            return False

        vm = self._voice_manager
        if vm is not None and vm.wake_event.is_set():
            vm.wake_event.clear()
            self.last_trigger = time.time()
            logger.info("[WakeWord] Wake detected via VoiceManager")
            return True

        return False

    def add_wake_word(self, word):
        word = word.lower().strip()
        if word not in self.wake_words:
            self.wake_words.append(word)

    def stats(self):
        return {
            "wake_words": self.wake_words,
            "energy_threshold": 0.5,
            "cooldown": self.cooldown,
        }
