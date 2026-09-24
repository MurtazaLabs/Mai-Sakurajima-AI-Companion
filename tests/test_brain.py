import json
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


class TestBrain:

    def _make_memory(self):
        with patch("memory.memory.VectorStore") as mock_vs:
            mock_vs.return_value.add.return_value = "mock_vector_id"
            from memory.memory import Memory
            return Memory()

    def _make_state(self):
        state = MagicMock()
        state.lock.__enter__.return_value = None
        state.lock.__exit__.return_value = None
        # Concrete float values so Emotion() constructor gets floats, not MagicMocks
        for k in ("happy", "lonely", "annoyed", "affection", "energy", "stress"):
            setattr(state.emotion, k, 0.5)
        state.emotion.model_dump.return_value = {
            "happy": 0.5, "lonely": 0.0, "annoyed": 0.0,
            "affection": 0.3, "energy": 0.5, "stress": 0.0,
        }
        state.relationship_scores.model_dump.return_value = {
            "trust": 0.5, "comfort": 0.5, "respect": 0.5,
            "affection": 0.3, "familiarity": 0.1,
        }
        state.runtime.is_thinking = False
        state.runtime.last_interaction_time = 0.0
        state.runtime.current_session_turns = 0
        state.save_state_to_disk = MagicMock()
        return state

    def _make_mock_memory(self):
        mem = MagicMock()
        mem.store.return_value = MagicMock()
        mem.get_context.return_value = []
        mem.get_structured.return_value = {}
        mem.recall.return_value = ""
        mem.process.return_value = None
        return mem

    def _make_brain(self, use_mock_memory=False, **overrides):
        with patch("memory.memory.VectorStore") as mock_vs:
            mock_vs.return_value.add.return_value = "mock_vector_id"
            from core.brain import Brain

            llm = MagicMock()
            llm.generate_with_tools.return_value = "mock response"
            llm.is_available.return_value = True

            kwargs = dict(
                llm=llm,
                memory=self._make_mock_memory() if use_mock_memory else self._make_memory(),
                executor=MagicMock(),
                state=self._make_state(),
            )
            kwargs.update(overrides)
            return Brain(**kwargs)

    def test_brain_accepts_minimal_init(self):
        brain = self._make_brain()
        assert brain is not None
        assert brain.memory is not None

    def test_memory_is_accessible(self):
        brain = self._make_brain()
        assert hasattr(brain.memory, "store")
        assert hasattr(brain.memory, "get_context")

    def test_brain_has_emotion(self):
        brain = self._make_brain()
        assert hasattr(brain, "emotion")

    def test_brain_has_personality_state(self):
        brain = self._make_brain()
        assert hasattr(brain, "personality_state")

    def test_brain_with_tool_registry(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry(event_bus=MagicMock())
        brain = self._make_brain(tool_registry=registry)
        assert brain.tool_registry is registry

    def test_brain_with_optional_subsystems(self):
        from agency.goals import GoalManager
        from agency.world import WorldModel
        from agency.procedural import ProceduralMemory
        bus = MagicMock()
        brain = self._make_brain(
            goal_manager=GoalManager(event_bus=bus),
            world_model=WorldModel(event_bus=bus),
            procedural_memory=ProceduralMemory(event_bus=bus),
        )
        assert brain.goal_manager is not None
        assert brain.world_model is not None
        assert brain.procedural_memory is not None

    def test_memory_store_works(self):
        brain = self._make_brain()
        node = brain.memory.store("I am excited about machine learning — it's important to me", "That's great! Let's explore it.")
        assert node is not None

    def test_brain_has_event_bus(self):
        from core.event_bus import EventBus
        bus = EventBus()
        brain = self._make_brain(event_bus=bus)
        assert brain.event_bus is bus


class TestBrainThink:

    def _make_state(self):
        state = MagicMock()
        state.lock.__enter__.return_value = None
        state.lock.__exit__.return_value = None
        for k in ("happy", "lonely", "annoyed", "affection", "energy", "stress"):
            setattr(state.emotion, k, 0.5)
        state.emotion.model_dump.return_value = {
            "happy": 0.5, "lonely": 0.0, "annoyed": 0.0,
            "affection": 0.3, "energy": 0.5, "stress": 0.0,
        }
        state.relationship_scores.model_dump.return_value = {
            "trust": 0.5, "comfort": 0.5, "respect": 0.5,
            "affection": 0.3, "familiarity": 0.1,
        }
        state.runtime.is_thinking = False
        state.runtime.last_interaction_time = 0.0
        state.runtime.current_session_turns = 0
        state.save_state_to_disk = MagicMock()
        return state

    def _make_mock_memory(self):
        mem = MagicMock()
        mem.store.return_value = MagicMock()
        mem.get_context.return_value = []
        mem.get_structured.return_value = {}
        mem.recall.return_value = ""
        mem.process.return_value = None
        return mem

    def _make_brain(self, **overrides):
        from core.brain import Brain

        llm = MagicMock()
        llm.generate_with_tools.return_value = "mock response"
        llm.is_available.return_value = True

        kwargs = dict(
            llm=llm,
            memory=self._make_mock_memory(),
            executor=MagicMock(),
            state=self._make_state(),
        )
        kwargs.update(overrides)
        return Brain(**kwargs)

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_normal_chat_returns_response(self, mock_style):
        brain = self._make_brain()
        brain.llm.generate_with_tools.return_value = "Hello there!"
        result = brain.think("hi")
        assert result == "Hello there!"

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_retries_empty_structured_reply(self, mock_style):
        brain = self._make_brain()
        truncated = (
            '{"thought": "he praised me", "decision": "accept", '
            '"speech_plan": {"intention": "warm", "tone": "happy", "pacing"'
        )
        brain.llm.generate_with_tools.side_effect = [
            truncated, "Thanks. I'm glad it helped.",
        ]
        result = brain.think("I handled it")
        assert result == "Thanks. I'm glad it helped."
        assert brain.llm.generate_with_tools.call_count == 2

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_retry_bounded_to_single(self, mock_style):
        brain = self._make_brain()
        truncated = '{"thought": "x", "decision": "y", "speech_plan": {"tone": "w"'
        brain.llm.generate_with_tools.side_effect = [truncated, truncated]
        result = brain.think("I handled it")
        assert result == ""
        assert brain.llm.generate_with_tools.call_count == 2

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_plain_text_does_not_retry(self, mock_style):
        brain = self._make_brain()
        brain.llm.generate_with_tools.return_value = "Hello there!"
        result = brain.think("hi")
        assert result == "Hello there!"
        assert brain.llm.generate_with_tools.call_count == 1

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_retry_exception_returns_empty(self, mock_style):
        brain = self._make_brain()
        truncated = '{"thought": "x", "decision": "y", "speech_plan": {"tone": "w"'

        def explode(system, gen_input, **kwargs):
            if brain.llm.generate_with_tools.call_count > 1:
                raise RuntimeError("network down")
            return truncated

        brain.llm.generate_with_tools.side_effect = explode
        result = brain.think("I handled it")
        assert result == ""
        assert brain.llm.generate_with_tools.call_count == 2

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_stores_memory(self, mock_style):
        brain = self._make_brain()
        brain.llm.generate_with_tools.return_value = "Sure thing"
        with patch.object(brain.memory, "process") as mock_process:
            brain.think("hello")
            assert mock_process.called

    def test_think_empty_input(self):
        brain = self._make_brain()
        result = brain.think("")
        assert result == "I didn't receive any input."

    def test_think_whitespace_input(self):
        brain = self._make_brain()
        result = brain.think("   ")
        assert result == "I didn't receive any input."

    def test_think_updates_emotion(self):
        brain = self._make_brain()
        with patch.object(brain.emotion, "update") as mock_update:
            brain.think("hello")
            call = mock_update.call_args
            assert call is not None
            assert call.args[0] == "hello"
            assert isinstance(call.args[1], dict)

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_publishes_event(self, mock_style):
        from core.event_bus import EventBus
        from core.event_specs import register_event_specs
        bus = EventBus()
        register_event_specs(bus)
        brain = self._make_brain(event_bus=bus)
        brain.llm.generate_with_tools.return_value = "response"
        received = []

        def capture(data):
            received.append(data)

        bus.subscribe("data.conversation.finished", capture)
        brain.think("hello")
        assert len(received) == 1
        assert "user_input" in received[0]
        assert received[0]["response"] == "response"
        assert received[0]["mode"] == "chat"

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_cognitive_push_turn(self, mock_style):
        brain = self._make_brain()
        brain.llm.generate_with_tools.return_value = "Hello!"
        with patch.object(brain.cognitive, "push_turn") as mock_push:
            brain.think("hi")
            mock_push.assert_called_once()

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_analytical_query_runs_reasoning(self, mock_style):
        brain = self._make_brain()
        brain.reasoning_engine = MagicMock()
        trace = MagicMock()
        trace.confidence = 0.85
        trace.reasoning_steps = []
        trace.known_facts = ["fact1"]
        trace.conclusion = "I think it's good"
        trace.to_dict.return_value = {}
        brain.reasoning_engine.reason.return_value = trace
        brain.thought_journal = MagicMock()
        brain.llm.generate_with_tools.return_value = "I think you should go for it."
        result = brain.think("why should I learn Python?")
        assert "go for it" in result
        assert brain.reasoning_engine.reason.called

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_complex_task_delegates_to_agent(self, mock_style):
        brain = self._make_brain()
        brain.agent = MagicMock()
        brain.agent.run.return_value = {
            "success": True,
            "result": {"conclusion": "Research complete"},
        }
        brain.llm.generate_with_tools.return_value = "I looked into it — research complete."
        result = brain.think("research the weather")
        assert "research complete" in result.lower()
        assert brain.llm.generate_with_tools.called
        call_args = brain.llm.generate_with_tools.call_args
        assert "Research complete" in call_args.args[1]

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_agent_not_set_skips_delegation(self, mock_style):
        brain = self._make_brain()
        brain.llm.generate_with_tools.return_value = "OK"
        brain.reasoning_engine = None
        with patch.object(brain, "_is_complex_task", return_value=True):
            result = brain.think("research something")
            assert result == "OK"

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_action_json_executes_action(self, mock_style):
        brain = self._make_brain()
        action = json.dumps({"type": "speak", "content": "hello world"})
        brain.llm.generate_with_tools.return_value = action
        brain.executor.run.return_value = {"output": "spoken"}
        result = brain.think("say hello")
        assert result == "spoken"

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_action_invalid_type_ignored(self, mock_style):
        brain = self._make_brain()
        action = json.dumps({"type": "invalid_action", "content": "test"})
        brain.llm.generate_with_tools.return_value = action
        result = brain.think("do something")
        assert brain.executor.run.called is False

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_action_via_registry(self, mock_style):
        brain = self._make_brain()
        registry = MagicMock()
        registry.get.return_value = MagicMock()
        registry.call.return_value = {"success": True, "result": "tool done"}
        brain.tool_registry = registry
        action = json.dumps({"type": "speak", "content": "hello"})
        brain.llm.generate_with_tools.return_value = action
        result = brain.think("say hello")
        assert brain.executor.run.called is False

    def test_think_llm_none_returns_fallback_with_context(self):
        brain = self._make_brain()
        brain.llm.generate_with_tools.return_value = None
        brain.memory.get_context.return_value = ["last conversation"]
        result = brain.think("hello")
        assert "having trouble" in result
        assert "last conversation" in result

    def test_think_llm_none_returns_generic_fallback(self):
        brain = self._make_brain()
        brain.llm.generate_with_tools.return_value = None
        brain.memory.get_context.return_value = []
        result = brain.think("hello")
        assert "having trouble connecting" in result

    def test_think_exception_returns_fallback(self):
        brain = self._make_brain()
        brain.llm.generate_with_tools.side_effect = RuntimeError("LLM crash")
        brain.memory.get_context.return_value = []
        result = brain.think("hello")
        assert "having trouble" in result

    @patch("core.brain.apply_style", side_effect=lambda x, **kw: x)
    def test_think_reasoning_trace_section_in_generation(self, mock_style):
        brain = self._make_brain()
        brain.reasoning_engine = MagicMock()
        trace = MagicMock()
        trace.confidence = 0.75
        trace.reasoning_steps = []
        trace.known_facts = ["fact_a"]
        trace.conclusion = "conclusion here"
        trace.to_dict.return_value = {}
        brain.reasoning_engine.reason.return_value = trace
        brain.thought_journal = MagicMock()
        brain.llm.generate_with_tools.return_value = "response"
        brain.think("what do you think about this?")
        call_args = brain.llm.generate_with_tools.call_args[0]
        assert "Reasoning confidence" in call_args[1]
        assert "conclusion here" in call_args[1]

    def test_think_stream_returns_iterator(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter(["chunk1", "chunk2"])
        with patch.object(brain.emotion, "update"):
            result = brain.think_stream("hello")
            assert list(result) == ["chunk1", "chunk2"]

    def test_think_stream_plain_text_streams_immediately(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter(["Hello ", "there!"])
        with patch.object(brain.emotion, "update"):
            assert list(brain.think_stream("hi")) == ["Hello ", "there!"]

    def test_think_stream_envelope_hidden(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter([
            '{"thought": "she asked", "decision": "answer", "speech_plan": '
            '{"intention": "help", "tone": "warm"}, "response": "sure, '
            'go ahead"}',
        ])
        with patch.object(brain.emotion, "update"):
            out = "".join(brain.think_stream("can I?"))
        assert out == "sure, go ahead"
        assert "speech_plan" not in out
        assert "thought" not in out

    def test_think_stream_truncated_envelope_swallowed(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter([
            '{"thought": "she praised me", "decision": "accept", '
            '"speech_plan": {"intention": "warm", "tone": "happy", "pacing"',
        ])
        with patch.object(brain.emotion, "update"):
            out = "".join(brain.think_stream("thanks"))
        assert out == ""
        assert "speech_plan" not in out

    def test_think_stream_prose_after_envelope_kept(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter([
            '{"thought": "x", "decision": "y", "speech_plan": {}, "response": "ok"}',
            " And that's all I meant.",
        ])
        with patch.object(brain.emotion, "update"):
            out = "".join(brain.think_stream("hello"))
        assert out == "ok And that's all I meant."
        assert "speech_plan" not in out

    def test_think_stream_truncated_envelope_swallows_tail(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter([
            '{"thought": "x", "decision": "y"',
            " and that's all I meant.",
        ])
        with patch.object(brain.emotion, "update"):
            out = "".join(brain.think_stream("hello"))
        assert out == ""
        assert "speech_plan" not in out

    def test_think_stream_empty_input(self):
        brain = self._make_brain()
        result = brain.think_stream("")
        assert list(result) == ["I didn't receive any input."]

    def test_think_stream_flat_action_executed(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter([json.dumps({"type": "open_app", "content": "chrome"})])
        brain.executor.run.return_value = {"output": "opened:chrome"}
        with patch.object(brain.emotion, "update"):
            with patch("core.brain.apply_style", side_effect=lambda x, **kw: x):
                out = "".join(brain.think_stream("open chrome"))
        assert out == "opened:chrome"
        brain.executor.run.assert_called_once_with({"type": "open_app", "content": "chrome"})

    def test_think_stream_envelope_action_executed(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter([json.dumps({
            "action": "call_tool", "tool": "execute_action",
            "params": {"type": "open_app", "content": "notepad"},
        })])
        brain.executor.run.return_value = {"output": "opened:notepad"}
        with patch.object(brain.emotion, "update"):
            with patch("core.brain.apply_style", side_effect=lambda x, **kw: x):
                out = "".join(brain.think_stream("open notepad"))
        assert out == "opened:notepad"
        brain.executor.run.assert_called_once_with({"type": "open_app", "content": "notepad"})

    def test_think_stream_partial_action_json_waits(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter([
            '{"type": "open_app"',
            ', "content": "chrome"}',
        ])
        brain.executor.run.return_value = {"output": "opened:chrome"}
        with patch.object(brain.emotion, "update"):
            with patch("core.brain.apply_style", side_effect=lambda x, **kw: x):
                out = "".join(brain.think_stream("open chrome"))
        assert out == "opened:chrome"

    def test_think_stream_invalid_action_ignored(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter([json.dumps({"type": "invalid_action", "content": "x"})])
        with patch.object(brain.emotion, "update"):
            out = "".join(brain.think_stream("do something"))
        assert out == ""
        brain.executor.run.assert_not_called()

    def test_think_stream_action_failure_returns_empty(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter([json.dumps({"type": "open_app", "content": "chrome"})])
        brain.executor.run.side_effect = RuntimeError("boom")
        with patch.object(brain.emotion, "update"):
            with patch("core.brain.apply_style", side_effect=lambda x, **kw: x):
                out = "".join(brain.think_stream("open chrome"))
        assert out == ""

    def test_think_stream_llm_none_fallback(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = None
        with patch.object(brain.emotion, "update"):
            result = brain.think_stream("hello")
            assert "I couldn't think of a response." in list(result)[0]

    def test_think_stream_exception(self):
        brain = self._make_brain()
        brain.llm.stream.side_effect = RuntimeError("stream error")
        with patch.object(brain.emotion, "update"):
            result = brain.think_stream("hello")
            assert "Sorry" in list(result)[0]


class TestBrainHelpers:

    def _make_state(self):
        state = MagicMock()
        state.lock.__enter__.return_value = None
        state.lock.__exit__.return_value = None
        for k in ("happy", "lonely", "annoyed", "affection", "energy", "stress"):
            setattr(state.emotion, k, 0.5)
        state.emotion.model_dump.return_value = {"happy": 0.5}
        state.relationship_scores.model_dump.return_value = {"trust": 0.5}
        state.runtime.is_thinking = False
        state.runtime.last_interaction_time = 0.0
        state.runtime.current_session_turns = 0
        state.save_state_to_disk = MagicMock()
        return state

    def _make_mock_memory(self):
        mem = MagicMock()
        mem.store.return_value = MagicMock()
        mem.get_context.return_value = []
        mem.get_structured.return_value = {}
        mem.recall.return_value = ""
        mem.process.return_value = None
        return mem

    def _make_brain(self, **overrides):
        from core.brain import Brain

        llm = MagicMock()
        llm.generate_with_tools.return_value = "mock response"
        llm.is_available.return_value = True

        kwargs = dict(
            llm=llm,
            memory=self._make_mock_memory(),
            executor=MagicMock(),
            state=self._make_state(),
        )
        kwargs.update(overrides)
        return Brain(**kwargs)

    def test_infer_user_mood_happy(self):
        brain = self._make_brain()
        assert brain._infer_user_mood("I'm so happy today") == "happy"
        assert brain._infer_user_mood("good news everyone") == "happy"

    def test_infer_user_mood_sad(self):
        brain = self._make_brain()
        assert brain._infer_user_mood("I feel sad") == "sad"
        assert brain._infer_user_mood("feeling lonely") == "sad"

    def test_infer_user_mood_angry(self):
        brain = self._make_brain()
        assert brain._infer_user_mood("I'm so angry") == "angry"
        assert brain._infer_user_mood("I'm annoyed") == "angry"

    def test_infer_user_mood_neutral(self):
        brain = self._make_brain()
        assert brain._infer_user_mood("what is the weather") == "neutral"

    def test_is_complex_task_with_agent(self):
        brain = self._make_brain(agent=MagicMock())
        assert brain._is_complex_task("research this topic") is True
        assert brain._is_complex_task("find out about X") is True
        assert brain._is_complex_task("hello") is False

    def test_is_complex_task_no_agent_no_reasoning(self):
        brain = self._make_brain()
        assert brain._is_complex_task("research") is False

    def test_is_analytical_query_with_reasoning(self):
        brain = self._make_brain(reasoning_engine=MagicMock())
        assert brain._is_analytical_query("why is the sky blue") is True
        assert brain._is_analytical_query("how does this work") is True
        assert brain._is_analytical_query("hello") is False

    def test_is_analytical_query_no_reasoning(self):
        brain = self._make_brain()
        assert brain._is_analytical_query("why?") is False

    def test_extract_json_valid(self):
        brain = self._make_brain()
        result = brain._extract_json('{"type": "speak", "content": "hello"}')
        assert result == {"type": "speak", "content": "hello"}

    def test_extract_json_no_json(self):
        brain = self._make_brain()
        assert brain._extract_json("just a normal response") is None

    def test_extract_json_invalid(self):
        brain = self._make_brain()
        assert brain._extract_json("{invalid}") is None

    def test_extract_json_non_string(self):
        brain = self._make_brain()
        assert brain._extract_json(123) is None

    def test_validate_action_valid(self):
        brain = self._make_brain()
        assert brain._validate_action({"type": "speak", "content": "hello"}) is True
        assert brain._validate_action({"type": "open_url", "content": "http://..."}) is True

    def test_validate_action_invalid_type(self):
        brain = self._make_brain()
        assert brain._validate_action({"type": "delete", "content": "x"}) is False

    def test_validate_action_not_dict(self):
        brain = self._make_brain()
        assert brain._validate_action("not a dict") is False

    def test_validate_action_no_content(self):
        brain = self._make_brain()
        assert brain._validate_action({"type": "speak"}) is False

    def test_validate_via_registry_no_registry(self):
        brain = self._make_brain()
        assert brain._validate_via_registry({"type": "speak"}) is False

    def test_validate_via_registry_with_registry(self):
        brain = self._make_brain()
        registry = MagicMock()
        registry.get.return_value = MagicMock()
        brain.tool_registry = registry
        assert brain._validate_via_registry({"type": "speak"}) is True
        registry.get.assert_called_with("speak")

    def test_safe_context_returns_string(self):
        brain = self._make_brain()
        brain.memory.get_context.return_value = [{"role": "user", "content": "hi"}]
        ctx = brain._safe_context()
        assert isinstance(ctx, str)
        assert "hi" in ctx

    def test_safe_context_empty(self):
        brain = self._make_brain()
        brain.memory.get_context.return_value = None
        assert brain._safe_context() == ""

    def test_safe_recall_dict_response(self):
        brain = self._make_brain()
        brain.memory.recall.return_value = {"memory": "I remember you like pizza"}
        result = brain._safe_recall("what do I like?")
        assert "pizza" in result

    def test_safe_recall_list_response(self):
        brain = self._make_brain()
        brain.memory.recall.return_value = [
            {"memory": "fact 1"},
            {"memory": "fact 2"},
        ]
        result = brain._safe_recall("what do you know?")
        assert "fact 1" in result
        assert "fact 2" in result

    def test_safe_recall_short_input(self):
        brain = self._make_brain()
        assert brain._safe_recall("ok") == ""

    def test_safe_store_calls_process(self):
        brain = self._make_brain()
        with patch.object(brain.memory, "process") as mock_process:
            brain._safe_store("hi", "hello")
            mock_process.assert_called_with("hi", "hello")

    def test_safe_store_fallback_to_store(self):
        brain = self._make_brain()
        del brain.memory.process
        with patch.object(brain.memory, "store") as mock_store:
            brain._safe_store("hi", "hello")
            mock_store.assert_called_with("hi", "hello")

    def test_safe_store_exception_does_not_raise(self):
        brain = self._make_brain()
        brain.memory.process.side_effect = RuntimeError("store fail")
        brain._safe_store("hi", "hello")

    def test_fallback_response_with_context(self):
        brain = self._make_brain()
        brain.memory.get_context.return_value = ["last turn"]
        result = brain._fallback_response("hello")
        assert "last turn" in result
        assert "having trouble" in result

    def test_fallback_response_no_context(self):
        brain = self._make_brain()
        brain.memory.get_context.return_value = []
        result = brain._fallback_response("hello")
        assert result == "I'm having trouble connecting right now. Please try again in a moment."

    def test_time_of_day_returns_string(self):
        brain = self._make_brain()
        tod = brain._time_of_day()
        assert tod in ("morning", "day", "evening", "night", "late_night")

    def test_stats_returns_dict(self):
        brain = self._make_brain()
        s = brain.stats()
        assert isinstance(s, dict)
        assert "emotion" in s
        assert "relationship" in s
        assert "runtime" in s

    def test_think_stream_updates_emotion(self):
        brain = self._make_brain()
        brain.llm.stream.return_value = iter(["chunk"])
        with patch.object(brain.emotion, "update") as mock_update:
            list(brain.think_stream("hello"))
            # emotion.update is now called with user_input and relationship context
            mock_update.assert_called_once()
            args, kwargs = mock_update.call_args
            assert args[0] == "hello"
            assert "trust" in args[1]

    def test_run_reasoning_with_engine(self):
        brain = self._make_brain()
        brain.reasoning_engine = MagicMock()
        trace = MagicMock()
        trace.conclusion = "done"
        trace.confidence = 0.9
        trace.to_dict.return_value = {}
        brain.reasoning_engine.reason.return_value = trace
        brain.thought_journal = MagicMock()
        result = brain._run_reasoning("why?")
        assert result is trace
        assert brain.thought_journal.store.called

    def test_run_reasoning_no_engine(self):
        brain = self._make_brain()
        assert brain._run_reasoning("why?") is None

    def test_run_reasoning_exception(self):
        brain = self._make_brain()
        brain.reasoning_engine = MagicMock()
        brain.reasoning_engine.reason.side_effect = ValueError("fail")
        result = brain._run_reasoning("why?")
        assert result is None

    def test_delegate_to_agent_no_agent(self):
        brain = self._make_brain()
        assert brain._delegate_to_agent("do something") is None

    def test_delegate_to_agent_success(self):
        brain = self._make_brain()
        brain.agent = MagicMock()
        brain.agent.run.return_value = {
            "success": True,
            "result": {"conclusion": "all done"},
        }
        result = brain._delegate_to_agent("do something")
        assert result == "all done"

    def test_delegate_to_agent_string_result(self):
        brain = self._make_brain()
        brain.agent = MagicMock()
        brain.agent.run.return_value = {
            "success": True,
            "result": "direct result",
        }
        result = brain._delegate_to_agent("do something")
        assert result == "direct result"

    def test_delegate_to_agent_failure(self):
        brain = self._make_brain()
        brain.agent = MagicMock()
        brain.agent.run.return_value = {"success": False}
        result = brain._delegate_to_agent("do something")
        assert result is None

    def test_delegate_to_agent_exception(self):
        brain = self._make_brain()
        brain.agent = MagicMock()
        brain.agent.run.side_effect = RuntimeError("fail")
        result = brain._delegate_to_agent("do something")
        assert result is None

    def test_knowledge_context_no_retriever(self):
        brain = self._make_brain()
        assert brain._knowledge_context("hello") == ""

    def test_knowledge_context_with_retriever(self):
        brain = self._make_brain()
        brain.retriever = MagicMock()
        brain.retriever.retrieve.return_value = [
            {"content": "fact 1", "source": "memory", "score": 0.9},
        ]
        ctx = brain._knowledge_context("what is your favorite color")
        assert "fact 1" in ctx
        assert "memory" in ctx

    def test_knowledge_context_exception(self):
        brain = self._make_brain()
        brain.retriever = MagicMock()
        brain.retriever.retrieve.side_effect = RuntimeError("retrieval fail")
        assert brain._knowledge_context("what about that thing") == ""

    def test_safe_structured_empty(self):
        brain = self._make_brain()
        brain.memory.get_structured.return_value = None
        assert brain._safe_structured() == {}

    def test_safe_structured_returns_dict(self):
        brain = self._make_brain()
        brain.memory.get_structured.return_value = {"system": {"key": "val"}}
        result = brain._safe_structured()
        assert result == {"system": {"key": "val"}}

    def test_safe_structured_reader_fallback(self):
        brain = self._make_brain()
        del brain.memory.get_structured
        brain.memory.reader.get_all.return_value = {"preferences": {"topic": "tech"}}
        result = brain._safe_structured()
        assert result == {"preferences": {"topic": "tech"}}
