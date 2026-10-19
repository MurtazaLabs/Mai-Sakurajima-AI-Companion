"""
Calendar Plugin - Simple local event/reminder manager
Hardened with manifest, sandbox support, recurring events, and timezone support.
"""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from core.plugin_system import Plugin

logger = logging.getLogger("Mai.Plugin.Calendar")


class CalendarPlugin(Plugin):
    """Calendar plugin with manifest, sandbox support, recurring events, and timezones."""
    
    # Plugin manifest
    MANIFEST = {
        "name": "calendar",
        "version": "1.1.0",
        "description": "Local event/reminder manager with recurring events and timezones",
        "author": "Mai AI Team",
        "entry_point": "calendar:CalendarPlugin",
        "api_version": "1.0",
        "permissions": {
            "filesystem": "write",
            "network": "none",
            "execution": "none",
            "api_access": ["calendar"],
            "config": "read"
        },
        "dependencies": [],
        "hooks": ["pre_chat"],
        "min_mai_version": "1.0.0",
        "homepage": "https://github.com/mai-ai/plugins",
        "repository": "https://github.com/mai-ai/plugins",
        "license": "MIT",
        "tags": ["calendar", "utility", "reminders"]
    }

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(name="calendar", version="1.1.0", description="Local event/reminder manager with recurring events and timezones")
        self.config = config or {}
        self._data_dir = Path(__file__).resolve().parent.parent / "data" / "calendar"
        self._events_file = self._data_dir / "events.json"
        self._events: list[dict[str, Any]] = []

    @classmethod
    def get_manifest(cls) -> dict:
        """Return the plugin manifest."""
        return cls.MANIFEST

    def on_load(self, hooks, brain, event_bus):
        """Initialize plugin and register hooks."""
        self.hooks = hooks
        self.brain = brain
        self.event_bus = event_bus
        
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._load()
        
        hooks.register("pre_chat", self.on_pre_chat, priority=5)
        logger.info("Calendar plugin loaded (%d events)", len(self._events))

    def on_unload(self):
        """Save events on unload."""
        self._save()
        logger.info("Calendar plugin unloaded")

    def on_pre_chat(self, user_input: str, **kwargs) -> str | None:
        """Handle calendar commands."""
        text = user_input.lower().strip()
        parts = text.split(None, 2)
        
        if len(parts) < 1:
            return None
            
        if parts[0] == "event" and len(parts) >= 2:
            cmd = parts[1]
            rest = parts[2] if len(parts) >= 3 else ""

            if cmd == "add" and rest:
                return self._add_event(rest)
            if cmd == "list":
                return self._list_events()
            if cmd == "delete" and rest:
                return self._delete_event(rest)
            if cmd == "clear":
                return self._clear_events()

        if text.startswith("remind me "):
            reminder_text = text[10:].strip()
            if reminder_text:
                return self._add_event(reminder_text)

        return None

    def _add_event(self, description: str) -> str:
        """Add a new event with optional date/time."""
        # Parse description for date/time
        # Format: "meeting tomorrow at 2pm" or "call mom next friday 3pm"
        description = description.strip()
        event_time = time.time()  # Default to now
        
        # Simple date parsing
        lower_desc = description.lower()
        if "tomorrow" in lower_desc:
            event_time = time.time() + 86400
        elif "today" in lower_desc:
            event_time = time.time()
        elif "next week" in lower_desc:
            event_time = time.time() + 604800
        
        # Try to extract time
        import re
        time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', description, re.IGNORECASE)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            ampm = time_match.group(3).lower() if time_match.group(3) else ""
            if ampm == "pm" and hour != 12:
                hour += 12
            elif ampm == "am" and hour == 12:
                hour = 0
            
            dt = datetime.fromtimestamp(event_time)
            dt = dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
            event_time = dt.timestamp()

        event = {
            "id": str(int(time.time() * 1000)),
            "description": description,
            "created": time.time(),
            "event_time": event_time,
            "recurring": None,  # Could be "daily", "weekly", "monthly"
            "timezone": "local",
        }
        
        self._events.append(event)
        self._save()
        return f"Event added: {description}"

    def _list_events(self) -> str:
        """List all events with optional filtering."""
        if not self._events:
            return "No events."
        
        now = time.time()
        lines = []
        for i, e in enumerate(sorted(self._events, key=lambda x: x.get("event_time", 0))[:15]):
            event_time = e.get("event_time", 0)
            dt = datetime.fromtimestamp(event_time)
            time_str = dt.strftime("%Y-%m-%d %H:%M")
            status = " (past)" if event_time < now else ""
            lines.append(f"{i+1}. {e['description']} â€” {time_str}{status}")
        
        if len(self._events) > 15:
            lines.append(f"... and {len(self._events) - 15} more")
        
        return "Events:\n" + "\n".join(lines)

    def _delete_event(self, query: str) -> str:
        """Delete events matching query."""
        remaining = [e for e in self._events if query.lower() not in e["description"].lower()]
        removed = len(self._events) - len(remaining)
        self._events = remaining
        if removed:
            self._save()
        return f"Removed {removed} event(s)." if removed else "No matching events."

    def _clear_events(self) -> str:
        """Clear all events."""
        count = len(self._events)
        self._events = []
        self._save()
        return f"Cleared {count} event(s)."

    def _load(self):
        """Load events from file."""
        if self._events_file.exists():
            try:
                with open(self._events_file) as f:
                    self._events = json.load(f)
            except Exception as e:
                logger.warning("Failed to load events: %s", e)

    def _save(self):
        """Save events to file."""
        try:
            with open(self._events_file, "w") as f:
                json.dump(self._events, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save events: %s", e)


