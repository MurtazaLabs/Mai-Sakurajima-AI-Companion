import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

try:
    from plyer import notification as plyer_notification
    _HAS_PLYER = True
except ImportError:
    _HAS_PLYER = False
    logger.warning("[Notifier] plyer not installed — notifications disabled")


class Notifier:
    """Bridge EventBus events to native Windows toast notifications.

    Subscribes to key EventBus topics and dispatches toasts via plyer.
    Gracefully degrades if plyer is unavailable.
    """

    def __init__(self, event_bus=None, app_name="Mai AI"):
        self.event_bus = event_bus
        self.app_name = app_name
        self._subs: list[Any] = []
        self._muted = False

    def wire(self, event_bus):
        """Subscribe to EventBus topics."""
        self.event_bus = event_bus
        if not event_bus:
            return
        subscriptions = {
            "state.emotion.changed": self._on_emotion_changed,
            "state.dreaming.finished": self._on_dream_completed,
            "state.goal.updated": self._on_goal_completed,
            "state.voice.wake": self._on_wake_detected,
            "error": self._on_error,
        }
        for topic, handler in subscriptions.items():
            try:
                sub = event_bus.on(topic, handler)
                self._subs.append(sub)
            except Exception as e:
                logger.debug("[Notifier] Subscribe %s: %s", topic, e)
        logger.info("[Notifier] Wired to event bus (%d topics)", len(subscriptions))

    def _notify(self, title, message, timeout=5):
        if self._muted or not _HAS_PLYER:
            return
        try:
            plyer_notification.notify(
                title=title,
                message=message,
                app_name=self.app_name,
                timeout=timeout,
            )
        except Exception as e:
            logger.debug("[Notifier] Toast failed: %s", e)

    def _on_emotion_changed(self, data=None):
        if isinstance(data, dict):
            emotion = data.get("dominant", "neutral")
            self._notify("Mai AI", f"Mood shifted to {emotion}")

    def _on_dream_completed(self, data=None):
        if isinstance(data, dict):
            level = data.get("level", "?")
            tasks = data.get("tasks", [])
            duration = data.get("duration", 0)
            self._notify("Mai AI Dream", f"Dream L{level} done — {len(tasks)} tasks in {duration}s")

    def _on_goal_completed(self, data=None):
        if isinstance(data, dict):
            name = data.get("name", data.get("description", data.get("id", "Unknown")))
            if data.get("status") == "completed":
                self._notify("Mai AI", f"Goal completed: {name}")

    def _on_wake_detected(self, data=None):
        self._notify("Mai AI", "Listening...", timeout=3)

    def _on_error(self, data=None):
        if isinstance(data, dict):
            msg = str(data.get("message", data.get("error", "")))
            if msg:
                self._notify("Mai AI Error", msg[:150], timeout=8)

    def mute(self):
        self._muted = True

    def unmute(self):
        self._muted = False

    def shutdown(self):
        self._muted = True
        self._subs.clear()
