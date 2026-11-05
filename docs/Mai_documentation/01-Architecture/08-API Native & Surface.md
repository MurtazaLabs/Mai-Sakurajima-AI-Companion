# 08 — API, Native, Observability, Prompt & Plugins

> Digest of `SUBSYSTEM_DOCUMENTATION/core.md` (API section) + `native.md`. Full: [[SUBSYSTEM_DOCUMENTATION/core]] (API), [[SUBSYSTEM_DOCUMENTATION/native]].

---

## API — REST, SSE, WebSocket (`api/`, 24 files, 4,084 lines)

Exposes Mai AI as a server: REST endpoints, SSE event stream, WebSocket bridge, static web UI.

- **`MaiAPI`** (`server.py`) — FastAPI facade, 12 route mixins, **~100 endpoints** (103 decorator sites): chat, memory, knowledge, voice, system, profile, agency, reasoning, tasks, dashboard, inspector, auth, permissions. `bootstrap()` sets `mai.app` / `mai.kernel` for the desktop daemon; `cleanup()` tears down.
- **SSE** (`stream_manager.py`) — subscribes to `STREAM_TOPICS`; loop captured at connection (`call_soon_threadsafe` / `run_coroutine_threadsafe`); reconnect backoff in `api/static/js/os.js`.
- **WebSocket** (`ws_bridge.py`) — daemon sync; `STREAM_TOPICS` imported single-source.
- **Metrics** — `GET /metrics` (Prometheus text format, auth-gated in production; degrades to 503 `metrics_unavailable`); optional OpenTelemetry tracing (`core/observability/`); mounted Oct 2026.

### Security Layers

| Layer | Detail |
|-------|--------|
| Auth | JWT + static token (`auth.py`, `get_current_user` single source) + **middleware gate covering every `/api/*` route** (exempt: login/refresh, SSO redirects, `/api/health` probe); **forced on whenever `API_HOST` isn't loopback**; session cookies HttpOnly + SameSite=Lax + Secure-on-HTTPS (all 9 sites); OIDC/SAML redirect targets restricted to local paths; JWT auto-secret random + persisted to `data/jwt_secret` |
| HTTPS | By default — `api/certs.py` auto-generates dev certs on first boot (openssl or cryptography); `certbot` for production |
| Rate limit | token-bucket; max_buckets cap 4096 + LRU eviction |
| Errors | `safe_error()` — no `str(e)` leaks; stable `internal_error` (all 35 response sites) |
| CORS | credentials disabled on wildcard origins |
| Static | mounts only `api/static` (explicit allowlist); all user-supplied content HTML-escaped before innerHTML (XSS fix, Oct 2026) |
| Tools/network | web scraper SSRF-guarded (public-target + connected-peer check + proxy bypass); marketplace plugins signature-required; sandbox `eval` locked down + env-gated |

Route groups (src): `routes_chat/memory/knowledge/voice/system/profile/agency/reasoning/tasks/dashboard/inspector/auth/permissions.py` + `middleware/rate_limiter.py`.

Built and live: `POST /api/voice/toggle` (`api/server.py:772`, auth-gated; impl in `api/routes_voice.py:93`).

## Native — Windows Desktop Bridge (`native/`, 6 files, 535 lines)

| Component | Role |
|-----------|------|
| `TrayDaemon` (tray.py) | pystray system tray; "Open Mai" focuses the AppWindow (webview fallback → browser) |
| `AppWindow` (app_window.py) | **M14 (Oct 2026)** — pywebview (Edge WebView2) frameless window at `/desktop`; close intercept → hide-to-tray; `show()` for tray re-focus |
| `Notifier` (notifier.py) | plyer toasts via EventBus (state.* topics) |
| `HotkeyManager` (hotkeys.py) | Alt+Space, Ctrl+Alt+M, Ctrl+Alt+C, Win+Shift+M (degrades without `keyboard`) |
| `StartupManager` (startup.py) | Windows HKCU Run key (`pythonw` sibling of venv interpreter) |
| `HealthMonitor` (watchdog.py) | PID watchdog + `/api/health` polling |

Entry `run_daemon.py` (M14 rewrite): single bootstrap via `MaiAPI()`, kernel from `mai.kernel`, uvicorn in daemon thread, AppWindow opens on main thread after ≤120s health poll; second launch → focuses running instance (port probe). Packaging `scripts/build_daemon.py` (PyInstaller, `--add-data` fixed) + `installer.iss` (Inno); `scripts/install_app.py` creates the Desktop shortcut + launch-at-login and refuses a voiceless interpreter. Bridge = `api/ws_bridge.py` WebSocket. See [[03-Features/Native OS Bridge Architecture]] for the full M14 record.

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