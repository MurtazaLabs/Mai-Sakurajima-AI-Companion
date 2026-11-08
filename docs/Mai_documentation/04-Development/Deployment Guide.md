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
`/api/*` (JWT/static token via `Authorization: Bearer …`). The web UI ships a
working browser login flow (`api/static/login.html` + `js/login.js` →
`/api/auth/login`, `/register`, `/refresh`, `/me`). Locally (desktop daemon,
loopback) auth stays off by design unless `API_REQUIRE_AUTH=true`.

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

# REST API only (no kernel FSM, no mic)
python run.py --mode api

# With custom bind (env names verified Nov 2026)
API_HOST=0.0.0.0 API_PORT=8080 python run.py --mode api
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
- [x] Multi-session / user profiles — `core/profile_store.py` (SQLite, tenant-aware) + `core/session_manager.py`; chat path remains single-user
- [ ] Memory scoping per profile on the chat path (retriever `user_id` filter exists)
- [ ] Cloud sync (S3/Backblaze B2 periodic backup) — not started
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

**Names verified against `config/settings.py` + `.env` (Nov 8 2026).** The
`MAI_API_*` / `JWT_SECRET_KEY` names used in earlier revisions of this guide do
not exist in the codebase.

```bash
# API
API_HOST=0.0.0.0            # non-loopback forces auth on /api/*
API_PORT=8000
API_REQUIRE_AUTH=true       # force auth even on loopback
API_CORS_ORIGINS=<comma-separated origins>
API_TRUSTED_HOSTS=<comma-separated hosts>
API_RATE_LIMIT_PER_MINUTE=60
API_RATE_LIMIT_CHAT=60
API_RATE_LIMIT_AUTH=10
API_RATE_LIMIT_INGEST=30
API_RATE_LIMIT_HEALTH=300

# Auth (JWT secret auto-generated + persisted to data/jwt_secret if unset)
API_JWT_SECRET=<strong-random>
API_JWT_ACCESS_EXPIRE_MINUTES=15
API_JWT_REFRESH_EXPIRE_DAYS=7

# LLM
OPENROUTER_API_KEY=<key>
LLM_PROVIDER=openrouter            # or "ollama" for local-first ordering (Oct 2026)
OPENROUTER_DEFAULT_MODEL=openrouter/free   # sanitized failover list; default router (free, no 402)
LLM_MODEL=qwen2.5:3b-instruct-q4_k_m       # Ollama model name (only used when Ollama is reachable)
LLM_MAX_CONTEXT=4096
LLM_TIMEOUT=120

# Paths
ROOT_DIR=E:/Mai_ai
MAI_OBSIDIAN_VAULT=E:/MaiMemory   # env override read by config/paths.py

# Voice
STT_BACKEND=whisper         # or "kyutai" (opt-in; above the RTF gate)
KYUTAI_STT_DIR=<path to stt-1b-en_fr>   # only for kyutai
```

### Settings Files (config/)

All settings live as plain constants in `config/*.py`, re-exported through
`config/settings.py`. There is **no blanket `MAI_` env prefix** — each module
reads its own exact key (`API_HOST`, `LLM_PROVIDER`, `STT_BACKEND`, `ROOT_DIR`,
…). A few security/sandbox opt-ins are `MAI_`-prefixed by design:
`MAI_OBSIDIAN_VAULT`, `MAI_ALLOW_UNSIGNED_PLUGINS=1`, `MAI_SCRAPER_ALLOW_PRIVATE=1`,
`MAI_PLUGIN_ALLOW_EVAL=1`. Desktop autostart is a CLI flag, not an env var:
`python run_daemon.py --install-startup` / `--uninstall-startup`.

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
- Tracer PII-redacted traces in `logs/cognitive_audit/*.json`

---

## Backup Strategy

### What to Back Up

| Data | Location | Frequency |
|------|----------|-----------|
| Vector DB | `vector_memory/` (ChromaDB) | Daily |
| SQLite state | `memory/mai.db` | Daily |
| Knowledge graph | `OBSIDIAN_VAULT/graph/graph.json` | Daily |
| Profiles | `data/profiles/profiles.db` | Daily |
| Obsidian vault | `OBSIDIAN_VAULT/` (default `~/MaiMemory`, override `MAI_OBSIDIAN_VAULT`) | Hourly (incremental) |
| Experience / journal JSONL | `data/experiences.jsonl`, per-store JSONL | Daily |
| Logs | `logs/` | Daily (rotate) |

The embedding cache is **in-process LRU only** (model-fingerprinted) — nothing to back up.

### Cloud Sync (Not Started)

- No `sync/` package exists. The plan (S3/B2 periodic sync, last-writer-wins
  conflict resolution, ~300 s interval) is roadmap work only — see
  [[00-Overview/CURRENT_STATE]] §4.

---

## Rollback Procedure

1. Stop daemon/API: `docker compose down` or tray → Quit
2. Restore `data/`, `OBSIDIAN_VAULT/`, `logs/` from backup
3. Restore `config/settings.py` if changed
4. Restart: `docker compose up -d` or run daemon

---

## Wiki Links

**Related:** [[03-Features/Native OS Bridge Architecture]] — daemon build/install • [[01-Architecture/08-API Native & Surface]] — API surface • [[01-Architecture/10-Status & Debt]] — hardening status • [[04-Development/Testing Strategy]] — CI/CD