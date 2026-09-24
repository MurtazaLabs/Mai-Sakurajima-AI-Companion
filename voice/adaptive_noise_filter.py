import time
import logging
import threading
import numpy as np

from voice.noise_filter import NoiseFilter
from voice.vad import VAD

logger = logging.getLogger(__name__)


class AdaptiveNoiseFilter:
    def __init__(self, sample_rate=16000, low_cut=80.0, high_cut=7600.0,
                 noise_floor_percentile=10, reduction_db=6.0,
                 vad_threshold=0.5, adaptation_interval=2.0,
                 adaptation_decay=0.85, min_profile_frames=10):
        self.sample_rate = sample_rate
        self._noise_filter = NoiseFilter(
            sample_rate=sample_rate,
            low_cut=low_cut,
            high_cut=high_cut,
            noise_floor_percentile=noise_floor_percentile,
            reduction_db=reduction_db,
        )
        self._vad = VAD(threshold=vad_threshold, sample_rate=sample_rate)
        self.adaptation_interval = adaptation_interval
        self.adaptation_decay = adaptation_decay
        self.min_profile_frames = min_profile_frames
        self._noise_frames = []
        self._last_profile_time = 0.0
        self._profile_lock = threading.RLock()
        self._frame_count = 0

    @property
    def noise_profile_available(self):
        return self._noise_filter.noise_profile is not None

    def learn_noise(self, audio, sample_rate=None):
        return self._noise_filter.learn_noise(audio, sample_rate)

    def add_chunk(self, chunk):
        is_speech = self._vad.is_speech(chunk)
        if not is_speech:
            with self._profile_lock:
                self._noise_frames.append(chunk.copy())
                if len(self._noise_frames) > self.min_profile_frames * 2:
                    self._noise_frames.pop(0)

        now = time.time()
        if (now - self._last_profile_time >= self.adaptation_interval
                and len(self._noise_frames) >= self.min_profile_frames):
            with self._profile_lock:
                stacked = np.concatenate(self._noise_frames)
                self._noise_filter.learn_noise(stacked)
                self._noise_frames = []
                self._last_profile_time = now
                self._frame_count += 1

    def filter(self, audio):
        return self._noise_filter.filter(audio)

    def reset(self):
        with self._profile_lock:
            self._noise_frames = []
            self._last_profile_time = 0.0
            self._frame_count = 0

    def stats(self):
        return {
            "adaptive_updates": self._frame_count,
            "profile_available": self.noise_profile_available,
            "buffered_frames": len(self._noise_frames),
        }
