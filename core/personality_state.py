# core/personality_state.py
import json
import logging
import os
import threading

logger = logging.getLogger("Mai.PersonalityState")


# Maps identity personality traits to numeric state baselines
IDENTITY_TRAIT_MAP = {
    "warmth": "Warm but not overly affectionate",
    "teasing": "Naturally witty",
    "directness": "Speaks naturally",
    "playfulness": "Occasionally playful",
    "affection": "Warm but not overly affectionate",
    "patience": "Calm and composed / Emotionally mature",
    "confidence": "Confident but humble",
}


class PersonalityState:

    def __init__(self, path=None):

        self.path = path
        self._lock = threading.RLock()

        # 🧠 stable modulation traits
        # Baselines are set to match identity/personality.py:
        #   "Calm and composed" → patience 0.7
        #   "Confident but humble" → confidence 0.5
        #   "Warm but not overly affectionate" → warmth 0.5, affection 0.3
        #   "Naturally witty" → teasing 0.5
        #   "Occasionally playful" → playfulness 0.4
        #   "Speaks naturally" → directness 0.5
        #   "Emotionally mature" → patience 0.7, confidence 0.5
        self.state = {
            "warmth": 0.5,
            "teasing": 0.5,
            "directness": 0.5,
            "playfulness": 0.4,
            "affection": 0.3,
            "patience": 0.7,
            "confidence": 0.5,
        }

        # 🎯 natural baseline
        self.baseline = self.state.copy()

    # ❤️ relationship influence
    def update_from_relationship(self, relationship):
        with self._lock:
            closeness = relationship.get("closeness", 0.5)
            trust = relationship.get("trust", 0.5)
            attachment = relationship.get("attachment", 0.5)

            self._shift("warmth", closeness * 0.08)
            self._shift("affection", attachment * 0.06)
            self._shift("confidence", trust * 0.05)

            if closeness > 0.7:
                self._shift("teasing", 0.03)
                self._shift("playfulness", 0.04)

    # 🎨 user preference influence
    def update_from_preferences(self, preferences):
        with self._lock:
            style = preferences.get("response_style", "normal")
            likes_teasing = preferences.get("likes_teasing", False)

            if style == "short":
                self._shift("directness", 0.08)
            if likes_teasing:
                self._shift("teasing", 0.07)
                self._shift("playfulness", 0.05)

    # 🪞 learned reflections
    def update_from_reflections(self, reflections):
        with self._lock:
            if reflections.get("responds_well_to_teasing", False):
                self._shift("teasing", 0.05)
            if reflections.get("needs_emotional_support", False):
                self._shift("warmth", 0.06)

    # 😊 emotion influence
    def update_from_emotion(self, emotion):
        with self._lock:
            annoyed = emotion.get("annoyed", 0.0)
            happy = emotion.get("happy", 0.5)
            affection = emotion.get("affection", 0.3)
            energy = emotion.get("energy", 0.5)

            self._shift("warmth", affection * 0.03)
            self._shift("playfulness", happy * 0.03)
            self._shift("patience", -annoyed * 0.05)
            self._shift("confidence", energy * 0.02)

    # 🌊 natural stabilization
    def decay(self):
        with self._lock:
            for trait in self.state:
                baseline = self.baseline[trait]
                current = self.state[trait]
                self.state[trait] += (baseline - current) * 0.02
            self._clamp()

    # ➕ gradual trait shifting
    def _shift(self, trait, amount):
        if trait not in self.state:
            return
        self.state[trait] += amount
        self._clamp()

    # 🔒 safe ranges
    def _clamp(self):

        for trait in self.state:

            self.state[trait] = max(
                0.0,
                min(1.0, self.state[trait])
            )

    # 📦 raw export
    def get(self):
        with self._lock:
            return {k: round(v, 2) for k, v in self.state.items()}

    def update_traits(self, adjustments, bounds=None):
        with self._lock:
            applied = {}
            for trait, delta in adjustments.items():
                if bounds and trait not in bounds:
                    continue
                lo, hi = bounds.get(trait, (0.0, 1.0)) if bounds else (0.0, 1.0)
                old = self.state.get(trait, 0.5)
                new = max(lo, min(hi, old + delta))
                if abs(new - old) > 0.001:
                    self.state[trait] = new
                    applied[trait] = round(new - old, 4)
            return applied

    # 💾 save to disk
    def save(self):
        if not self.path:
            return
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self.path), exist_ok=True)
                with open(self.path, "w", encoding="utf-8") as f:
                    json.dump({"state": self.state, "baseline": self.baseline}, f, indent=2)
            except Exception as e:
                logger.warning("PersonalityState save error: %s", e)

    def load(self):
        if not self.path or not os.path.exists(self.path):
            return
        with self._lock:
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data.get("state"), dict):
                    self.state.update(data["state"])
                if isinstance(data.get("baseline"), dict):
                    self.baseline.update(data["baseline"])
            except Exception as e:
                logger.warning("PersonalityState load error: %s", e)

    # 🧠 conversational modifiers
    def get_style_modifiers(self):
        with self._lock:
            modifiers = []
            if self.state["warmth"] > 0.7:
                modifiers.append("Speak in a softer and emotionally warmer tone.")
            if self.state["directness"] > 0.7:
                modifiers.append("Keep responses concise and direct.")
            if self.state["teasing"] > 0.7:
                modifiers.append("Use playful teasing naturally.")
            if self.state["playfulness"] > 0.7:
                modifiers.append("Sound more playful and lively.")
            if self.state["patience"] < 0.3:
                modifiers.append("Sound slightly impatient.")
            return modifiers