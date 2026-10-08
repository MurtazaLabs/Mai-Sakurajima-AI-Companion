# Disconnected Systems — Audit & Remediation Plan

**Date:** 2026-10-06
**Scope:** Full-repository scan of every Mai module for systems that exist on disk but are not connected to the running application — the same class of problem as the previously discovered Redis subsystem.
**Status of this document:** Audit + plan only. **No code was changed in this pass.** Phase 1 deletions are NOT executed. Phase 2 wiring is NOT started.

> **User decision (recorded):** The functional-but-unwired systems must be **wired to their respective places**, not deleted. Deletions are limited to the Phase 1 list below and require explicit approval before execution.

---

## 1. Methodology

- **AST import graph** over all Mai Python modules — **380 modules parsed** (excluding `mai_env/`, `.git/`, `__pycache__/`, `.obsidian/`, `api/static/`, `node_modules/`, `.pytest_cache/`, `data/`, `logs/`, `important/`, `.freebuff/`, `.opencode/`).
- Files parsed with `encoding="utf-8-sig"` (`plugins/calendar.py` carries a U+FEFF BOM).
- 7 parse failures = `tests/fix_*.py` scratch files (unterminated triple-quoted strings — debris, see Phase 1).
- **Live-set roots:** `run` (CLI entry) and `api/server` (module-level `app`, used by `run_daemon.py`). Anything reachable from these roots via imports = live.
- Two graph corrections applied after the first run (which produced false positives):
  1. Package `__init__.py` execution is modeled via `ancestors()` — the first run mis-resolved `core.model_lifecycle` to the wrong package.
  2. `.freebuff/` and `.opencode/` excluded — agent-harness skills, not Mai code.
- **Cross-verification sweep:** grep for class names (lazy/string imports), path strings (subprocess spawns), and `__main__` guards.
- Every classification below was **verified twice**.

**Result:** **248 live** modules · **6 test/tool-only** · **28 raw disconnected candidates** (refined below; several were false positives on re-verification — most notably `voice/speaker/*`, see §6).

---

## 2. Answer to the status question — "already deleted / not connected / useless / useful"

| Bucket | Verdict |
|---|---|
| `core/brain_facade.py` (853 L), `core/stateless_brain_worker.py` (700 L) | **Already deleted** in an earlier session (staged `git rm`). Both were *broken*, not merely unwired — see §3. |
| Coordinator trio + `core/tasks.py` + `voice/audio_utils.py` + `tests/fix_*.py` | **Still on disk. Not connected, and superseded/useless** — safe deletes, zero capability loss (Phase 1, §4). |
| Redis layer, Prometheus/OTel, SQL/Alembic, plugin CLI/marketplace, Discord, native watchdog/startup, small test-only modules | **Not connected, but useful and functional** — per user decision these will be **wired**, not deleted (Phase 2, §5). |
| `voice/speaker/*` (~460 L) | **Already wired — false positive.** No action needed. |

---

## 3. Already deleted (earlier sessions — for the record)

- **`core/brain_facade.py` (853 L, `git rm`)** — broken: `ImportError: cannot import name 'PromptContext' from 'core.memory_coordinator'` (line 810); imported nonexistent `core.brain_router`; duplicated live methods; garbage trailing import block. Zero inbound refs (only comments in `core/stateless_brain_worker.py`, `core/prompt_coordinator.py:359`, one doc line).
- **`core/stateless_brain_worker.py` (700 L, `git rm -f`)** — unconstructable: `_init_dependencies` reads `self.tool_coordinator` before `_init_coordinators` (runs later) assigns it → `AttributeError`; `think`/`think_stream`/`shutdown` all `pass`; `WorkerConfig` ×2; `_parse_redis_host`/`_parse_redis_port`/`_init_coordinators` ×2; 4 verbatim import blocks; `create_engine` imported after use.
- **`core/prompt_coordinator.py`** — comment repointed "set by BrainFacade" → "set by Brain" (unstaged edit).
- **`tests/test_horizontal_scaling.py`** — rewritten (unstaged): dropped dead `StatelessBrainWorker` import, removed latent `NameError` (undefined `create_session_manager()`), cross-instance tests now honestly skip-gated with `pytest.skip`. Now **1 passed, 2 skipped** (previously a misleading "3 passed" — Redis was never running and the fallbacks made the tests vacuous).

