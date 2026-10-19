import threading
import logging
import webbrowser
from typing import Optional, Any

logger = logging.getLogger(__name__)

try:
    import pystray
    from PIL import Image, ImageDraw
    _HAS_TRAY = True
except ImportError:
    _HAS_TRAY = False
    logger.warning("[Tray] pystray not installed — tray disabled")


class TrayDaemon:
    """System tray icon with context menu for Mai AI.

    Requires pystray + Pillow. Gracefully degrades if unavailable.
    """

    def __init__(self, host="localhost", port=8000, voice_manager=None,
                 brain=None, on_quit=None, on_open=None):
        self.host = host
        self.port = port
        self.voice_manager = voice_manager
        self.brain = brain
        self.on_quit = on_quit
        self.on_open = on_open
        self._icon: Optional[Any] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    def _create_image(self):
        """Generate a simple 64x64 tray icon (pink circle on transparent)."""
        if not _HAS_TRAY:
            return None
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        margin = 4
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=(255, 140, 180, 255),
        )
        return img

    @property
    def _tooltip(self):
        if not self.brain:
            return "Mai AI"
        try:
            emo = self.brain.state.emotion
            mood = f"{getattr(emo, 'happy', 0):.1f}/{getattr(emo, 'energy', 0):.1f}"
        except Exception:
            mood = "?"
        return f"Mai AI | {mood}"

    def _build_menu(self):
        if not _HAS_TRAY:
            return []
        items = [
            pystray.MenuItem("Open Mai", self._action_open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Toggle Voice", self._action_toggle_voice),
            pystray.MenuItem("Settings", self._action_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self._action_quit),
        ]
        return items

    def _action_open(self):
        if self.on_open:
            try:
                self.on_open()
                return
            except Exception as e:
                logger.warning("[Tray] Open callback failed: %s", e)
        webbrowser.open(f"http://{self.host}:{self.port}/desktop")

    def _action_toggle_voice(self):
        if self.voice_manager:
            try:
                self.voice_manager.toggle()
                logger.info("[Tray] Voice toggled")
            except Exception as e:
                logger.warning("[Tray] Voice toggle: %s", e)

    def _action_settings(self):
        webbrowser.open(f"http://{self.host}:{self.port}/system")

    def _action_quit(self):
        logger.info("[Tray] Quit requested")
        if self._icon:
            self._icon.stop()
        if self.on_quit:
            self.on_quit()

    def start(self):
        if not _HAS_TRAY:
            logger.info("[Tray] pystray unavailable — skipping tray")
            return
        if self._running:
            return
        self._running = True

        def _run():
            try:
                image = self._create_image()
                if not image:
                    return
                menu = self._build_menu()
                self._icon = pystray.Icon(
                    "mai_ai", image, self._tooltip, menu,
                )
                self._icon.run()
            except Exception as e:
                logger.warning("[Tray] Error: %s", e)
            finally:
                self._running = False

        self._thread = threading.Thread(target=_run, daemon=True, name="tray-daemon")
        self._thread.start()
        logger.info("[Tray] Started")

    def stop(self):
        self._running = False
        if self._icon:
            try:
                self._icon.stop()
            except Exception as e:
                logger.debug("[Tray] Stop: %s", e)
        self._icon = None
        logger.info("[Tray] Stopped")

    def update_tooltip(self):
        """Refresh the tray tooltip."""
        if self._icon and _HAS_TRAY:
            try:
                self._icon.title = self._tooltip
            except Exception as e:
                logger.debug("[Tray] Tooltip update: %s", e)
