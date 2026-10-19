import logging
import threading
import time

import numpy as np

from voice.speaker.speaker_database import SpeakerDatabase
from voice.speaker.speaker_encoder import SpeakerEncoder
from voice.speaker.speaker_profile import SpeakerProfile

logger = logging.getLogger("Mai.SpeakerManager")


class SpeakerManager:
    """Lock ordering: SpeakerManager._lock -> SpeakerEncoder._lock."""

    def __init__(
        self,
        profiles_dir: str,
    ):
        self.encoder = SpeakerEncoder()
        self.db = SpeakerDatabase(profiles_dir)
        self._lock = threading.RLock()
        self._threshold_high = 0.7
        self._threshold_low = 0.3

    @property
    def ready(self) -> bool:
        return self.encoder.ready

    def _match(self, embedding: list[float]) -> tuple[SpeakerProfile | None, float]:
        with self._lock:
            profile, score = self.db.search(embedding, threshold=self._threshold_low)
            if profile is not None and score >= self._threshold_high:
                profile.last_seen = time.time()
                profile.confidence = score
                self.db.save(profile)
        return profile, score

    def identify(self, audio_path: str) -> tuple[SpeakerProfile | None, float]:
        try:
            embedding = self.encoder.embed(audio_path)
            if embedding is None:
                return None, 0.0
            return self._match(embedding)

        except Exception as exc:
            logger.warning("identify() failed: %s", exc)
            return None, 0.0

    def identify_raw(
        self, audio: np.ndarray, sample_rate: int = 16000
    ) -> tuple[SpeakerProfile | None, float]:
        try:
            embedding = self.encoder.embed_raw(audio, sample_rate)
            if embedding is None:
                return None, 0.0
            return self._match(embedding)

        except Exception as exc:
            logger.warning("identify_raw() failed: %s", exc)
            return None, 0.0

    def register(
        self, name: str, audio_path: str
    ) -> SpeakerProfile | None:
        try:
            embedding = self.encoder.embed(audio_path)
            return self._register_with_embedding(name, embedding)

        except Exception as exc:
            logger.warning("register(%s) failed: %s", name, exc)
            return None

    def register_raw(
        self, name: str, audio: np.ndarray, sample_rate: int = 16000
    ) -> SpeakerProfile | None:
        try:
            embedding = self.encoder.embed_raw(audio, sample_rate)
            return self._register_with_embedding(name, embedding)

        except Exception as exc:
            logger.warning("register_raw(%s) failed: %s", name, exc)
            return None

    def _register_with_embedding(
        self, name: str, embedding: list[float] | None
    ) -> SpeakerProfile | None:
        if embedding is None:
            return None

        with self._lock:
            existing = self.db.load(name)
            if existing is not None:
                existing.embedding = embedding
                existing.sample_count += 1
                existing.last_seen = time.time()
                existing.confidence = 1.0
                self.db.save(existing)
                return existing

            profile = SpeakerProfile(
                name=name,
                embedding=embedding,
                confidence=1.0,
                sample_count=1,
            )
            self.db.save(profile)
        return profile

    def update_embedding(self, name: str, audio_path: str) -> SpeakerProfile | None:
        try:
            with self._lock:
                profile = self.db.load(name)
                if profile is None:
                    logger.warning("update_embedding(%s): not found", name)
                    return None

                embedding = self.encoder.embed(audio_path)
                if embedding is None:
                    return None

                profile.embedding = embedding
                profile.sample_count += 1
                profile.last_seen = time.time()
                self.db.save(profile)
            return profile

        except Exception as exc:
            logger.warning("update_embedding(%s) failed: %s", name, exc)
            return None

    def delete(self, name: str) -> bool:
        return self.db.delete(name)

    def stats(self) -> dict:
        profiles = self.db.list_all()
        return {
            "total_speakers": len(profiles),
            "ready": self.ready,
            "speakers": [
                {
                    "name": p.name,
                    "confidence": round(p.confidence, 3),
                    "sample_count": p.sample_count,
                    "last_seen": p.last_seen,
                }
                for p in profiles
            ],
        }
