# Package re-export consumed dynamically via the plugin entry_point
# "calendar:CalendarPlugin" (module attribute lookup, not a static import).
from .calendar import CalendarPlugin  # noqa: F401
