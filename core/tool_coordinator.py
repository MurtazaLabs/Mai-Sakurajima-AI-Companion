# core/tool_coordinator.py
"""
ToolCoordinator - Handles tool execution, validation, and response processing.

Extracted from Brain/ResponsePipeline to decouple tool handling logic.
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from core.event_specs import CONVERSATION_FINISHED, STATE_REASONING_COMPLETE
from core.mai_message import publish_event

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of tool pipeline processing."""
    handled: bool = False
    response: Optional[str] = None
    action: Optional[Dict[str, Any]] = None
    tool_result: Optional[Dict[str, Any]] = None


class ToolCoordinator:
    """
    Coordinates tool execution, validation, and response processing.
    
    Extracted from Brain/ResponsePipeline to decouple tool handling logic.
    """

    def __init__(
        self,
        tool_registry: Any,
        executor: Any,
        event_bus: Any,
        memory: Any = None,
    ):
        self.tool_registry = tool_registry
        self.executor = executor
        self.event_bus = event_bus
        self.memory = memory

    def process(
        self,
        raw: str,
        user_input: str,
        emotion_getter,
        cognitive: Any,
        memory_coordinator: Any,
        post_think_hooks,
        tool_registry=None,
        executor=None,
        user_id: str = "",
    ) -> 'PipelineResult':
        """
        Process raw LLM output, extract and validate actions, execute tools,
        and return formatted response.
        """
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

        # Execute the action
        if self.tool_registry and self._validate_via_registry(action):
            tool_result = self.tool_registry.call(
                action["type"], 
                **({"content": action.get("content", "")})
            )
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

        # Memory & cognitive updates
        if memory_coordinator:
            memory_coordinator.after_think(
                user_input, 
                f"[ACTION] {response}", 
                user_id=user_id
            )
        if cognitive:
            cognitive.push_turn(user_input, f"[ACTION] {response}")

        # Event publishing
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

        return PipelineResult(
            handled=True, 
            response=response,
            action=action,
            tool_result=output if isinstance(output, dict) else None
        )

    def fallback(self, user_input: str) -> str:
        """Generate fallback response when tools fail."""
        try:
            if self.memory and hasattr(self.memory, "get_context"):
                ctx = self.memory.get_context(limit=3)
                if ctx:
                    last = ctx[-1] if isinstance(ctx, list) else str(ctx)
                    return f"I'm having trouble connecting right now. Based on our last conversation: {last}"
        except Exception as e:
            logging.getLogger(__name__).debug("Fallback context retrieval failed: %s", e)
        return "I'm having trouble connecting right now. Please try again in a moment."

    # --- JSON extraction & normalization ---

    def _extract_json(self, text) -> Optional[dict]:
        """Extract JSON object from text."""
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
            logging.getLogger(__name__).error("[JSON EXTRACT ERROR] %s", e)
            return None

    def _normalize_action(self, action: dict) -> Optional[dict]:
        """Accept agent-style envelope {"action": "call_tool", "tool": X, "params": {...}}
        and flatten it to the executor's {"type": ..., "content": ...} shape."""
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
            logging.getLogger(__name__).debug("Action normalization failed: %s", e)
            return None

    def _validate_action(self, action: dict) -> bool:
        """Validate action has allowed type and string content."""
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
            logging.getLogger(__name__).debug("Action validation failed: %s", e)
            return False

    def _validate_via_registry(self, action: dict) -> bool:
        """Check if action type exists in tool registry."""
        if self.tool_registry is None:
            return False
        try:
            tool = self.tool_registry.get(action.get("type", ""))
            return tool is not None
        except Exception as e:
            logging.getLogger(__name__).debug("Registry validation failed: %s", e)
            return False