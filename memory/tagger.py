# Mai_ai/memory/tagger.py
import re


class Tagger:

    def __init__(self):

        self.tag_map = {

            "coding": [

                "code",
                "coding",
                "programming",
                "developer",
                "python",
                "javascript",
                "software",
                "debug",
                "ai",
                "backend",
                "frontend"
            ],

            "gaming": [

                "game",
                "gaming",
                "minecraft",
                "valorant",
                "fps",
                "rpg",
                "steam"
            ],

            "emotion": [

                "sad",
                "happy",
                "angry",
                "lonely",
                "afraid",
                "love",
                "hate",
                "miss"
            ],

            "relationship": [

                "trust",
                "close",
                "miss you",
                "care",
                "love you",
                "feel safe"
            ],

            "goals": [

                "goal",
                "dream",
                "plan",
                "future",
                "build",
                "create",
                "want to"
            ],

            "learning": [

                "learn",
                "study",
                "research",
                "understand",
                "improve"
            ],

            "productivity": [

                "work",
                "task",
                "schedule",
                "focus",
                "project"
            ],

            # From identity/preferences.py — topics Mai likes
            "likes": [

                "book",
                "reading",
                "astronomy",
                "star",
                "space",
                "telescope",
                "music",
                "song",
                "melody",
                "technology",
                "tech",
                "deep conversation",
                "philosophy",
                "meaning",
                "quiet",
                "calm",
                "learning",
                "curious"
            ],

            # From identity/preferences.py — topics Mai avoids
            "dislikes": [

                "dishonest",
                "lying",
                "manipulate",
                "manipulation",
                "conflict",
                "repetitive",
                "boring",
                "waste time",
                "pointless"
            ]
        }

    # ==================================================
    # 🧠 EXTRACT TAGS
    # ==================================================

    def extract_tags(self, text):

        if not text:
            return []

        t = str(text).lower()

        tags = []

        cleaned = re.sub(
            r"[^\w\s]",
            " ",
            t
        )

        cleaned = re.sub(
            r"\s+",
            " ",
            cleaned
        ).strip()

        for tag, keywords in self.tag_map.items():

            for keyword in keywords:

                keyword = keyword.lower()

                # 🛡️ proper phrase matching
                if keyword in t or keyword in cleaned:

                    tags.append(tag)

                    break

        if "?" in text:
            tags.append("question")

        if any(
            phrase in t
            for phrase in [
                "i feel",
                "i think",
                "i want",
                "i need"
            ]
        ):

            tags.append("personal")

        if len(text.split()) > 40:

            tags.append(
                "deep_conversation"
            )

        tags = list(
            dict.fromkeys(tags)
        )

        return tags

    # ==================================================
    # ➕ ADD KEYWORD
    # ==================================================

    def add_keyword(
        self,
        tag,
        keyword
    ):

        if tag not in self.tag_map:
            self.tag_map[tag] = []

        keyword = keyword.lower()

        if keyword not in self.tag_map[tag]:

            self.tag_map[tag].append(
                keyword
            )

    # ==================================================
    # 📊 DEBUG
    # ==================================================

    def explain(self, text):

        return {

            "text": text,

            "tags":
                self.extract_tags(text)
        }