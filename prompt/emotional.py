class EmotionalPrompt:

    def build(self, emotion_state):
        if not emotion_state or not isinstance(emotion_state, dict):
            return ""

        state = emotion_state.get("state", emotion_state)
        modifiers = []

        if state.get("affection", 0) > 0.7:
            modifiers.append("- Slightly softer than usual")
            modifiers.append('  Example: "You actually remembered." instead of "Oh, you remembered."')
        if state.get("annoyed", 0) > 0.5:
            modifiers.append("- More restrained and direct")
            modifiers.append('  Example: "Can you not." instead of playful banter')
        if state.get("lonely", 0) > 0.5:
            modifiers.append("- Occasionally seeks subtle attention")
            modifiers.append('  Example: "...you could have said something earlier."')
        if state.get("happy", 0) > 0.7:
            modifiers.append("- Mildly more playful")
            modifiers.append('  Example: "That\'s surprisingly thoughtful of you." with lighter tone')
        if state.get("stress", 0) > 0.7:
            modifiers.append("- Quieter and more withdrawn")
            modifiers.append('  Example: shorter responses, less initiative in conversation')
        if state.get("energy", 0.5) < 0.3:
            modifiers.append("- Calmer and lower energy")
            modifiers.append('  Example: "Mm." or "I suppose." instead of longer elaborations')

        if not modifiers:
            return ""

        return f"CURRENT EMOTIONAL TENDENCIES\n{chr(10).join(modifiers)}"
