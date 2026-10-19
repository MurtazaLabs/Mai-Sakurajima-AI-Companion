# reasoning/learning.py
import logging

logger = logging.getLogger(__name__)


class LearningEngine:

    def __init__(self, belief_engine=None, event_bus=None):
        self.belief_engine = belief_engine
        self.event_bus = event_bus

    def generalize(self, memories):
        if not memories:
            return []

        patterns = self._extract_patterns(memories)
        generalizations = self._build_generalizations(patterns)

        if generalizations and self.event_bus:
            from core.event_specs import LEARNING_GENERALIZED
            from core.mai_message import publish_event
            publish_event(self.event_bus, LEARNING_GENERALIZED, {
                "count": len(generalizations),
                "generalizations": generalizations,
            }, source="reasoning")

        return generalizations

    def adjust_behavior(self, reflections):
        if not reflections:
            return {}

        adjustments = {}

        stress_signals = ["stressed", "anxious", "overwhelmed", "tired", "sad"]
        positive_signals = ["happy", "excited", "grateful", "thankful", "great"]

        stress_count = 0
        positive_count = 0

        for ref in reflections:
            text = ""
            if isinstance(ref, dict):
                text = ref.get("summary", "") + " " + " ".join(ref.get("patterns", []))
            else:
                text = str(ref)

            text_lower = text.lower()
            for word in stress_signals:
                if word in text_lower:
                    stress_count += 1
            for word in positive_signals:
                if word in text_lower:
                    positive_count += 1

        if stress_count > positive_count:
            adjustments["comfort_behavior"] = min(0.3, 0.05 * stress_count)
            adjustments["energy_conservation"] = True

        if positive_count > stress_count:
            adjustments["playfulness_boost"] = min(0.2, 0.03 * positive_count)

        if adjustments and self.event_bus:
            from core.event_specs import BEHAVIOR_ADJUSTED
            from core.mai_message import publish_event
            publish_event(self.event_bus, BEHAVIOR_ADJUSTED, adjustments, source="reasoning")

        return adjustments

    def _extract_patterns(self, memories):
        patterns = []

        preferences = []
        locations = []
        identities = []

        for mem in memories:
            text = ""
            mem_type = ""
            if isinstance(mem, dict):
                text = str(mem.get("text", mem.get("content", "")))
                mem_type = str(mem.get("memory_type", mem.get("type", "")))
            else:
                text = str(getattr(mem, "text", getattr(mem, "content", "")))
                mem_type = str(getattr(mem, "memory_type", getattr(mem, "type", "")))

            text_lower = text.lower()

            for word in ["like", "love", "enjoy"]:
                if f" {word} " in f" {text_lower} ":
                    idx = text_lower.find(f" {word} ")
                    after = text[idx + len(word) + 1:].strip().rstrip(".!,")
                    if after:
                        preferences.append(after)

            if mem_type in ("location",):
                locations.append(text)

            if mem_type in ("identity",):
                identities.append(text)

        if preferences:
            patterns.append({
                "type": "preference_cluster",
                "items": preferences[:5],
                "count": len(preferences),
            })

        if locations:
            patterns.append({
                "type": "location_cluster",
                "items": locations[:3],
                "count": len(locations),
            })

        if identities:
            patterns.append({
                "type": "identity_cluster",
                "items": identities[:3],
                "count": len(identities),
            })

        return patterns

    def _build_generalizations(self, patterns):
        generalizations = []

        for pattern in patterns:
            if pattern["type"] == "preference_cluster" and pattern["count"] >= 2:
                general = self._generalize_preferences(pattern["items"])
                if general:
                    generalizations.append(general)

            if pattern["type"] == "location_cluster" and pattern["count"] >= 1:
                generalizations.append({
                    "generalization": f"User is associated with: {', '.join(pattern['items'][:2])}",
                    "confidence": min(0.8, 0.3 + 0.15 * pattern["count"]),
                    "source": "location_cluster",
                })

        return generalizations

    def _generalize_preferences(self, items):
        if not items:
            return None

        coffee_related = {"coffee", "tea", "espresso", "latte", "cappuccino"}
        food_related = {"pizza", "pasta", "burger", "sushi", "salad"}
        tech_related = {"python", "programming", "coding", "software", "tech"}

        item_set = {item.lower().strip() for item in items}

        if item_set & coffee_related:
            return {
                "generalization": "User prefers warm beverages",
                "confidence": min(0.8, 0.4 + 0.15 * len(item_set & coffee_related)),
                "source": "preference_cluster",
            }

        if item_set & food_related:
            return {
                "generalization": "User has specific food preferences",
                "confidence": min(0.8, 0.3 + 0.15 * len(item_set & food_related)),
                "source": "preference_cluster",
            }

        if item_set & tech_related:
            return {
                "generalization": "User is interested in technology",
                "confidence": min(0.8, 0.3 + 0.15 * len(item_set & tech_related)),
                "source": "preference_cluster",
            }

        return {
            "generalization": f"User likes: {', '.join(items[:3])}",
            "confidence": min(0.6, 0.2 + 0.1 * len(items)),
            "source": "preference_cluster",
        }
