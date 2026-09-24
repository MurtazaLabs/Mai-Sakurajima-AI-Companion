import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from reasoning.thought_packet import (
    ThoughtPacket,
    parse_thought_packet,
    strip_envelope,
    default_speech_plan,
    SPEECH_PLAN_FIELDS,
)
from reasoning.journal import ThoughtJournal


class TestThoughtPacketContract:

    def test_all_fields_default(self):
        p = ThoughtPacket()
        assert p.thought == ""
        assert p.decision == ""
        assert p.response == ""
        assert p.speech_plan == default_speech_plan()
        assert p.is_structured is False

    def test_speech_plan_fields(self):
        p = ThoughtPacket(speech_plan={"intention": "tease", "tone": "playful"})
        assert p.speech_plan["intention"] == "tease"
        assert p.speech_plan["tone"] == "playful"
        for field in SPEECH_PLAN_FIELDS:
            assert field in p.speech_plan

    def test_speech_plan_junk_coerced(self):
        p = ThoughtPacket(speech_plan="not a dict")
        assert p.speech_plan == default_speech_plan()

    def test_summary_shape(self):
        p = ThoughtPacket(thought="t", decision="d", response="r")
        s = p.summary()
        assert s["thought"] == "t"
        assert s["decision"] == "d"
        assert s["response"] == "r"
        assert s["is_structured"] is True


class TestParseThoughtPacket:

    def test_plain_text_is_response(self):
        p = parse_thought_packet("Just a normal reply.")
        assert p.response == "Just a normal reply."
        assert p.is_structured is False

    def test_empty_is_empty(self):
        p = parse_thought_packet("")
        assert p.response == ""

    def test_full_envelope(self):
        raw = json.dumps({
            "thought": "she mentioned someone else",
            "decision": "tease lightly, hold warmth",
            "speech_plan": {"intention": "tease", "tone": "playful"},
            "response": "Oh? Someone new~",
        })
        p = parse_thought_packet(raw)
        assert p.thought == "she mentioned someone else"
        assert p.decision == "tease lightly, hold warmth"
        assert p.speech_plan["intention"] == "tease"
        assert p.response == "Oh? Someone new~"
        assert p.is_structured is True

    def test_fenced_envelope(self):
        raw = '```json\n{"thought": "x", "decision": "y", "speech_plan": {}, "response": "hi"}\n```'
        p = parse_thought_packet(raw)
        assert p.thought == "x"
        assert p.response == "hi"

    def test_degrade_missing_optional_fields(self):
        raw = '{"response": "only response given"}'
        p = parse_thought_packet(raw)
        assert p.response == "only response given"
        assert p.thought == ""
        assert p.decision == ""
        assert p.is_structured is False

    def test_envelope_without_response_does_not_leak_json(self):
        raw = '{"thought": "thinking", "decision": "deciding"}'
        p = parse_thought_packet(raw)
        assert p.thought == "thinking"
        assert p.decision == "deciding"
        assert p.response == ""
        assert "{" not in p.response

    def test_truncated_json_lead_does_not_leak(self):
        raw = (
            '{"thought": "He is echoing back what I said in his words", '
            '"decision": "respond calmly but stay warm", '
            '"speech_plan": {"intention": "soothe", "tone": "gentle", "pacing"'
        )
        p = parse_thought_packet(raw)
        assert p.response == ""
        assert "thought" not in p.response
        assert "speech_plan" not in p.response
        assert "{" not in p.response

    def test_truncated_json_lead_consumes_tail(self):
        raw = '{"thought": "x", "decision": "y" and then I said hello'
        p = parse_thought_packet(raw)
        assert p.response == ""
        assert p.had_envelope is True

    def test_balanced_bad_json_lead_stripped(self):
        raw = '{"thought": x} and here is the reply'
        p = parse_thought_packet(raw)
        assert p.response == "and here is the reply"

    def test_prose_before_truncated_json_stripped(self):
        raw = "That's fine. {\"thought\": \"x\", \"decision\": \"y\""
        p = parse_thought_packet(raw)
        assert p.response == "That's fine."

    def test_short_brace_prose_untouched(self):
        p = parse_thought_packet("use {braces} like so")
        assert p.response == "use {braces} like so"

    def test_prose_before_envelope_keeps_envelope_response(self):
        raw = "my reply: {\"thought\": \"t\", \"decision\": \"d\", \"speech_plan\": {}, \"response\": \"spoken\"}"
        p = parse_thought_packet(raw)
        assert p.response == "spoken"

    def test_invalid_json_degrades_to_plain(self):
        p = parse_thought_packet("This is { not valid json")
        assert p.response == "This is { not valid json"
        assert p.is_structured is False

    def test_strip_envelope(self):
        raw = '{"thought": "t", "decision": "d", "speech_plan": {}, "response": "visible"}'
        assert strip_envelope(raw) == "visible"

    def test_non_serializable_input(self):
        p = parse_thought_packet(None)
        assert p.response == ""


