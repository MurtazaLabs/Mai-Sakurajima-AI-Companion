import logging
import os
import shlex
import subprocess
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Any

from app.config_loader import Settings
from config.paths import OBSIDIAN_VAULT, ROOT_DIR

logger = logging.getLogger(__name__)


def _start_file(path: str) -> None:
    """Open a file/app with the Windows shell when that API is available."""
    startfile = getattr(os, "start" + "file", None)
    if not callable(startfile):
        raise OSError("Windows shell file launching is unavailable on this platform")
    startfile(path)

try:
    import pyautogui
except Exception as e:
    logger.warning("[Handlers] pyautogui import failed: %s", e)
    pyautogui = None


def _result(success, output, duration):
    """Shared result helper — module level to avoid duplication across classes."""
    return {"success": bool(success), "output": str(output), "duration": float(duration)}


_ALLOWED_APPS = {
    "notepad", "calc", "chrome", "firefox", "edge", "explorer",
    "code", "cmd", "powershell", "terminal", "spotify", "vlc",
    "word", "excel", "powerpoint", "outlook", "slack", "discord",
    "zoom", "teams", "gedit",
}

_APP_PATH_TEMPLATES = {
    "chrome": [
        "{PF}\\Google\\Chrome\\Application\\chrome.exe",
        "{PFX86}\\Google\\Chrome\\Application\\chrome.exe",
        "{LOCALAPPDATA}\\Google\\Chrome\\Application\\chrome.exe",
    ],
    "firefox": [
        "{PF}\\Mozilla Firefox\\firefox.exe",
        "{PFX86}\\Mozilla Firefox\\firefox.exe",
    ],
    "edge": [
        "{PFX86}\\Microsoft\\Edge\\Application\\msedge.exe",
        "{PF}\\Microsoft\\Edge\\Application\\msedge.exe",
    ],
    "code": [
        "{LOCALAPPDATA}\\Programs\\Microsoft VS Code\\Code.exe",
        "{PF}\\Microsoft VS Code\\bin\\code.cmd",
    ],
    "spotify": [
        "{APPDATA}\\Spotify\\Spotify.exe",
        "{LOCALAPPDATA}\\Spotify\\Spotify.exe",
    ],
    "vlc": [
        "{PF}\\VideoLAN\\VLC\\vlc.exe",
        "{PFX86}\\VideoLAN\\VLC\\vlc.exe",
    ],
    "discord": [
        "{LOCALAPPDATA}\\Discord\\Discord.exe",
    ],
    "slack": [
        "{LOCALAPPDATA}\\slack\\slack.exe",
        "{APPDATA}\\Slack\\slack.exe",
    ],
    "zoom": [
        "{APPDATA}\\Zoom\\bin\\Zoom.exe",
    ],
    "teams": [
        "{LOCALAPPDATA}\\Microsoft\\Teams\\current\\Teams.exe",
    ],
    "outlook": [
        "{PF}\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
        "{PFX86}\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE",
    ],
    "word": [
        "{PF}\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
        "{PFX86}\\Microsoft Office\\root\\Office16\\WINWORD.EXE",
    ],
    "excel": [
        "{PF}\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
        "{PFX86}\\Microsoft Office\\root\\Office16\\EXCEL.EXE",
    ],
    "powerpoint": [
        "{PF}\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
        "{PFX86}\\Microsoft Office\\root\\Office16\\POWERPNT.EXE",
    ],
}


