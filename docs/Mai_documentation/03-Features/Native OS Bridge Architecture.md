# Native OS Bridge — Architecture Plan

> **Date:** Jul 22 2026 | **Status:** Proposed → **Phases 1-3 Complete (Jul 24)** | **Priority:** P1 — Production Hardening

---

## Motivation

The current "OS" is a desktop-themed web SPA — draggable divs and a taskbar rendered in a browser tab. There is no native integration: no system tray, no global hotkeys, no background persistence, no native notifications. The kernel blocks the terminal; closing the browser kills the UI but not the brain.

**Goal:** Transform Mai AI from a browser app into a native Windows daemon with a web UI client. The AI runs in the system tray; the browser is one of many possible frontends.

---

## Architecture

```
┌──────────────────────────────────────────┐
│          Browser (Web UI)                │
│  ┌────────┐ ┌────────┐ ┌──────────┐     │
│  │ Desktop│ │  Chat  │ │  Memory  │     │
│  │  Shell │ │   UI   │ │  Browser │     │
│  └───┬────┘ └───┬────┘ └────┬─────┘     │
│      │          │           │           │
│      └── HTTP / WS / SSE ───┘           │
└─────────────────┼────────────────────────┘
                  │
┌─────────────────┼────────────────────────┐
│     Mai Daemon (Python, background)       │
│                                           │
│  ┌─────────────────────────────────────┐  │
│  │         FastAPI / Uvicorn           │  │
│  │  ┌───────┐ ┌───────┐ ┌──────────┐  │  │
│  │  │ REST  │ │  WS   │ │ SSE      │  │  │
│  │  │  API  │ │ Bridge│ │ Streams  │  │  │
│  │  └───────┘ └───┬───┘ └──────────┘  │  │
│  └────────────────┼────────────────────┘  │
│                   │                       │
│  ┌────────────────┼────────────────────┐  │
│  │     Application Core (existing)     │  │
│  │  Brain, Kernel, Memory, Voice...   │  │
│  └─────────────────────────────────────┘  │
│                   │                       │
│  ┌────────────────┼────────────────────┐  │
│  │      Native Bridge Layer (NEW)      │  │
│  │  ┌──────────┐ ┌─────────┐ ┌──────┐  │  │
│  │  │  Tray    │ │  Global │ │ Win  │  │  │
│  │  │  Daemon  │ │  Hotkeys│ │ Notif│  │  │
│  │  ├──────────┤ ├─────────┤ ├──────┤  │  │
│  │  │Clipboard │ │ File    │ │Power │  │  │
│  │  │ Bridge   │ │ Watcher │ │ Mgmt │  │  │
│  │  └──────────┘ └─────────┘ └──────┘  │  │
│  └──────────────────────────────────────┘  │
└────────────────────────────────────────────┘
```

### Process Model

```
┌──────────────────────┐
│   Windows Shell      │
│  (explorer.exe)      │
│       │              │
│       │ launch on    │
│       │ startup      │
│       ▼              │
│  ┌────────────────┐  │
│  │ Mai Daemon     │  │  ←── Background process (no console)
│  │ mai-daemon.exe │  │       GUI subsystem, NOT console
│  │                │  │
│  │ ├─ Tray Icon   │  │       System tray (notification area)
│  │ ├─ Hotkey      │  │       Global hotkey listener
│  │ │   Listener   │  │
│  │ ├─ WS Server   │  │       Localhost WebSocket server
│  │ ├─ REST API    │  │       Localhost REST API
│  │ ├─ Brain       │  │       AI core (always alive)
│  │ ├─ Voice       │  │       STT/TTS (on-demand)
│  │ └─ Scheduler   │  │       Background tasks
│  └────────────────┘  │
│       │              │
│       │ spawns on    │
│       │ hotkey/open  │
│       ▼              │
│  ┌────────────────┐  │
│  │ Browser Tab    │  │  ←── Optional frontend
│  │ (Web UI)       │  │       Connects via WS + HTTP
│  └────────────────┘  │
└──────────────────────┘
```

Key property: **The daemon does not depend on the browser.** Closing the tab leaves the AI running. The browser is a detachable UI client, not the host.

---

## Implementation Phases

### Phase 1 — Foundation (Complete ✅)

#### 1a — Daemon Mode
Refactored `AIOSKernel.run()` to operate in two modes:

