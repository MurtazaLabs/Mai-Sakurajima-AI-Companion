"""Tests for the prompt architect subsystem."""
from unittest.mock import patch

from prompt.agent import AgentPrompt
from prompt.builder import PromptBuilder
from prompt.character import CharacterPrompt
from prompt.context import ContextPrompt
from prompt.emotional import EmotionalPrompt

SAMPLE_IDENTITY = {
    "identity": {
        "name": "Mai",
        "self_concept": [
            "I am Mai Sakurajima",
            "I have a calm personality",
        ],
    },
    "personality": {
        "traits": ["Reserved", "Observant", "Blunt"],
    },
    "values": {
        "beliefs": [
            "Actions speak louder than words",
            "Respect personal space",
        ],
    },
    "speech": {
        "style": [
            "Direct and straightforward",
            "Uses subtle sarcasm",
        ],
    },
    "preferences": {},
    "boundaries": {
        "rules": [
            "No unnecessary small talk",
            "Respect privacy",
        ],
    },
}


# ---------------------------------------------------------------------------
# core.prompt_builder
# ---------------------------------------------------------------------------

class TestCorePromptBuilder:
    """Tests for core.prompt_builder module."""

    def test_build_system_prompt_delegates_to_prompt_builder(self):
        with patch("core.prompt_builder._builder") as mock_builder:
            mock_builder.build_system.return_value = "assembled system prompt"
            from core.prompt_builder import build_system_prompt

            result = build_system_prompt(
                context="ctx", emotion={"happy": 0.8}, behavior="calm",
                personality="P", relationship="R", recall="MEM",
                knowledge="KNO", tool_defs=[{"name": "t"}],
                system_notes="SN", speech_pacing="slow",
            )

            mock_builder.build_system.assert_called_once_with(
                emotion_state={"happy": 0.8},
                behavior="calm",
                memory_context="ctx",
                recall="MEM",
                knowledge="KNO",
                tool_defs=[{"name": "t"}],
                graph=None,
                personality="P",
                relationship="R",
                system_notes="SN",
                speech_pacing="slow",
                cognitive_state=None,
                identity_data=None,
                monologue_enabled=False,
            )
            assert result == "assembled system prompt"

    def test_build_system_prompt_default_emotion(self):
        """emotion=None should become an empty dict before passing."""
        with patch("core.prompt_builder._builder") as mock_builder:
            mock_builder.build_system.return_value = ""
            from core.prompt_builder import build_system_prompt

            build_system_prompt()

            call_kwargs = mock_builder.build_system.call_args[1]
            assert call_kwargs["emotion_state"] == {}

    def test_get_identity_returns_string(self):
        with patch("core.prompt_builder._get_identity_impl", return_value="Mai Sakurajima"):
            from core.prompt_builder import get_identity
            result = get_identity()
            assert isinstance(result, str)
            assert result == "Mai Sakurajima"


# ---------------------------------------------------------------------------
# prompt.character
# ---------------------------------------------------------------------------

