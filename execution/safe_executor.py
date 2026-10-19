import logging
import threading
import time

from app.config_loader import (
    EXECUTOR_BLOCKED_COMMANDS,
    EXECUTOR_COOLDOWN,
    EXECUTOR_MIN_CONFIDENCE,
    EXECUTOR_MODE,
)

logger = logging.getLogger(__name__)


class SafeExecutor:

    def __init__(self, executor, mode=None, confirm_fn=None):
        self.executor = executor
        self.mode = mode or EXECUTOR_MODE
        self.last_action_time = 0
        self.cooldown = EXECUTOR_COOLDOWN
        self.history = []
        self.min_confidence = EXECUTOR_MIN_CONFIDENCE
        self.permissions = {
            "safe": {"open_app", "open_url", "search"},
            "advanced": {"open_app", "open_url", "search", "type_text"},
            "admin": {"open_app", "open_url", "search", "type_text", "run_command"},
        }
        self.blocked_commands = EXECUTOR_BLOCKED_COMMANDS
        # Optional confirmation gate. Default None = fail-closed: interactive
        # confirmations are auto-declined, which keeps headless/CI runs safe.
        # A UI (desktop app, web panel) can inject a callable that asks the
        # user and returns True/False.
        self.confirm_fn = confirm_fn
        self._lock = threading.RLock()

    def run(self, action: dict):
        if not action:
            return "[Invalid action]"
        if "type" not in action:
            return "[Missing action type]"
        action_type = action["type"]
        if action_type == "speak":
            return action.get("content", "")
        if not self._cooldown_ready():
            return "[Execution cooldown active]"
        allowed = self.permissions.get(self.mode, set())
        if action_type not in allowed:
            self._log(action, "blocked_permission")
            return f"[Blocked: {action_type} not allowed in {self.mode} mode]"
        confidence = action.get("confidence", 1.0)
        if confidence < self.min_confidence:
            logger.warning("Low confidence action (%.2f)", confidence)
            if not self._confirm(action):
                self._log(action, "cancelled_low_confidence")
                return "[Cancelled: low confidence]"
        valid, reason = self._validate(action)
        if not valid:
            self._log(action, f"blocked_validation:{reason}")
            return f"[Blocked: {reason}]"
        if action_type == "run_command" and self.mode == "admin":
            if not self._confirm(action):
                self._log(action, "cancelled_by_user")
                return "[Command cancelled]"
        try:
            result = self.executor.run(action)
            self.last_action_time = time.time()
            self._log(action, "success")
            return result
        except Exception as e:
            self._log(action, f"error:{e!s}")
            return f"[Execution error: {e!s}]"

    _SHELL_METACHARACTERS = set(";&|`$><\n(){}[]*?!\n\\")

    def _validate(self, action):
        action_type = action["type"]
        if action_type == "open_url":
            url = action.get("content") or action.get("url", "")
            if not (url.startswith("http://") or url.startswith("https://")):
                return False, "invalid_url"
        if action_type == "run_command":
            command = action.get("content") or action.get("command", "")
            if not isinstance(command, str) or not command.strip():
                return False, "empty_command"
            lowered = command.lower()
            for blocked in self.blocked_commands:
                if blocked in lowered:
                    return False, f"dangerous_command:{blocked}"
            if len(command) > 500:
                return False, "command_too_long"
            for ch in self._SHELL_METACHARACTERS:
                if ch in command:
                    return False, f"disallowed_character:{ch!r}"
            if "  " in command:
                return False, "consecutive_spaces"
        return True, "ok"

    def _confirm(self, action):
        if self.confirm_fn is None:
            logger.warning(
                "Action confirmation requested but no confirm_fn is configured — auto-declined: %s",
                action,
            )
            return False
        try:
            allowed = self.confirm_fn(action)
        except Exception as e:
            logger.error("confirm_fn raised, declining action: %s", e)
            return False
        return bool(allowed)

    def _cooldown_ready(self):
        return time.time() - self.last_action_time >= self.cooldown

    def _log(self, action, status):
        with self._lock:
            self.history.append({"timestamp": time.time(), "mode": self.mode, "action": action, "status": status})
            if len(self.history) > 1000:
                self.history.pop(0)

    def set_mode(self, mode):
        if mode not in self.permissions:
            return "[Invalid mode]"
        self.mode = mode
        return f"[Mode switched to {mode}]"

    def stats(self):
        with self._lock:
            total = len(self.history)
            success = len([h for h in self.history if h["status"] == "success"])
            blocked = len([h for h in self.history if "blocked" in h["status"]])
            errors = len([h for h in self.history if "error" in h["status"]])
            return {"total": total, "success": success, "blocked": blocked, "errors": errors, "mode": self.mode}
