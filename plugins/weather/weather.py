"""
Weather Plugin - Fetches current weather via OpenWeatherMap API
Hardened with manifest, sandbox support, error handling, and caching.
"""
import json
import logging
import os
import time
import urllib.parse
import urllib.request
import urllib.error
from functools import lru_cache
from typing import Optional, Dict, Any

from core.plugin_system import Plugin
from plugins.plugin_manifest import PluginManifest, PluginPermission, PluginDependency

logger = logging.getLogger("Mai.Plugin.Weather")


class WeatherPlugin:
    """Weather plugin with manifest, sandbox support, and caching."""
    
    # Plugin manifest - defines metadata, permissions, and dependencies
    MANIFEST = {
        "name": "weather",
        "version": "1.1.0",
        "description": "Fetches current weather via OpenWeatherMap API",
        "author": "Mai AI Team",
        "entry_point": "weather:WeatherPlugin",
        "api_version": "1.0",
        "permissions": {
            "filesystem": "none",
            "network": "outbound",
            "execution": "none",
            "api_access": ["weather"],
            "config": "read"
        },
        "dependencies": [],
        "hooks": ["pre_chat"],
        "min_mai_version": "1.0.0",
        "homepage": "https://github.com/mai-ai/plugins",
        "repository": "https://github.com/mai-ai/plugins",
        "license": "MIT",
        "tags": ["weather", "utility", "api"]
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.api_key = self.config.get("api_key") or os.environ.get("OPENWEATHER_API_KEY", "")
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"
        self._cache: Dict[str, tuple[float, str]] = {}  # city -> (timestamp, result)
        self.cache_ttl = 600  # 10 minutes

    @classmethod
    def get_manifest(cls) -> dict:
        """Return the plugin manifest."""
        return cls.MANIFEST

    def on_load(self, hooks, brain, event_bus):
        """Initialize plugin and register hooks."""
        self.hooks = hooks
        self.brain = brain
        self.event_bus = event_bus
        
        if not self.api_key:
            logger.warning("OPENWEATHER_API_KEY not set — weather lookups will fail")
        
        hooks.register("pre_chat", self.on_pre_chat, priority=5)
        logger.info("Weather plugin loaded (api_key=%s)", bool(self.api_key))

    def on_unload(self):
        """Cleanup on unload."""
        logger.info("Weather plugin unloaded")

    def on_pre_chat(self, user_input: str, **kwargs) -> Optional[str]:
        """Handle weather queries."""
        text = user_input.lower().strip()
        if not text.startswith("weather"):
            return None
        
        parts = text.split(None, 1)
        if len(parts) < 2:
            return "Please specify a city. Example: weather London"
        
        city = parts[1].strip()
        return self._fetch_weather(city)

    @lru_cache(maxsize=100)
    def _fetch_weather(self, city: str) -> str:
        """Fetch weather with caching."""
        # Check cache first
        cache_key = city.lower()
        if cache_key in self._cache:
            timestamp, result = self._cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return result
        
        if not self.api_key:
            return "Weather API key not configured. Set OPENWEATHER_API_KEY."
        
        params = urllib.parse.urlencode({
            "q": city, 
            "appid": self.api_key, 
            "units": "metric"
        })
        url = f"{self.base_url}?{params}"
        
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return f"City not found: {city}"
            return f"Weather API error: {e.code}"
        except urllib.error.URLError as e:
            return f"Network error: {e.reason}"
        except Exception as e:
            logger.error("Weather fetch failed: %s", e)
            return f"Weather lookup failed: {e}"
        
        desc = data.get("weather", [{}])[0].get("description", "unknown")
        temp = data.get("main", {}).get("temp", "?")
        humidity = data.get("main", {}).get("humidity", "?")
        wind = data.get("wind", {}).get("speed", "?")
        
        result = (
            f"Weather in {city}: {desc}, "
            f"{temp:.1f}°C, humidity {humidity}%, wind {wind} m/s"
        )
        
        # Cache result
        self._cache[cache_key] = (time.time(), result)
        return result

    def _fetch_weather(self, city: str) -> str:
        """Wrapper for cached fetch."""
        return self._fetch_weather(city)


# For backward compatibility with old plugin system
class WeatherPlugin:
    """Legacy wrapper for old plugin system."""
    
    def __init__(self):
        self._impl = None
    
    def __getattr__(self, name):
        if self._impl is None:
            from plugins.weather import WeatherPlugin as NewWeatherPlugin
            self._impl = NewWeatherPlugin()
        return getattr(self._impl, name)

    def __init__(self):
        self._impl = WeatherPlugin()
        self.__dict__.update(self._impl.__dict__)