class TestCharacterPrompt:
    """Tests for CharacterPrompt -- identity and personality assembly."""

    @patch("prompt.character.get_identity", return_value=SAMPLE_IDENTITY)
    def test_build_returns_non_empty_string(self, mock_get_id):
        cp = CharacterPrompt()
        result = cp.build()
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("prompt.character.get_identity", return_value=SAMPLE_IDENTITY)
    def test_build_contains_identity_section(self, mock_get_id):
        cp = CharacterPrompt()
        result = cp.build()
        assert "IDENTITY" in result
        assert "Mai Sakurajima" in result
        assert "calm personality" in result

    @patch("prompt.character.get_identity", return_value=SAMPLE_IDENTITY)
    def test_build_contains_personality_traits(self, mock_get_id):
        cp = CharacterPrompt()
        result = cp.build()
        assert "CORE PERSONALITY" in result
        assert "Reserved" in result
        assert "Observant" in result
        assert "Blunt" in result

    @patch("prompt.character.get_identity", return_value=SAMPLE_IDENTITY)
    def test_build_contains_values(self, mock_get_id):
        cp = CharacterPrompt()
        result = cp.build()
        assert "VALUES" in result
        assert "Actions speak louder than words" in result
        assert "Respect personal space" in result

    @patch("prompt.character.get_identity", return_value=SAMPLE_IDENTITY)
    def test_build_contains_speech_style(self, mock_get_id):
        cp = CharacterPrompt()
        result = cp.build()
        assert "SPEECH STYLE" in result
        assert "Direct and straightforward" in result
        assert "Uses subtle sarcasm" in result

    @patch("prompt.character.get_identity", return_value=SAMPLE_IDENTITY)
    def test_build_contains_boundaries(self, mock_get_id):
        cp = CharacterPrompt()
        result = cp.build()
        assert "BOUNDARIES" in result
        assert "unnecessary small talk" in result
        assert "privacy" in result

    @patch("prompt.character.get_identity", return_value=SAMPLE_IDENTITY)
    def test_build_contains_interaction_rules(self, mock_get_id):
        cp = CharacterPrompt()
        result = cp.build()
        assert "INTERACTION RULES" in result
        assert "Speak naturally as yourself" in result

    @patch("prompt.character.get_identity", return_value=SAMPLE_IDENTITY)
    def test_build_contains_tone_examples(self, mock_get_id):
        cp = CharacterPrompt()
        result = cp.build()
        assert "TONE EXAMPLES" in result
        assert "you're trying harder than usual" in result

    @patch("prompt.character.get_identity", return_value=SAMPLE_IDENTITY)
    def test_build_ends_with_name_assertion(self, mock_get_id):
        cp = CharacterPrompt()
        result = cp.build()
        assert "You are Mai Sakurajima" in result

    @patch("prompt.character.get_identity", return_value=SAMPLE_IDENTITY)
    def test_build_is_idempotent(self, mock_get_id):
        cp = CharacterPrompt()
        assert cp.build() == cp.build()


# ---------------------------------------------------------------------------
# prompt.emotional
# ---------------------------------------------------------------------------

class TestEmotionalPrompt:
    """Tests for EmotionalPrompt -- threshold-gated emotional modulation."""

    def setup_method(self):
        self.ep = EmotionalPrompt()

    def test_empty_emotion_returns_empty(self):
        assert self.ep.build(None) == ""
        assert self.ep.build({}) == ""
        assert self.ep.build({"state": {}}) == ""

    def test_non_dict_emotion_returns_empty(self):
        assert self.ep.build("invalid") == ""
        assert self.ep.build(42) == ""

    def test_high_affection_adds_softer_tendency(self):
        result = self.ep.build({"affection": 0.8, "state": {"affection": 0.8}})
        assert "Slightly softer than usual" in result

    def test_low_affection_no_tendency(self):
        result = self.ep.build({"affection": 0.5, "state": {"affection": 0.5}})
        assert result == ""

    def test_high_annoyed_adds_restrained(self):
        result = self.ep.build({"annoyed": 0.6, "state": {"annoyed": 0.6}})
        assert "More restrained and direct" in result

    def test_high_lonely_adds_attention_seeking(self):
        result = self.ep.build({"lonely": 0.6, "state": {"lonely": 0.6}})
        assert "Occasionally seeks subtle attention" in result

    def test_high_happy_adds_playful(self):
        result = self.ep.build({"happy": 0.8, "state": {"happy": 0.8}})
        assert "Mildly more playful" in result

    def test_high_stress_adds_withdrawn(self):
        result = self.ep.build({"stress": 0.8, "state": {"stress": 0.8}})
        assert "Quieter and more withdrawn" in result

    def test_low_energy_adds_calmer(self):
        result = self.ep.build({"energy": 0.2, "state": {"energy": 0.2}})
        assert "Calmer and lower energy" in result

    def test_multiple_emotions_combined(self):
        result = self.ep.build({
            "affection": 0.9, "happy": 0.8,
            "state": {"affection": 0.9, "happy": 0.8},
        })
        assert "Slightly softer than usual" in result
        assert "Mildly more playful" in result

    def test_returns_empty_when_no_thresholds_met(self):
        result = self.ep.build({"affection": 0.5, "annoyed": 0.3, "state": {"affection": 0.5, "annoyed": 0.3}})
        assert result == ""

    def test_uses_energy_default_of_0_5(self):
        """Energy key missing inside state should default to 0.5, not trigger low-energy."""
        result = self.ep.build({"state": {"happy": 0.9}})
        assert "Mildly more playful" in result
        assert "Calmer and lower energy" not in result


