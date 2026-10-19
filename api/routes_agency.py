"""Agency domain logic for the Mai API (goals, tools, world model).

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for how this is composed.
"""
import logging
from typing import Any

from api.errors import safe_error

logger = logging.getLogger("api.server")

class AgencyMixin:
    """Goals, tool registry, and world-model handlers."""

    # Set by MaiAPI at runtime — declared here for type checker
    goal_manager: Any = None
    tool_registry: Any = None
    world_model: Any = None

    def agency_goals(self):
        if not self.goal_manager:
            return {"error": "goal_manager_not_available"}
        try:
            all_goals = self.goal_manager.list()
            return {
                "goals": [g.to_dict() for g in all_goals],
                "stats": self.goal_manager.stats(),
            }
        except Exception as e:
            return {"error": safe_error(e)}

    def agency_tools(self):
        if not self.tool_registry:
            return {"error": "tool_registry_not_available"}
        try:
            tools = self.tool_registry.tool_definitions_for_llm()
            return {"tools": tools, "stats": self.tool_registry.stats()}
        except Exception as e:
            return {"error": safe_error(e)}

    def agency_world(self):
        if not self.world_model:
            return {"error": "world_model_not_available"}
        try:
            entities = self.world_model.all_entities()
            categories = self.world_model.list_categories()
            return {"entities": entities, "categories": categories, "stats": self.world_model.stats()}
        except Exception as e:
            return {"error": safe_error(e)}
