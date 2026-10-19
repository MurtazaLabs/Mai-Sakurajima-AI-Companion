import logging

import numpy as np

logger = logging.getLogger(__name__)


class UtteranceSegmenter:
    def __init__(self, sample_rate=16000, silence_threshold=0.01,
                 min_silence_duration=0.6, min_utterance_duration=0.3,
                 max_utterance_duration=30.0):
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.min_silence_frames = int(min_silence_duration * sample_rate)
        self.min_utterance_frames = int(min_utterance_duration * sample_rate)
        self.max_utterance_frames = int(max_utterance_duration * sample_rate)

    def segment(self, audio):
        if len(audio) == 0:
            return []

        try:
            energy = np.abs(audio)
            is_speech = energy > self.silence_threshold
            if not np.any(is_speech):
                return []

            segments = []
            start = None
            silence_run = 0

            for i in range(len(audio)):
                if is_speech[i]:
                    if start is None:
                        start = i
                    silence_run = 0
                else:
                    if start is not None:
                        silence_run += 1
                        if silence_run >= self.min_silence_frames:
                            end = i - silence_run + 1
                            if end - start >= self.min_utterance_frames:
                                chunk = audio[start:end]
                                if len(chunk) <= self.max_utterance_frames:
                                    segments.append(chunk)
                                else:
                                    segments.extend(self._split_long(chunk))
                            start = None

            if start is not None:
                remaining = audio[start:]
                if len(remaining) >= self.min_utterance_frames:
                    if len(remaining) <= self.max_utterance_frames:
                        segments.append(remaining)
                    else:
                        segments.extend(self._split_long(remaining))
            return segments
        except Exception as e:
            logger.warning("[UtteranceSegmenter] segment error: %s", e)
            return [audio] if len(audio) > 0 else []

    def _split_long(self, audio):
        chunks = []
        for i in range(0, len(audio), self.max_utterance_frames):
            chunk = audio[i:i + self.max_utterance_frames]
            if len(chunk) >= self.min_utterance_frames:
                chunks.append(chunk)
        return chunks