# ---------------------------------------------------------------------------
# prompt.context
# ---------------------------------------------------------------------------

class TestContextPrompt:
    """Tests for ContextPrompt -- assembling memory, recall, knowledge, etc."""

    def setup_method(self):
        self.cp = ContextPrompt()

    def test_empty_build_includes_honesty_guardrail(self):
        result = self.cp.build()
        assert "RETRIEVAL RULES" in result
        assert "don't know" in result
        assert "MEMORY CONTEXT" in result
        assert "(none available)" in result

    def test_behavior_adds_learned_rules_section(self):
        result = self.cp.build(behavior="Speak calmly")
        assert "LEARNED BEHAVIOR RULES" in result
        assert "Speak calmly" in result

    def test_emotional_adds_emotional_tendencies(self):
        result = self.cp.build(emotional="CURRENT EMOTIONAL TENDENCIES\n- Calm")
        assert "CURRENT EMOTIONAL TENDENCIES" in result

    def test_memory_context_adds_memory_section(self):
        result = self.cp.build(memory_context="User likes coffee")
        assert "MEMORY CONTEXT" in result
        assert "User likes coffee" in result

    def test_recall_adds_relevant_memories_section(self):
        result = self.cp.build(recall="Yesterday we talked about books")
        assert "RELEVANT MEMORIES" in result
        assert "Yesterday we talked about books" in result

    def test_knowledge_adds_knowledge_section(self):
        result = self.cp.build(knowledge="Python is a programming language")
        assert "KNOWLEDGE" in result
        assert "Python is a programming language" in result

    def test_all_fields_combined(self):
        result = self.cp.build(
            memory_context="ctx",
            recall="rec",
            knowledge="kno",
            behavior="beh",
            emotional="emo",
        )
        assert "LEARNED BEHAVIOR RULES" in result
        assert "MEMORY CONTEXT" in result
        assert "RELEVANT MEMORIES" in result
        assert "KNOWLEDGE" in result
        # emotional is embedded, no header added by ContextPrompt itself
        assert "emo" in result

    def test_partial_fields(self):
        result = self.cp.build(memory_context="only memory")
        assert "MEMORY CONTEXT" in result
        assert "LEARNED BEHAVIOR RULES" not in result
        assert "KNOWLEDGE" not in result

    def test_sections_separated_by_newlines(self):
        result = self.cp.build(memory_context="A", recall="B")
        assert "\n\n" in result


# ---------------------------------------------------------------------------
# prompt.agent
# ---------------------------------------------------------------------------

class TestAgentPrompt:
    """Tests for AgentPrompt -- capabilities and tool definitions."""

    def setup_method(self):
        self.ap = AgentPrompt()

    def test_build_without_tools_contains_only_base_instructions(self):
        result = self.ap.build()
        assert "CAPABILITIES" in result
        assert "AVAILABLE ACTIONS" not in result

    def test_build_with_tools_adds_actions_section(self):
        tools = [{"name": "search", "description": "Search the web", "parameters": {"q": {"type": "string"}}}]
        result = self.ap.build(tool_defs=tools)
        assert "AVAILABLE ACTIONS" in result
        assert "search: Search the web" in result
        assert "q (string)" in result

    def test_build_with_multiple_tools(self):
        tools = [
            {"name": "search", "description": "Web search", "parameters": {}},
            {"name": "calc", "description": "Calculator", "parameters": {"expr": {"type": "string"}}},
        ]
        result = self.ap.build(tool_defs=tools)
        assert "search: Web search" in result
        assert "calc: Calculator" in result
        assert "expr (string)" in result

    def test_base_instructions_contain_speak_and_json_options(self):
        result = self.ap.build()
        assert "respond with ONLY a single JSON object" in result
        assert "- speak: say the content aloud" in result
        assert '{"type": "open_app", "content": "chrome"}' in result

    def test_tool_section_handles_missing_keys_gracefully(self):
        tools = [{"name": "test"}]
        result = self.ap.build(tool_defs=tools)
        assert "test:" in result

    def test_build_agent_system_returns_full_prompt(self):
        result = self.ap.build_agent_system(tools_description="Tool: xyz")
        assert "access to tools" in result
        assert "Tool: xyz" in result
        assert "report results clearly" in result.lower()
        assert "ACCURACY RULES" in result
        assert "don't know" in result