| Mode | Behavior | Use case |
|------|----------|----------|
| `foreground` | Current blocking loop, polls wake word, FSM-driven | `python run.py` |
| `background` | Non-blocking `start()` / `stop()`, timer-driven background tick | Daemon mode |

**Changes:** `core/os_kernel.py` — extract `_tick()`; `app/lifecycle.py` — add `background_start()`; new `KernelMode` enum.

#### 1b — WebSocket Bridge
Added WebSocket endpoint to FastAPI server:
- `GET /ws` — upgrades to WebSocket; client sends `{"type": "subscribe", "topics": [...]}`
- Server pushes events from EventBus topics to connected WS clients
- Client can send commands: `{"type": "command", "action": "wake", "payload": {...}}`
- Reuses `StreamManager` event bus subscription pattern

**Files:** `api/ws_bridge.py`, `api/server.py` | **Deps:** `websockets==16.0` (exists)

#### 1c — System Tray
Background thread with system tray icon and context menu:

| Menu Item | Action |
|-----------|--------|
| Open Mai | Opens `http://localhost:8000/desktop` in default browser |
| Toggle Voice | Calls `voice_manager.toggle()` |
| Status | Shows current phase, emotion, memory count (tooltip) |
| Settings | Opens settings page in browser |
| Quit | Graceful shutdown of entire daemon |

**Files:** `native/tray.py`, `native/__init__.py` | **Deps:** `pystray`, `Pillow`, `pywin32`

#### 1d — Windows Notifications
Bridge `EventBus` event types to native Windows toast notifications:

| EventBus Topic | Toast Behavior |
|----------------|----------------|
| `emotion_change` | Notify on significant shifts (e.g., mood drop) |
| `dream_complete` | Brief summary of dream insight |
| `goal_completed` | "Goal X completed" |
| `wake_word` | "Listening..." toast |
| `error` | Critical error notification |

**Files:** `native/notifier.py` | **Deps:** `plyer`

---

### Phase 2 — OS Integration (Complete ✅)

#### 2a — Global Hotkeys
Register global hotkeys that work even when browser is not focused:

| Hotkey | Action |
|--------|--------|
| `Alt+Space` | Toggle Mai voice (wake/listen) |
| `Ctrl+Alt+M` | Open Mai desktop UI |
| `Ctrl+Alt+C` | Open chat interface |
| `Win+Shift+M` | Quick capture (send clipboard content to Mai) |

**Files:** `native/hotkeys.py` | **Deps:** `keyboard`

#### 2b — Clipboard Bridge
Expose system clipboard read/write via REST API:
- `GET /api/system/clipboard` — Read current clipboard content (plain text)
- `POST /api/system/clipboard` — Write text to clipboard
- Used by `DesktopActions.type_text()` flow and by plugins

**Files:** `api/routes_system.py`, `execution/handlers.py` | **Deps:** `pyperclip`

#### 2c — File System Bridge
Extend REST API with safe file system operations:
- `GET /api/system/fs/list?path=C:\...` — List directory (filtered, sandboxed)
- `GET /api/system/fs/read?path=...` — Read text file (size-limited)
- `POST /api/system/fs/write` — Write text file (sandboxed)
- `POST /api/system/fs/watch` — Start watching a directory (uses existing `watchdog`)

All paths validated against an allowlist of directories.

**Files:** `api/routes_system.py`, `execution/handlers.py` | **Deps:** `watchdog` (exists)

---

### Phase 3 — Polish & Packaging (Complete ✅)

