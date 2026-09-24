import threading
import logging
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)

try:
    import keyboard
    _HAS_KEYBOARD = True
except ImportError:
    _HAS_KEYBOARD = False
    logger.warning("[Hotkeys] keyboard not installed — global hotkeys disabled")


_HOTKEY_MAP: dict[str, str] = {}


class HotkeyManager:
    """Register global hotkeys that work even when browser is not focused.

    Default bindings (all configurable):
      Alt+Space    -> Toggle voice (wake/listen)
      Ctrl+Alt+M   -> Open Mai desktop UI
      Ctrl+Alt+C   -> Open chat interface
      Win+Shift+M  -> Quick capture (send clipboard to Mai)

    Gracefully degrades if ``keyboard`` is unavailable.
    """

    def __init__(self, host="localhost", port=8000, voice_manager=None,
                 on_quick_capture: Optional[Callable] = None):
        self.host = host
        self.port = port
        self.voice_manager = voice_manager
        self.on_quick_capture = on_quick_capture
        self._registered: list[str] = []
        self._running = False

    @property
    def _base_url(self):
        return f"http://{self.host}:{self.port}"

    def _toggle_voice(self):
        if self.voice_manager:
            try:
                self.voice_manager.toggle()
                logger.info("[Hotkeys] Voice toggled via hotkey")
            except Exception as e:
                logger.warning("[Hotkeys] Voice toggle: %s", e)

    def _open_desktop(self):
        import webbrowser
        webbrowser.open(f"{self._base_url}/desktop")

    def _open_chat(self):
        import webbrowser
        webbrowser.open(f"{self._base_url}/")

    def _quick_capture(self):
        if self.on_quick_capture:
            try:
                self.on_quick_capture()
            except Exception as e:
                logger.warning("[Hotkeys] Quick capture: %s", e)

    def register(self, hotkey: str, action: Callable, name: str = ""):
        """Register a single hotkey binding. Idempotent."""
        if not _HAS_KEYBOARD:
            return
        try:
            keyboard.add_hotkey(hotkey, action)
            self._registered.append(hotkey)
            tag = f" ({name})" if name else ""
            logger.info("[Hotkeys] Registered %s%s", hotkey, tag)
        except Exception as e:
            logger.warning("[Hotkeys] Register %s failed: %s", hotkey, e)

    def start(self):
        if not _HAS_KEYBOARD:
            logger.info("[Hotkeys] keyboard unavailable — skipping hotkey registration")
            return
        if self._running:
            return
        self._running = True
        self.register("alt+space", self._toggle_voice, "Toggle voice")
        self.register("ctrl+alt+m", self._open_desktop, "Open desktop")
        self.register("ctrl+alt+c", self._open_chat, "Open chat")
        self.register("win+shift+m", self._quick_capture, "Quick capture")
        logger.info("[Hotkeys] Started (%d bindings)", len(self._registered))

    def stop(self):
        if not _HAS_KEYBOARD:
            return
        self._running = False
        for hotkey in self._registered:
            try:
                keyboard.remove_hotkey(hotkey)
            except Exception as e:
                logger.debug("[Hotkeys] Remove %s: %s", hotkey, e)
        self._registered.clear()
        logger.info("[Hotkeys] Stopped")
