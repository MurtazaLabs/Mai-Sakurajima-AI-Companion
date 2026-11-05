# Deployment Guide

> Production deployment options for Mai AI: Docker, native Windows daemon installer, production hardening checklist.

---

## Deployment Options

### 1. Docker (Recommended for Server/Cloud)

**Files:** `Dockerfile`, `docker-compose.yml`, `requirements-docker.txt`

```bash
# Build
docker compose build

# Run (background)
docker compose up -d

# Logs
docker compose logs -f

# Stop
docker compose down
```

**Volumes (persisted — mirrors `config/paths.py`):**
- `./data:/app/data` — certs, JWT secret, Obsidian vault (`/app/data/vault`)
- `./vector_memory:/app/vector_memory` — vector store
- `./memory:/app/memory` — memory pipeline state
- `./cache:/app/cache` — embedding cache
- `./logs:/app/logs` — application logs

**Auth note:** the container binds `API_HOST=0.0.0.0`, so auth is *enforced* on
`/api/*` (JWT/static token via `Authorization: Bearer …`). The web UI has no
browser login flow yet — REST clients work today; the Java M14 client wires the
login/token flow. Locally (desktop daemon, loopback) auth stays off by design.

**Ports:** `8000:8000` (FastAPI)

**Restart policy:** `unless-stopped`

**Base image:** `python:3.10-slim`

---

### 2. Native Windows Daemon (Recommended for Desktop)

**Entry point:** `run_daemon.py`

**Components:**
- System tray (`native/tray.py`) — pystray icon + menu
- Global hotkeys (`native/hotkeys.py`) — Alt+Space, Ctrl+Alt+M, Ctrl+Alt+C, Win+Shift+M
- WebSocket bridge (`api/ws_bridge.py`) — daemon ↔ browser sync
- Health monitor (`native/watchdog.py`) — PID watchdog + `/api/health` polling
- Startup registration (`native/startup.py`) — HKCU Run key

**Build installer:**
```bash
# PyInstaller single EXE
python scripts/build_daemon.py

# Inno Setup installer
# Requires Inno Setup 6+ installed
iscc scripts/installer.iss
```

**Output:** `dist/mai-daemon.exe` + `Output/Mai AI Setup.exe`

**Installed location:** `%LOCALAPPDATA%\Mai AI\`

**Auto-start:** Registered via `StartupManager` on first run (user consent).

---

### 3. Development / CLI Mode

```bash
# Interactive CLI (blocks terminal)
python run.py

# REST API only
python -m api.server

# With custom config
MAI_API_HOST=0.0.0.0 MAI_API_PORT=8080 python run.py
```

---

## Production Hardening Checklist

### ✅ Completed
- [x] Rate limiting (token-bucket, 4096 bucket cap + LRU eviction)
- [x] Error sanitization (`safe_error()` — no `str(e)` leaks)
- [x] CORS strict mode (credentials disabled on wildcard origins)
- [x] Static file allowlist (only `api/static/` mounted)
- [x] FS sandbox (allowlist: `ROOT_DIR`, `OBSIDIAN_VAULT`)
- [x] App whitelist (20+ apps in `SystemActions.open_app()`)
- [x] Keystroke filter (blocks Alt+F4, Ctrl+W, etc.)
- [x] SHA-256 VAD model verification
- [x] JWT auth infrastructure (`auth.py`, `get_current_user`) + enforcement on `/api/config` + `/metrics`
- [x] **HTTPS** — `api/certs.py` auto-generates dev certs on first boot (openssl or pure-python fallback); production Let's Encrypt
- [x] Health registry with fail-safe telemetry
- [x] Metrics endpoint (`/metrics`, Prometheus text format) + optional OpenTelemetry tracing
- [x] **Desktop app shell** — `run_daemon.py` + pywebview `AppWindow` (hide-to-tray), `scripts/install_app.py` shortcut + autostart (M14, Oct 2026)
- [x] **Oct-19 security fixes** — SSRF-guarded scraper (public-target + connected-peer + proxy bypass), sandbox eval lockdown, marketplace signature enforcement, auth cookie flags, redirect-target allowlist, XSS escape in chat.js

### 🟡 In Progress / Partial
- [ ] Multi-session / user profiles (memory scoping, profile CRUD)
- [ ] Cloud sync (S3/Backblaze B2 periodic backup)
- [ ] Structured logging pipeline (JSON, Loki/ELK compatible)
- [ ] Let's Encrypt certs for public deployments (dev HTTPS auto-generated is done)

### ❌ Not Started
- [ ] Alerting (PagerDuty, email, Discord webhook)
- [ ] Backup/DR strategy (vault, vector DB, profiles)
- [ ] Load testing (locust/k6)
- [ ] Chaos engineering (latency injection, failure injection)

---

## Configuration for Production

### Environment Variables

```bash
# API
MAI_API_HOST=0.0.0.0
MAI_API_PORT=8000
MAI_API_WORKERS=4

