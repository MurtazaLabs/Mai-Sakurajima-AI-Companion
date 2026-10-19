# Mai_ai/memory/experience.py
# M6 · Emotional Experience — first-class experiential memory.
# Cheap fields (event / meaning / emotion / relationship impact) are captured
# at ingest; reflection / lessons / growth are computed lazily at dreaming.
# M8 · Replay dedup — the same event text is recorded once (md5 fingerprint,
# reload-safe). Replays of the same turn no longer double-record (spec §9).
import hashlib
import json
import logging
import threading
import time
import uuid

logger = logging.getLogger(__name__)


class EmotionExperience:

    __slots__ = (
        "emotion",
        "event",
        "growth",
        "id",
        "lessons",
        "meaning",
        "reflection",
        "relationship_impact",
        "significance",
        "timestamp",
    )

    def __init__(
        self,
        event="",
        meaning="",
        emotion=None,
        relationship_impact=None,
        reflection=0,
        lessons=None,
        growth="",
        significance=0.5,
        timestamp=None,
        exp_id=None,
    ):
        self.id = exp_id or str(uuid.uuid4())
        self.event = str(event or "").strip()
        self.meaning = str(meaning or "").strip()
        self.emotion = dict(emotion or {})
        self.relationship_impact = dict(relationship_impact or {})
        self.reflection = max(0, int(reflection or 0))
        self.lessons = list(lessons or [])
        self.growth = str(growth or "").strip()
        self.significance = max(0.0, min(1.0, float(significance or 0.0)))
        self.timestamp = timestamp if timestamp is not None else time.time()

    @property
    def reflected(self):
        return self.reflection > 0

    def to_dict(self):
        return {
            "id": self.id,
            "event": self.event,
            "meaning": self.meaning,
            "emotion": dict(self.emotion),
            "relationship_impact": dict(self.relationship_impact),
            "reflection": self.reflection,
            "lessons": list(self.lessons),
            "growth": self.growth,
            "significance": self.significance,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            data = {}
        return cls(
            event=data.get("event", ""),
            meaning=data.get("meaning", ""),
            emotion=data.get("emotion"),
            relationship_impact=data.get("relationship_impact"),
            reflection=data.get("reflection", 0),
            lessons=data.get("lessons"),
            growth=data.get("growth", ""),
            significance=data.get("significance", 0.5),
            timestamp=data.get("timestamp"),
            exp_id=data.get("id"),
        )


class ExperienceStore:
    """Append-only JSONL store for EmotionExperience objects.

    Cheap ingest: record() appends one line. Dreaming reads significant /
    unreflected entries and lazily fills meaning/lessons/growth via
    mark_reflected(). Thread-safe with RLock.

    M8 · Replay dedup: each distinct event text is recorded once. A repeated
    event (same turn replayed) returns None instead of appending, so callers
    know nothing was recorded and skip side effects (e.g. EXPERIENCE_RECORDED).
    Fingerprints are rebuilt on load, so the dedup survives restarts.
    """

    def __init__(self, path: str | None = None):
        self._lock = threading.RLock()
        self._path = str(path) if path else None
        self._experiences: list[EmotionExperience] = []
        self._fingerprints: dict[str, str] = {}  # md5(event) -> experience id
        self._deduped = 0
        if self._path:
            self._load()

    @staticmethod
    def _fingerprint(event: str) -> str:
        return hashlib.md5(str(event or "").encode("utf-8")).hexdigest()

    def _load(self):
        try:
            with open(self._path or "", "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        exp = EmotionExperience.from_dict(json.loads(line))
                        self._experiences.append(exp)
                        self._fingerprints[self._fingerprint(exp.event)] = exp.id
                    except Exception as e:
                        logger.debug("[ExperienceStore] skip bad line: %s", e)
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug("[ExperienceStore] load failed: %s", e)

    def record(self, experience: EmotionExperience):
        if not experience or not experience.event:
            return experience
        fp = self._fingerprint(experience.event)
        with self._lock:
            if fp in self._fingerprints:
                self._deduped += 1
                return None
            self._experiences.append(experience)
            self._fingerprints[fp] = experience.id
            if self._path:
                try:
                    with open(self._path, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps(experience.to_dict()) + "\n")
                except Exception as e:
                    logger.debug("[ExperienceStore] append failed: %s", e)
        return experience

    def record_event(
        self,
        event: str,
        meaning: str = "",
        emotion: dict | None = None,
        relationship_impact: dict | None = None,
        significance: float = 0.5,
    ) -> EmotionExperience:
        exp = EmotionExperience(
            event=event,
            meaning=meaning,
            emotion=emotion,
            relationship_impact=relationship_impact,
            significance=significance,
        )
        return self.record(exp)

    def significant(self, threshold: float = 0.6) -> list:
        with self._lock:
            return [e for e in self._experiences if e.significance >= threshold]

    def unreflected(self, threshold: float = 0.0) -> list:
        with self._lock:
            return [e for e in self._experiences
                    if e.significance >= threshold and not e.reflected]

    def mark_reflected(self, exp_id: str, meaning="", lessons=None, growth="") -> bool:
        with self._lock:
            for e in self._experiences:
                if e.id == exp_id:
                    e.reflection += 1
                    if meaning:
                        e.meaning = str(meaning)
                    if lessons:
                        e.lessons = list(lessons)
                    if growth:
                        e.growth = str(growth)
                    self._rewrite()
                    return True
        return False

    def _rewrite(self):
        if not self._path:
            return
        try:
            with open(self._path or "", "w", encoding="utf-8") as fh:
                fh.writelines(json.dumps(e.to_dict()) + "\n" for e in self._experiences)
        except Exception as e:
            logger.debug("[ExperienceStore] rewrite failed: %s", e)

    def recent(self, n=10):
        with self._lock:
            return list(self._experiences[-n:])

    def format_context(self, limit: int = 3, min_significance: float = 0.6, query: str | None = None) -> str:
        """Format reflected experiences for context injection.
        
        If query is provided, only experiences with relevance above threshold
        are included (M12 relevance gating).
        """
        with self._lock:
            reflected = [
                e for e in self._experiences
                if e.reflected and e.significance >= min_significance and e.meaning
            ]
            if not reflected:
                return ""
            
            # If query provided, filter by relevance
            if query:
                from core.memory_coordinator import _dice_score
                relevant = []
                for e in reflected:
                    score = _dice_score(query, e.event)
                    if score >= 0.10:  # EXPERIENCE_RELEVANCE_MIN_SCORE
                        relevant.append((score, e))
                if not relevant:
                    return ""
                # Sort by relevance score descending, then significance
                relevant.sort(key=lambda x: (x[0], x[1].significance), reverse=True)
                reflected = [e for _, e in relevant[:limit]]
            else:
                # Sort by significance descending, then by timestamp descending
                reflected.sort(key=lambda e: (e.significance, e.timestamp), reverse=True)
                reflected = reflected[:limit]
            
            lines = []
            for e in reflected:
                lesson_str = f" | what it taught me: {e.lessons[0]}" if e.lessons else ""
                growth_str = f" | growth: {e.growth}" if e.growth else ""
                lines.append(
                    f"- {e.event} — {e.meaning}{lesson_str}{growth_str}"
                )
            return "\n".join(lines)

    def get(self, exp_id: str):
        with self._lock:
            for e in self._experiences:
                if e.id == exp_id:
                    return e
        return None

    def count(self):
        with self._lock:
            return len(self._experiences)

    def stats(self):
        with self._lock:
            return {
                "count": len(self._experiences),
                "reflected": sum(1 for e in self._experiences if e.reflected),
                "significant": sum(1 for e in self._experiences if e.significance >= 0.6),
                "deduped": self._deduped,
            }