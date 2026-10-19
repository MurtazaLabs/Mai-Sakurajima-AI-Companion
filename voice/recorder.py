import logging
import threading
import time
from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

logger = logging.getLogger(__name__)

STATE_LISTENING = "listening"
STATE_RECORDING = "recording"
STATE_FINALIZING = "finalizing"

_ADAPTIVE_RATE = 0.01
_MIN_FLOOR = 1e-6


class Recorder:
    """Continuous VAD-gated recorder.

    State machine:
        LISTENING → VAD detects sustained speech → RECORDING
        RECORDING  → silence timeout / max duration → FINALIZING
        FINALIZING → build result → callback → LISTENING

    The recorder is created once and lives for the lifetime of VoiceManager.
    No start_recording() / wait() polling — utterances are pushed to a callback.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        silence_timeout: float = 0.7,
        min_recording: float = 0.5,
        max_recording: float = 30.0,
        vad=None,
        speech_onset_frames: int = 3,
        energy_threshold: float = 0.02,
        min_chunk_amplitude: float = 0.001,
    ):
        self.sample_rate = sample_rate
        self.silence_timeout = silence_timeout
        self.min_recording = min_recording
        self.max_recording = max_recording
        self._vad: Any | None = vad
        self._speech_onset_frames = speech_onset_frames
        self._callback: Callable[[np.ndarray | None], None] | None = None
        self._state = STATE_LISTENING
        self._audio: list[NDArray[np.float32]] = []
        self._silence_start: float | None = None
        self._recording_start: float | None = None
        self._speech_frames = 0
        self._lock = threading.RLock()
        self._noise_floor = _MIN_FLOOR
        self._settled = False
        self._energy_threshold = energy_threshold
        self._min_chunk_amplitude = min_chunk_amplitude

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    def set_callback(self, callback: Callable[[np.ndarray | None], None]) -> None:
        self._callback = callback

    def add_chunk(self, chunk: NDArray[np.float32]) -> None:
        with self._lock:
            if self._state == STATE_LISTENING:
                self._update_noise_floor(chunk)
                # Skip VAD for near-silent chunks — prevents noise-triggered
                # recording cycles from ambient mic hiss / fan noise.
                if np.max(np.abs(chunk)) < self._min_chunk_amplitude:
                    self._speech_frames = 0
                    return
                speech = self._is_speech(chunk)
                if speech:
                    self._speech_frames += 1
                    if self._speech_frames >= self._speech_onset_frames:
                        logger.info("[Recorder] Speech onset detected — starting recording")
                        self._state = STATE_RECORDING
                        self._audio = [np.copy(chunk)]
                        self._silence_start = None
                        self._recording_start = time.time()
                        self._speech_frames = 0
                else:
                    self._speech_frames = 0
                return

            if self._state == STATE_RECORDING:
                self._update_noise_floor(chunk)
                self._audio.append(np.copy(chunk))
                speech = self._is_speech(chunk)
                if speech:
                    self._silence_start = None
                else:
                    if self._silence_start is None:
                        self._silence_start = time.time()
                        logger.debug("[Recorder] Silence started (chunk %d)", len(self._audio))
                    elif time.time() - self._silence_start >= self.silence_timeout:
                        logger.info("[Recorder] Silence timeout — finalizing (%.1fs idle)",
                                    time.time() - self._silence_start)
                        self._finalize(reason="silence")
                        return

                if self._recording_start is None:
                    logger.warning("Recording start is None")
                    return
                elapsed = time.time() - self._recording_start
                if elapsed >= self.max_recording:
                    logger.info("[Recorder] Max duration reached (%.1fs) — finalizing", elapsed)
                    self._finalize(reason="max_duration")

    def stop(self):
        with self._lock:
            self._state = STATE_LISTENING
            self._audio = []
            self._speech_frames = 0
            self._silence_start = None
        self._recording_start = None

    def _is_speech(self, chunk):
        if self._vad is not None:
            try:
                return self._vad.is_speech(chunk)
            except Exception as e:
                logger.warning("[Recorder] VAD error: %s", e)
        return self._volume_above_noise_floor(chunk)

    def _volume_above_noise_floor(self, chunk):
        volume = np.abs(chunk).mean()
        # Higher multiplier + absolute floor prevents silent noise from
        # continuously triggering the recorder when VAD is unavailable.
        threshold = max(self._noise_floor * 10.0, 0.001)
        return volume > threshold

    def _update_noise_floor(self, chunk):
        volume = np.abs(chunk).mean()
        if not self._settled:
            self._noise_floor = self._noise_floor * (1 - _ADAPTIVE_RATE) + volume * _ADAPTIVE_RATE
            if self._noise_floor > 0:
                self._settled = True
        elif volume < self._noise_floor * 2.0:
            self._noise_floor = self._noise_floor * (1 - _ADAPTIVE_RATE * 0.1) + volume * (_ADAPTIVE_RATE * 0.1)

    def _finalize(self, reason=""):
        self._state = STATE_FINALIZING
        result = self._build_result(reason=reason)
        self._state = STATE_LISTENING
        self._audio = []
        self._speech_frames = 0
        self._silence_start = None
        self._recording_start = None
        if result is not None and self._callback:
            try:
                self._callback(result)
            except Exception as e:
                logger.warning("[Recorder] Callback error: %s", e)

    def _build_result(self, reason=""):
        if not self._audio:
            return None
        audio = np.concatenate(self._audio)
        elapsed = time.time() - self._recording_start if self._recording_start else 0
        if elapsed < self.min_recording:
            logger.debug("[Recorder] Discarded short (%.3fs < %.3fs)", elapsed, self.min_recording)
            return None
        max_val = np.max(np.abs(audio))
        logger.info("[Recorder] Utterance: reason=%s elapsed=%.2fs samples=%d max=%.4f",
                    reason, elapsed, len(audio), max_val)
        if max_val < self._energy_threshold:
            logger.info("[Recorder] Discarded low-energy (max=%.4f < %.4f)", max_val, self._energy_threshold)
            return None
        if max_val > 0:
            audio = audio / max_val
        return audio.astype(np.float32)
