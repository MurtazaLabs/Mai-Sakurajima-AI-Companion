# Plugin SDK Design

## Plugin Lifecycle

```
discovered → loaded → activated → deactivated → unloaded
                ↓
            (error → unloaded)
```

- **discovered**: Plugin file found in plugins/ directory
- **loaded**: Module imported, Plugin subclass detected
- **activated**: on_load() called, hooks registered
- **deactivated**: on_unload() called, hooks unregistered
- **unloaded**: Cleanup complete

## Hook Architecture

### Hook Registry
```python
# Core hooks available for plugin registration
HOOKS = {
    "pre_chat":        (1, 10),    # (priority_range, args: message, context)
    "post_response":   (1, 10),    # (priority_range, args: response, context)
    "memory_store":    (1, 10),    # (priority_range, args: memory_object)
    "memory_retrieve": (1, 10),    # (priority_range, args: query, results)
    "llm_pre_call":    (1, 10),    # (priority_range, args: prompt, model)
    "llm_post_call":   (1, 10),    # (priority_range, args: response, duration)
    "system_startup":  (1, 10),    # (priority_range, args: brain)
    "system_shutdown": (1, 10),    # (priority_range, args: None)
    "error_occurred":  (1, 10),    # (priority_range, args: exception, context)
}
```

## Plugin Base Class

```python
class Plugin:
    name: str
    version: str
    description: str

    def on_load(self, hooks: HookRegistry, brain: Brain, event_bus: EventBus) -> None: ...
    def on_unload(self) -> None: ...
    def on_activate(self) -> None: ...
    def on_deactivate(self) -> None: ...
```

## Sandboxing

- Plugins run in the same process (Python GIL safety)
- No filesystem access outside plugin directory
- No subprocess execution
- Network access restricted to configured allowlist
- Opaque error isolation (one plugin crash doesn't affect others)
- Memory limit warning at 100MB per plugin

## Manifest Format

```json
{
  "name": "weather-plugin",
  "version": "1.0.0",
  "author": "Mai AI Team",
  "description": "Fetches weather data via OpenWeatherMap",
  "hooks": ["pre_chat", "post_response"],
  "dependencies": {
    "requests": ">=2.28.0"
  },
  "min_api_version": "2.0.0",
  "permissions": ["network:weather-api"],
  "settings": {
    "api_key_env": "WEATHER_API_KEY",
    "default_unit": "celsius"
  }
}
```

## Packaging

```
weather-plugin/
├── manifest.json
├── plugin.py
├── requirements.txt
└── README.md

Distribution: .zip archive (named <plugin-name>.plugin)
Install: Place in plugins/ directory and restart
```
