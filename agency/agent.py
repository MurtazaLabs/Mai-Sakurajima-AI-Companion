import json
import logging
import threading
import time

logger = logging.getLogger(__name__)


class Agent:

    def __init__(self, registry, event_bus=None, max_steps=10, history_cap=50):
        self.registry = registry
        self.event_bus = event_bus
        self.max_steps = max_steps
        self._lock = threading.RLock()
        self._history = []
        self._history_cap = max(1, history_cap)

    def run(self, task, context=None):
        if not task:
            return {"success": False, "error": "no_task_provided"}

        context = context or {}
        start = time.time()

        steps = []
        result = None

        for step_num in range(1, self.max_steps + 1):
            plan = self._plan_next(task, steps, context)

            if plan is None or plan.get("action") == "complete":
                result = plan.get("result", {}) if plan else {}
                if plan:
                    steps.append({
                        "step": step_num,
                        "action": "complete",
                        "result": result,
                        "timestamp": time.time(),
                    })
                break

            action = plan.get("action")
            tool_name = plan.get("tool")
            params = plan.get("params", {})

            step_start = time.time()
            try:
                tool_result = self.registry.call(tool_name, **params)
            except Exception as e:
                logger.error("[Agent] Tool call crashed (%s): %s", tool_name, e)
                tool_result = {"success": False, "error": f"tool_crash:{e}"}
            step_duration = round(time.time() - step_start, 3)

            step_record = {
                "step": step_num,
                "action": action,
                "tool": tool_name,
                "params": params,
                "duration": step_duration,
                "success": tool_result.get("success", False),
                "result": tool_result,
                "timestamp": time.time(),
            }
            steps.append(step_record)

            if self.event_bus:
                from core.event_specs import AGENT_STEP
                from core.mai_message import publish_event
                publish_event(self.event_bus, AGENT_STEP, step_record, source="agency")

            if not tool_result.get("success"):
                logger.warning("[Agent] Step %s failed: %s — %s", step_num, tool_name, tool_result.get('error'))

        total_duration = round(time.time() - start, 3)
        summary = {
            "task": task,
            "steps": len(steps),
            "total_duration": total_duration,
            "success": steps and steps[-1].get("action") == "complete",
            "result": result,
        }
        with self._lock:
            self._history.append(summary)
            if len(self._history) > self._history_cap:
                del self._history[:len(self._history) - self._history_cap]

        if self.event_bus:
            from core.event_specs import AGENT_COMPLETED, STATE_AGENT_COMPLETED
            from core.mai_message import publish_event
            publish_event(self.event_bus, AGENT_COMPLETED, summary, source="agency")
            publish_event(self.event_bus, STATE_AGENT_COMPLETED, summary, source="agency")

        return summary

    @staticmethod
    def _is_analysis_task(task: str) -> bool:
        lowered = task.lower()
        return any(w in lowered for w in ["reason", "think", "analyze", "why", "how", "what"])

    def _plan_next(self, task, completed_steps, context):
        if not completed_steps:
            return self._initial_plan(task, context)

        last = completed_steps[-1]
        if not last.get("success"):
            alt = self._fallback_plan(last)
            if alt:
                return alt

        evidence = []
        for s in completed_steps:
            r = s.get("result", {})
            if r.get("success"):
                evidence.append(r.get("result"))

        # Multi-step continuation: after evidence-gathering succeeds, run ONE
        # synthesis pass over the collected evidence before concluding.
        if (
            last.get("success")
            and evidence
            and self._is_analysis_task(task)
            and not any(s.get("action") == "synthesize" for s in completed_steps)
        ):
            summary = json.dumps(evidence, default=str)[:1500]
            return {
                "action": "synthesize",
                "tool": "reason",
                "params": {"query": f"{task} — synthesize this evidence: {summary}"},
            }

        if not evidence:
            # Every step failed and no fallback remains — honest failure.
            return None

        return {
            "action": "complete",
            "result": {
                "conclusion": f"Completed {len(completed_steps)} step(s) for: {task}",
                "evidence_count": len(evidence),
                "steps_performed": len(completed_steps),
            },
        }

    def _initial_plan(self, task, context):
        task_lower = task.lower()

        if any(w in task_lower for w in ["reason", "think", "analyze", "why", "how", "what"]):
            return {"action": "call_tool", "tool": "reason", "params": {"query": task}}

        if any(w in task_lower for w in ["remember", "recall", "memory", "what happened"]):
            return {"action": "call_tool", "tool": "search_memories", "params": {"query": task, "limit": 5}}

        if any(w in task_lower for w in ["open", "launch", "start", "search for"]):
            if "open" in task_lower or "launch" in task_lower:
                app = task_lower.replace("open", "").replace("launch", "").strip()
                return {"action": "call_tool", "tool": "execute_action", "params": {"type": "open_app", "content": app}}
            query = task_lower.replace("search for", "").replace("search", "").strip()
            return {"action": "call_tool", "tool": "execute_action", "params": {"type": "search", "content": query}}

        if any(w in task_lower for w in ["believe", "belief", "know about"]):
            topic = task_lower.replace("believe about", "").replace("know about", "").strip()
            return {"action": "call_tool", "tool": "get_beliefs", "params": {"topic": topic}}

        return {"action": "call_tool", "tool": "reason", "params": {"query": task}}

    def _fallback_plan(self, failed_step):
        tool = failed_step.get("tool")
        if tool == "reason":
            return {"action": "call_tool", "tool": "search_memories", "params": {"query": failed_step.get("params", {}).get("query", ""), "limit": 3}}
        if tool == "execute_action":
            return {"action": "call_tool", "tool": "get_brain_state", "params": {}}
        if tool in ("get_beliefs", "search_memories"):
            return {"action": "call_tool", "tool": "retrieve_knowledge", "params": {"query": failed_step.get("params", {}).get("query", failed_step.get("params", {}).get("topic", "")), "top_k": 3}}
        return None

    def history(self, limit=10):
        with self._lock:
            return self._history[-limit:]