class TestJournalMonologue:

    def test_store_monologue_appends(self):
        journal = ThoughtJournal()
        packet = ThoughtPacket(thought="t", decision="d", response="r")
        entry = journal.store_monologue(packet, query="hello")
        assert entry["thought"] == "t"
        assert entry["decision"] == "d"
        assert entry["response"] == "r"
        assert entry["query"] == "hello"
        assert journal.count() == 1

    def test_store_monologue_keeps_reasoning_entries(self):
        journal = ThoughtJournal()
        journal.store({"query": "q", "conclusion": "c"})
        packet = ThoughtPacket(thought="t", response="r")
        journal.store_monologue(packet, query="q2")
        assert journal.count() == 2

    def test_store_monologue_persists_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "journal.jsonl"
            journal = ThoughtJournal(path=str(path))
            packet = ThoughtPacket(thought="t", decision="d", response="r")
            journal.store_monologue(packet, query="q")
            journal2 = ThoughtJournal(path=str(path))
            assert journal2.count() == 1
            assert journal2.recent(1)[0]["thought"] == "t"


class TestPromptMonologue:

    def test_monologue_section_present_when_enabled(self):
        from prompt.builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build_system(monologue_enabled=True)
        assert "OPTIONAL THOUGHT ENVELOPE" in result
        assert "response" in result

    def test_monologue_section_absent_when_disabled(self):
        from prompt.builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build_system(monologue_enabled=False)
        assert "OPTIONAL THOUGHT ENVELOPE" not in result

    def test_default_is_disabled(self):
        from prompt.builder import PromptBuilder
        builder = PromptBuilder()
        result = builder.build_system()
        assert "OPTIONAL THOUGHT ENVELOPE" not in result

    def test_wrapper_passes_flag(self):
        from core.prompt_builder import build_system_prompt
        result = build_system_prompt(monologue_enabled=True)
        assert "OPTIONAL THOUGHT ENVELOPE" in result


