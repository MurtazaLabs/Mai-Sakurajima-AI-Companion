"""Native desktop window for Mai — wraps the local web UI via pywebview.

Falls back gracefully when pywebview/WebView2 is unavailable: ``start()``
returns False so callers can fall back to the system browser. Closing the
window hides it to the tray (the daemon keeps running); quitting is done
from the tray menu.
"""
import logging

logger = logging.getLogger(__name__)

try:
    import webview
    _HAS_WEBVIEW = True
except Exception:
    _HAS_WEBVIEW = False
    logger.warning("[AppWindow] pywebview not available — desktop window disabled")


class AppWindow:
    """Native window pointing at Mai's local web UI."""

    def __init__(self, host="127.0.0.1", port=8000, ssl=False, title="Mai",
                 width=1100, height=750):
        scheme = "https" if ssl else "http"
        self.url = f"{scheme}://{host}:{port}/desktop"
        self.title = title
        self.width = width
        self.height = height
        self._window = None

    def show(self):
        """Show the window if it is hidden (tray 'Open Mai')."""
        try:
            if self._window is not None:
                self._window.show()
        except Exception as e:
            logger.debug("[AppWindow] Show: %s", e)

    def _on_closing(self, *_args):
        """Intercept close → hide to tray; keep the daemon alive."""
        try:
            if self._window is not None:
                self._window.hide()
        except Exception as e:
            logger.debug("[AppWindow] Hide-on-close: %s", e)
        return False  # cancel destruction

    def start(self) -> bool:
        """Open the window (blocks inside the GUI loop). False = unavailable."""
        if not _HAS_WEBVIEW:
            return False
        try:
            self._window = webview.create_window(
                self.title, self.url,
                width=self.width, height=self.height,
                min_size=(800, 550),
            )
            try:
                self._window.events.closing += self._on_closing
            except Exception as e:
                logger.debug("[AppWindow] closing event unavailable: %s", e)
            webview.start()
            return True
        except Exception as e:
            logger.warning("[AppWindow] Failed to start window: %s", e)
            return False