# ---------------------------------------------------------------------------
# prompt.builder (integration)
# ---------------------------------------------------------------------------

class TestPromptBuilder:
    """Tests for PromptBuilder -- composite assembly of all sections."""

    @patch("prompt.builder.CharacterPrompt")
    @patch("prompt.builder.EmotionalPrompt")
    @patch("prompt.builder.ContextPrompt")
    @patch("prompt.builder.AgentPrompt")
    def test_build_system_assembles_all_sections(
        self, MockAgent, MockContext, MockEmo, MockChar
    ):
        MockChar.return_value.build.return_value = "CHARACTER"
        MockEmo.return_value.build.return_value = "EMOTIONAL"
        MockContext.return_value.build.return_value = "CONTEXT"
        MockAgent.return_value.build.return_value = "AGENT"

        builder = PromptBuilder()
        result = builder.build_system(
            emotion_state={"happy": 0.9}, behavior="calm",
            memory_context="memories", personality="P", relationship="R",
            system_notes="SN", speech_pacing="SPEECH_PACING",
        )

        assert "CHARACTER" in result
        assert "PERSONALITY DYNAMICS" in result
        assert "RELATIONSHIP STATE" in result
        assert "SYSTEM RULES" in result
        assert "CONTEXT" in result
        assert "AGENT" in result
        assert "SPEECH_PACING" in result

    @patch("prompt.builder.CharacterPrompt")
    @patch("prompt.builder.EmotionalPrompt")
    @patch("prompt.builder.ContextPrompt")
    @patch("prompt.builder.AgentPrompt")
    def test_build_system_empty_sections_omitted(
        self, MockAgent, MockContext, MockEmo, MockChar
    ):
        """When optional params are empty/falsy, corresponding sections should be omitted."""
        MockChar.return_value.build.return_value = "CHARACTER"
        MockEmo.return_value.build.return_value = ""
        MockContext.return_value.build.return_value = ""
        MockAgent.return_value.build.return_value = "AGENT"

        builder = PromptBuilder()
        result = builder.build_system()

        assert "CHARACTER" in result
        assert "AGENT" in result
        assert "PERSONALITY DYNAMICS" not in result
        assert "RELATIONSHIP STATE" not in result
        assert "SYSTEM RULES" not in result

    @patch("prompt.builder.CharacterPrompt")
    @patch("prompt.builder.EmotionalPrompt")
    @patch("prompt.builder.ContextPrompt")
    @patch("prompt.builder.AgentPrompt")
    def test_build_system_extra_sections_only_when_provided(
        self, MockAgent, MockContext, MockEmo, MockChar
    ):
        MockChar.return_value.build.return_value = "CHARACTER"
        MockEmo.return_value.build.return_value = ""
        MockContext.return_value.build.return_value = ""
        MockAgent.return_value.build.return_value = "AGENT"

        builder = PromptBuilder()
        result = builder.build_system(personality="P", relationship=None, system_notes=None)

        assert "PERSONALITY DYNAMICS" in result
        assert "P" in result
        assert "RELATIONSHIP STATE" not in result
        assert "SYSTEM RULES" not in result

    @patch("prompt.builder.CharacterPrompt")
    @patch("prompt.builder.EmotionalPrompt")
    @patch("prompt.builder.ContextPrompt")
    @patch("prompt.builder.AgentPrompt")
    def test_build_agent_method(self, MockAgent, MockContext, MockEmo, MockChar):
        MockAgent.return_value.build_agent_system.return_value = "AGENT SYSTEM"
        builder = PromptBuilder()
        tools = [{"name": "t", "description": "d"}]

        result = builder.build_agent(tool_defs=tools)

        MockAgent.return_value.build_agent_system.assert_called_once()
        assert result == "AGENT SYSTEM"

    def test_stats_returns_section_count(self):
        builder = PromptBuilder()
        stats = builder.stats()
        assert isinstance(stats, dict)
        assert stats["sections"] == 6
