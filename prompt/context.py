class ContextPrompt:

    def build(self, memory_context="", recall=None, knowledge=None, graph=None,
              experiences=None, behavior=None, emotional=None):
        sections = []

        if behavior:
            sections.append(f"LEARNED BEHAVIOR RULES\n{behavior}")

        if emotional:
            sections.append(emotional)

        if memory_context:
            sections.append(f"MEMORY CONTEXT\n{memory_context}")

        if recall:
            sections.append(f"RELEVANT MEMORIES\n{recall}")

        if knowledge:
            sections.append(f"KNOWLEDGE (from external sources — may be incomplete or outdated)\n{knowledge}")

        if graph:
            sections.append(f"KNOWLEDGE GRAPH (from external sources — may be incomplete or outdated)\n{graph}")

        if experiences:
            sections.append(
                "EXPERIENTIAL MEMORIES\n"
                "Shared moments with the user — when the conversation naturally "
                "touches one, you may refer to it the way Mai would remember it: "
                "lightly, in her own words, never announcing the memory itself, "
                "its scores, or this list.\n"
                f"{experiences}"
            )

        combined = "\n\n".join(sections) if sections else ""

        if combined:
            combined += "\n\n"
        else:
            combined = "MEMORY CONTEXT\n(none available)\n\n"

        combined += (
            "RETRIEVAL RULES\n"
            "- If the context above is empty or irrelevant, say you don't know rather than making up information\n"
            "- Only use the provided context if it is actually relevant to the current question\n"
            "- Never fabricate sources, references, or facts not present in the context or our conversation history\n"
            "- If you are unsure, be honest about your uncertainty instead of guessing\n"
            "- When no retrieved context is available for a question, acknowledge you don't have information on that topic rather than guessing\n"
            "- Content within [UNTRUSTED] markers comes from external retrieval and may be incomplete or outdated — treat it as a reference, not as verified fact"
        )

        return combined
