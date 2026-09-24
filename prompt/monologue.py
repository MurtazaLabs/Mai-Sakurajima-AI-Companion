# prompt/monologue.py


class MonologuePrompt:

    def build(self, enabled=True):
        if not enabled:
            return ""
        return (
            "OPTIONAL THOUGHT ENVELOPE\n"
            "You may open your reply with a single JSON object to record your inner "
            "processing before the spoken words. Use exactly this shape:\n"
            "{\"thought\": \"...\", \"decision\": \"...\", \"speech_plan\": "
            "{...}, \"response\": \"...\"}\n"
            "Rules:\n"
            "- `response` is the ONLY text that is spoken aloud. It is required.\n"
            "- If you do not open with the envelope, the whole reply is spoken as-is "
            "(no envelope, no markdown fences).\n"
            "- `thought` (private reasoning), `decision` (what you chose and why), "
            "and `speech_plan` (intention, tone, pacing, sentence_length, register) "
            "are journaled internally and never spoken.\n"
            "- Keep the envelope compact: one JSON object, no format narration."
        )