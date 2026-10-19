import logging
import threading
from typing import Any

import numpy as np
from numpy.typing import NDArray

from app.config_loader import Settings

logger = logging.getLogger(__name__)


class TranscriptionUnavailable(Exception):
    """Raised when Faster-Whisper model cannot be initialized for transcription."""


class FasterWhisperSTT:

    def __init__(
        self,
        model_size=None,
        sample_rate=None,
        max_record_seconds=None,
        silence_threshold=None,
        silence_duration=None,
        input_device=None
    ):
        self.sample_rate = sample_rate or Settings.VOICE_SAMPLE_RATE
        self.max_record_seconds = max_record_seconds or Settings.MAX_RECORDING_SECONDS
        self.silence_threshold = silence_threshold or Settings.SILENCE_THRESHOLD
        self.silence_duration = silence_duration or Settings.SILENCE_DURATION
        self._model_size = model_size or Settings.WHISPER_MODEL

        self.device = "cpu"

        self._input_device = input_device
        self._lock = threading.RLock()
        self.model: Any | None = None
        self._device_resolved = False

    def _resolve_device(self) -> None:
        if self._device_resolved:
            return
        import sounddevice as sd
        if self._input_device is not None:
            try:
                info = sd.query_devices(self._input_device)
                logger.info("[STT] Using configured device %d: %s", self._input_device, info["name"])
            except Exception as e:
                logger.warning("[STT] Configured device %s unavailable: %s — falling back", self._input_device, e)
                self._input_device = None
        if self._input_device is None:
            for i, dev in enumerate(sd.query_devices()):
                if dev["max_input_channels"] > 0:
                    self._input_device = i
                    logger.info("[STT] Auto-detected mic: %s (ID: %d)", dev["name"], i)
                    break
            if self._input_device is None:
                fallback = sd.default.device[0]
                logger.warning("[STT] No input device found — using default: %s", fallback)
                self._input_device = fallback
        self._device_resolved = True

    @property
    def input_device(self) -> int | None:
        self._resolve_device()
        return self._input_device

    def _ensure_model(self) -> bool:
        with self._lock:
            if self.model is not None:
                return True
            try:
                logger.info("Loading Faster-Whisper model '%s' on %s (int8)...", self._model_size, self.device)
                from faster_whisper import WhisperModel as FWModel
                self.model = FWModel(self._model_size, device=self.device, compute_type="int8")
                dummy = np.zeros(16000, dtype=np.float32)
                try:
                    segs, _ = self.model.transcribe(dummy, language="en")
                    for _ in segs:
                        pass
                    logger.debug("[STT] Warmup complete")
                except Exception as e:
                    logger.warning("STT warmup failed: %s", e)
                return True
            except Exception as e:
                logger.error("Failed to load Faster-Whisper model: %s", e)
                return False

    def transcribe(self, audio: NDArray[np.float32], language: str = "en", initial_prompt: str | None = None) -> str:
        if not self._ensure_model():
            raise TranscriptionUnavailable(
                "Faster-Whisper unavailable: model failed to load"
            )
        with self._lock:
            model = self.model
        assert model is not None
        kwargs: dict = dict(language=language)
        if initial_prompt:
            kwargs["initial_prompt"] = initial_prompt
        segments, _info = model.transcribe(audio, **kwargs)
        return " ".join(seg.text for seg in segments).strip()

    def set_model(self, model_size: str) -> bool:
        try:
            logger.info("Switching to %s...", model_size)
            from faster_whisper import WhisperModel as FWModel
            with self._lock:
                self.model = FWModel(model_size, device=self.device, compute_type="int8")
                self._model_size = model_size
            return True
        except Exception as e:
            logger.error("Model switch error: %s", e)
            return False

    def stats(self) -> dict:
        return {
            "device": self.device,
            "input_device": self.input_device,
            "sample_rate": self.sample_rate,
            "max_record_seconds": self.max_record_seconds,
            "silence_threshold": self.silence_threshold,
            "silence_duration": self.silence_duration,
        }