---

## 4. Phase 1 — Safe deletes (~1,500 L total, zero capability loss) — NOT executed

All items verified twice: zero inbound references from the live graph, no lazy/string imports, no subprocess path spawns, no `__main__` entry points.

| # | Item | Lines | Why dead |
|---|------|-------|----------|
| 1.1 | `core/prompt_coordinator.py` | 362 | Superseded by live `prompt/orchestrator` + `ResponsePipeline` |
| 1.2 | `core/tool_coordinator.py` | 208 | Superseded by live `agency/agent` tool loop |
| 1.3 | `core/agent_coordinator.py` | 259 | `_fallback_plan` duplicated nearly verbatim in live `agency/agent.py` |
| 1.4 | `core/tasks.py` (`TaskManager`) | 245 | Zero refs; superseded by live, wired `core/scheduler.py` |
| 1.5 | `voice/audio_utils.py` | 28 | 4 trivial numpy helpers, unused |
| 1.6 | `tests/fix_prometheus.py`, `fix_server.py`, `fix_server2-5.py`, `fix_server_final.py` | — | Unparseable scratch (unterminated triple-quoted strings); never collected by pytest |

---

## 5. Phase 2 — Functional but unwired → WIRE (approved direction)

### 2a. Redis layer (horizontal scaling) — **DONE (2026-10-07)**
- **Modules:** `core/event_bus_redis.py` (850 L), `core/state/redis_state.py` (384 L), `config/redis_config.py`
- **Implemented:** backend selector in `app/builders/infrastructure.py` — `_resolve_redis_client()` builds + pings a client from `MAI_REDIS_URL` (single shared client, 5s connect/read timeouts); reachable → `RedisEventBus` + `RedisSharedState`; unset/unreachable/malformed → historical in-process `EventBus` + file-backed `SharedState` (**default unchanged**). Live backend recorded on `app.event_bus_backend` / `app.shared_state_backend` (`"redis"` | `"in-process"`) and logged.
- **Interface parity added to `RedisSharedState`:** `lock` (public RLock alias), `state_dir`, and `db` (`EvidenceDB` SQLite evidence store) — required by `RelationshipEngineV2` (`state.lock`, `state.db.log_evidence/get_all_evidence`), `Brain`, and `OsKernel`.
- **Two latent bugs fixed in the blast radius:** (1) `core/state/db.py` used `logger` without defining it (`NameError` on any SQLite failure path); (2) `RedisSharedState.load_state_from_disk()` flipped `_available = False` on a corrupt/unparsable Redis *value*, permanently disabling Redis for the process — parse failures now log and fall back to the local file; connection loss is still detected in `_get_redis()`. The legacy `EvidenceDB = RedisSharedState` alias (shadowed the real import, zero importers) was removed.
- **Degradation behavior:** construct+ping failure at boot → WARNING logged with reason → in-process fallback (verified live against `redis://127.0.0.1:1`). Later connection loss inside Redis classes still degrades via their own cached-flag paths.
- **Verification:** `tests/test_redis_backend_selector.py` (9 tests — default path, unreachable/malformed/blank URL fallbacks, fake-client Redis wiring, dispatch, interface parity, RelationshipEngineV2 on RedisSharedState); `tests/test_horizontal_scaling.py` now uses `tmp_path` (no repo-root pollution) → 1 passed / 2 honest skips. End-to-end `infrastructure.build()` on a fresh `AIApplication`: default + fallback paths both verified. Regression sweep 314 passed; collect 1,847 / 0 errors.
- **Note:** `REDIS_HOST/PORT/DB` env vars (`config/redis_config.from_env`, `Settings.REDIS_CONFIG`) remain a separate, pre-existing config path; the builder gate is `MAI_REDIS_URL` only.
- **Not yet verified against a live Redis server** (none available in this environment) — cross-worker sharing remains covered only by the skip-gated tests.

