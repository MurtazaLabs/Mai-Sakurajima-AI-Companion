import time
import json
import logging
import threading

logger = logging.getLogger(__name__)


class ToolDefinition:

    def __init__(self, name, description, handler, parameters=None, category="general"):
        self.name = str(name)
        self.description = str(description)
        self.handler = handler
        self.parameters = dict(parameters or {})
        self.category = str(category)
        self.created = time.time()
        self.call_count = 0
        self.last_call = 0.0

    def __repr__(self):
        return f"Tool(name={self.name}, category={self.category})"


class ToolRegistry:

    def __init__(self, event_bus=None):
        self._tools = {}
        self._lock = threading.RLock()
        self.event_bus = event_bus

    def register(self, name, description, handler, parameters=None, category="general"):
        with self._lock:
            if name in self._tools:
                logger.warning("[ToolRegistry] Overwriting tool: %s", name)

            tool = ToolDefinition(
                name=name,
                description=description,
                handler=handler,
                parameters=parameters,
                category=category,
            )
            self._tools[name] = tool

            if self.event_bus:
                from core.event_specs import TOOL_REGISTERED
                from core.mai_message import publish_event
                publish_event(self.event_bus, TOOL_REGISTERED, {
                    "name": name,
                    "category": category,
                }, source="agency")

            return tool

    def unregister(self, name):
        with self._lock:
            return self._tools.pop(name, None)

    def get(self, name):
        with self._lock:
            return self._tools.get(name)

    def list(self, category=None):
        with self._lock:
            if category:
                return {n: t for n, t in self._tools.items() if t.category == category}
            return dict(self._tools)

    def call(self, name, **kwargs):
        with self._lock:
            tool = self._tools.get(name)

        if not tool:
            logger.error("[ToolRegistry] Unknown tool: %s", name)
            return {"success": False, "error": f"unknown_tool:{name}"}

        try:
            with self._lock:
                tool.call_count += 1
                tool.last_call = time.time()

            self._publish_tool_started(name)

            start = time.time()
            result = tool.handler(**kwargs)
            duration = round(time.time() - start, 3)

            if self.event_bus:
                from core.event_specs import TOOL_CALLED
                from core.mai_message import publish_event
                publish_event(self.event_bus, TOOL_CALLED, {
                    "name": name,
                    "duration": duration,
                    "success": True,
                }, source="agency")

            self._publish_tool_completed(name, True, duration)

            return {
                "success": True,
                "tool": name,
                "result": result,
                "duration": duration,
            }

        except Exception as e:
            logger.error("[ToolRegistry] Tool call failed: %s — %s", name, e)
            if self.event_bus:
                from core.event_specs import TOOL_CALLED
                from core.mai_message import publish_event
                publish_event(self.event_bus, TOOL_CALLED, {
                    "name": name,
                    "success": False,
                    "error": str(e),
                }, source="agency")
            self._publish_tool_completed(name, False, None)
            return {"success": False, "tool": name, "error": str(e)}

    def _publish_tool_started(self, name):
        """Announce tool execution on the state bus so a live UI can show
        in-progress work. Carries the registry tool name only - never the
        arguments or the result."""
        if not self.event_bus:
            return
        try:
            from core.event_specs import STATE_TOOL_STARTED
            from core.mai_message import publish_event
            publish_event(self.event_bus, STATE_TOOL_STARTED, {"name": name}, source="agency")
        except Exception as e:
            logger.debug("[ToolRegistry] tool-started publish failed: %s", e)

    def _publish_tool_completed(self, name, success, duration):
        """Announce tool completion. Deliberately omits the error string that
        the `data.*` event carries, so internal failure detail never reaches the
        presentation layer."""
        if not self.event_bus:
            return
        try:
            from core.event_specs import STATE_TOOL_COMPLETED
            from core.mai_message import publish_event
            payload = {"name": name, "success": bool(success)}
            if duration is not None:
                payload["duration"] = duration
            publish_event(self.event_bus, STATE_TOOL_COMPLETED, payload, source="agency")
        except Exception as e:
            logger.debug("[ToolRegistry] tool-completed publish failed: %s", e)

    def tool_definitions_for_llm(self, category=None):
        tools = self.list(category=category)
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "category": t.category,
            }
            for t in tools.values()
        ]

    def stats(self):
        with self._lock:
            return {
                "total_tools": len(self._tools),
                "tools_by_category": {
                    cat: len([t for t in self._tools.values() if t.category == cat])
                    for cat in {t.category for t in self._tools.values()}
                },
                "total_calls": sum(t.call_count for t in self._tools.values()),
            }
