# Mai_ai/memory/router.py
import json
import logging
import re

logger = logging.getLogger(__name__)


class MemoryRouter:

    def __init__(self):

        # 🧠 routing thresholds
        self.importance_threshold = 0.75

        self.emotional_threshold = 0.7

        # 📁 valid obsidian folders
        self.valid_routes = {
            "conversation",
            "identity",
            "preferences",
            "relationship",
            "reflections",
            "archive",
        }


    # ==================================================
    # 🧠 MAIN ROUTER
    # ==================================================
    def route(
        self,
        text,
        score,
        tags,
        emotion
    ):

        if not text:

            return {
                "routes": ["conversation"],
                "primary": "conversation",
                "confidence": {
                    "conversation": 0.5
                }
            }

        try:

            t = text.lower().strip()

            routes = []

            confidence = {}

            tags = tags or []

            emotion = emotion or {}


            # ==================================================
            # ⭐ IMPORTANT MEMORY
            # ==================================================
            if score >= self.importance_threshold:

                routes.append("conversation")

                confidence["conversation"] = 0.95


            # ==================================================
            # 👤 IDENTITY MEMORY
            # ==================================================
            identity_patterns = [
                "i am",
                "i'm",
                "my name",
                "i was",
                "i work as",
                "i live",
                "my age",
                "i study",
                "i like to be called",
            ]

            if any(
                phrase in t
                for phrase in identity_patterns
            ):

                routes.append("identity")

                confidence["identity"] = 0.85


            # ==================================================
            # ❤️ PREFERENCES
            # ==================================================
            preference_patterns = [
                "i like",
                "i love",
                "i hate",
                "i prefer",
                "favorite",
                "i enjoy",
            ]

            if any(
                phrase in t
                for phrase in preference_patterns
            ):

                routes.append("preferences")

                confidence["preferences"] = 0.80


            # ==================================================
            # 🤝 RELATIONSHIP SIGNALS
            # ==================================================
            relationship_patterns = [
                "trust you",
                "miss you",
                "feel safe",
                "you matter",
                "need you",
                "with you",
                "care about you",
                "love you",
            ]

            if any(
                phrase in t
                for phrase in relationship_patterns
            ):

                routes.append("relationship")

                confidence["relationship"] = 0.90


            # ==================================================
            # ❤️ EMOTIONAL MEMORIES
            # ==================================================
            if (
                isinstance(emotion, dict)
                and
                emotion.get(
                    "intensity",
                    0.5
                ) >= self.emotional_threshold
            ):

                # ⚠️ FIX: Route emotional memories into safely available folders
                if "relationship" not in routes:

                    routes.append("relationship")

                confidence["relationship"] = max(
                    confidence.get(
                        "relationship",
                        0.0
                    ),
                    0.90
                )


            # ==================================================
            # 🎯 GOALS / TASKS
            # ==================================================
            goal_patterns = [
                "i want to",
                "my goal",
                "i plan to",
                "i need to",
                "i will",
                "trying to",
            ]

            if any(
                phrase in t
                for phrase in goal_patterns
            ):

                routes.append("conversation")

                confidence["conversation"] = max(
                    confidence.get(
                        "conversation",
                        0.0
                    ),
                    0.75
                )


            # ==================================================
            # 🔁 HABITS / ROUTINES
            # ==================================================
            habit_patterns = [
                "every day",
                "usually",
                "always",
                "often",
                "routine",
            ]

            if any(
                phrase in t
                for phrase in habit_patterns
            ):

                routes.append("preferences")

                confidence["preferences"] = max(
                    confidence.get(
                        "preferences",
                        0.0
                    ),
                    0.70
                )


            # ==================================================
            # 🧠 TAG-BASED ROUTING
            # ==================================================
            lowered_tags = [
                str(t).lower()
                for t in tags
            ]

            if "reflection" in lowered_tags:

                routes.append("reflections")

                confidence["reflections"] = 0.85


            # ==================================================
            # 📁 FILTER INVALID ROUTES
            # ==================================================
            routes = [
                r for r in routes
                if r in self.valid_routes
            ]


            # ==================================================
            # 🧠 FALLBACK
            # ==================================================
            if not routes:

                routes = ["conversation"]

                confidence["conversation"] = 0.5


            # ==================================================
            # 🧠 REMOVE DUPLICATES
            # ==================================================
            routes = list(
                dict.fromkeys(routes)
            )

            return {
                "routes": routes,
                "primary": routes[0],
                "confidence": confidence,
            }

        except Exception as e:
            logger.exception("[MEMORY ROUTER ERROR] %s", e)

            return {
                "routes": ["conversation"],
                "primary": "conversation",
                "confidence": {
                    "conversation": 0.5
                }
            }


    # ==================================================
    # 🛠️ INTERNAL UTILITIES
    # ==================================================
    def _extract_json(self, text: str) -> dict:
        """Safely clean markdown artifacts and parse raw JSON text fields from LLM."""
        if not text:
            return {}
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Fallback wrapper cleaner if the LLM slips up and returns codeblocks
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0).strip())
                except json.JSONDecodeError:
                    logger.debug("[Router] JSON fallback parse failed — returning empty")
            return {}


    # ==================================================
    # 📊 DEBUG ROUTING
    # ==================================================
    def stats(self):

        return {
            "importance_threshold":
                self.importance_threshold,
            "emotional_threshold":
                self.emotional_threshold,
            "valid_routes":
                list(self.valid_routes),
        }