class TestBrainMonologueWiring:

    def _make_brain(self):
        from core.brain import Brain
        from core.state.shared_state import SharedState
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.state.shared_state.EvidenceDB"):
                state = SharedState(Path(tmpdir))
                return Brain(llm=None, memory=None, executor=None, state=state)

    def test_parse_thought_stores_last_packet(self):
        brain = self._make_brain()
        raw = json.dumps({"thought": "t", "decision": "d", "response": "hello"})
        packet = brain._parse_thought(raw)
        assert packet.response == "hello"
        assert brain.last_thought_packet is packet

    def test_parse_thought_degrades(self):
        brain = self._make_brain()
        packet = brain._parse_thought("plain reply")
        assert packet.response == "plain reply"
        assert packet.is_structured is False

    def test_parse_thought_truncated_json_never_leaks(self):
        brain = self._make_brain()
        raw = (
            '{"thought": "he said he handled it", '
            '"decision": "acknowledge", '
            '"speech_plan": {"intention": "praise", "tone": "warm", "pacing"'
        )
        packet = brain._parse_thought(raw)
        assert packet.response == ""
        assert packet.had_envelope is True
        assert "speech_plan" not in packet.response
        assert "{" not in packet.response

    def test_think_truncated_json_returns_clean_text(self):
        from core.brain import Brain, BrainDeps
        from core.state.shared_state import SharedState
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.state.shared_state.EvidenceDB"):
                with patch("core.brain.apply_style", side_effect=lambda x, **kw: x):
                    state = SharedState(Path(tmpdir))
                    llm = MagicMock()
                    llm.generate_with_tools.return_value = (
                        '{"thought": "he praised me", "decision": "accept", '
                        '"speech_plan": {"intention": "warm", "tone": "happy", "pacing"'
                    )
                    mem = MagicMock()
                    mem.get_context.return_value = []
                    mem.get_structured.return_value = {}
                    mem.recall.return_value = ""
                    mem.process.return_value = None
                    mem.store.return_value = MagicMock()
                    brain = Brain(
                        llm=llm, memory=mem, executor=MagicMock(), state=state,
                        deps=BrainDeps(thought_journal=None),
                    )
                    result = brain.think("I handled it")
                    assert "speech_plan" not in result
                    assert "{" not in result
                    assert "thought" not in result

    def test_think_journals_monologue(self):
        from core.brain import Brain, BrainDeps
        from core.state.shared_state import SharedState
        from reasoning.journal import ThoughtJournal
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.state.shared_state.EvidenceDB"):
                state = SharedState(Path(tmpdir))
                journal = ThoughtJournal()
                llm = MagicMock()
                llm.generate_with_tools.return_value = json.dumps({
                    "thought": "inner",
                    "decision": "outer",
                    "speech_plan": {"tone": "playful"},
                    "response": "spoken text",
                })
                mem = MagicMock()
                mem.get_context.return_value = []
                mem.get_structured.return_value = {}
                mem.recall.return_value = ""
                mem.process.return_value = None
                mem.store.return_value = MagicMock()
                brain = Brain(
                    llm=llm, memory=mem, executor=MagicMock(), state=state,
                    deps=BrainDeps(thought_journal=journal),
                )
                result = brain.think("hello")
                assert "spoken text" in result
                assert journal.count() >= 1
                entry = journal.recent(1)[0]
                assert entry["thought"] == "inner"

    def test_think_plain_reply_unchanged(self):
        from core.brain import Brain, BrainDeps
        from core.state.shared_state import SharedState
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.state.shared_state.EvidenceDB"):
                with patch("core.brain.apply_style", side_effect=lambda x, **kw: x):
                    state = SharedState(Path(tmpdir))
                    llm = MagicMock()
                    llm.generate_with_tools.return_value = "mock response"
                    mem = MagicMock()
                    mem.get_context.return_value = []
                    mem.get_structured.return_value = {}
                    mem.recall.return_value = ""
                    mem.process.return_value = None
                    mem.store.return_value = MagicMock()
                    brain = Brain(
                        llm=llm, memory=mem, executor=MagicMock(), state=state,
                        deps=BrainDeps(thought_journal=None),
                    )
                    result = brain.think("hello")
                    assert result == "mock response"

    def test_event_spec_registered(self):
        from core.event_bus import EventBus
        from core.event_specs import (
            register_event_specs, STATE_MONOLOGUE_GENERATED, VERTEX_SPECS,
        )
        bus = EventBus()
        register_event_specs(bus)
        names = {s.name for s in VERTEX_SPECS}
        assert STATE_MONOLOGUE_GENERATED in names
        assert bus.registry is not None

    def test_orchestrator_enables_monologue_on_chat(self):
        from core.brain import Brain, BrainDeps
        from core.state.shared_state import SharedState
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.state.shared_state.EvidenceDB"):
                state = SharedState(Path(tmpdir))
                mem = MagicMock()
                mem.get_context.return_value = []
                mem.get_structured.return_value = {}
                mem.recall.return_value = ""
                mem.process.return_value = None
                mem.store.return_value = MagicMock()
                brain = Brain(
                    llm=None, memory=mem, executor=MagicMock(), state=state,
                    deps=BrainDeps(thought_journal=None),
                )
                system = brain.prompt_orchestrator.build("hello", monologue=True)
                assert "OPTIONAL THOUGHT ENVELOPE" in system

    def test_stream_path_disables_monologue(self):
        from core.brain import Brain, BrainDeps
        from core.state.shared_state import SharedState
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("core.state.shared_state.EvidenceDB"):
                state = SharedState(Path(tmpdir))
                mem = MagicMock()
                mem.get_context.return_value = []
                mem.get_structured.return_value = {}
                mem.recall.return_value = ""
                mem.process.return_value = None
                mem.store.return_value = MagicMock()
                brain = Brain(
                    llm=None, memory=mem, executor=MagicMock(), state=state,
                    deps=BrainDeps(thought_journal=None),
                )
                system = brain.prompt_orchestrator.build("hello", monologue=False)
                assert "OPTIONAL THOUGHT ENVELOPE" not in system
