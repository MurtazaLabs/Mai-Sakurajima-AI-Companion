import time
import threading
import logging

from core.utils import EmotionName, EmotionProfile

logger = logging.getLogger(__name__)

EMOTION_NAMES = [e.value for e in EmotionName]

EMOTION_PROFILES = {
    EmotionProfile.NEUTRAL:       {"happy": 0.5, "lonely": 0.3, "annoyed": 0.1, "affection": 0.3, "energy": 0.5, "stress": 0.2, "jealousy": 0.0},
    EmotionProfile.HAPPY:         {"happy": 0.8, "lonely": 0.1, "annoyed": 0.05, "affection": 0.6, "energy": 0.7, "stress": 0.1, "jealousy": 0.0},
    EmotionProfile.SAD:           {"happy": 0.2, "lonely": 0.7, "annoyed": 0.2, "affection": 0.2, "energy": 0.3, "stress": 0.4, "jealousy": 0.0},
    EmotionProfile.AFFECTIONATE:  {"happy": 0.7, "lonely": 0.1, "annoyed": 0.05, "affection": 0.9, "energy": 0.6, "stress": 0.1, "jealousy": 0.0},
    EmotionProfile.STRESSED:      {"happy": 0.2, "lonely": 0.4, "annoyed": 0.5, "affection": 0.1, "energy": 0.4, "stress": 0.9, "jealousy": 0.2},
    EmotionProfile.ENERGETIC:     {"happy": 0.7, "lonely": 0.2, "annoyed": 0.1, "affection": 0.4, "energy": 0.9, "stress": 0.3, "jealousy": 0.0},
    EmotionProfile.LONELY:        {"happy": 0.2, "lonely": 0.8, "annoyed": 0.2, "affection": 0.2, "energy": 0.3, "stress": 0.4, "jealousy": 0.0},
    EmotionProfile.ANNOYED:       {"happy": 0.2, "lonely": 0.3, "annoyed": 0.7, "affection": 0.1, "energy": 0.5, "stress": 0.6, "jealousy": 0.3},
    EmotionProfile.JEALOUS:       {"happy": 0.3, "lonely": 0.4, "annoyed": 0.4, "affection": 0.5, "energy": 0.4, "stress": 0.5, "jealousy": 0.8},
}

EMOTION_PROFILE_DESCRIPTIONS = {
    EmotionProfile.NEUTRAL:      "Calm and balanced",
    EmotionProfile.HAPPY:        "Joyful and content",
    EmotionProfile.SAD:          "Melancholic and reflective",
    EmotionProfile.AFFECTIONATE: "Warm and caring",
    EmotionProfile.STRESSED:     "Tense and overwhelmed",
    EmotionProfile.ENERGETIC:    "Lively and engaged",
    EmotionProfile.LONELY:       "Longing for connection",
    EmotionProfile.ANNOYED:      "Irritated and frustrated",
    EmotionProfile.JEALOUS:      "Possessive and guarded",
}


class EmotionHistory:
    def __init__(self, max_entries=500):
        self._lock = threading.RLock()
        self._entries = []
        self._max_entries = max_entries

    def record(self, snapshot, trigger=None):
        with self._lock:
            entry = {
                "timestamp": time.time(),
                "state": dict(snapshot),
                "dominant": max(snapshot, key=snapshot.get) if snapshot else "",
            }
            if trigger:
                entry["trigger"] = dict(trigger)
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]

    def recent(self, limit=10):
        with self._lock:
            return list(self._entries[-limit:])

    def since(self, since_time):
        with self._lock:
            return [e for e in self._entries if e["timestamp"] >= since_time]

    def count(self):
        with self._lock:
            return len(self._entries)

    def stats(self):
        with self._lock:
            if not self._entries:
                return {"count": 0, "earliest": 0, "latest": 0}
            return {
                "count": len(self._entries),
                "earliest": self._entries[0]["timestamp"],
                "latest": self._entries[-1]["timestamp"],
            }


class EmotionTriggerLog:
    def __init__(self, max_entries=200):
        self._lock = threading.RLock()
        self._entries = []
        self._max_entries = max_entries

    def record(self, trigger_type, source, delta, new_state):
        with self._lock:
            entry = {
                "timestamp": time.time(),
                "type": trigger_type,
                "source": str(source)[:100],
                "delta": dict(delta),
                "new_state": dict(new_state),
            }
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]

    def recent(self, limit=20):
        with self._lock:
            return list(self._entries[-limit:])

    def by_type(self, trigger_type, limit=50):
        with self._lock:
            return [e for e in self._entries if e["type"] == trigger_type][-limit:]

    def count(self):
        with self._lock:
            return len(self._entries)


def find_closest_profile(state):
    if not state:
        return EmotionProfile.NEUTRAL
    best_name = EmotionProfile.NEUTRAL
    best_dist = float("inf")
    for name, profile in EMOTION_PROFILES.items():
        dist = sum(abs(state.get(k, 0) - profile.get(k, 0)) for k in EMOTION_NAMES)
        if dist < best_dist:
            best_dist = dist
            best_name = name
    return best_name
