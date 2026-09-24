# Mai_ai/memory/emotion_analyzer.py
import re


class EmotionAnalyzer:
    def __init__(self):

        # 🧠 emotional vocabulary
        self.emotions = {

            "affection": [
                "love",
                "adore",
                "care",
                "miss",
                "darling",
                "cherish"
            ],

            "joy": [
                "happy",
                "excited",
                "great",
                "amazing",
                "fun",
                "wonderful"
            ],

            "sadness": [
                "sad",
                "hurt",
                "cry",
                "lonely",
                "depressed",
                "upset"
            ],

            "anger": [
                "hate",
                "angry",
                "annoyed",
                "furious",
                "mad",
                "irritated"
            ],

            "fear": [
                "afraid",
                "scared",
                "worried",
                "anxious",
                "nervous"
            ],

            "stress": [
                "tired",
                "exhausted",
                "overwhelmed",
                "burned out",
                "stressed"
            ]
        }

        # ⚡ intensity modifiers
        self.intensity_words = {

            "very": 0.15,

            "really": 0.15,

            "extremely": 0.25,

            "so": 0.10,

            "a lot": 0.10
        }

    # 🧠 analyze emotional state
    def analyze(self, text):

        if not text:

            return self._neutral()

        text = text.lower()

        scores = {}

        # 🔍 detect emotions
        for emotion, keywords in self.emotions.items():

            score = 0

            for keyword in keywords:

                matches = len(
                    re.findall(
                        rf"\b{re.escape(keyword)}\b",
                        text
                    )
                )

                score += matches

            if score > 0:
                scores[emotion] = score

        # 😐 no emotion detected
        if not scores:

            return self._neutral()

        # ⚡ intensity calculation
        intensity = 0.5

        for word, boost in self.intensity_words.items():

            if word in text:
                intensity += boost

        intensity = min(1.0, intensity)

        # 🧠 strongest emotion
        dominant = max(
            scores,
            key=lambda k: scores[k],
            default="neutral"
        )

        # 🎭 mixed emotions
        mixed = [
            emotion
            for emotion, value in scores.items()
            if value >= 1 and emotion != dominant
        ]

        # 📊 confidence
        total_score = sum(scores.values())

        confidence = min(
            1.0,
            0.5 + total_score * 0.1
        )

        return {

            "type": dominant,

            "intensity": round(
                intensity,
                2
            ),

            "confidence": round(
                confidence,
                2
            ),

            "secondary": mixed,

            "raw_scores": scores
        }

    # 😐 fallback neutral state
    def _neutral(self):

        return {

            "type": "neutral",

            "intensity": 0.3,

            "confidence": 1.0,

            "secondary": [],

            "raw_scores": {}
        }