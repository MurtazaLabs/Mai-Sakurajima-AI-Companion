# core/needs_engine.py
import logging
import threading
import time

from app.config_loader import Settings

logger = logging.getLogger(__name__)

NEED_NAMES = (
    "connection",
    "attention",
    "security",
    "recognition",
    "autonomy",
    "novelty",
    "rest",
)


def _need_baselines():
    return {
        "connection": Settings.NEED_CONNECTION_BASELINE,
        "attention": Settings.NEED_ATTENTION_BASELINE,
        "security": Settings.NEED_SECURITY_BASELINE,
        "recognition": Settings.NEED_RECOGNITION_BASELINE,
        "autonomy": Settings.NEED_AUTONOMY_BASELINE,
        "novelty": Settings.NEED_NOVELTY_BASELINE,
        "rest": Settings.NEED_REST_BASELINE,
    }


class NeedsEngine:

    def __init__(self, event_bus=None):
        self.lock = threading.RLock()
        self.event_bus = event_bus
        self.baselines = _need_baselines()
        self._needs = {
            name: baseline
            for name, baseline in self.baselines.items()
        }
        self._dips = {name: 0.0 for name in self.baselines}
        self.last_tick = time.time()
        self._events_published = 0

    def snapshot(self):
        with self.lock:
            return {
                "needs": self._needs.copy(),
                "baselines": self.baselines.copy(),
                "dips": self._dips.copy(),
            }

    def unmet(self, threshold=0.45):
        with self.lock:
            return {
                name: value
                for name, value in self._needs.items()
                if value < threshold
            }

    def _recovery(self):
        now = time.time()
        elapsed = min(now - self.last_tick, 86400)
        rate = min(elapsed / 60.0, 1.0) * Settings.NEED_RECOVERY_SPEED
        for name in self._needs:
            baseline = self.baselines[name]
            current = self._needs[name]
            self._needs[name] = max(
                Settings.EMOTION_MIN_VALUE,
                min(1.0, current + (baseline - current) * rate)
            )
            self._dips[name] = max(0.0, self._dips[name] - rate)
        self.last_tick = now

    def _apply_dip(self, name, amount):
        self._needs[name] = max(
            Settings.EMOTION_MIN_VALUE,
            self._needs[name] - amount
        )
        self._dips[name] += amount

    def _apply_boost(self, name, amount):
        self._needs[name] = min(1.0, self._needs[name] + amount)

    def _mentions_other_audience(self, text):
        lowered = text.lower()
        return any(word in lowered for word in Settings.EMOTION_OTHER_AUDIENCE_WORDS)

    def evaluate(self, text, relationship=None):
        with self.lock:
            if not text:
                return {
                    "needs": dict(self._needs),
                    "triggered": [],
                    "security_dip": self._dips["security"] > 0.05,
                    "unmet": list(self.unmet(threshold=0.25)),
                }

            self._recovery()

            if not isinstance(relationship, dict):
                relationship = {}
            closeness = relationship.get("closeness", Settings.DEFAULT_RELATIONSHIP_CLOSENESS)
            attachment = relationship.get("attachment", Settings.DEFAULT_RELATIONSHIP_ATTACHMENT)
            affection = relationship.get("affection", Settings.DEFAULT_RELATIONSHIP_ATTACHMENT)
            trust = relationship.get("trust", Settings.DEFAULT_RELATIONSHIP_TRUST)
            text = str(text).lower()
            triggered = []

            if self._mentions_other_audience(text):
                self._apply_dip("attention", Settings.NEED_DIP_ATTENTION * (0.5 + closeness))
                self._apply_dip("connection", Settings.NEED_DIP_CONNECTION)
                triggered.append("other_audience")
                if trust < Settings.EMOTION_JEALOUSY_TRUST_GATE:
                    self._apply_dip("security", Settings.NEED_DIP_SECURITY)
                    triggered.append("security")

            if any(word in text for word in Settings.EMOTION_ABSENCE_WORDS):
                self._apply_dip("connection", Settings.NEED_DIP_CONNECTION)
                triggered.append("absence")

            if any(word in text for word in Settings.EMOTION_GRATITUDE_WORDS):
                self._apply_boost("recognition", Settings.NEED_DIP_ATTENTION * 0.5)
                triggered.append("gratitude")

            lowered = text.lower()
            if (
                "stop" in lowered or "don't" in lowered or "no" == lowered.strip()
                or "leave" in lowered or "enough" in lowered
            ):
                self._apply_dip("rest", Settings.NEED_DIP_REST)
                triggered.append("rest")

            paused = self.unmet(threshold=0.25)
            result = {
                "needs": dict(self._needs),
                "triggered": triggered,
                "security_dip": self._dips["security"] > 0.05,
                "unmet": list(paused),
            }

            if self.event_bus:
                try:
                    from core.event_specs import STATE_NEEDS_UPDATED
                    from core.mai_message import publish_event
                    publish_event(
                        self.event_bus,
                        STATE_NEEDS_UPDATED,
                        {
                            "needs": dict(self._needs),
                            "triggered": triggered,
                            "unmet": list(paused),
                        },
                        source="cognition",
                    )
                    self._events_published += 1
                except Exception as e:
                    logger.debug("[NeedsEngine] publish failed: %s", e)

            return result