class SystemActions:
    """Open applications and URLs."""

    def __init__(self, allowed_apps=None):
        self.last_action = None
        self._allowed_apps = set(allowed_apps or _ALLOWED_APPS)

    @staticmethod
    def _resolve_app_path(app_name):
        """Resolve a bare app name to an install path on Windows. Tries the
        known-path templates, then PATH lookup. Returns None when unresolvable."""
        import shutil

        base = os.path.splitext(os.path.basename(str(app_name)))[0].lower()
        env = {
            "PF": os.environ.get("ProgramFiles", r"C:\Program Files"),
            "PFX86": os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            "APPDATA": os.environ.get("APPDATA", ""),
            "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
        }
        for template in _APP_PATH_TEMPLATES.get(base, []):
            try:
                candidate = template.format(**env)
            except (KeyError, IndexError):
                continue
            if os.path.isfile(candidate):
                return candidate
        found = shutil.which(base)
        if found and os.path.isfile(found):
            return found
        return None

    def open_app(self, app_name):
        self.last_action = f"Opening {app_name}"
        if not app_name:
            return self._result(False, "no_app_specified", 0)
        try:
            app_name = str(app_name).strip()
            base = os.path.splitext(os.path.basename(app_name))[0].lower()
            if base not in self._allowed_apps:
                logger.warning("[SystemActions] Blocked app not in whitelist: %s", app_name)
                return self._result(False, "app_not_allowed", 0)
            if os.name == "nt":
                try:
                    _start_file(app_name)
                except OSError:
                    resolved = self._resolve_app_path(app_name)
                    if not resolved:
                        return self._result(False, f"app_not_found:{app_name}", 0)
                    _start_file(resolved)
                return self._result(True, f"opened:{app_name}", 0)
            else:
                subprocess.Popen([app_name])
            return self._result(True, f"opened:{app_name}", 0)
        except Exception as e:
            return self._result(False, str(e), 0)

    def open_url(self, url):
        self.last_action = f"Opening {url}"
        if not url:
            return self._result(False, "no_url_provided", 0)
        try:
            url = str(url).strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "https://" + url
            webbrowser.open(url)
            return self._result(True, f"opened:{url}", 0)
        except Exception as e:
            return self._result(False, str(e), 0)

    def search(self, query):
        self.last_action = f"Searching: {query}"
        if not query:
            return self._result(False, "no_search_query", 0)
        try:
            encoded = urllib.parse.quote(str(query))
            url = Settings.SEARCH_ENGINE_URL + encoded
            webbrowser.open(url)
            return self._result(True, f"searching:{query}", 0)
        except Exception as e:
            return self._result(False, str(e), 0)

    _result = staticmethod(_result)


