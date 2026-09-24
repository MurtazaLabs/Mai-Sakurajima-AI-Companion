import threading


class VoiceMetrics:
    def __init__(self):
        self._lock = threading.RLock()
        self.recordings = 0
        self.total_duration_seconds = 0.0
        self.total_audio_bytes = 0
        self.successful_transcriptions = 0
        self.failed_transcriptions = 0
        self.wake_detections = 0
        self.speaker_identifications = 0
        self.errors = 0
        self._transcription_confidence_sum = 0.0

    def record_recording(self, duration, audio_length):
        with self._lock:
            self.recordings += 1
            self.total_duration_seconds += duration
            self.total_audio_bytes += audio_length

    def record_transcription(self, success):
        with self._lock:
            if success:
                self.successful_transcriptions += 1
            else:
                self.failed_transcriptions += 1

    def record_wake(self):
        with self._lock:
            self.wake_detections += 1

    def record_speaker_id(self):
        with self._lock:
            self.speaker_identifications += 1

    def record_error(self):
        with self._lock:
            self.errors += 1

    def avg_duration(self):
        with self._lock:
            if self.recordings == 0:
                return 0.0
            return self.total_duration_seconds / self.recordings

    def transcription_success_rate(self):
        with self._lock:
            total = self.successful_transcriptions + self.failed_transcriptions
            if total == 0:
                return 1.0
            return self.successful_transcriptions / total

    def stats(self):
        with self._lock:
            return {
                "recordings": self.recordings,
                "total_duration_seconds": round(self.total_duration_seconds, 2),
                "total_audio_bytes": self.total_audio_bytes,
                "avg_duration_seconds": round(self.avg_duration(), 3),
                "successful_transcriptions": self.successful_transcriptions,
                "failed_transcriptions": self.failed_transcriptions,
                "transcription_success_rate": round(self.transcription_success_rate(), 3),
                "wake_detections": self.wake_detections,
                "speaker_identifications": self.speaker_identifications,
                "errors": self.errors,
            }
