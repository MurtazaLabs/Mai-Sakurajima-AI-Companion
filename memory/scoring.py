# Mai_ai/memory/scoring.py
import re


class MemoryScorer:

    def __init__(self):

        self.base_score = 0.2

        self.strong_emotions = {

            "love": 0.3,
            "hate": 0.3,
            "miss": 0.25,
            "afraid": 0.35,
            "sad": 0.25,
            "happy": 0.2,
            "angry": 0.25,
            "lonely": 0.35,
            "trust": 0.25,
            "important": 0.4,
            "never forget": 0.5
        }

        self.identity_phrases = [

            "i am",
            "my name",
            "i work",
            "i live",
            "i was born",
            "my goal",
            "i dream"
        ]

    # ==================================================
    # 🧠 MAIN SCORE
    # ==================================================

    def score(
        self,
        text,
        emotion=None,
        reinforcement=1,
        novelty=1.0
    ):

        if not text:
            return 0.0

        t = str(text).lower()

        score = self.base_score

        # 🧠 explicit memory signals
        if any(
            phrase in t
            for phrase in [
                "remember",
                "don't forget",
                "important"
            ]
        ):

            score += 0.4

        # ❤️ emotional salience
        for word, value in self.strong_emotions.items():

            pattern = (
                r"\b"
                + re.escape(word)
                + r"\b"
            )

            if re.search(pattern, t):

                score += value

        # 🧠 identity importance
        if any(
            phrase in t
            for phrase in self.identity_phrases
        ):

            score += 0.25

        word_count = len(t.split())

        if word_count > 25:
            score += 0.05

        if word_count > 60:
            score += 0.05

        # 😊 emotion intensity
        if (
            emotion
            and
            isinstance(emotion, dict)
        ):

            intensity = float(
                emotion.get(
                    "intensity",
                    0.5
                )
            )

            score += intensity * 0.2

        # 🔁 reinforcement
        score += min(
            reinforcement * 0.03,
            0.15
        )

        # ✨ novelty
        score *= float(novelty)

        # ❓ questions
        if "?" in t:
            score += 0.03

        # 🧠 disclosure
        if any(
            phrase in t
            for phrase in [
                "i feel",
                "i think",
                "i want",
                "i need"
            ]
        ):

            score += 0.08

        score = max(
            0.0,
            min(score, 1.0)
        )

        return round(score, 2)

    # ==================================================
    # 📊 DEBUG
    # ==================================================

    def explain(self, text):

        return {

            "text": text,

            "score":
                self.score(text)
        }