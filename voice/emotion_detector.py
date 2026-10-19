import logging
import threading
from collections import deque

import numpy as np

logger = logging.getLogger(__name__)

EMOTION_LABELS = {
    0: "neutral",
    1: "happy",
    2: "sad",
    3: "angry",
    4: "stressed",
    5: "energetic",
}


class VoiceEmotionDetector:
    def __init__(self, sample_rate=16000, frame_ms=30, history_seconds=2.0):
        self.sample_rate = sample_rate
        self.frame_samples = int(sample_rate * frame_ms / 1000)
        self.history_samples = int(sample_rate * history_seconds)
        self._audio_history = deque(maxlen=self.history_samples)
        self._lock = threading.RLock()

    def add_audio(self, chunk):
        with self._lock:
            if isinstance(chunk, np.ndarray):
                self._audio_history.extend(chunk.tolist())
            else:
                self._audio_history.extend(chunk)
 
    def _get_history(self):
        with self._lock:
            if len(self._audio_history) < self.frame_samples * 2:
                return None
            return np.array(list(self._audio_history)[-self.history_samples:], dtype=np.float32)

    def compute_features(self, audio):
        if audio is None or len(audio) < self.frame_samples * 2:
            return None
        audio = audio - np.mean(audio)
        audio = audio / (np.std(audio) + 1e-12)

        energy = np.mean(audio ** 2)

        fft = np.fft.rfft(audio)
        magnitude = np.abs(fft)
        freqs = np.fft.rfftfreq(len(audio), d=1.0 / self.sample_rate)
        total_energy = np.sum(magnitude ** 2) + 1e-12
        spectral_centroid = np.sum(freqs * magnitude) / np.sum(magnitude + 1e-12)

        low_bin = int(300 / (self.sample_rate / len(audio)))
        high_bin = int(3400 / (self.sample_rate / len(audio)))
        speech_energy_ratio = np.sum(magnitude[low_bin:high_bin] ** 2) / total_energy if high_bin > low_bin else 0.5

        low_freq = int(80 / (self.sample_rate / len(audio)))
        high_freq = int(400 / (self.sample_rate / len(audio)))
        low_energy_ratio = np.sum(magnitude[low_freq:high_freq] ** 2) / total_energy if high_freq > low_freq else 0.3

        zcr = np.mean(np.abs(np.diff(np.sign(audio)))) / 2.0

        autocorr = np.correlate(audio, audio, mode="full")
        autocorr = autocorr[len(autocorr) // 2:]
        if len(autocorr) > 1:
            pitch_range = autocorr[int(self.sample_rate / 500):int(self.sample_rate / 60)] if int(self.sample_rate / 500) < int(self.sample_rate / 60) else autocorr[1:]
            pitch_conf = np.max(pitch_range) / (np.max(autocorr) + 1e-12) if np.max(autocorr) > 0 else 0.0
        else:
            pitch_conf = 0.0

        return {
            "energy": float(energy),
            "spectral_centroid": float(spectral_centroid),
            "speech_energy_ratio": float(speech_energy_ratio),
            "low_energy_ratio": float(low_energy_ratio),
            "zcr": float(zcr),
            "pitch_confidence": float(pitch_conf),
        }

    def classify_emotion(self, features):
        if features is None:
            return "neutral", 0.5

        e = features["energy"]
        sc = features["spectral_centroid"]
        ser = features["speech_energy_ratio"]
        ler = features["low_energy_ratio"]
        zcr = features["zcr"]
        pc = features["pitch_confidence"]

        scores = {
            "neutral": 0.3,
            "happy": 0.0,
            "sad": 0.0,
            "angry": 0.0,
            "stressed": 0.0,
            "energetic": 0.0,
        }

        if e < 0.01:
            scores["neutral"] += 0.3
            scores["sad"] += 0.1
        elif e > 0.1:
            scores["angry"] += 0.3
            scores["stressed"] += 0.2
            scores["energetic"] += 0.2
        elif e > 0.04:
            scores["happy"] += 0.2
            scores["energetic"] += 0.2
        else:
            scores["neutral"] += 0.2

        if sc > 2000:
            scores["happy"] += 0.2
            scores["energetic"] += 0.2
        elif sc < 800:
            scores["sad"] += 0.2
            scores["neutral"] += 0.1
        else:
            scores["neutral"] += 0.1

        if ser > 0.6:
            scores["neutral"] += 0.2
            scores["happy"] += 0.1
        elif ser < 0.3:
            scores["angry"] += 0.2
            scores["stressed"] += 0.2

        if ler > 0.3:
            scores["sad"] += 0.2
            scores["neutral"] += 0.1

        if zcr > 0.1:
            scores["angry"] += 0.2
            scores["stressed"] += 0.2
            scores["energetic"] += 0.1
        elif zcr < 0.03:
            scores["sad"] += 0.2
            scores["neutral"] += 0.1

        if pc > 0.5:
            scores["happy"] += 0.2
            scores["energetic"] += 0.2
        elif pc < 0.2:
            scores["neutral"] += 0.1
            scores["sad"] += 0.1

        emotion = max(scores, key=scores.__getitem__)
        confidence = min(scores[emotion], 0.95)
        return emotion, max(confidence, 0.3)

    def detect(self, audio=None):
        if audio is not None:
            self.add_audio(audio)
        history = self._get_history()
        if history is None:
            return "neutral", 0.3, {}
        features = self.compute_features(history)
        emotion, confidence = self.classify_emotion(features)
        return emotion, confidence, features or {}
