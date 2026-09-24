# 08 — API, Native, Observability, Prompt & Plugins

> Digest of `SUBSYSTEM_DOCUMENTATION/core.md` (API section) + `native.md`. Full: [[SUBSYSTEM_DOCUMENTATION/core]] (API), [[SUBSYSTEM_DOCUMENTATION/native]].

---

## API — REST, SSE, WebSocket (`api/`, 23 files, 3,035 lines)

Exposes Mai AI as a server: REST endpoints, SSE event stream, WebSocket bridge, static web UI.

- **`MaiAPI`** (`server.py`) — FastAPI facade, 11 route mixins (~60 routes): chat, memory, knowledge, voice, system, profile, agency, reasoning, tasks, dashboard, inspector, auth, permissions. `bootstrap()` → `run.bootstrap_system()`; `cleanup()` tears down.
- **SSE** (`stream_manager.py`) — subscribes to `STREAM_TOPICS`; loop captured at connection (`call_soon_threadsafe` / `run_coroutine_threadsafe`); reconnect backoff in `api/static/js/os.js`.
- **WebSocket** (`ws_bridge.py`) — daemon sync; `STREAM_TOPICS` imported single-source.

### Security Layers

| Layer | Detail |
|-------|--------|
| Auth | JWT + static token (`auth.py`, `get_current_user` single source) |
| Rate limit | token-bucket; max_buckets cap 4096 + LRU eviction |
| Errors | `safe_error()` — no `str(e)` leaks; stable `internal_error` |
| CORS | credentials disabled on wildcard origins |
| Static | mounts only `api/static` (explicit allowlist) |

Route groups (src): `routes_chat/memory/knowledge/voice/system/profile/agency/reasoning/tasks/dashboard/inspector/auth/permissions.py` + `middleware/rate_limiter.py`.

## Native — Windows Desktop Bridge (`native/`, 6 files, 535 lines)

| Component | Role |
|-----------|------|
| `TrayDaemon` (tray.py) | pystray system tray |
| `Notifier` (notifier.py) | plyer toasts via EventBus |
| `HotkeyManager` (hotkeys.py) | Alt+Space, Ctrl+Alt+M, Ctrl+Alt+C, Win+Shift+M (degrades without `keyboard`) |
| `StartupManager` (startup.py) | Windows HKCU Run key |
| `HealthMonitor` (watchdog.py) | PID watchdog + `/api/health` polling |

Entry `run_daemon.py`; packaging `scripts/build_daemon.py` (PyInstaller) + `installer.iss` (Inno). Bridge = `api/ws_bridge.py` WebSocket.

## Observability (3 files, 756 lines)

| Component | Role |
|-----------|------|
| `HealthRegistry` (health.py) | global thread-safe health register |
| `EventInspector` (event_inspector.py) | live event inspection (feeds dashboard) |
| `Tracer` (tracer.py) | run tracing; PII redaction on disk (`_redact_text`/`_redact_trail`) |

## Prompt (7 files, 330 lines)

`CharacterPrompt` (persona + speech pacing), `EmotionalPrompt`, `ContextPrompt`, `AgentPrompt`, `PromptBuilder` — all stateless, thoroughly documented; compat wrappers in `core/prompt_builder.py` + `core/prompt_orchestrator.py`.

## Plugins (6 files, 446 lines + loader in core)

`weather`, `news`, `calendar`, `system_monitor`, `web_scraper`, `example_plugin`. Mechanics (`core/plugin_system.py`): `HookRegistry` (priority-ordered, error isolation), `Plugin` (`on_load(hooks, brain, event_bus)`, `on_unload()`), `PluginLoader` (discovers `plugins/*.py`; validated names on API load endpoint).

## Known Issues

- Plugin ecosystem young (roadmap: manifest, lifecycle, marketplace).
- Dashboard code split between `observability/` and `api/`.

---

## Wiki Links

**Previous:** [[07-Voice Subsystem]]  
**Next:** [[09-Events & Data Flow]] — event fabric reference + data flow  
**Related:** [[03-Features/Native OS Bridge Architecture]] — daemon architecture detail • [[03-Features/Discord Integration Plan]] — Discord bot uses API • [[04-Development/Deployment Guide]] — Docker, installer