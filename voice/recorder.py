import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from typing import Any

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
        pre_roll: float = 0.4,
        trailing_keep: float = 0.2,
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
        # Onset frames belong to the utterance: without this the first
        # 100-200ms of every phrase was dropped, so short wake words reached
        # STT as mid-word fragments and decoded to "" (live log 2026-10-27).
        self._pre_roll_max = max(0, int(pre_roll * sample_rate))
        self._pre_roll: deque[NDArray[np.float32]] = deque()
        self._pre_roll_samples = 0
        self._trailing_keep = trailing_keep
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
            # Hardware/driver glitches and unstable DSP stages (AEC weights,
            # FFT filter) can emit |values| > 1.0 (observed: 30.4, 1.17e11).
            # Recorder audio is float32 in [-1, 1] by contract — sanitize once
            # here so every upstream producer is covered.
            chunk = np.asarray(chunk)
            if not np.all(np.isfinite(chunk)):
                # NaN breaks every comparison — the peak clamp missed it (live
                # log 12:10:49: max=nan utterance reached the VAD gate).
                logger.warning("[Recorder] Non-finite chunk sanitized (nan/inf -> 0)")
                chunk = np.nan_to_num(chunk, nan=0.0, posinf=1.0, neginf=-1.0)
            if chunk.size and np.max(np.abs(chunk)) > 1.0:
                logger.warning("[Recorder] Corrupt chunk clamped (peak=%.4f)", np.max(np.abs(chunk)))
                chunk = np.clip(chunk, -1.0, 1.0)
            chunk = chunk.astype(np.float32)
            if self._state == STATE_LISTENING:
                self._push_pre_roll(chunk)
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
                        self._audio = list(self._pre_roll)
                        self._pre_roll.clear()
                        self._pre_roll_samples = 0
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
            self._pre_roll.clear()
            self._pre_roll_samples = 0
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

    def _push_pre_roll(self, chunk):
        """Keep the most recent ~pre_roll seconds so the utterance can start
        before the onset sample instead of after it. pre_roll=0 keeps exactly
        the current chunk (the onset frame itself must never be dropped)."""
        self._pre_roll.append(np.copy(chunk))
        self._pre_roll_samples += chunk.size
        cap = max(0, self._pre_roll_max)
        while len(self._pre_roll) > 1 and (
                self._pre_roll_samples - self._pre_roll[0].size >= cap):
            self._pre_roll_samples -= self._pre_roll.popleft().size

    def _trim_trailing_silence(self, audio):
        """Drop the silence tail the recorder waits through (silence_timeout),
        keeping a short guard so word endings are not clipped. Shorter audio is
        directly less STT work: kyutai decode time scales with clip length."""
        if not self._trailing_keep or not len(audio):
            return audio
        frame = 160  # 10 ms
        floor = max(float(np.max(np.abs(audio))) * 0.02, 1e-4)
        end = len(audio)
        min_len = int(self.sample_rate * 0.2)
        while end - frame > min_len:
            seg = audio[end - frame:end]
            if float(np.sqrt(np.mean(seg * seg))) < floor:
                end -= frame
            else:
                break
        return audio[:min(len(audio), end + int(self._trailing_keep * self.sample_rate))]

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
        audio = self._trim_trailing_silence(audio)
        max_val = np.max(np.abs(audio))
        logger.info("[Recorder] Utterance: reason=%s elapsed=%.2fs samples=%d max=%.4f",
                    reason, elapsed, len(audio), max_val)
        if max_val < self._energy_threshold:
            logger.info("[Recorder] Discarded low-energy (max=%.4f < %.4f)", max_val, self._energy_threshold)
            return None
        if max_val > 0:
            audio = audio / max_val
        return audio.astype(np.float32)
