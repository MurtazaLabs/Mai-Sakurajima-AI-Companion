# Deployment

> Production deployment options: Docker, native Windows daemon installer, configuration.

---

## Deployment Options

### 1. Docker (Recommended for Server/Cloud)

**Files**: `Dockerfile`, `docker-compose.yml`, `requirements-docker.txt`

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

**Volumes (persisted):**
- `./data:/app/data` — memory, graph, profiles
- `./cache:/app/cache` — embedding cache
- `./logs:/app/logs` — application logs
- `./knowledge_docs:/app/knowledge_docs` — KB source files

**Ports:** `8000:8000` (FastAPI)

**Restart policy:** `unless-stopped`

**Base image:** `python:3.10-slim`

---

### 2. Native Windows Daemon (Desktop)

**Entry point:** `run_daemon.py` (or `python run.py --mode daemon`)

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
iscc scripts/installer.iss
```

**Output:** `dist/mai-daemon.exe` + `Output/Mai AI Setup.exe`

**Installed location:** `%LOCALAPPDATA%\Mai AI\`

**Auto-start:** Registered via `StartupManager` on first run (user consent)

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
LLM_DEFAULT_PROVIDER=openrouter

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

### Settings Files (`config/`)

All settings in `config/settings.py` with per-module configs in `config/*.py`. Override via env vars (prefix `MAI_`).

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
- [x] JWT auth infrastructure (`auth.py`, `get_current_user`)
- [x] Health registry with fail-safe telemetry

### 🟡 In Progress / Partial
- [ ] HTTPS certificates (auto-gen via `cryptography`/`trustme` for dev; Let's Encrypt for prod)
- [ ] JWT auth enforced on all routes (currently optional)
- [ ] Multi-session / user profiles (memory scoping, profile CRUD)
- [ ] Cloud sync (S3/Backblaze B2 periodic backup)
- [ ] Structured logging pipeline (JSON, Loki/ELK compatible)
- [ ] Metrics endpoint (`/metrics` for Prometheus)

### ❌ Not Started
- [ ] Alerting (PagerDuty, email, Discord webhook)
- [ ] Backup/DR strategy (vault, vector DB, profiles)
- [ ] Load testing (locust/k6)
- [ ] Chaos engineering (latency injection, failure injection)

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

## Rollout Strategy

1. **Canary** — Deploy to staging, run integration tests
2. **Blue/Green** — Swap traffic after health checks pass
3. **Rollback** — Immediate if health checks fail

---

*Last updated: 2026-09-03*