# Auth
JWT_SECRET_KEY=<strong-random-64-char>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
STATIC_API_TOKEN=<fallback-token>

# LLM
OPENROUTER_API_KEY=<key>
OLLAMA_HOST=http://localhost:11434
LLM_PROVIDER=openrouter            # or "ollama" for local-first ordering (Oct 2026)
OPENROUTER_DEFAULT_MODEL=openrouter/free   # sanitized failover list; default router (free, no 402)

# Paths
OBSIDIAN_VAULT=E:/MaiMemory
ROOT_DIR=E:/Murtaza project/Mai_ai
LOG_DIR=E:/Murtaza project/Mai_ai/logs

# Voice
KOKORO_MODEL=hexgrad/Kokoro-82M
VAD_MODEL_URL=<checksummed-url>
SPEAKER_EMBEDDING_MODEL=<path>

# Native
MAI_DAEMON_MODE=1
MAI_STARTUP_REGISTER=1
```

### Settings Files (config/)

All settings in `config/settings.py` with per-module configs in `config/*.py`. Override via env vars (prefix `MAI_`).

---

## Monitoring & Observability

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health` | Liveness — returns `{"status": "ok"}` if all core subsystems healthy |
| `GET /api/status` | Readiness — emotion, goals, world model stats |
| `GET /api/inspector/events` | Event inspector — live event stream |
| `GET /api/inspector/traces` | Tracer — recent traces |

### Key Metrics to Watch

- `health_registry.stats()` — subsystem health (ok/warn/error/stalled)
- `event_bus.stats()` — publish/subscribe throughput, latency
- `scheduler.stats()` — task success/failure rates
- `voice_manager.metrics` — VAD/STT/TTS latency, interruption rate
- `memory_pipeline.stats()` — store/retrieve latency, consolidation runs

### Logging

- Structured JSON logs in `logs/`
- Cognitive audit logs in `logs/cognitive_audit/`
- Orchestrator transitions in `logs/orchestrator/transitions.jsonl`
- Tracer PII-redacted traces in `data/traces/`

---

## Backup Strategy

### What to Back Up

| Data | Location | Frequency |
|------|----------|-----------|
| Vector DB | `data/vector_db/chroma.sqlite3` | Daily |
| Knowledge graph | `data/graph/graph.json` | Daily |
| Profiles | `data/profiles/profiles.db` | Daily |
| Obsidian vault | `OBSIDIAN_VAULT/` | Hourly (incremental) |
| Embedding cache | `data/cache/` | Weekly |
| Logs | `logs/` | Daily (rotate) |

### Cloud Sync (Planned)

- `sync/cloud_sync.py` — S3/B2 periodic sync
- Conflict resolution: last-writer-wins + timestamp logging
- Configurable interval (default 300s)

---

## Rollback Procedure

1. Stop daemon/API: `docker compose down` or tray → Quit
2. Restore `data/`, `OBSIDIAN_VAULT/`, `logs/` from backup
3. Restore `config/settings.py` if changed
4. Restart: `docker compose up -d` or run daemon

---

## Wiki Links

**Related:** [[03-Features/Native OS Bridge Architecture]] — daemon build/install • [[01-Architecture/08-API Native & Surface]] — API surface • [[01-Architecture/10-Status & Debt]] — hardening status • [[04-Development/Testing Strategy]] — CI/CD