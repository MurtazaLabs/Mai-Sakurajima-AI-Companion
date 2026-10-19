"""Task/goal domain logic for the Mai API (goals, subtasks, procedural memory).

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for how this is composed.
"""
import logging
from typing import Any

from api.errors import safe_error

logger = logging.getLogger("api.server")


class TasksMixin:
    """Goal/task CRUD and procedural memory handlers."""

    goal_manager: Any = None
    procedural_memory: Any = None

    def tasks_list(self):
        if not self.goal_manager:
            return {"error": "goal_manager_not_available"}
        try:
            all_goals = self.goal_manager.list()
            active = self.goal_manager.list("active")
            return {
                "goals": [g.to_dict() for g in all_goals],
                "active": [g.to_dict() for g in active],
                "stats": self.goal_manager.stats(),
            }
        except Exception as e:
            return {"error": safe_error(e)}

    def tasks_create(self, body: dict):
        if not self.goal_manager:
            return {"error": "goal_manager_not_available"}
        description = body.get("description", "").strip()
        if not description:
            return {"error": "description_required"}
        priority = body.get("priority", "normal")
        if priority not in ("high", "normal", "low"):
            priority = "normal"
        try:
            goal = self.goal_manager.create(description, priority, {})
            return {"goal": goal.to_dict()}
        except Exception as e:
            return {"error": safe_error(e)}

    def tasks_complete(self, goal_id: str):
        if not self.goal_manager:
            return {"error": "goal_manager_not_available"}
        try:
            ok = self.goal_manager.complete(goal_id)
            return {"completed": ok}
        except Exception as e:
            return {"error": safe_error(e)}

    def tasks_cancel(self, goal_id: str):
        if not self.goal_manager:
            return {"error": "goal_manager_not_available"}
        try:
            ok = self.goal_manager.cancel(goal_id)
            return {"cancelled": ok}
        except Exception as e:
            return {"error": safe_error(e)}

    def tasks_activate(self, goal_id: str):
        if not self.goal_manager:
            return {"error": "goal_manager_not_available"}
        try:
            ok = self.goal_manager.activate(goal_id)
            return {"activated": ok}
        except Exception as e:
            return {"error": safe_error(e)}

    def tasks_add_subtask(self, goal_id: str, body: dict):
        if not self.goal_manager:
            return {"error": "goal_manager_not_available"}
        description = body.get("description", "").strip()
        if not description:
            return {"error": "description_required"}
        try:
            subtask = self.goal_manager.add_subtask(goal_id, description)
            if subtask:
                return {"subtask": subtask}
            return {"error": "goal_not_found"}
        except Exception as e:
            return {"error": safe_error(e)}

    def tasks_complete_subtask(self, goal_id: str, subtask_id: str):
        if not self.goal_manager:
            return {"error": "goal_manager_not_available"}
        try:
            ok = self.goal_manager.complete_subtask(goal_id, subtask_id)
            return {"completed": ok}
        except Exception as e:
            return {"error": safe_error(e)}

    def tasks_procedural(self):
        if not self.procedural_memory:
            return {"error": "procedural_memory_not_available"}
        try:
            rules = self.procedural_memory.list()
            return {
                "rules": [
                    {
                        "rule": r.rule,
                        "context": r.context,
                        "confidence": r.confidence,
                        "source": r.source,
                        "apply_count": r.apply_count,
                        "last_applied": r.last_applied,
                    }
                    for r in rules
                ],
                "stats": self.procedural_memory.stats(),
            }
        except Exception as e:
            return {"error": safe_error(e)}
