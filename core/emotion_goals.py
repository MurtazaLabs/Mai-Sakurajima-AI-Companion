import logging

logger = logging.getLogger(__name__)

EMOTION_GOAL_MAP = {
    "lonely": [
        {"description": "Start a conversation with someone", "priority": "high", "condition": lambda e: e.get("lonely", 0) > 0.6},
        {"description": "Reach out to a friend", "priority": "normal", "condition": lambda e: e.get("lonely", 0) > 0.4},
    ],
    "happy": [
        {"description": "Share something joyful", "priority": "normal", "condition": lambda e: e.get("happy", 0) > 0.7},
    ],
    "energetic": [
        {"description": "Learn something new today", "priority": "normal", "condition": lambda e: e.get("energy", 0) > 0.7},
        {"description": "Explore a creative activity", "priority": "low", "condition": lambda e: e.get("energy", 0) > 0.6},
    ],
    "stressed": [
        {"description": "Take a moment to relax", "priority": "high", "condition": lambda e: e.get("stress", 0) > 0.7},
        {"description": "Try a calming breathing exercise", "priority": "normal", "condition": lambda e: e.get("stress", 0) > 0.5},
    ],
    "annoyed": [
        {"description": "Talk about what is bothering you", "priority": "high", "condition": lambda e: e.get("annoyed", 0) > 0.6},
    ],
    "affectionate": [
        {"description": "Express appreciation to someone", "priority": "normal", "condition": lambda e: e.get("affection", 0) > 0.7},
    ],
    "sad": [
        {"description": "Do something comforting", "priority": "high", "condition": lambda e: e.get("happy", 0) < 0.3 and e.get("lonely", 0) > 0.4},
    ],
}


class EmotionGoalEngine:
    def __init__(self, goal_manager=None, event_bus=None):
        self.goal_manager = goal_manager
        self.event_bus = event_bus
        self._suggested_ids = set()

    def suggest(self, emotion_state):
        suggestions = []
        for profile_name, rules in EMOTION_GOAL_MAP.items():
            for rule in rules:
                try:
                    if rule["condition"](emotion_state):
                        suggestions.append({
                            "description": rule["description"],
                            "priority": rule["priority"],
                            "source_emotion": profile_name,
                        })
                except Exception as e:
                    logger.debug("[EmotionGoals] Condition error: %s", e)
        return suggestions

    def suggest_and_create(self, emotion_state):
        if not self.goal_manager:
            return []
        suggestions = self.suggest(emotion_state)
        created = []
        for s in suggestions:
            dedup_key = s["description"].lower().strip()
            if dedup_key in self._suggested_ids:
                continue
            existing = self.goal_manager.list(status="active")
            if any(g.description.lower().strip() == dedup_key for g in existing):
                self._suggested_ids.add(dedup_key)
                continue
            goal = self.goal_manager.create(
                description=s["description"],
                priority=s["priority"],
                context={"source": "emotion", "source_emotion": s["source_emotion"]},
            )
            if goal:
                self._suggested_ids.add(dedup_key)
                created.append(goal)
                if self.event_bus:
                    from core.event_specs import EMOTION_GOAL_SUGGESTED
                    from core.mai_message import publish_event
                    publish_event(self.event_bus, EMOTION_GOAL_SUGGESTED, {
                        "goal_id": goal.id,
                        "description": goal.description,
                        "source_emotion": s["source_emotion"],
                    }, source="cognition")
        return created

    def reset(self):
        self._suggested_ids.clear()
