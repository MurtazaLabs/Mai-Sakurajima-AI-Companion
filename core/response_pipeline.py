import json
import logging

logger = logging.getLogger(__name__)


class PipelineResult:

    def __init__(self, handled=False, response=None):
        self.handled = handled
        self.response = response


class ResponsePipeline:

    def __init__(self, tool_registry=None, executor=None, event_bus=None, memory=None):
        self.tool_registry = tool_registry
        self.executor = executor
        self.event_bus = event_bus
        self.memory = memory

    def process(self, raw, user_input, emotion_getter, cognitive, memory_coordinator, post_think_hooks, tool_registry=None, executor=None, user_id=""):
        self.tool_registry = tool_registry or self.tool_registry
        self.executor = executor or self.executor
        action = self._extract_json(raw)
        if not isinstance(action, dict):
            return PipelineResult()

        action = self._normalize_action(action)
        if action is None:
            return PipelineResult()

        if not (self._validate_action(action) or self._validate_via_registry(action)):
            return PipelineResult()

        if self.tool_registry and self._validate_via_registry(action):
            tool_result = self.tool_registry.call(action["type"], content=action.get("content", ""))
            if tool_result.get("success"):
                output = str(tool_result.get("result", "done"))
            elif self.executor:
                output = self.executor.run(action)
            else:
                output = {"error": "no executor available"}
        elif self.executor:
            output = self.executor.run(action)
        else:
            output = {"error": "no executor available"}

        if not isinstance(output, dict):
            output = {"output": str(output)}

        result_output = output.get("output", "done")
        response = str(result_output)

        memory_coordinator.after_think(user_input, f"[ACTION] {response}", user_id=user_id)
        cognitive.push_turn(user_input, f"[ACTION] {response}")

        if self.event_bus:
            from core.event_specs import CONVERSATION_FINISHED, STATE_REASONING_COMPLETE
            from core.mai_message import publish_event
            publish_event(self.event_bus, CONVERSATION_FINISHED, {
                "user_input": user_input,
                "response": response,
                "emotion": emotion_getter(),
                "mode": "action",
            }, source="cognition")
            publish_event(self.event_bus, STATE_REASONING_COMPLETE, {
                "user_input": user_input,
                "response": response,
                "mode": "action",
            }, source="cognition")

        post_think_hooks(user_input, response, memory_coordinator.get_structured())
        return PipelineResult(handled=True, response=response)

    def fallback(self, user_input):
        try:
            if self.memory and hasattr(self.memory, "get_context"):
                ctx = self.memory.get_context(limit=3)
                if ctx:
                    last = ctx[-1] if isinstance(ctx, list) else str(ctx)
                    return f"I'm having trouble connecting right now. Based on our last conversation: {last}"
        except Exception as e:
            logger.debug("Fallback context retrieval failed: %s", e)
        return "I'm having trouble connecting right now. Please try again in a moment."

    def _extract_json(self, text):
        try:
            if not isinstance(text, str):
                return None
            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1 or end <= start:
                return None
            snippet = text[start:end]
            return json.loads(snippet)
        except Exception as e:
            logger.error("[JSON EXTRACT ERROR] %s", e)
            return None

    def _normalize_action(self, action):
        """Accept the agent-style envelope {"action": "call_tool", "tool": X,
        "params": {...}} and flatten it to the executor's {"type": ..., "content": ...}
        shape. The flat shape passes through untouched."""
        try:
            if not isinstance(action, dict):
                return None
            if action.get("action") == "call_tool" and isinstance(action.get("params"), dict):
                params = action["params"]
                flat = {
                    "type": params.get("type") or action.get("tool", ""),
                    "content": params.get("content", ""),
                }
                return flat
            return action
        except Exception as e:
            logger.debug("Action normalization failed: %s", e)
            return None

    def _validate_action(self, action):
        try:
            if not isinstance(action, dict):
                return False
            allowed = [
                "open_app", "open_url", "type_text",
                "run_command", "search", "speak",
            ]
            action_type = action.get("type")
            content = action.get("content")
            if action_type not in allowed:
                return False
            if not isinstance(content, str):
                return False
            return True
        except Exception as e:
            logger.debug("Action validation failed: %s", e)
            return False

    def _validate_via_registry(self, action):
        if self.tool_registry is None:
            return False
        try:
            tool = self.tool_registry.get(action.get("type", ""))
            return tool is not None
        except Exception as e:
            logger.debug("Registry validation failed: %s", e)
            return False
