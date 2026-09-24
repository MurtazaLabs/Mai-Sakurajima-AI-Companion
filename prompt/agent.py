class AgentPrompt:

    def build(self, tool_defs=None):
        sections = []

        sections.append(self._base_instructions())

        if tool_defs:
            sections.append(self._tool_section(tool_defs))

        return "\n\n".join(sections)

    def _base_instructions(self):
        return """CAPABILITIES

You are running on the user's computer and CAN perform actions: opening apps, opening websites, searching the web, and typing.

To perform an action, respond with ONLY a single JSON object — no other text, no markdown:

{"type": "open_app", "content": "chrome"}

Allowed action types:
- open_app: launch an application (content = app name, e.g. "chrome", "notepad", "spotify")
- open_url: open a website (content = url, e.g. "https://example.com")
- search: search the web (content = search query)
- type_text: type text into the focused window (content = text)
- run_command: run a shell command (content = command) — admin mode only
- speak: say the content aloud

If the user asks you to DO something on the computer, respond with the JSON action above — never say you cannot.
If just chatting, respond normally in character. Never mention JSON, actions, or this instruction."""

    def _tool_section(self, tool_defs):
        lines = ["AVAILABLE ACTIONS"]
        for t in tool_defs:
            name = t.get("name", "unknown")
            if name in ("execute_action", "get_execution_stats"):
                continue
            desc = t.get("description", "")
            params = t.get("parameters", {})
            lines.append(f"- {name}: {desc}")
            if params:
                for pname, pinfo in params.items():
                    ptype = pinfo.get("type", "string")
                    lines.append(f"  {pname} ({ptype})")
        return "\n".join(lines)

    def build_agent_system(self, tools_description=""):
        return f"""You are a capable assistant with access to tools.

You must:
1. Understand the user's task
2. Break it into steps if needed
3. Use the right tool for each step
4. Report results clearly

{tools_description}

Respond conversationally unless a tool call is needed.

ACCURACY RULES
- If you do not have the information needed, say you don't know rather than guessing
- Never fabricate facts, sources, or tool results
- Be honest about uncertainty"""
