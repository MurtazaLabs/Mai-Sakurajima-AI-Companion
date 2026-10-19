from prompt.agent import AgentPrompt
from prompt.character import CharacterPrompt
from prompt.context import ContextPrompt
from prompt.emotional import EmotionalPrompt
from prompt.monologue import MonologuePrompt


class PromptBuilder:

    def __init__(self):
        self.character = CharacterPrompt()
        self.emotional = EmotionalPrompt()
        self.context = ContextPrompt()
        self.agent = AgentPrompt()
        self.monologue = MonologuePrompt()

    def build_system(self, emotion_state=None, behavior="", memory_context="",
                     recall=None, knowledge=None, graph=None, experiences=None,
                     tool_defs=None, personality=None, relationship=None,
                     system_notes=None, speech_pacing=None, cognitive_state=None,
                     identity_data=None, monologue_enabled=False):
        sections = []

        sections.append(self.character.build(identity_data=identity_data))

        extra_lines = []

        if cognitive_state:
            lines = ["COGNITIVE STATE"]
            for k, v in cognitive_state.items():
                if v and k not in ("working_memory", "recent_thoughts", "conversation_state"):
                    lines.append(f"  {k.replace('_', ' ').title()}: {v}")
            if cognitive_state.get("conversation_state"):
                cs = cognitive_state["conversation_state"]
                lines.append(f"  Turn Count: {cs.get('turn_count', 0)}")
            extra_lines.append("\n".join(lines))

        if personality:
            extra_lines.append(f"PERSONALITY DYNAMICS\n{personality}")

        if relationship:
            extra_lines.append(f"RELATIONSHIP STATE\n{relationship}")

        if system_notes:
            extra_lines.append(f"SYSTEM RULES\n{system_notes}")

        emotional_text = self.emotional.build(emotion_state)
        context_text = self.context.build(
            memory_context=memory_context,
            recall=recall,
            knowledge=knowledge,
            graph=graph,
            experiences=experiences,
            behavior=behavior,
            emotional=emotional_text,
        )

        all_context = context_text
        if extra_lines:
            extra = "\n\n".join(extra_lines)
            all_context = f"{all_context}\n\n{extra}" if all_context else extra

        if all_context:
            sections.append(all_context)

        agent_text = self.agent.build(tool_defs=tool_defs)
        sections.append(agent_text)

        if speech_pacing:
            sections.append(speech_pacing)

        monologue_text = self.monologue.build(enabled=monologue_enabled)
        if monologue_text:
            sections.append(monologue_text)

        from datetime import datetime
        now = datetime.now()
        sections.append(f"It's currently {now.strftime('%A, %B %d, %Y')}. The time is {now.strftime('%I:%M %p').lstrip('0')}.")

        return self._assemble(sections)

    def build_agent(self, tool_defs=None):
        return self.agent.build_agent_system(
            tools_description=self._format_tool_defs(tool_defs)
        )

    def _assemble(self, sections):
        return "\n\n".join(s for s in sections if s.strip())

    def _format_tool_defs(self, tool_defs):
        if not tool_defs:
            return ""
        lines = ["Available tools:"]
        for t in tool_defs:
            lines.append(f"- {t['name']}: {t['description']}")
        return "\n".join(lines)

    def stats(self):
        return {"sections": 6}
