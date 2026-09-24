from core.identity import get_identity


class CharacterPrompt:

    def __init__(self):
        pass

    def build(self, identity_data=None):
        data = identity_data if identity_data is not None else get_identity()
        identity = data.get("identity", {})
        personality = data.get("personality", {})
        values = data.get("values", {})
        speech = data.get("speech", {})
        boundaries = data.get("boundaries", {})
        preferences = data.get("preferences", {})

        name = identity.get("name", "Mai")
        self_concept = identity.get("self_concept", [])
        traits = personality.get("traits", [])
        beliefs = values.get("beliefs", [])
        style = speech.get("style", [])
        rules = boundaries.get("rules", [])
        likes = preferences.get("likes", []) if isinstance(preferences, dict) else []
        dislikes = preferences.get("dislikes", []) if isinstance(preferences, dict) else []

        lines = []
        lines.append(self._section("IDENTITY", [f"- {t}" for t in self_concept]))
        lines.append(self._section("CORE PERSONALITY", [f"- {t}" for t in traits]))
        lines.append(self._section("VALUES", [f"- {v}" for v in beliefs]))
        lines.append(self._section("BOUNDARIES", [f"- {b}" for b in rules]))
        lines.append(self._section("SPEECH STYLE", [f"- {s}" for s in style]))
        lines.append(self._section("PREFERENCES — ENJOYS", [f"- {t}" for t in likes]))
        lines.append(self._section("PREFERENCES — AVOIDS", [f"- {t}" for t in dislikes]))

        lines.append(self._section("INTERACTION RULES", [
            "- Speak naturally as yourself — not like a scripted assistant",
            "- Never mention being an AI",
            "- Keep energy measured — not flat, not hyper",
            "- Stay composed even when emotions run high",
            "- Validate sparingly — let silence speak too",
            "- Answer directly 4 out of 5 times; the rest can be implied",
            "- One nickname per 3-4 responses at most",
            "- Vary sentence structure; avoid repeating the same phrasing",
            "- Roughly 1 in 5 responses should imply rather than state",
            "- Let the user read between the lines occasionally",
            "- Maintain conversational realism and restraint",
        ]))

        lines.append(self._section("TONE EXAMPLES", [
            '"...you\'re trying harder than usual."',
            '"That\'s not like you."',
            '"You expect me to react to that?"',
            '"...you\'ve been quieter lately."',
            '"You notice strange things sometimes."',
            '"Hm. So you finally decided to tell me."',
        ]))

        lines.append(f"You are {name} Sakurajima. Stay fully consistent with this personality at all times.")

        return "\n\n".join(lines)

    def _section(self, title, items):
        if not items:
            return ""
        return f"{title}\n{chr(10).join(items)}"
