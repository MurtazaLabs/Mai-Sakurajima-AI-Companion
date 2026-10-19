# Mai_ai/memory/reflection.py
import logging
import random
import threading
from collections import Counter
from typing import Any

logger = logging.getLogger(__name__)

from app.config_loader import Settings


class MemoryReflectionEngine:

    def __init__(self):

        # ==================================================
        # 🧠 THREAD SAFETY
        # ==================================================

        self.lock = threading.RLock()

        # ==================================================
        # 🧠 CONFIG
        # ==================================================

        self.history_limit = (
            Settings.REFLECTION_HISTORY_LIMIT
        )

        self.max_ranked_nodes = (
            Settings.REFLECTION_MAX_RANKED_NODES
        )

        self.max_top_reflections = (
            Settings.REFLECTION_MAX_TOP_RESULTS
        )

        # ==================================================
        # 🧠 RUNTIME MEMORY
        # ==================================================

        self.previous_reflections = []

    # ==================================================
    # 🧠 MAIN REFLECTION SYSTEM
    # ==================================================

    def generate(
        self,
        nodes
    ):

        if not nodes:
            return None

        if not isinstance(nodes, list):
            return None

        with self.lock:

            try:

                # ==================================================
                # 🧠 PRIORITIZE IMPORTANT MEMORIES
                # ==================================================

                ranked_nodes = sorted(

                    nodes,

                    key=lambda n: (

                        getattr(
                            n,
                            "score",
                            Settings.REFLECTION_DEFAULT_SCORE
                        )

                        *

                        max(
                            1,
                            getattr(
                                n,
                                "reinforcement_count",
                                0
                            )
                        )
                    ),

                    reverse=True

                )[:self.max_ranked_nodes]

                reflections = []

                # ==================================================
                # 🧠 PATTERN TRACKING
                # ==================================================

                tag_counter: Counter[str] = Counter()

                emotion_counter: Counter[str] = Counter()

                memory_type_counter: Counter[str] = Counter()

                # ==================================================
                # 🧠 ANALYZE MEMORIES
                # ==================================================

                for node in ranked_nodes:

                    tags = getattr(
                        node,
                        "tags",
                        []
                    )

                    if not isinstance(tags, list):
                        tags = []

                    emotion = getattr(
                        node,
                        "emotion",
                        {}
                    )

                    if not isinstance(emotion, dict):
                        emotion = {}

                    memory_type = getattr(
                        node,
                        "memory_type",
                        "conversation"
                    )

                    # ==================================================
                    # 🧠 COUNT PATTERNS
                    # ==================================================

                    for tag in tags:

                        tag_counter[
                            str(tag).lower()
                        ] += 1

                    emotion_type = str(
                        emotion.get(
                            "type",
                            "neutral"
                        )
                    ).lower()

                    emotion_counter[
                        emotion_type
                    ] += 1

                    memory_type_counter[
                        memory_type
                    ] += 1

                    # ==================================================
                    # 🧠 CODING INTEREST
                    # ==================================================

                    if any(
                        tag in tags
                        for tag in [
                            "coding",
                            "programming"
                        ]
                    ):

                        reflections.append({

                            "text":
                                "User consistently shows strong interest in coding and technical topics.",

                            "confidence":
                                Settings.REFLECTION_CODING_CONFIDENCE,

                            "type":
                                "interest"
                        })

                    # ==================================================
                    # 🧠 AI INTEREST
                    # ==================================================

                    node_text = str(
                        getattr(
                            node,
                            "text",
                            ""
                        )
                    ).lower()

                    if any(
                        keyword in node_text
                        for keyword in
                        Settings.REFLECTION_AI_KEYWORDS
                    ):

                        reflections.append({

                            "text":
                                "User frequently explores AI and intelligence-related ideas.",

                            "confidence":
                                Settings.REFLECTION_AI_CONFIDENCE,

                            "type":
                                "interest"
                        })

                    # ==================================================
                    # 🧠 EMOTIONAL LEARNING
                    # ==================================================

                    if emotion_type in (
                        Settings.REFLECTION_POSITIVE_EMOTIONS
                    ):

                        reflections.append({

                            "text":
                                "The current conversational style appears emotionally positive for the user.",

                            "confidence":
                                Settings.REFLECTION_EMOTIONAL_CONFIDENCE,

                            "type":
                                "emotional"
                        })

                    if emotion_type in (
                        Settings.REFLECTION_NEGATIVE_EMOTIONS
                    ):

                        reflections.append({

                            "text":
                                "Certain conversational patterns may create emotional friction for the user.",

                            "confidence":
                                Settings.REFLECTION_EMOTIONAL_CONFIDENCE,

                            "type":
                                "emotional"
                        })

                    # ==================================================
                    # 🧠 PERSONAL DISCLOSURE
                    # ==================================================

                    if (
                        "personal" in tags
                        or
                        memory_type == "identity"
                    ):

                        reflections.append({

                            "text":
                                "User increasingly shares personal thoughts and identity-related information.",

                            "confidence":
                                Settings.REFLECTION_RELATIONSHIP_CONFIDENCE,

                            "type":
                                "relationship"
                        })

                # ==================================================
                # 🧠 LONG-TERM PATTERNS
                # ==================================================

                if tag_counter.get(
                    "coding",
                    0
                ) >= Settings.REFLECTION_CODING_THRESHOLD:

                    reflections.append({

                        "text":
                            "Coding appears to be a stable long-term interest.",

                        "confidence":
                            Settings.REFLECTION_PATTERN_CONFIDENCE,

                        "type":
                            "pattern"
                    })

                if tag_counter.get(
                    "personal",
                    0
                ) >= Settings.REFLECTION_PERSONAL_THRESHOLD:

                    reflections.append({

                        "text":
                            "User is becoming increasingly comfortable with personal disclosure.",

                        "confidence":
                            Settings.REFLECTION_PERSONAL_CONFIDENCE,

                        "type":
                            "relationship"
                    })

                if (
                    emotion_counter.get(
                        "positive",
                        0
                    )
                    >
                    emotion_counter.get(
                        "negative",
                        0
                    )
                ):

                    reflections.append({

                        "text":
                            "Recent interactions have generally carried a positive emotional tone.",

                        "confidence":
                            Settings.REFLECTION_POSITIVE_TONE_CONFIDENCE,

                        "type":
                            "emotional"
                    })

                if memory_type_counter.get(
                    "relationship",
                    0
                ) >= Settings.REFLECTION_RELATIONSHIP_THRESHOLD:

                    reflections.append({

                        "text":
                            "Relationship-oriented interactions are becoming increasingly significant.",

                        "confidence":
                            Settings.REFLECTION_RELATIONSHIP_PATTERN_CONFIDENCE,

                        "type":
                            "relationship"
                    })

                # ==================================================
                # 🚫 NO REFLECTIONS
                # ==================================================

                if not reflections:
                    return None

                # ==================================================
                # 🚫 REMOVE REPETITIONS
                # ==================================================

                available: list[dict[str, Any]] = [

                    reflection

                    for reflection in reflections

                    if reflection["text"]
                    not in self.previous_reflections
                ]

                if not available:
                    available = reflections

                # ==================================================
                # 🧠 PRIORITIZE CONFIDENT REFLECTIONS
                # ==================================================

                available = sorted(

                    available,

                    key=lambda r: float(
                        r.get(
                            "confidence",
                            Settings.REFLECTION_DEFAULT_CONFIDENCE
                        )
                    ),

                    reverse=True
                )

                top_reflections = available[
                    :self.max_top_reflections
                ]

                selected = random.choice(
                    top_reflections
                )

                # ==================================================
                # 🧠 STORE HISTORY
                # ==================================================

                self._remember(
                    selected["text"]
                )

                return {

                    "reflection":
                        selected["text"],

                    "confidence":
                        round(
                            float(
                                selected.get(
                                    "confidence",
                                    Settings.REFLECTION_DEFAULT_CONFIDENCE
                                )
                            ),
                            3
                        ),

                    "type":
                        selected.get(
                            "type",
                            "general"
                        ),

                    "total_patterns":
                        len(reflections),

                    "dominant_tags":
                        dict(
                            tag_counter.most_common(
                                Settings.REFLECTION_TOP_TAGS
                            )
                        ),

                    "dominant_emotions":
                        dict(
                            emotion_counter.most_common(
                                Settings.REFLECTION_TOP_EMOTIONS
                            )
                        )
                }

            except Exception as e:
                logger.exception("[REFLECTION ERROR] %s", e)
                return None

    # ==================================================
    # 🧠 STORE REFLECTION HISTORY
    # ==================================================

    def _remember(
        self,
        reflection
    ):

        if not reflection:
            return

        with self.lock:

            self.previous_reflections.append(
                reflection
            )

            # 🧠 limit memory growth
            if (
                len(self.previous_reflections)
                >
                self.history_limit
            ):

                self.previous_reflections.pop(0)

    # ==================================================
    # 🧹 CLEAR HISTORY
    # ==================================================

    def clear_history(self):

        with self.lock:

            self.previous_reflections.clear()

    # ==================================================
    # 📊 DEBUG STATS
    # ==================================================

    def stats(self):

        with self.lock:

            return {

                "stored_reflections":
                    len(
                        self.previous_reflections
                    ),

                "history_limit":
                    self.history_limit,

                "max_ranked_nodes":
                    self.max_ranked_nodes
            }