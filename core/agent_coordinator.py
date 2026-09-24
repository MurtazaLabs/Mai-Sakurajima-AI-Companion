# core/agent_coordinator.py
"""
AgentCoordinator - Handles multi-step agent task execution with planning and fallback.

Extracted from Brain/Agent to decouple agent orchestration logic.
"""
import json
import time
import threading
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentStep:
    """Record of a single agent step."""
    step: int
    action: str
    tool: str
    params: Dict[str, Any]
    duration: float
    success: bool
    result: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class AgentResult:
    """Result of agent execution."""
    task: str
    steps: List[AgentStep] = field(default_factory=list)
    total_duration: float = 0.0
    success: bool = False
    result: Dict[str, Any] = field(default_factory=dict)


class AgentCoordinator:
    """
    Coordinates multi-step agent task execution with planning, fallback, and evidence synthesis.
    
    Extracted from Brain/Agent to decouple agent orchestration logic.
    """

    def __init__(
        self,
        registry: Any,
        event_bus: Any = None,
        max_steps: int = 10,
        history_cap: int = 50,
    ):
        self.registry = registry
        self.event_bus = event_bus
        self.max_steps = max_steps
        self._lock = threading.RLock()
        self._history: List[AgentResult] = []
        self._history_cap = max(1, history_cap)

    def run(self, task: str, context: Optional[Dict[str, Any]] = None) -> 'AgentResult':
        """
        Execute a task with multi-step planning and execution.
        
        Args:
            task: The task description
            context: Optional context for the task
            
        Returns:
            AgentResult with execution details
        """
        if not task:
            return AgentResult(
                task=task,
                success=False,
                result={"error": "no_task_provided"}
            )

        context = context or {}
        start = time.time()
        steps: List[AgentStep] = []
        result = None

        for step_num in range(1, self.max_steps + 1):
            plan = self._plan_next(task, steps, context)

            if plan is None or plan.get("action") == "complete":
                result = plan.get("result", {}) if plan else {}
                if plan:
                    steps.append(AgentStep(
                        step=step_num,
                        action="complete",
                        tool="",
                        params={},
                        duration=0.0,
                        success=True,
                        result=result,
                        timestamp=time.time(),
                    ))
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

            step_record = AgentStep(
                step=step_num,
                action=action,
                tool=tool_name,
                params=params,
                duration=step_duration,
                success=tool_result.get("success", False),
                result=tool_result,
                timestamp=time.time(),
            )
            steps.append(step_record)

            if self.event_bus:
                from core.event_specs import AGENT_STEP
                from core.mai_message import publish_event
                publish_event(self.event_bus, AGENT_STEP, step_record.__dict__, source="agency")

            if not tool_result.get("success"):
                logger.warning(
                    "[Agent] Step %s failed: %s — %s", step_num, tool_name, tool_result.get('error')
                )

        total_duration = round(time.time() - start, 3)
        summary = AgentResult(
            task=task,
            steps=len(steps),
            total_duration=total_duration,
            success=steps and steps[-1].action == "complete",
            result=result,
        )

        with self._lock:
            self._history.append(summary)
            if len(self._history) > self._history_cap:
                del self._history[:len(self._history) - self._history_cap]

        if self.event_bus:
            from core.event_specs import AGENT_COMPLETED, STATE_AGENT_COMPLETED
            from core.mai_message import publish_event
            publish_event(self.event_bus, AGENT_COMPLETED, summary.__dict__, source="agency")
            publish_event(self.event_bus, STATE_AGENT_COMPLETED, summary.__dict__, source="agency")

        return summary

    @staticmethod
    def _is_analysis_task(task: str) -> bool:
        """Check if task requires analysis/reasoning."""
        lowered = task.lower()
        return any(w in lowered for w in ["reason", "think", "analyze", "why", "how", "what"])

    def _plan_next(self, task: str, completed_steps: List[AgentStep], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Plan the next step based on task and completed steps."""
        if not completed_steps:
            return self._initial_plan(task, context)

        last = completed_steps[-1]
        if not last.success:
            alt = self._fallback_plan(last)
            if alt:
                return alt

        # Collect evidence from successful steps
        evidence = []
        for s in completed_steps:
            r = s.result
            if r.get("success"):
                evidence.append(r.get("result"))

        # Multi-step continuation: after evidence-gathering succeeds, run ONE
        # synthesis pass over the collected evidence before concluding.
        if (
            last.success
            and evidence
            and self._is_analysis_task(task)
            and not any(s.action == "synthesize" for s in completed_steps)
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

    def _initial_plan(self, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate initial plan based on task keywords."""
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

    def _fallback_plan(self, failed_step: AgentStep) -> Optional[Dict[str, Any]]:
        """Generate fallback plan when a step fails."""
        tool = failed_step.tool
        if tool == "reason":
            return {"action": "call_tool", "tool": "search_memories", "params": {"query": failed_step.params.get("query", ""), "limit": 3}}
        if tool == "execute_action":
            return {"action": "call_tool", "tool": "get_brain_state", "params": {}}
        if tool in ("get_beliefs", "search_memories"):
            return {"action": "call_tool", "tool": "retrieve_knowledge", "params": {"query": failed_step.params.get("query", failed_step.params.get("topic", "")), "top_k": 3}}
        return None

    def history(self, limit: int = 10) -> List['AgentResult']:
        """Get execution history."""
        with self._lock:
            return self._history[-limit:]


# Required imports
import json
import time
import threading
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)
from dataclasses import dataclass, field