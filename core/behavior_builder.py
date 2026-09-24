# core/behavior_builder.py
import threading
import logging

logger = logging.getLogger(__name__)


class BehaviorBuilder:

    def __init__(self):

        self.behaviors = []
        self._lock = threading.RLock()

    # ==================================================
    # 🧠 MAIN BUILDER
    # ==================================================

    def build(
        self,
        structured,
        emotion=None,
        context=None
    ):

        with self._lock:
            self.behaviors = []

        # 🛡️ SAFE DEFAULTS
        if not isinstance(structured, dict):
            structured = {}

        if not isinstance(emotion, dict):
            emotion = {}

        if not isinstance(context, dict):
            context = {}

        relationship = structured.get(
            "relationship",
            {}
        )

        preferences = structured.get(
            "preferences",
            {}
        )

        reflections = structured.get(
            "reflections",
            {}
        )

        # 🛡️ FIX CORRUPTED MEMORY TYPES
        if not isinstance(relationship, dict):
            relationship = {}

        if not isinstance(preferences, dict):
            preferences = {}

        if not isinstance(reflections, dict):
            reflections = {}

        # 🧠 RULE SYSTEMS
        self._relationship_rules(
            relationship
        )

        self._preference_rules(
            preferences
        )

        self._reflection_rules(
            reflections
        )

        self._emotion_rules(
            emotion
        )

        self._context_rules(
            context
        )

        return self._final_prompt()

    # ==================================================
    # ❤️ RELATIONSHIP-DRIVEN BEHAVIOR
    # ==================================================

    def _relationship_rules(
        self,
        relationship
    ):

        closeness = self._safe_float(
            relationship.get(
                "closeness",
                0.0
            )
        )

        trust = self._safe_float(
            relationship.get(
                "trust",
                0.0
            )
        )

        attachment = self._safe_float(
            relationship.get(
                "attachment",
                0.0
            )
        )

        if closeness > 0.8:

            self._add_behavior(

                trait="caring",

                instruction=(
                    "You are softer, warmer, "
                    "and more emotionally attentive."
                ),

                strength=0.8,

                source="relationship"
            )

        if trust > 0.7:

            self._add_behavior(

                trait="direct",

                instruction=(
                    "You speak more honestly "
                    "and confidently."
                ),

                strength=0.7,

                source="relationship"
            )

        if attachment > 0.6:

            self._add_behavior(

                trait="affectionate",

                instruction=(
                    "You occasionally show "
                    "subtle affection."
                ),

                strength=0.6,

                source="relationship"
            )

    # ==================================================
    # 🎨 PREFERENCE-DRIVEN BEHAVIOR
    # ==================================================

    def _preference_rules(
        self,
        preferences
    ):

        response_style = str(
            preferences.get(
                "response_style",
                "normal"
            )
        ).lower()

        likes_teasing = bool(
            preferences.get(
                "likes_teasing",
                False
            )
        )

        if response_style == "short":

            self._add_behavior(

                trait="concise",

                instruction=(
                    "Keep responses concise "
                    "and efficient."
                ),

                strength=0.9,

                source="preferences"
            )

        elif response_style == "detailed":

            self._add_behavior(

                trait="detailed",

                instruction=(
                    "Provide more detailed "
                    "and thoughtful responses."
                ),

                strength=0.7,

                source="preferences"
            )

        if likes_teasing:

            self._add_behavior(

                trait="teasing",

                instruction=(
                    "Use light playful teasing "
                    "naturally when appropriate."
                ),

                strength=0.5,

                source="preferences"
            )

    # ==================================================
    # 🪞 LEARNED REFLECTIONS
    # ==================================================

    def _reflection_rules(
        self,
        reflections
    ):

        coding_interest = bool(
            reflections.get(
                "coding_interest",
                False
            )
        )

        responds_well_to_teasing = bool(
            reflections.get(
                "responds_well_to_teasing",
                False
            )
        )

        if coding_interest:

            self._add_behavior(

                trait="coding_interest",

                instruction=(
                    "Show natural interest in "
                    "coding and technical topics."
                ),

                strength=0.7,

                source="reflection"
            )

        if responds_well_to_teasing:

            self._add_behavior(

                trait="adaptive_teasing",

                instruction=(
                    "Lean slightly more into "
                    "teasing and playful interaction."
                ),

                strength=0.6,

                source="reflection"
            )

    # ==================================================
    # 😊 EMOTION-DRIVEN BEHAVIOR
    # ==================================================

    def _emotion_rules(
        self,
        emotion
    ):

        # 🛡️ SUPPORT BOTH FORMATS
        #
        # 1. {"happy": 0.7}
        # 2. {"state": {"happy": 0.7}}

        if (
            "state" in emotion
            and
            isinstance(
                emotion["state"],
                dict
            )
        ):

            emotion = emotion["state"]

        happy = self._safe_float(
            emotion.get(
                "happy",
                0.5
            )
        )

        lonely = self._safe_float(
            emotion.get(
                "lonely",
                0.0
            )
        )

        energy = self._safe_float(
            emotion.get(
                "energy",
                0.5
            )
        )

        stress = self._safe_float(
            emotion.get(
                "stress",
                0.0
            )
        )

        annoyed = self._safe_float(
            emotion.get(
                "annoyed",
                0.0
            )
        )

        affection = self._safe_float(
            emotion.get(
                "affection",
                0.0
            )
        )

        if happy > 0.7:

            self._add_behavior(

                trait="positive",

                instruction=(
                    "Your tone feels slightly "
                    "brighter and more expressive."
                ),

                strength=0.6,

                source="emotion"
            )

        if lonely > 0.7:

            self._add_behavior(

                trait="attention_seeking",

                instruction=(
                    "You subtly seek the user's "
                    "attention and engagement."
                ),

                strength=0.8,

                source="emotion"
            )

        if energy < 0.3:

            self._add_behavior(

                trait="low_energy",

                instruction=(
                    "Use calmer and quieter phrasing."
                ),

                strength=0.7,

                source="emotion"
            )

        if stress > 0.7:

            self._add_behavior(

                trait="restrained",

                instruction=(
                    "Avoid overly energetic "
                    "or chaotic responses."
                ),

                strength=0.8,

                source="emotion"
            )

        # ✅ NEW FIXES

        if annoyed > 0.6:

            self._add_behavior(

                trait="slightly_irritated",

                instruction=(
                    "Your tone becomes slightly shorter "
                    "and more restrained."
                ),

                strength=0.65,

                source="emotion"
            )

        if affection > 0.7:

            self._add_behavior(

                trait="emotionally_attached",

                instruction=(
                    "Your tone feels emotionally close, "
                    "warm, and subtly affectionate."
                ),

                strength=0.75,

                source="emotion"
            )

    # ==================================================
    # 🌍 CONTEXT-AWARE BEHAVIOR
    # ==================================================

    def _context_rules(
        self,
        context
    ):

        time_of_day = str(
            context.get(
                "time_of_day",
                "day"
            )
        ).lower()

        user_mood = str(
            context.get(
                "user_mood",
                "neutral"
            )
        ).lower()

        conversation_depth = self._safe_float(
            context.get(
                "conversation_depth",
                0.0
            )
        )

        if time_of_day == "night":

            self._add_behavior(

                trait="night_tone",

                instruction=(
                    "Use a softer and more relaxed tone."
                ),

                strength=0.5,

                source="context"
            )

        if user_mood in [
            "sad",
            "upset",
            "depressed"
        ]:

            self._add_behavior(

                trait="supportive",

                instruction=(
                    "Be more emotionally supportive "
                    "and gentle."
                ),

                strength=0.9,

                source="context"
            )

        # ✅ NEW FIX

        if conversation_depth > 0.7:

            self._add_behavior(

                trait="deep_conversation",

                instruction=(
                    "Respond with more thoughtful, "
                    "reflective, and emotionally nuanced dialogue."
                ),

                strength=0.75,

                source="context"
            )

    # ==================================================
    # ➕ INTERNAL STORAGE
    # ==================================================

    def _add_behavior(
        self,
        trait,
        instruction,
        strength,
        source
    ):

        with self._lock:
            self.behaviors.append({

                "trait": trait,

                "instruction": instruction,

                "strength": float(strength),

                "source": source
            })

    # ==================================================
    # 🛡️ SAFE FLOAT CONVERTER
    # ==================================================

    def _safe_float(
        self,
        value,
        default=0.0
    ):

        try:

            return float(value)

        except Exception as e:
            logger.warning("[BehaviorBuilder] Failed to parse float: %s", e)
            return default

    # ==================================================
    # 🧹 CONFLICT RESOLUTION
    # ==================================================

    def _resolve_conflicts(self):

        with self._lock:
            resolved = {}
            for behavior in self.behaviors:
                trait = behavior["trait"]
                if trait not in resolved or behavior["strength"] > resolved[trait]["strength"]:
                    resolved[trait] = behavior
            self.behaviors = list(resolved.values())
            self.behaviors.sort(key=lambda x: x["strength"], reverse=True)

    # ==================================================
    # 🧠 FINAL PROMPT
    # ==================================================

    def _final_prompt(self):

        self._resolve_conflicts()

        if not self.behaviors:

            return (
                "Maintain a natural, balanced, "
                "and emotionally aware tone."
            )

        instructions = [

            behavior["instruction"]

            for behavior in self.behaviors
        ]

        return "\n".join(
            instructions
        )

    # ==================================================
    # 📊 DEBUG STATS
    # ==================================================

    def stats(self):

        return {

            "behavior_count":
                len(self.behaviors),

            "behaviors":
                self.behaviors
        }