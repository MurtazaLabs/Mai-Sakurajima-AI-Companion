import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def compute_text_overlap(a: str, b: str) -> float:
    words_a = set(str(a).lower().split())
    words_b = set(str(b).lower().split())
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union_size = len(words_a | words_b)
    return len(intersection) / union_size if union_size > 0 else 0.0


class EmotionName(str, Enum):
    HAPPY = "happy"
    LONELY = "lonely"
    ANNOYED = "annoyed"
    AFFECTION = "affection"
    ENERGY = "energy"
    STRESS = "stress"
    JEALOUSY = "jealousy"


class TimeOfDay(str, Enum):
    LATE_NIGHT = "late_night"
    MORNING = "morning"
    DAY = "day"
    EVENING = "evening"
    NIGHT = "night"


class UserMood(str, Enum):
    SAD = "sad"
    HAPPY = "happy"
    ANGRY = "angry"
    NEUTRAL = "neutral"


class EmotionProfile(str, Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    AFFECTIONATE = "affectionate"
    STRESSED = "stressed"
    ENERGETIC = "energetic"
    LONELY = "lonely"
    JEALOUS = "jealous"
    ANNOYED = "annoyed"


def safe_call(obj: Any, method_name: str, *args, fallback: T | None = None, log_name: str = "", **kwargs) -> T | None:
    try:
        if hasattr(obj, method_name):
            result = getattr(obj, method_name)(*args, **kwargs)
            return result if result is not None else fallback
        return fallback
    except Exception as e:
        name = log_name or (obj.__class__.__name__ if obj else "?")
        logger.debug("[%s.%s] %s", name, method_name, e)
        return fallback


def safe_attr(obj: Any, attr: str, fallback: T | None = None, log_name: str = "") -> T | None:
    try:
        return getattr(obj, attr, fallback)
    except Exception as e:
        name = log_name or (obj.__class__.__name__ if obj else "?")
        logger.debug("[%s.%s] %s", name, attr, e)
        return fallback


def safe_call_fn(fn: Callable | None, *args, fallback: T | None = None, log_name: str = "", **kwargs) -> T | None:
    if fn is None:
        return fallback
    try:
        result = fn(*args, **kwargs)
        return result if result is not None else fallback
    except Exception as e:
        name = log_name or getattr(fn, "__name__", "?")
        logger.debug("[%s] %s", name, e)
        return fallback


class TTLCache:
    """Simple thread-safe TTL cache using OrderedDict.

    Args:
        maxsize: Maximum number of entries before eviction (LRU).
        ttl: Time-to-live in seconds for each entry.
    """

    def __init__(self, maxsize: int = 128, ttl: float = 300.0):
        self._maxsize = maxsize
        self._ttl = ttl
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            if key not in self._cache:
                return None
            value, expiry = self._cache[key]
            if time.time() > expiry:
                del self._cache[key]
                return None
            self._cache.move_to_end(key)
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._cache[key] = (value, time.time() + self._ttl)
            self._cache.move_to_end(key)
            while len(self._cache) > self._maxsize:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._cache)
