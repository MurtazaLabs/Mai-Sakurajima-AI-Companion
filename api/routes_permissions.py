"""Security/permission domain logic for the Mai API.

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for how this is composed.
"""
import logging
from typing import Any

from api.errors import safe_error

logger = logging.getLogger("api.server")


class PermissionsMixin:
    """Security settings, app whitelist, blocked commands, permission mode."""

    brain: Any = None
    safe_executor: Any = None

    def permissions_all(self):
        info = {}
        try:
            from agency.tools import _EXECUTE_ALLOWED_TYPES
            from execution.handlers import _ALLOWED_APPS, _DESTRUCTIVE_PATTERNS
            info["allowed_apps"] = sorted(_ALLOWED_APPS)
            info["destructive_hotkeys"] = _DESTRUCTIVE_PATTERNS
            info["allowed_action_types"] = sorted(_EXECUTE_ALLOWED_TYPES)
        except Exception as e:
            logger.exception("[Permissions] hardcoded settings: %s", e)
            info["allowed_apps"] = []
            info["destructive_hotkeys"] = []
            info["allowed_action_types"] = []
        try:
            from app.config_loader import (
                API_RATE_LIMIT_PER_MINUTE,
                EXECUTOR_BLOCKED_COMMANDS,
                EXECUTOR_COOLDOWN,
                EXECUTOR_MIN_CONFIDENCE,
                EXECUTOR_MODE,
            )
            info["mode"] = EXECUTOR_MODE
            info["cooldown"] = EXECUTOR_COOLDOWN
            info["min_confidence"] = EXECUTOR_MIN_CONFIDENCE
            info["blocked_commands"] = EXECUTOR_BLOCKED_COMMANDS
            from api.auth import api_auth_required
            info["auth_required"] = api_auth_required()
            info["rate_limit_per_minute"] = API_RATE_LIMIT_PER_MINUTE
        except Exception as e:
            logger.exception("[Permissions] config settings: %s", e)
        try:
            from config.settings import Settings
            s = Settings()
            info["safe_executor_present"] = hasattr(s, "EXECUTOR_MODE")
        except Exception as e:
            logger.exception("[Permissions] settings: %s", e)
            info["safe_executor_present"] = False
        try:
            if self.brain and hasattr(self.brain, "tool_registry") and self.brain.tool_registry:
                info["tool_count"] = len(self.brain.tool_registry.list())
        except Exception as e:
            logger.exception("[Permissions] tool registry: %s", e)
        return info

    def permissions_set_mode(self, body: dict):
        mode = body.get("mode", "")
        if mode not in ("safe", "advanced", "admin"):
            return {"error": "invalid_mode"}
        if not self.safe_executor:
            return {"error": "safe_executor_not_available"}
        try:
            # Update in-memory executor
            self.safe_executor.set_mode(mode)
            # Persist to config manager
            if self.config_manager:
                self.config_manager.set("EXECUTOR_MODE", mode)
            return {"mode": mode, "status": "updated"}
        except Exception as e:
            return {"error": safe_error(e)}
