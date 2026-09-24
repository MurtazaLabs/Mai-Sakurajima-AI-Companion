import numpy as np
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class NoiseFilter:
    def __init__(self, sample_rate=16000, low_cut=80.0, high_cut=7600.0,
                 noise_floor_percentile=10, reduction_db=6.0):
        self.sample_rate = sample_rate
        self.low_cut = low_cut
        self.high_cut = high_cut
        self.noise_floor_percentile = noise_floor_percentile
        self.reduction_db = reduction_db
        self._noise_profile: Optional[np.ndarray] = None

    @property
    def noise_profile(self):
        return self._noise_profile

    def learn_noise(self, audio, sample_rate=None):
        sr = sample_rate or self.sample_rate
        try:
            freqs = np.fft.rfftfreq(len(audio), d=1.0 / sr)
            spectrum = np.abs(np.fft.rfft(audio))
            noise_floor = np.percentile(spectrum, self.noise_floor_percentile)
            self._noise_profile = np.maximum(spectrum, noise_floor)
            return True
        except Exception as e:
            logger.warning("[NoiseFilter] learn_noise error: %s", e)
            return False

    def filter(self, audio):
        if len(audio) < 2:
            return audio
        try:
            filtered = self._bandpass(audio)
            if self._noise_profile is not None:
                filtered = self._spectral_subtract(filtered)
            return filtered
        except Exception as e:
            logger.warning("[NoiseFilter] filter error: %s", e)
            return audio

    def _bandpass(self, audio):
        nyquist = self.sample_rate / 2.0
        low = self.low_cut / nyquist
        high = self.high_cut / nyquist
        if low <= 0 or high <= 0 or low >= 1 or high >= 1:
            return audio
        fft = np.fft.rfft(audio)
        freqs = np.fft.rfftfreq(len(audio), d=1.0 / self.sample_rate)
        mask = (freqs >= self.low_cut) & (freqs <= self.high_cut)
        fft = fft * mask
        return np.fft.irfft(fft, n=len(audio)).astype(audio.dtype)

    def _spectral_subtract(self, audio):
        if self._noise_profile is None:
            return audio.copy()
        fft = np.fft.rfft(audio)
        magnitude = np.abs(fft)
        phase = np.angle(fft)
        reduction_linear = 10 ** (-self.reduction_db / 20.0)
        noise_est = self._noise_profile.mean() * reduction_linear
        cleaned = np.maximum(magnitude - noise_est, 0)
        new_fft = cleaned * np.exp(1j * phase)
        return np.fft.irfft(new_fft, n=len(audio)).astype(audio.dtype)
