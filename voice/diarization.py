import time
import logging
import threading
import numpy as np

from voice.vad import VAD

logger = logging.getLogger(__name__)


class SpeakerSegment:
    def __init__(self, start_sample, end_sample, speaker_id, confidence=0.0):
        self.start_sample = start_sample
        self.end_sample = end_sample
        self.speaker_id = speaker_id
        self.confidence = confidence
        self.duration = (end_sample - start_sample)

    def to_dict(self):
        return {
            "start_sample": self.start_sample,
            "end_sample": self.end_sample,
            "speaker_id": self.speaker_id,
            "confidence": self.confidence,
            "duration": self.duration,
        }


class DiarizationEngine:
    def __init__(self, sample_rate=16000, vad_threshold=0.5,
                 min_segment_samples=3200, max_segment_samples=48000,
                 similarity_threshold=0.65, embedding_dim=192,
                 vad=None):
        self.sample_rate = sample_rate
        self.min_segment_samples = min_segment_samples
        self.max_segment_samples = max_segment_samples
        self.similarity_threshold = similarity_threshold
        self.embedding_dim = embedding_dim
        self._vad = vad or VAD(threshold=vad_threshold, sample_rate=sample_rate)
        self._lock = threading.RLock()
        self._speaker_profiles = {}
        self._segment_count = 0
        self._mel_filterbank = None

    def register_profile(self, speaker_id, embedding):
        with self._lock:
            self._speaker_profiles[speaker_id] = np.asarray(embedding, dtype=np.float32)

    def remove_profile(self, speaker_id):
        with self._lock:
            self._speaker_profiles.pop(speaker_id, None)

    def _cosine_similarity(self, a, b):
        a = np.asarray(a, dtype=np.float32).flatten()
        b = np.asarray(b, dtype=np.float32).flatten()
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b) + 1e-12
        return float(dot / norm)

    def _find_best_speaker(self, embedding):
        if embedding is None:
            return "__unknown__", 0.0
        with self._lock:
            best_id = "__unknown__"
            best_conf = 0.0
            for sid, profile in list(self._speaker_profiles.items()):
                sim = self._cosine_similarity(embedding, profile)
                if sim > best_conf and sim >= self.similarity_threshold:
                    best_conf = sim
                    best_id = sid
        return best_id, best_conf

    def _build_mel_filterbank(self, n_fft):
        if self._mel_filterbank is not None and self._mel_filterbank[0].shape[1] == n_fft:
            return self._mel_filterbank
        mel_bins = 40
        mel_filter = np.zeros((mel_bins, n_fft))
        mel_min = 0
        mel_max = 2595 * np.log10(1 + self.sample_rate / 700.0)
        mel_points = np.linspace(mel_min, mel_max, mel_bins + 2)
        hz_points = 700 * (10 ** (mel_points / 2595) - 1)
        bins = np.floor(hz_points / self.sample_rate * n_fft * 2).astype(int)
        bins = np.clip(bins, 0, n_fft - 1)
        for m in range(1, mel_bins + 1):
            if bins[m] > bins[m - 1]:
                mel_filter[m - 1, bins[m - 1]:bins[m]] = np.linspace(0, 1, bins[m] - bins[m - 1])
            else:
                mel_filter[m - 1, bins[m - 1]] = 1.0
            if bins[m + 1] > bins[m]:
                mel_filter[m - 1, bins[m]:bins[m + 1]] = np.linspace(1, 0, bins[m + 1] - bins[m])
            else:
                mel_filter[m - 1, bins[m]] = 1.0
        self._mel_filterbank = (mel_filter, mel_bins)
        return self._mel_filterbank

    def _extract_embedding(self, audio):
        try:
            n = len(audio)
            features = []
            frame_step = int(0.01 * self.sample_rate)
            frame_len = int(0.025 * self.sample_rate)
            for start in range(0, n - frame_len + 1, frame_step):
                frame = audio[start:start + frame_len]
                frame = frame * np.hanning(len(frame))
                fft = np.abs(np.fft.rfft(frame))
                mel_filter, mel_bins = self._build_mel_filterbank(len(fft))
                mel_energy = np.log(np.dot(mel_filter, fft ** 2) + 1e-12)
                features.append(mel_energy)

            if len(features) < 5:
                return None

            features = np.array(features, dtype=np.float32)
            mean = np.mean(features, axis=0)
            std = np.std(features, axis=0) + 1e-12
            features = (features - mean) / std

            if features.shape[1] >= self.embedding_dim:
                embedding = np.mean(features, axis=0)[:self.embedding_dim]
            else:
                embedding = np.pad(np.mean(features, axis=0), (0, self.embedding_dim - features.shape[1]))
            embedding = embedding / (np.linalg.norm(embedding) + 1e-12)
            return embedding.astype(np.float32)
        except Exception as e:
            logger.warning("[Diarization] Embedding error: %s", e)
            return None

    def segment(self, audio):
        try:
            audio = np.asarray(audio, dtype=np.float32)
            frame_size = 512
            segments = []
            seg_start = None

            for i in range(0, len(audio), frame_size):
                chunk = audio[i:i + frame_size]
                if len(chunk) < frame_size:
                    chunk = np.pad(chunk, (0, frame_size - len(chunk)))
                is_speech = self._vad.is_speech(chunk)

                if is_speech and seg_start is None:
                    seg_start = i
                elif not is_speech and seg_start is not None:
                    total_samples = i + frame_size - seg_start
                    if total_samples >= self.min_segment_samples:
                        seg_audio = audio[seg_start:i + frame_size]
                        embedding = self._extract_embedding(seg_audio)
                        speaker_id, conf = self._find_best_speaker(embedding) if embedding is not None else ("__unknown__", 0.0)
                        segments.append(SpeakerSegment(
                            start_sample=seg_start,
                            end_sample=i + frame_size,
                            speaker_id=speaker_id,
                            confidence=conf,
                        ))
                    seg_start = None

            if seg_start is not None:
                seg_audio = audio[seg_start:]
                if len(seg_audio) >= self.min_segment_samples:
                    embedding = self._extract_embedding(seg_audio)
                    speaker_id, conf = self._find_best_speaker(embedding) if embedding is not None else ("__unknown__", 0.0)
                    segments.append(SpeakerSegment(
                        start_sample=seg_start,
                        end_sample=len(audio),
                        speaker_id=speaker_id,
                        confidence=conf,
                    ))

            self._merge_adjacent_segments(segments)
            with self._lock:
                self._segment_count += len(segments)
            return segments
        except Exception as e:
            logger.error("[Diarization] segment error: %s", e)
            return []

    def _merge_adjacent_segments(self, segments):
        if len(segments) < 2:
            return
        merged = [segments[0]]
        for seg in segments[1:]:
            prev = merged[-1]
            if (seg.speaker_id == prev.speaker_id
                    and seg.confidence > 0.5
                    and prev.confidence > 0.5):
                prev.end_sample = seg.end_sample
                prev.confidence = max(prev.confidence, seg.confidence)
                prev.duration = seg.end_sample - prev.start_sample
            else:
                merged.append(seg)
        segments[:] = merged

    def stats(self):
        with self._lock:
            return {
                "registered_profiles": len(self._speaker_profiles),
                "total_segments": self._segment_count,
                "profile_ids": list(self._speaker_profiles.keys()),
            }
