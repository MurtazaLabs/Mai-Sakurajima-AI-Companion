import threading
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
#  ToolRegistry tests
# ---------------------------------------------------------------------------

class TestToolStateProjections:
    """The UI subscribes exclusively to `state.*`; tool execution must be
    observable as in-progress work, not only as a post-hoc record."""

    def _types(self, bus):
        return [c[0][0].type for c in bus.publish_message.call_args_list]

    def test_started_and_completed_bracket_the_call(self):
        from agency.registry import ToolRegistry
        bus = MagicMock()
        registry = ToolRegistry(event_bus=bus)
        registry.register("ok", "desc", lambda: "done")
        registry.call("ok")
        types = self._types(bus)
        assert "state.tool.started" in types
        assert "state.tool.completed" in types
        assert types.index("state.tool.started") < types.index("state.tool.completed")

    def test_completed_reports_success_and_duration(self):
        from agency.registry import ToolRegistry
        bus = MagicMock()
        registry = ToolRegistry(event_bus=bus)
        registry.register("ok", "desc", lambda: "done")
        registry.call("ok")
        msg = [c[0][0] for c in bus.publish_message.call_args_list
               if c[0][0].type == "state.tool.completed"][-1]
        assert msg.payload["name"] == "ok"
        assert msg.payload["success"] is True
        assert "duration" in msg.payload

    def test_failure_still_completes_and_omits_the_error_string(self):
        from agency.registry import ToolRegistry
        bus = MagicMock()
        registry = ToolRegistry(event_bus=bus)

        def fail(**kw):
            raise ValueError("secret internal detail")

        registry.register("fail", "desc", fail)
        registry.call("fail")
        msg = [c[0][0] for c in bus.publish_message.call_args_list
               if c[0][0].type == "state.tool.completed"][-1]
        assert msg.payload["success"] is False
        # The data.* event carries the error for diagnostics; the state
        # projection must not leak internal failure detail to the UI.
        assert "error" not in msg.payload
        assert "secret internal detail" not in str(msg.payload)

    def test_unknown_tool_publishes_no_state_projection(self):
        from agency.registry import ToolRegistry
        bus = MagicMock()
        registry = ToolRegistry(event_bus=bus)
        result = registry.call("nope")
        assert result["success"] is False
        assert "state.tool.started" not in self._types(bus)

    def test_no_bus_does_not_raise(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register("ok", "desc", lambda: "done")
        assert registry.call("ok")["success"] is True


class TestToolRegistry:

    def test_register_adds_tool(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        fn = lambda: "ok"
        registry.register("test_tool", "A test tool", fn)
        tool = registry.get("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.handler is fn
        assert tool.call_count == 0

    def test_register_with_parameters_and_category(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        fn = lambda x: x
        registry.register(
            "calc", "Calculator", fn,
            parameters={"x": {"type": "number"}},
            category="math",
        )
        tool = registry.get("calc")
        assert tool.parameters == {"x": {"type": "number"}}
        assert tool.category == "math"

    def test_register_overwrite_warning(self, caplog):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register("dup", "first", lambda: 1)
        registry.register("dup", "second", lambda: 2)
        assert any("Overwriting" in r.msg for r in caplog.records)

    def test_register_publishes_event(self):
        from agency.registry import ToolRegistry
        bus = MagicMock()
        registry = ToolRegistry(event_bus=bus)
        registry.register("evt_tool", "desc", lambda: 0)
        bus.publish_message.assert_called_once()
        msg = bus.publish_message.call_args[0][0]
        assert msg.type == "data.tool.registered"
        assert msg.payload == {
            "name": "evt_tool",
            "category": "general",
        }

    def test_get_returns_none_for_missing(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_unregister_removes_tool(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register("bye", "desc", lambda: 0)
        removed = registry.unregister("bye")
        assert removed is not None
        assert registry.get("bye") is None

    def test_unregister_missing_returns_none(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        assert registry.unregister("nope") is None

    def test_list_returns_all_tools(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register("a", "desc", lambda: 0, category="cat1")
        registry.register("b", "desc", lambda: 0, category="cat2")
        registry.register("c", "desc", lambda: 0, category="cat1")
        all_tools = registry.list()
        assert len(all_tools) == 3

    def test_list_filters_by_category(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register("a", "desc", lambda: 0, category="cat1")
        registry.register("b", "desc", lambda: 0, category="cat2")
        cat1 = registry.list(category="cat1")
        assert list(cat1.keys()) == ["a"]

    def test_call_invokes_handler(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register("greet", "desc", lambda first: f"Hello {first}")
        result = registry.call("greet", first="Mai")
        assert result["success"] is True
        assert result["result"] == "Hello Mai"
        assert result["tool"] == "greet"
        assert "duration" in result

    def test_call_updates_call_count_and_last_call(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register("inc", "desc", lambda: 42)
        registry.call("inc")
        registry.call("inc")
        tool = registry.get("inc")
        assert tool.call_count == 2
        assert tool.last_call > 0

    def test_call_missing_tool_returns_error(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        result = registry.call("ghost")
        assert result["success"] is False
        assert "unknown_tool" in result["error"]

    def test_call_handler_exception_returns_error(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        def crash(**kw):
            raise RuntimeError("boom")
        registry.register("crash", "desc", crash)
        result = registry.call("crash")
        assert result["success"] is False
        assert "boom" in result["error"]

    def test_call_publishes_success_event(self):
        from agency.registry import ToolRegistry
        bus = MagicMock()
        registry = ToolRegistry(event_bus=bus)
        registry.register("ok", "desc", lambda: "done")
        registry.call("ok")
        bus.publish_message.assert_called()
        calls = [c[0][0] for c in bus.publish_message.call_args_list]
        # `data.tool.called` is the record; the state projections bracket it for
        # a live interface, so they are asserted separately rather than by
        # position.
        data_calls = [m for m in calls if m.type == "data.tool.called"]
        assert data_calls, [m.type for m in calls]
        payload = data_calls[-1].payload
        assert payload["name"] == "ok"
        assert payload["success"] is True
        assert "duration" in payload

    def test_call_publishes_failure_event(self):
        from agency.registry import ToolRegistry
        bus = MagicMock()
        registry = ToolRegistry(event_bus=bus)
        def fail(**kw):
            raise ValueError("fail")
        registry.register("fail", "desc", fail)
        registry.call("fail")
        # find the failure publish
        calls = [c[0][0] for c in bus.publish_message.call_args_list
                 if c[0][0].type == "data.tool.called"]
        assert len(calls) >= 1
        payload = calls[-1].payload
        assert payload["success"] is False
        assert "fail" in payload["error"]

    def test_tool_definitions_for_llm_returns_schema(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register("t1", "desc1", lambda: 0, parameters={"p1": {"type": "string"}}, category="core")
        registry.register("t2", "desc2", lambda: 0, category="memory")
        defs = registry.tool_definitions_for_llm()
        assert len(defs) == 2
        names = {d["name"] for d in defs}
        assert names == {"t1", "t2"}
        t1 = [d for d in defs if d["name"] == "t1"][0]
        assert t1["parameters"] == {"p1": {"type": "string"}}
        assert t1["category"] == "core"

    def test_tool_definitions_for_llm_filters_category(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register("t1", "desc", lambda: 0, category="core")
        registry.register("t2", "desc", lambda: 0, category="memory")
        defs = registry.tool_definitions_for_llm(category="memory")
        assert len(defs) == 1
        assert defs[0]["name"] == "t2"

    def test_stats_returns_counts(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register("a", "desc", lambda: 0, category="x")
        registry.register("b", "desc", lambda: 0, category="x")
        registry.register("c", "desc", lambda: 0, category="y")
        registry.call("a")
        registry.call("a")
        registry.call("b")
        stats = registry.stats()
        assert stats["total_tools"] == 3
        assert stats["total_calls"] == 3
        assert stats["tools_by_category"] == {"x": 2, "y": 1}

    def test_thread_safety(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        registry.register("inc", "desc", lambda: 42)

        errors = []

        def concurrent_call():
            for _ in range(100):
                try:
                    registry.call("inc")
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=concurrent_call) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert registry.get("inc").call_count == 1000

    def test_call_passes_kwargs_correctly(self):
        from agency.registry import ToolRegistry
        registry = ToolRegistry()
        def echo(**kw):
            return kw
        registry.register("echo", "desc", echo)
        result = registry.call("echo", a=1, b="two")
        assert result["success"] is True
        assert result["result"] == {"a": 1, "b": "two"}


# ---------------------------------------------------------------------------
#  register_builtin_tools tests
# ---------------------------------------------------------------------------

class TestRegisterBuiltinTools:

    def _make_mock_subsystem(self, methods=None):
        m = MagicMock()
        if methods:
            for method_name in methods:
                getattr(m, method_name).return_value = f"{method_name}_result"
        return m

    def test_registers_core_tools_when_brain_given(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        brain = self._make_mock_subsystem(["get_state", "set_emotion", "set_topic"])
        register_builtin_tools(registry, brain=brain)

        assert registry.get("get_brain_state") is not None
        assert registry.get("set_emotion") is not None
        assert registry.get("set_topic") is not None

    def test_registers_memory_tools_when_memory_given(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        memory = self._make_mock_subsystem(["store", "search", "recall"])
        register_builtin_tools(registry, memory=memory)

        assert registry.get("store_memory") is not None
        assert registry.get("search_memories") is not None
        assert registry.get("recall") is not None

    def test_registers_knowledge_tools(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        kr = self._make_mock_subsystem(["retrieve"])
        register_builtin_tools(registry, knowledge_retriever=kr)

        assert registry.get("retrieve_knowledge") is not None

    def test_registers_belief_tools(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        be = self._make_mock_subsystem(["get_beliefs_by_topic", "update_belief"])
        register_builtin_tools(registry, belief_engine=be)

        assert registry.get("get_beliefs") is not None
        assert registry.get("update_belief") is not None

    def test_registers_reasoning_tools(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        re = self._make_mock_subsystem(["reason"])
        register_builtin_tools(registry, reasoning_engine=re)

        assert registry.get("reason") is not None

    def test_registers_execution_tools(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        ex = self._make_mock_subsystem(["run", "stats"])
        register_builtin_tools(registry, executor=ex)

        assert registry.get("execute_action") is not None
        assert registry.get("get_execution_stats") is not None

    def test_skips_when_subsystem_none(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        register_builtin_tools(registry)
        assert len(registry.list()) == 0

    def test_get_brain_state_calls_brain_get_state(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        brain = self._make_mock_subsystem(["get_state"])
        brain.get_state.return_value = {"emotion": "happy"}
        register_builtin_tools(registry, brain=brain)

        result = registry.call("get_brain_state")
        assert result["success"] is True
        brain.get_state.assert_called_once()

    def test_store_memory_calls_memory_store(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        memory = self._make_mock_subsystem(["store"])
        register_builtin_tools(registry, memory=memory)

        registry.call("store_memory", text="hello", memory_type="test", tags=["a"])
        memory.store.assert_called_once_with(text="hello", memory_type="test", tags=["a"])

    def test_search_memories_calls_memory_search(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        memory = self._make_mock_subsystem(["search"])
        register_builtin_tools(registry, memory=memory)

        registry.call("search_memories", query="test", limit=5)
        memory.search.assert_called_once_with(query="test", limit=5)

    def test_reason_calls_reasoning_engine(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        re = self._make_mock_subsystem(["reason"])
        register_builtin_tools(registry, reasoning_engine=re)

        registry.call("reason", query="why?")
        re.reason.assert_called_once_with(query="why?")

    def test_execute_action_calls_executor(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        ex = self._make_mock_subsystem(["run", "stats"])
        register_builtin_tools(registry, executor=ex)

        registry.call("execute_action", type="open_app", content="calc")
        ex.run.assert_called_once_with(action={"type": "open_app", "content": "calc"})

    def test_get_execution_stats_calls_executor_stats(self):
        from agency.registry import ToolRegistry
        from agency.tools import register_builtin_tools
        registry = ToolRegistry()
        ex = self._make_mock_subsystem(["run", "stats"])
        register_builtin_tools(registry, executor=ex)

        registry.call("get_execution_stats")
        ex.stats.assert_called_once()


# ---------------------------------------------------------------------------
#  Agent tests
# ---------------------------------------------------------------------------

class TestAgent:

    @pytest.fixture
    def registry(self):
        from agency.registry import ToolRegistry
        reg = ToolRegistry()
        reg.register("reason", "reasoning",
                      lambda **kw: {"conclusion": "done", "confidence": 0.9})
        reg.register("search_memories", "search",
                      lambda **kw: {"results": ["mem1", "mem2"]})
        reg.register("get_beliefs", "beliefs",
                      lambda **kw: {"beliefs": ["b1"]})
        reg.register("get_brain_state", "state",
                      lambda: {"emotion": "neutral"})
        reg.register("retrieve_knowledge", "knowledge",
                      lambda **kw: {"knowledge": ["k1"]})
        reg.register("execute_action", "execute",
                      lambda **kw: {"status": "ok"})
        return reg

    def test_run_completes_successfully(self, registry):
        from agency.agent import Agent
        agent = Agent(registry)
        result = agent.run("analyze the data")
        assert result["success"] is True
        assert result["steps"] >= 1
        assert "result" in result

    def test_run_empty_task_returns_error(self, registry):
        from agency.agent import Agent
        agent = Agent(registry)
        result = agent.run("")
        assert result["success"] is False
        assert result["error"] == "no_task_provided"

    def test_run_empty_task_no_result_key(self, registry):
        from agency.agent import Agent
        agent = Agent(registry)
        result = agent.run(None)
        assert result["success"] is False
        assert result["error"] == "no_task_provided"

    def test_run_respects_max_steps(self, registry):
        from agency.agent import Agent
        # make every call fail so agent keeps trying
        fail_reg = MagicMock()
        fail_reg.call.return_value = {"success": False, "error": "fail"}
        agent = Agent(fail_reg, max_steps=3)
        result = agent.run("anything")
        # after max_steps, it ends — success depends on last step
        assert result["steps"] <= 3

    def test_run_publishes_events(self, registry):
        from agency.agent import Agent
        bus = MagicMock()
        agent = Agent(registry, event_bus=bus)
        agent.run("recall something")
        # should publish agent.step and agent.completed
        step_events = [c[0][0] for c in bus.publish_message.call_args_list if c[0][0].type == "data.agent.step"]
        completed_events = [c[0][0] for c in bus.publish_message.call_args_list if c[0][0].type == "data.agent.completed"]
        assert len(step_events) >= 1
        assert len(completed_events) == 1

    def test_initial_plan_reason_task(self, registry):
        from agency.agent import Agent
        agent = Agent(registry)
        result = agent.run("why is the sky blue")
        assert result["success"] is True

    def test_initial_plan_remember_task(self, registry):
        from agency.agent import Agent
        agent = Agent(registry)
        result = agent.run("remember what we talked about")
        assert result["success"] is True

    def test_initial_plan_open_task(self, registry):
        from agency.agent import Agent
        agent = Agent(registry)
        # execute_action is registered
        result = agent.run("open calculator")
        assert result["success"] is True

    def test_initial_plan_belief_task(self, registry):
        from agency.agent import Agent
        agent = Agent(registry)
        result = agent.run("know about physics")
        assert result["success"] is True

    def test_fallback_on_failed_step(self, registry):
        from agency.agent import Agent
        # make reason fail so fallback to search_memories runs
        reg = MagicMock()
        call_results = [
            {"success": False, "error": "fail"},        # reason fails
            {"success": True, "result": "fallback_ok"}, # search works
        ]
        reg.call.side_effect = call_results
        agent = Agent(reg)
        result = agent.run("analyze something")
        # it should have called reason (fail) then search_memories (fallback) and complete
        assert result["success"] is True

    def test_fallback_concrete_reason_to_search(self):
        """Agent fallback: reason -> search_memories (both handlers raise)."""
        from agency.agent import Agent
        from agency.registry import ToolRegistry
        reg = ToolRegistry()
        call_log = []
        def _reason(**kw):
            call_log.append("reason")
            raise RuntimeError("boom")
        def _search(**kw):
            call_log.append("search")
            raise RuntimeError("boom")
        reg.register("reason", "r", _reason)
        reg.register("search_memories", "s", _search)
        agent = Agent(reg)
        r = agent.run("analyze test")
        assert "reason" in call_log
        assert "search" in call_log
        # all steps failed → honest failure (A-4), no complete marker
        assert r["success"] is False
        assert r["steps"] >= 2

    def test_history_stores_summaries(self, registry):
        from agency.agent import Agent
        agent = Agent(registry)
        agent.run("analyze first")
        agent.run("recall second")
        hist = agent.history()
        assert len(hist) == 2
        assert hist[0]["task"] == "analyze first"
        assert hist[1]["task"] == "recall second"

    def test_history_limit(self, registry):
        from agency.agent import Agent
        agent = Agent(registry)
        for i in range(20):
            agent.run(f"task {i}")
        hist = agent.history(limit=5)
        assert len(hist) == 5

    def test_context_passed_through(self, registry):
        from agency.agent import Agent
        agent = Agent(registry)
        result = agent.run("analyze", context={"user": "Mai"})
        assert result is not None
        assert result["task"] == "analyze"


