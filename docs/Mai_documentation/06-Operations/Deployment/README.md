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

# REST API only (no kernel FSM, no mic)
python run.py --mode api

# With custom bind (verified Nov 2026)
API_HOST=0.0.0.0 API_PORT=8080 python run.py --mode api
```

---

## Configuration for Production

### Environment Variables

**Names verified against `config/settings.py` + `.env` (Nov 8 2026).** The
`MAI_API_*` / `JWT_SECRET_KEY` names used in earlier revisions do not exist.

```bash
# API
API_HOST=0.0.0.0
API_PORT=8000
API_REQUIRE_AUTH=true
API_CORS_ORIGINS=<comma-separated origins>
API_TRUSTED_HOSTS=<comma-separated hosts>
API_RATE_LIMIT_PER_MINUTE=60

# Auth (JWT secret auto-generated + persisted to data/jwt_secret if unset)
API_JWT_SECRET=<strong-random>
API_JWT_ACCESS_EXPIRE_MINUTES=15
API_JWT_REFRESH_EXPIRE_DAYS=7

# LLM
OPENROUTER_API_KEY=<key>
LLM_PROVIDER=openrouter              # or "ollama" for local-first; failover chain preserved
OPENROUTER_DEFAULT_MODEL=openrouter/free
LLM_MODEL=qwen2.5:3b-instruct-q4_k_m

# Paths
ROOT_DIR=E:/Mai_ai
MAI_OBSIDIAN_VAULT=E:/MaiMemory   # env override read by config/paths.py

# Voice
STT_BACKEND=whisper          # or "kyutai" (opt-in, above the RTF gate)
KYUTAI_STT_DIR=<path to stt-1b-en_fr>
```

Desktop autostart is a CLI flag, not an env var:
`python run_daemon.py --install-startup` / `--uninstall-startup`.

### Settings Files (`config/`)

All settings are plain constants in `config/*.py`, re-exported through
`config/settings.py`. There is **no `MAI_` env prefix** — each module reads its
exact key (`API_HOST`, `LLM_PROVIDER`, `STT_BACKEND`, `ROOT_DIR`, …).

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
- [x] JWT auth (`auth.py` — login/refresh/register, static token, OIDC/SAML scaffolding; auto secret persisted to `data/jwt_secret`)
- [x] Auth enforced on every `/api/*` route when `API_REQUIRE_AUTH=true` **or** the bind host is not loopback (`api_auth_middleware`)
- [x] HTTPS dev certificates auto-generated (`api/certs.py`); Let's Encrypt still manual for public deployments
- [x] Prometheus `/metrics` exporter (auth-gated in production)
- [x] Health registry with fail-safe telemetry
- [x] Security headers + trusted hosts middleware

### 🟡 In Progress / Partial
- [ ] Let's Encrypt automation for public deployments (dev HTTPS is done)
- [ ] Multi-session / user profiles — `ProfileStore` (SQLite, tenant-aware) + `SessionManager` exist; memory scoping per profile on the chat path is not wired
- [ ] Cloud sync (S3/Backblaze B2) — not started
- [ ] Log shipping pipeline (Loki/ELK compatible) — JSON logs exist, no shipper

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
| Vector DB | `vector_memory/` (ChromaDB) | Daily |
| SQLite state | `memory/mai.db` | Daily |
| Knowledge graph | `OBSIDIAN_VAULT/graph/graph.json` (exported into the vault) | Daily |
| Profiles | `data/profiles/profiles.db` | Daily |
| Obsidian vault | `OBSIDIAN_VAULT/` (default `~/MaiMemory`, override `MAI_OBSIDIAN_VAULT`) | Hourly (incremental) |
| Experience / journal JSONL | `data/experiences.jsonl`, per-store JSONL | Daily |
| Logs | `logs/` | Daily (rotate) |

The embedding cache is **in-process LRU only** — nothing to back up (`cache/` holds temp artifacts, not model outputs).

### Cloud Sync (Not Started)

- No `sync/` package exists. S3/B2 periodic sync, last-writer-wins conflict
  resolution and a configurable interval are roadmap items only.

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