### 2b. Prometheus + OpenTelemetry — **DONE (2026-10-07)**
- **Modules:** `core/observability/opentelemetry_tracing.py` (474 L), `core/observability/prometheus_metrics.py` (409 L), `core/observability/__init__.py` (91 L)
- Note: **two observability packages** — `observability/` (live: HealthRegistry, EventInspector) vs `core/observability/` (was dead).
- **Implemented — `/metrics`:** `@app.get("/metrics")` in `api/server.py` behind `_require_auth` (401 when `API_REQUIRE_AUTH=true`, anonymous pass-through in dev), returning the Prometheus text exposition format; refreshes CPU/memory gauges per scrape (psutil optional); degrades to stable 503 `metrics_unavailable` if `prometheus_client` is missing — the API always boots.
- **Implemented — middleware:** `PrometheusMiddleware` mounted via guarded `add_middleware` (`_prometheus_active` flag). Made **body-safe**: no longer consumes the request body inside `BaseHTTPMiddleware` (would break downstream POST parsing).
- **Dependencies:** `prometheus-client==0.20.0` + `psutil==5.9.6` added to `requirements.txt` and installed — `monitoring/prometheus.yml`, `scripts/smoke-tests.sh` and the Grafana dashboards all already expected this endpoint.
- **Three latent bugs fixed (the module was unimportable — that's why it was dead):** (1) `prometheus_metrics.py` imported nonexistent `core.mai_message.get_correlation_id` (both correlation imports unused — removed); (2) `core/observability/__init__.py` imported nonexistent `TraceAttributes` from the OTel module (stale name; removed from import + `__all__`); (3) `update_system_metrics()` pushed the raw cumulative CPU total into a Counter every scrape, inflating every `rate()` — now increments by delta with a baseline. Additionally the OTel module's 7 instrumentation imports + exporter/metrics imports are now guarded (`_optional_import`) — the `opentelemetry-instrumentation-*` extras are not installed and their absence no longer breaks import; `init_tracing()` works with the OTel core alone and `_auto_instrument()` skips missing packages.
- **Implemented — OTel gate:** `_maybe_init_otel()` in `api/server.py`, called **before** `FastAPI()` construction so global instrumentation hooks see the app. Strictly opt-in via `MAI_OTEL_ENABLED` (1/true/yes/on), default **OFF** — default boot unchanged. Optional `MAI_OTEL_ENDPOINT` (OTLP collector) and `MAI_OTEL_SAMPLE_RATE` (default 0.1, clamped 0–1). Failure to init logs a warning and continues.
- **Verification:** `tests/test_metrics_endpoint.py` (9 tests — route registered with `_require_auth` dependency, auth enforced 401 / anonymous pass-through, scrape with **actual recorded series** (`mai_http_requests_total{…}` — not just the `# TYPE` header), POST body intact through middleware, OTel default-off + opt-in truthy variants). Live double-scrape: 200, `text/plain; version=0.0.4`, `mai_http_requests_total{`, `mai_process_memory_bytes`, `mai_process_cpu_seconds_total` all present. Regression 84 passed; collect 1,856 / 0 errors.
- **Note:** `opentelemetry-instrumentation-*` extras (fastapi/httpx/redis/…) remain uninstalled — add them only when real tracing backends are deployed; everything degrades cleanly without them. Grafana dashboards + Prometheus scrape config are now live-compatible (scrape `localhost:8000/metrics`).

### 2c. SQL + Alembic — **DONE (2026-10-07)**
- **Modules:** `core/state/database.py` (174 L), `core/state/alembic/env.py` (73 L), `core/state/alembic/versions/001_initial.py` (108 L)
- **Implemented — `alembic.ini`** (repo root): `script_location = core/state/alembic`, logging config for `fileConfig`; plus the missing `script.py.mako` so future revisions can be autogenerated.
- **Implemented — env.py single source of truth:** `get_database_url()` now delegates to `core.state.database.get_database_url()` (POSTGRES_DSN → DATABASE_URL → `sqlite:///{MEMORY_DIR}/mai.db`) instead of its own hardcoded `sqlite:///./memory/mai.db` fallback — migrations and the runtime engine always target the same DB. `fileConfig(..., disable_existing_loggers=False)` so auto-migration at boot cannot silence Mai's loggers.
- **Implemented — builder wiring:** `_build_database()` in `app/builders/infrastructure.py` → `app.database` (lazy SQLAlchemy Engine — no connection until first use, so an unreachable PostgreSQL never crashes boot), `app.database_url` (credential-masked in logs), `app.database_migrations_applied`. `_maybe_run_migrations()` runs `alembic upgrade head` programmatically **only when `MAI_DB_AUTO_MIGRATE` is truthy (default OFF)**; script_location anchored to the repo root (forward slashes — backslashes break ConfigParser interpolation).
- **Two latent bugs fixed (the initial migration could never run):** `001_initial.py` declared `index=True` columns AND explicit `op.create_index` for the same auto-generated names (`ix_memory_nodes_user_id`, `ix_relationship_evidence_timestamp`) → `OperationalError: index already exists` on first `upgrade head`. Explicit duplicates removed with explanatory notes.
- **One consistency fix:** `database.get_database_url()` now reads config attributes dynamically (was import-time-bound), so tests/runtime overrides are visible to both env.py and the engine.
- **Verification:** `tests/test_sql_engine_wiring.py` (7 tests — ini/script-location integrity, `upgrade head` creates all 6 tables + `alembic_version`, `downgrade base` removes them, builder engine connects + `SELECT 1`, credential masking, auto-migrate default-off/opt-in). End-to-end `infrastructure.build()` on a fresh `AIApplication`: Engine wired, migrations off by default, URL from configured `MEMORY_DIR`. Regression 165 passed; collect 1,863 / 0 errors.
- **Untouched by design:** JSON storage stays (do NOT migrate); live `core/state/models.py` unchanged; live `model_lifecycle` keeps its own direct sqlite. Manual migration path: `alembic upgrade head` from the repo root.

### 2d. Plugin CLI + marketplace — **DONE (2026-10-07)**
- **Modules:** `plugins/cli.py` (373 L, `__main__` at L372), `plugins/marketplace_client.py` (399 L)
- Plugin system itself is **LIVE**: `core/plugin_system.py` imports `plugins.plugin_manifest` + sandbox; `api/routes_plugins.py` + `app/builders/runtime.py` import `plugins.lifecycle`; 6 manifest plugins (weather, calendar, news, system_monitor, web_scraper, example_plugin) are dynamically loaded from `plugins.json` — NOT dead.
- **Dedup executed:** the 5 flat copies (`plugins/{news,weather,system_monitor,web_scraper,example_plugin}.py`) were byte-identical (cmp + md5) shadows — `PluginLoader.load()` prefers a `<name>/manifest.json` dir and only falls back to flat files when no manifest dir exists. Flat copies deleted via staged `git rm`; canonical `<name>/` layout kept; policy documented in `plugins/README.md`.
- **8 phantom-enum bugs fixed** (`PluginState.ENABLED`/`INSTALLED` do not exist — the enum defines ACTIVATED/DISCOVERED): 4 in `lifecycle.py` (install dependency filters, update, get_enabled_plugins) and 4 in `routes_plugins.py` — these made the live `/api/plugins/installed` route crash with AttributeError.
- **Routes repaired:** duplicate `GET /installed` registration removed; per-request `bootstrap_system()` boots replaced with the app-wired manager (`runtime.py` now calls `set_lifecycle_manager(...)`; unset → clean 503, never a silent temp-dir manager); missing `os`/`Path` imports in the publish route added; auth (`api.auth.get_current_user` — same single source as `_require_auth`) added to all mutating routes.
- **Marketplace client wired:** `/marketplace/search` + `/marketplace/{name}` read `plugins/registry.json` via `file://` through the real client (built-in catalog as offline fallback); `POST /marketplace/install` is client-driven (download → SHA-256 → dependency resolution → extract → registry record). All 6 registry `package_url`s point at real local `.mpkg` files in `dist/plugins/`, so install works fully offline.
- **Two client/lifecycle bugs fixed:** (1) `fetch_registry` let a stale remote-fetch cache (`~/.cache/mai/marketplace/registry.json` with placeholder URLs/checksums) shadow an explicitly configured `file://` registry — file registries are now authoritative; (2) the lifecycle registry path collided with the marketplace catalog (`plugins/registry.json` parsed as installed-plugin records → `cli list` crash) — lifecycle registry now lives at `plugins/data/lifecycle_registry.json`.
- **CLI exposed:** `logging.basicConfig(INFO)` added to `main()` (the tool logged via logger and printed nothing — visibly broken), parent-flag ordering documented; `plugins/README.md` added (canonical layout, dedup policy, CLI cheatsheet, API table).
- **Verification:** `tests/test_plugin_marketplace.py` (17 tests — dedup assertions, loader manifest preference, enum fixes, registry-path separation, client file:// search, routes incl. **real API install end-to-end** + 401 auth + 503-without-manager + offline fallback, CLI subprocess). CLI verified live: `--help`, `list`, `search`, and a full `install example_plugin` into a temp dir (exit 0, package extracted). Regression 84 passed; collect 1,880 / 0 errors.
- **Pre-existing finding (flagged, not fixed):** the legacy `WeatherPlugin` wrapper at the tail of `plugins/weather/weather.py` has two `__init__` definitions (instantiation would recurse) — unreachable via the loader (it picks the first `Plugin` subclass) and byte-identical in the canonical copy; cleanup candidate for a later pass.

### 2e. Discord
- **Modules:** `integrations/discord_bot.py` (82 L), own `__main__`; no DISCORD token in `.env` or `config/settings.py`.
- **Plan:** add `DISCORD_BOT_TOKEN` to `config/settings.py`; manual-start only (optional entry point), never auto-boot.

### 2f. Native watchdog + startup
- **Modules:** `native/watchdog.py` (118 L) — subprocess watchdog; `app/orchestrator.py`'s watchdog is a separate in-process one (no path-string spawn refs to the native one). `native/startup.py` (84 L) — no docstring; the other 4 native modules are live.
- **Plan:** `run_daemon.py --watchdog` flag; login-autostart wired to the tray menu.

### 2g. Small test-only modules
| Module | Lines | Class/API | Wiring seam |
|---|-------|-----------|-------------|
| `observability/tracer.py` | 173 | `CognitiveAuditor` | EventInspector / health seam |
| `core/emotion_goals.py` | 86 | `EmotionGoalEngine` | post-think hook registration (same seam as PostThinkHooks) |
| `core/identity/profiles.py` | 99 | `get_profile` / `_default_profile` | identity bootstrapping |

- `knowledge/vault_janitor.py` (160 L) is test-only but served by `scripts/sweep_graph_junk.py` — intentional; leave as-is.

---

## 6. Corrected finding — `voice/speaker/*` already wired

An earlier draft listed `voice/speaker/*` (~460 L) as test-only. **That was a false positive** caused by a `grep -iv "speak"` filter that swallowed the wiring lines.

Verified: `app/builders/voice.py` constructs `SpeakerManager(profiles_dir=str(cfg.ROOT_DIR / cfg.SPEAKER_PROFILES_DIR))` with `health_registry` registration + graceful fallback to None. **No work needed.**

---

## 7. Constraints & guardrails

- `api/stream_manager.py` — user's uncommitted change; **do not touch**.
- `core/state/models.py` — LIVE; **never delete**.
- Redis / OTel default **OFF** — opt-in only; default boot behavior unchanged.
- `docs/Mai_documentation/.obsidian/workspace.json` — user's editor state; do not touch.
- No commits/pushes unless asked.
- Phase 1 deletions require explicit user approval before execution.

---

## 8. Verification baselines

- `python -m pytest --collect-only -q` → **1,880 collected, 0 errors** (re-verified post-2d; +17 new plugin/marketplace tests vs the 1,863 post-2c count).
- `python -m pytest tests/test_brain.py tests/test_llm.py tests/test_memory.py -q` → **184 passed** (exact match, re-verified post-Phase-1).
- `import core.brain`, `import app.builder`, `import api.server` (module-level `app` — `run_daemon` must use it) all OK (re-verified post-Phase-1).
- `tests/test_horizontal_scaling.py` → 1 passed, 2 skipped (post-repair).

---

## 9. Trackable checklist

### Phase 1 — safe deletes — **DONE (2026-10-07)**
- [x] 1.1 Delete `core/prompt_coordinator.py`
- [x] 1.2 Delete `core/tool_coordinator.py`
- [x] 1.3 Delete `core/agent_coordinator.py`
- [x] 1.4 Delete `core/tasks.py`
- [x] 1.5 Delete `voice/audio_utils.py`
- [x] 1.6 Delete `tests/fix_*.py` debris — 8 files: fix_prometheus, fix_server, fix_server2–5, fix_server_final, **plus `fix_signing.py`** (one-off byte-patcher for `plugins/signing.py`, missed in the audit listing; zero references, same debris class)
- [x] Re-run pytest collect + smoke imports after deletions — fresh inbound-ref sweep clean (only self-headers, this doc, and `important/full_codebase.txt` dump); 1,838 collected / 0 errors; 184 passed; smoke imports OK

**Execution note:** all 13 files deleted via staged `git rm` (`-f` for `prompt_coordinator.py`, superseding its earlier comment edit); ~1,560 L removed. Not committed.

### Phase 2 — wiring (approved direction)
- [x] 2a Redis backend selector in `app/builders/infrastructure.py` (opt-in via `MAI_REDIS_URL`) — **DONE (2026-10-07)**; parity additions + 2 latent bug fixes; 9 new tests; default/fallback paths verified end-to-end
- [x] 2b `/metrics` mount in `api/server.py` + optional OTel via `MAI_OTEL_ENABLED` — **DONE (2026-10-07)**; 3 unimportable-module bugs fixed; middleware body-safe; 9 new tests; live scrape verified
- [x] 2c `alembic.ini` + `app.database` engine in Infrastructure — **DONE (2026-10-07)**; 2 broken-migration bugs fixed; `MAI_DB_AUTO_MIGRATE` opt-in; 7 new tests; up/down migrations verified
- [x] 2d Plugin CLI/marketplace exposure + duplicate plugin-copy cleanup — **DONE (2026-10-07)**; 5 shadowed copies deleted; 8 phantom-enum + 2 registry bugs fixed; client-driven API install verified end-to-end; 17 new tests
- [ ] 2e `DISCORD_BOT_TOKEN` config + manual-start entry point
- [ ] 2f `run_daemon.py --watchdog` flag + tray-menu autostart
- [ ] 2g `tracer.py` → EventInspector seam · `emotion_goals.py` → post-think hook · `identity/profiles.py` → identity bootstrap
- [ ] Re-run pytest + boot smoke test after each wiring item
