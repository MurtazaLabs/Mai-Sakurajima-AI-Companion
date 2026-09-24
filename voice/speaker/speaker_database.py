import json
import logging
import math
import os
import threading
from pathlib import Path

from voice.speaker.speaker_profile import SpeakerProfile

logger = logging.getLogger("Mai.SpeakerDatabase")


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(ai * bi for ai, bi in zip(a, b))
    norm_a = math.sqrt(sum(ai * ai for ai in a))
    norm_b = math.sqrt(sum(bi * bi for bi in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class SpeakerDatabase:

    def __init__(self, profiles_dir: str | Path):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _path(self, name: str) -> Path:
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        return self.profiles_dir / f"{safe}.json"

    def save(self, profile: SpeakerProfile) -> bool:
        with self._lock:
            try:
                path = self._path(profile.name)
                path.write_text(json.dumps(profile.to_dict(), indent=2), encoding="utf-8")
                return True
            except Exception as exc:
                logger.warning("save(%s) failed: %s", profile.name, exc)
                return False

    def load(self, name: str) -> SpeakerProfile | None:
        with self._lock:
            try:
                path = self._path(name)
                if not path.exists():
                    return None
                data = json.loads(path.read_text(encoding="utf-8"))
                return SpeakerProfile.from_dict(data)
            except Exception as exc:
                logger.warning("load(%s) failed: %s", name, exc)
                return None

    def delete(self, name: str) -> bool:
        with self._lock:
            try:
                path = self._path(name)
                if path.exists():
                    path.unlink()
                    return True
                return False
            except Exception as exc:
                logger.warning("delete(%s) failed: %s", name, exc)
                return False

    def list_all(self) -> list[SpeakerProfile]:
        with self._lock:
            results = []
            for fpath in self.profiles_dir.glob("*.json"):
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                    results.append(SpeakerProfile.from_dict(data))
                except Exception as exc:
                    logger.warning("list_all skipped %s: %s", fpath.name, exc)
            return results

    def search(
        self, query_embedding: list[float], threshold: float = 0.5
    ) -> tuple[SpeakerProfile | None, float]:
        best_profile = None
        best_score = 0.0
        for profile in self.list_all():
            if not profile.embedding:
                continue
            score = _cosine_similarity(query_embedding, profile.embedding)
            if score > best_score:
                best_score = score
                best_profile = profile

        if best_score >= threshold:
            return best_profile, best_score
        return None, best_score

    def count(self) -> int:
        return len(list(self.profiles_dir.glob("*.json")))
