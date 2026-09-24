import time
import logging
import threading

logger = logging.getLogger(__name__)


TRAIT_BOUNDS = {
    "warmth": (0.2, 0.9),
    "teasing": (0.1, 0.85),
    "directness": (0.2, 0.9),
    "playfulness": (0.1, 0.8),
    "affection": (0.1, 0.8),
    "patience": (0.3, 0.95),
    "confidence": (0.2, 0.9),
}

TRAIT_SIGNAL_MAP = {
    "comfort_behavior": {"warmth": 0.02, "affection": 0.02},
    "playfulness_boost": {"playfulness": 0.02, "teasing": 0.01},
    "energy_conservation": {"patience": 0.01, "confidence": -0.01},
}


class PersonalityEvolution:
    """Adjust personality traits based on behavior signals and reflections.

    Maps behavior signals (e.g. comfort_behavior, playfulness_boost) to trait deltas,
    parses reflection text for trait-relevant keywords, applies bounded adjustments,
    logs history, and publishes events.
    """

    def __init__(self, personality_state, event_bus=None):
        self.personality_state = personality_state
        self.event_bus = event_bus
        self._lock = threading.RLock()
        self._adjustment_log = []
        self._max_log = 100

    def evolve(self, behavior_adjustments=None, reflections=None):
        if not behavior_adjustments and not reflections:
            return {}

        adjustments = {}

        if behavior_adjustments:
            for signal, delta in behavior_adjustments.items():
                if signal in TRAIT_SIGNAL_MAP:
                    trait_deltas = TRAIT_SIGNAL_MAP[signal]
                    for trait, amount in trait_deltas.items():
                        adjustments[trait] = adjustments.get(trait, 0) + amount

        if reflections:
            for ref in reflections:
                text = ""
                if isinstance(ref, dict):
                    text = ref.get("summary", "") + " " + " ".join(ref.get("patterns", []))
                else:
                    text = str(ref)
                text_lower = text.lower()
                if "teasing" in text_lower or "playful" in text_lower:
                    adjustments["teasing"] = adjustments.get("teasing", 0) + 0.01
                if "warm" in text_lower or "affection" in text_lower:
                    adjustments["affection"] = adjustments.get("affection", 0) + 0.01
                if "patient" in text_lower or "calm" in text_lower:
                    adjustments["patience"] = adjustments.get("patience", 0) + 0.01

        if not adjustments:
            return {}

        applied = self.personality_state.update_traits(adjustments, TRAIT_BOUNDS)
        if applied:
                with self._lock:
                    self._adjustment_log.append({
                        "timestamp": time.time(),
                        "adjustments": dict(applied),
                        "signals": behavior_adjustments,
                    })
                    if len(self._adjustment_log) > self._max_log:
                        self._adjustment_log.pop(0)
                logger.info("[Evolution] Applied: %s", applied)

                if self.event_bus:
                    from core.event_specs import EVOLUTION_ADJUSTED
                    from core.mai_message import publish_event
                    publish_event(self.event_bus, EVOLUTION_ADJUSTED, {
                        "adjustments": applied,
                        "current_state": self.personality_state.get(),
                    }, source="agency")

                self.personality_state.save()

        return applied

    def history(self, limit=10):
        with self._lock:
            return self._adjustment_log[-limit:]