#### 3a — Startup Registration
- `native/startup.py` — Register daemon to run at Windows startup via registry `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- Optional Windows Service mode via `pywin32` `win32serviceutil`

#### 3b — Installer
- `scripts/build_daemon.py` — PyInstaller-based single EXE for the daemon
- Inno Setup installer: installs daemon, start menu shortcut, uninstaller

#### 3c — Error Recovery
- Auto-restart on crash (watchdog process or Windows Service recovery)
- Health endpoint monitoring from an external watchdog script
- Graceful degradation: if tray fails, fall back to console mode

#### 3d — Frontend Enhancements
- Reconnection logic in `api/static/js/os.js` — detect daemon disconnect, show "Daemon offline" overlay, auto-reconnect
- Connection status indicator in browser UI (green/yellow/red dot)

---

## Dependency Map

```
Phase 1a (Daemon Mode)     ─── no new deps
Phase 1b (WebSocket)       ─── websockets==16.0 ✓ (exists)
Phase 1c (System Tray)     ─── pystray + Pillow + pywin32 (NEW)
Phase 1d (Notifications)   ─── plyer (NEW)
Phase 2a (Global Hotkeys)  ─── keyboard (NEW)
Phase 2b (Clipboard)       ─── pyperclip (NEW)
Phase 2c (File System)     ─── watchdog ✓ (exists)
Phase 3a (Startup)         ─── pywin32 (NEW)
Phase 3b (Installer)       ─── PyInstaller + Inno Setup (NEW)
Phase 3c (Error Recovery)  ─── no new deps
Phase 3d (Frontend)        ─── no new deps
```

### New Dependencies (added to requirements.txt)

```txt
pystray>=0.19.5            # System tray icon
Pillow>=10.0.0             # Image processing (icon)
pywin32>=306               # Windows API (tray, startup, clipboard)
plyer>=2.1.0               # Cross-platform notifications
keyboard>=0.13.5           # Global hotkeys
pyperclip>=1.9.0           # Clipboard access
```

---

## File Manifest

### New Files

| File | Purpose |
|------|---------|
| `native/__init__.py` | Package init |
| `native/tray.py` | `TrayDaemon` — system tray icon + menu |
| `native/notifier.py` | `Notifier` — Windows toast notifications |
| `native/hotkeys.py` | `HotkeyManager` — global hotkey registration |
| `native/startup.py` | Auto-start registration |
| `native/watchdog.py` | `HealthMonitor` — PID watchdog + health polling |
| `api/ws_bridge.py` | `WSBridge` — WebSocket endpoint + client manager |
| `scripts/build_daemon.py` | PyInstaller build script |
| `scripts/installer.iss` | Inno Setup installer script |

### Modified Files

| File | Changes |
|------|---------|
| `core/os_kernel.py` | Extract `_tick()`; add `KernelMode` enum; add `start_background()` / `stop_background()` |
| `app/lifecycle.py` | Add `background_start()` mode |
| `api/server.py` | Register WebSocket endpoint, inject `WSBridge` |
| `api/stream_manager.py` | Add WS client manager alongside SSE |
| `api/routes_system.py` | Add clipboard, file system endpoints |
| `execution/handlers.py` | Add clipboard methods, `FileSystemActions` class |
| `api/static/js/os.js` | WS connection, reconnection, status indicators |
| `requirements.txt` | Add 6 new dependencies |

---

## Security Model

| Layer | Control |
|-------|---------|
| **File system** | Directory allowlist only; no access outside `C:\Users\...\Mai\`, project dir, temp dir |
| **Clipboard** | Read requires explicit permission (API token scope); write always allowed |
| **Hotkeys** | Registered at install time; no arbitrary code execution from hotkey |
| **WebSocket** | Same auth as REST API (bearer token); no unauthenticated WS connections |
| **Network** | Daemon binds to `127.0.0.1` only; not exposed to LAN by default |
| **Startup** | `HKCU\CurrentVersion\Run` only (no admin elevation) |

---

## Testing Strategy

| Component | Approach |
|-----------|----------|
| Daemon mode | Unit test `_tick()` isolation; integration test background cycle |
| WebSocket | `pytest` with `websockets` client connecting to test server |
| System tray | Manual (no headless tray testing); mock `pystray.Icon` in unit tests |
| Notifications | Manual; mock `plyer` notification API in unit tests |
| Hotkeys | Manual; mock `keyboard.add_hotkey` in unit tests |
| Clipboard | Unit test with `pyperclip` mock or isolated clipboard context |
| File system | Integration test with temp directory allowlist |
| Frontend | Manual: connect/disconnect, reconnect, status indicator |

---

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `pystray` unstable on Windows | Medium | Fall back to hidden console window; use `pywin32` Shell_NotifyIcon directly |
| Global hotkey conflicts | Medium | Configurable hotkey bindings in settings; warn on conflict |
| Daemon crash loses brain state | Low | SharedState persists to disk every 30s; brain state saved before shutdown |
| `pywin32` missing on clean Windows | Low | Bundled with PyInstaller build; fallback graceful degradation |
| WebSocket reconnect storm | Low | Exponential backoff; max reconnect interval 30s |

---

## Wiki Links

**Related:** [[01-Architecture/08-API Native & Surface]] — API/native overview • [[01-Architecture/07-Voice Subsystem]] — voice integration • [[04-Development/Deployment Guide]] — Docker, installer details • [[05-Reference/Complete Folder Structure]] — native/ folder detail