class CommandActions:
    """Run shell commands (blocking and async)."""

    def __init__(self, blocked_commands=None, command_timeout=None, max_output=None):
        self.blocked_commands = blocked_commands or Settings.EXECUTOR_BLOCKED_COMMANDS
        self.command_timeout = command_timeout or Settings.EXECUTOR_COMMAND_TIMEOUT
        self.max_output = max_output or Settings.EXECUTOR_MAX_OUTPUT
        self.running_processes = []
        self._lock = threading.RLock()
        self.last_action = None

    _SHELL_METACHARACTERS = set(";&|`$><\n(){}[]*?!\\")

    def _validate_command(self, command):
        """Return an error key string if command is unsafe, else None."""
        lowered = command.lower()
        for blocked in self.blocked_commands:
            if blocked in lowered:
                return "blocked_dangerous_command"
        if len(command) > 500:
            return "command_too_long"
        for ch in self._SHELL_METACHARACTERS:
            if ch in command:
                return "disallowed_character"
        if "  " in command:
            return "consecutive_spaces"
        return None

    def run_command(self, command, timeout=None):
        self.last_action = f"Running command: {command}"
        if not command:
            return self._result(False, "no_command_provided", 0)
        command = str(command).strip()
        timeout = timeout or self.command_timeout

        error = self._validate_command(command)
        if error:
            return self._result(False, error, 0)

        start = time.time()
        try:
            args = shlex.split(command, posix=False)
            result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
            output = result.stdout or result.stderr or "command_executed"
            output = output[:self.max_output]
            return self._result(result.returncode == 0, output.strip(), round(time.time() - start, 2))
        except subprocess.TimeoutExpired:
            return self._result(False, "command_timeout", round(time.time() - start, 2))
        except Exception as e:
            return self._result(False, str(e), round(time.time() - start, 2))

    def run_async_command(self, command):
        if not command:
            return self._result(False, "no_command_provided", 0)
        command = str(command).strip()

        error = self._validate_command(command)
        if error:
            return self._result(False, error, 0)

        def worker():
            try:
                args = shlex.split(command, posix=False)
                subprocess.Popen(args)
            except Exception as e:
                logger.error("[ASYNC ERROR] %s", e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return self._result(True, f"async_started:{command}", 0)

    _result = staticmethod(_result)


_DESTRUCTIVE_PATTERNS = {
    "alt+f4", "alt+f2", "ctrl+w", "ctrl+q", "ctrl+shift+esc",
    "ctrl+alt+del", "ctrl+alt+f4", "win+r", "win+d",
    "win+l", "win+e", "win+x",
}

class DesktopActions:
    """Desktop automation (typing)."""

    def __init__(self, typing_delay=None, typing_interval=None):
        self.typing_delay = typing_delay or Settings.EXECUTOR_TYPING_DELAY
        self.typing_interval = typing_interval or Settings.EXECUTOR_TYPING_INTERVAL
        self.last_action = None

    def type_text(self, text):
        self.last_action = "Typing text"
        if not text:
            return self._result(False, "no_text_provided", 0)
        if pyautogui is None:
            return self._result(False, "pyautogui_not_available", 0)
        text_str = str(text)
        lower = text_str.lower()
        if lower.strip() in _DESTRUCTIVE_PATTERNS:
            logger.warning("[DesktopActions] Blocked destructive hotkey: %s", lower.strip())
            return self._result(False, "destructive_hotkey_blocked", 0)
        try:
            time.sleep(self.typing_delay)
            pyautogui.write(text_str, interval=self.typing_interval)
            return self._result(True, "typed_successfully", 0)
        except Exception as e:
            return self._result(False, str(e), 0)

    _result = staticmethod(_result)


_CLIPBOARD_SANDBOX_DIRS: list[str] = [str(ROOT_DIR), str(OBSIDIAN_VAULT)]


def _configure_sandbox(*directories: str):
    _CLIPBOARD_SANDBOX_DIRS.clear()
    _CLIPBOARD_SANDBOX_DIRS.extend(str(d) for d in directories)


def _path_allowed(path: str) -> bool:
    p = os.path.abspath(path)
    if not _CLIPBOARD_SANDBOX_DIRS:
        return True
    return any(p.startswith(os.path.abspath(d)) for d in _CLIPBOARD_SANDBOX_DIRS)


class ClipboardActions:
    """Read/write system clipboard via pyperclip."""

    def __init__(self):
        self._pyperclip = None
        self._init_pyperclip()

    def _init_pyperclip(self):
        try:
            import pyperclip
            self._pyperclip = pyperclip
        except ImportError:
            logger.warning("[Clipboard] pyperclip not installed")

    def read(self) -> dict:
        if not self._pyperclip:
            return _result(False, "pyperclip_not_available", 0)
        try:
            text = self._pyperclip.paste()
            return _result(True, text, 0)
        except Exception as e:
            return _result(False, str(e), 0)

    def write(self, text: str) -> dict:
        if not self._pyperclip:
            return _result(False, "pyperclip_not_available", 0)
        if not text:
            return _result(False, "no_text_provided", 0)
        try:
            self._pyperclip.copy(str(text))
            return _result(True, "clipboard_written", 0)
        except Exception as e:
            return _result(False, str(e), 0)


class FileSystemActions:
    """Safe file system operations restricted to an allowlist of directories."""

    MAX_READ_SIZE = 512 * 1024

    def __init__(self):
        self._watchers: dict[str, Any] = {}
        self._watch_lock = threading.RLock()

    def list_dir(self, path: str) -> dict:
        if not _path_allowed(path):
            return _result(False, "path_not_allowed", 0)
        try:
            p = Path(path)
            if not p.is_dir():
                return _result(False, "not_a_directory", 0)
            entries = []
            for child in sorted(p.iterdir()):
                try:
                    entries.append({
                        "name": child.name,
                        "type": "dir" if child.is_dir() else "file",
                        "size": child.stat().st_size if child.is_file() else 0,
                        "modified": child.stat().st_mtime,
                    })
                except OSError:
                    continue
            return _result(True, entries, 0)
        except Exception as e:
            return _result(False, str(e), 0)

    def read_file(self, path: str) -> dict:
        if not _path_allowed(path):
            return _result(False, "path_not_allowed", 0)
        try:
            p = Path(path)
            if not p.is_file():
                return _result(False, "not_a_file", 0)
            if p.stat().st_size > self.MAX_READ_SIZE:
                return _result(False, "file_too_large", 0)
            text = p.read_text(encoding="utf-8", errors="replace")
            return _result(True, text, 0)
        except Exception as e:
            return _result(False, str(e), 0)

    def write_file(self, path: str, content: str) -> dict:
        if not _path_allowed(path):
            return _result(False, "path_not_allowed", 0)
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(str(content), encoding="utf-8")
            return _result(True, "file_written", 0)
        except Exception as e:
            return _result(False, str(e), 0)
