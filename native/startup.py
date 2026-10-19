import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


_STARTUP_REG_KEY = (
    r"Software\Microsoft\Windows\CurrentVersion\Run"
)


class StartupManager:
    """Register/unregister Mai AI to run at Windows startup.

    Uses HKCU\\CurrentVersion\\Run (no admin elevation needed).
    Also provides a helper to check if running as a Windows service.
    """

    def __init__(self, app_name="MaiAI", executable_path: str = ""):
        self.app_name = app_name
        self.executable_path = executable_path or self._default_exe()

    @staticmethod
    def _default_exe() -> str:
        if getattr(sys, "frozen", False):
            return sys.executable
        python = Path(sys.executable)
        pythonw = python.parent / "pythonw.exe"
        python_bin = pythonw if pythonw.exists() else python
        script = Path(__file__).resolve().parent.parent / "run_daemon.py"
        return f'"{python_bin}" "{script}"'

    def is_registered(self) -> bool:
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _STARTUP_REG_KEY, 0, winreg.KEY_READ
            ) as key:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                return bool(value)
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.warning("[Startup] Check registration failed: %s", e)
            return False

    def register(self) -> bool:
        import winreg
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _STARTUP_REG_KEY, 0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ,
                                  self.executable_path)
            logger.info("[Startup] Registered: %s", self.executable_path)
            return True
        except Exception as e:
            logger.error("[Startup] Registration failed: %s", e)
            return False

    def unregister(self) -> bool:
        import winreg
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _STARTUP_REG_KEY, 0,
                winreg.KEY_SET_VALUE,
            ) as key:
                winreg.DeleteValue(key, self.app_name)
            logger.info("[Startup] Unregistered")
            return True
        except FileNotFoundError:
            return True
        except Exception as e:
            logger.error("[Startup] Unregister failed: %s", e)
            return False

    @staticmethod
    def is_service() -> bool:
        try:
            import win32serviceutil
            return True
        except ImportError:
            return False
