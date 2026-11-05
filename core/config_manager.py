"""Runtime config manager — persists user overrides to JSON.

Provides get/set for a mutable config layer that sits on top of the
static ``config/*.py`` module-level constants. Overrides are saved to
``data/runtime_config.json`` and apply until the next restart.
"""
import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
_CONFIG_PATH = os.path.join(_CONFIG_DIR, "runtime_config.json")

_SAFE_KEYS = {
    "LLM_MODEL", "LLM_TEMPERATURE", "LLM_TOP_P",
    "WHISPER_MODEL", "KOKORO_VOICE", "KOKORO_LANG_CODE",
    "SILENCE_THRESHOLD", "SILENCE_DURATION", "VAD_THRESHOLD",
    "DEBUG_MODE", "LOG_LEVEL", "ENABLE_AUTONOMY",
    "SCHEDULER_ENABLED",
    "AI_NAME", "LLM_MAX_CONTEXT",
    "EXECUTOR_MODE",
}

_KEY_META = {
    "LLM_MODEL": {"label": "LLM Model", "category": "ai", "type": "text"},
    "LLM_TEMPERATURE": {"label": "Temperature", "category": "ai", "type": "float", "min": 0.0, "max": 2.0, "step": 0.05},
    "LLM_TOP_P": {"label": "Top-P", "category": "ai", "type": "float", "min": 0.0, "max": 1.0, "step": 0.05},
    "LLM_MAX_CONTEXT": {"label": "Max Context Tokens", "category": "ai", "type": "int", "min": 512, "max": 32768},
    "WHISPER_MODEL": {"label": "Whisper Model", "category": "voice", "type": "select", "options": ["tiny", "base", "small", "medium", "large"]},
    "KOKORO_VOICE": {"label": "TTS Voice", "category": "voice", "type": "text"},
    "KOKORO_LANG_CODE": {"label": "TTS Language Code", "category": "voice", "type": "text"},
    "SILENCE_THRESHOLD": {"label": "Silence Threshold", "category": "voice", "type": "float", "min": 0.001, "max": 0.1, "step": 0.001},
    "SILENCE_DURATION": {"label": "Silence Duration (s)", "category": "voice", "type": "float", "min": 0.1, "max": 5.0, "step": 0.1},
    "VAD_THRESHOLD": {"label": "VAD Threshold", "category": "voice", "type": "float", "min": 0.0, "max": 1.0, "step": 0.05},
    "DEBUG_MODE": {"label": "Debug Mode", "category": "system", "type": "bool"},
    "LOG_LEVEL": {"label": "Log Level", "category": "system", "type": "select", "options": ["DEBUG", "INFO", "WARNING", "ERROR"]},
    "ENABLE_AUTONOMY": {"label": "Autonomous Mode", "category": "system", "type": "bool"},
    "SCHEDULER_ENABLED": {"label": "Scheduler", "category": "system", "type": "bool"},
    "AI_NAME": {"label": "AI Name", "category": "system", "type": "text"},
    "EXECUTOR_MODE": {"label": "Executor Mode", "category": "system", "type": "select", "options": ["safe", "advanced", "admin"]},
}


class ConfigManager:
    """Thread-safe runtime config overrides persisted to JSON."""

    def __init__(self):
        self._lock = threading.RLock()
        self._overrides = {}
        self._load()

    def _load(self):
        try:
            os.makedirs(_CONFIG_DIR, exist_ok=True)
            if os.path.isfile(_CONFIG_PATH):
                with open(_CONFIG_PATH, "r") as f:
                    self._overrides = json.load(f)
        except Exception as e:
            logger.warning("[Config] Failed to load overrides: %s", e)

    def _save(self):
        try:
            os.makedirs(_CONFIG_DIR, exist_ok=True)
            with open(_CONFIG_PATH, "w") as f:
                json.dump(self._overrides, f, indent=2)
        except Exception as e:
            logger.warning("[Config] Failed to save overrides: %s", e)

    def get_all(self):
        with self._lock:
            return dict(self._overrides)

    def get(self, key, default=None):
        with self._lock:
            return self._overrides.get(key, default)

    def set(self, key, value):
        if key not in _SAFE_KEYS:
            return False
        with self._lock:
            self._overrides[key] = value
            self._save()
        return True

    def set_many(self, items):
        updated = {}
        with self._lock:
            for k, v in items.items():
                if k in _SAFE_KEYS:
                    self._overrides[k] = v
                    updated[k] = v
            if updated:
                self._save()
        return updated

    def get_meta(self, key):
        return _KEY_META.get(key, {})

    def list_safe_keys(self):
        return sorted(_SAFE_KEYS)
