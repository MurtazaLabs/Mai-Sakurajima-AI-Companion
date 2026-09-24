"""Voice domain logic for the Mai API (status + detailed diagnostics).

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for how this is composed.
"""
import logging
from typing import Any, Optional
from api.errors import safe_error

logger = logging.getLogger("api.server")


class VoiceMixin:
    """Voice manager status + deep diagnostics handlers."""

    # Set by MaiAPI at runtime — declared here for type checker
    voice: Any = None
    voice_manager: Any = None

    def voice_status(self):
        if not self.voice_manager:
            return {"state": "unavailable"}
        try:
            vm = self.voice_manager
            state_str = vm.state.value if hasattr(vm.state, 'value') else str(vm.state)
            wake_words = []
            if hasattr(vm, 'wake_detector') and vm.wake_detector:
                wake_words = vm.wake_detector.wake_words
            return {
                "state": state_str,
                "is_speaking": vm.is_speaking() if hasattr(vm, 'is_speaking') else False,
                "wake_detected": vm.wake_event.is_set() if hasattr(vm, 'wake_event') else False,
                "mic_active": vm.running if hasattr(vm, 'running') else False,
                "wake_words": wake_words,
            }
        except Exception as e:
            return {"state": "error", "error": safe_error(e)}

    def voice_details(self):
        details = {}
        v = self.voice
        vm = self.voice_manager
        if v:
            try:
                details["realtime"] = v.stats() if hasattr(v, "stats") else {}
                if hasattr(v, "tts") and v.tts and hasattr(v.tts, "stats"):
                    details["tts"] = v.tts.stats()
            except Exception as e:
                logger.exception("[Voice] realtime: %s", e)
        if vm:
            try:
                details["vad_threshold"] = getattr(vm, "vad_threshold", None)
                details["silence_timeout"] = getattr(vm, "silence_timeout", None)
                details["min_recording"] = getattr(vm, "min_recording", None)
                details["max_recording"] = getattr(vm, "max_recording", None)
                details["sample_rate"] = getattr(vm, "sample_rate", None)
            except Exception as e:
                logger.exception("[Voice] config: %s", e)
            try:
                if hasattr(vm, "_metrics") and vm._metrics and hasattr(vm._metrics, "stats"):
                    details["metrics"] = vm._metrics.stats()
            except Exception as e:
                logger.exception("[Voice] metrics: %s", e)
            try:
                if hasattr(vm, "emotion_detector") and vm.emotion_detector:
                    emo_label, conf, feats = vm.emotion_detector.detect()
                    details["emotion_detector"] = {"label": emo_label, "confidence": conf, "features": feats if feats else {}}
            except Exception as e:
                logger.exception("[Voice] emotion detector: %s", e)
            try:
                if hasattr(vm, "adaptive_noise_filter") and vm.adaptive_noise_filter and hasattr(vm.adaptive_noise_filter, "stats"):
                    details["adaptive_noise"] = vm.adaptive_noise_filter.stats()
            except Exception as e:
                logger.exception("[Voice] noise filter: %s", e)
            try:
                if hasattr(vm, "full_aec") and vm.full_aec and hasattr(vm.full_aec, "stats"):
                    details["full_aec"] = vm.full_aec.stats()
            except Exception as e:
                logger.exception("[Voice] full_aec: %s", e)
            try:
                if hasattr(vm, "diarization_engine") and vm.diarization_engine and hasattr(vm.diarization_engine, "stats"):
                    details["diarization"] = vm.diarization_engine.stats()
            except Exception as e:
                logger.exception("[Voice] diarization: %s", e)
            try:
                if hasattr(vm, "stt") and vm.stt and hasattr(vm.stt, "stats"):
                    details["stt"] = vm.stt.stats()
            except Exception as e:
                logger.exception("[Voice] stt: %s", e)
        return details

    def voice_toggle(self):
        if not self.voice_manager:
            return {"state": "unavailable"}
        try:
            vm = self.voice_manager
            running = vm.running if hasattr(vm, 'running') else False
            if running:
                self._stop_voice_conversation()
                vm.stop()
                return {"state": "stopped", "active": False}
            else:
                vm.start()
                self._start_voice_conversation()
                return {"state": "started", "active": True}
        except Exception as e:
            return {"state": "error", "error": safe_error(e)}
