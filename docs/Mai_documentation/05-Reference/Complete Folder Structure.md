# Complete Folder Structure

> Verified against the repository **2026-11-08** (`main` @ `2cd6181`).
> Excludes runtime/editor artifacts: `mai_env/`, `__pycache__/`, `.pytest_cache/`,
> `.mypy_cache/`, `.ruff_cache/`, `node_modules/`, `.git/`, log/data contents.
>
> Capability status: [[00-Overview/CURRENT_STATE]].

---

## Python Inventory (measured Nov 8 2026)

| Package | .py files | Lines |
|---------|-----------|-------|
| `core/` | 66 | 16,030 |
| `api/` | 24 | 4,952 |
| `memory/` | 28 | 7,378 |
| `knowledge/` | 29 | 5,853 |
| `voice/` | 33 | 4,665 |
| `plugins/` | 14 | 3,851 |
| `agency/` | 12 | 2,540 |
| `app/` | 18 | 2,329 |
| `llm/` | 4 | 1,489 |
| `config/` | 21 | 1,303 |
| `execution/` | 4 | 987 |
| `scripts/` | 8 | 997 |
| `reasoning/` | 5 | 895 |
| `evaluation/` | 5 | 768 |
| `observability/` | 3 | 796 |
| `native/` | 7 | 610 |
| `prompt/` | 7 | 350 |
| `profiling/` | 4 | 108 |
| `integrations/` | 1 | 82 |
| root (`run.py`, `run_daemon.py`) | 2 | 383 |
| **Source subtotal** | **295** | **56,366** |
| `tests/` | 88 | 23,658 |
| **Total** | **383** | **80,024** |

**Tests:** 88 py files, 77 `test_*.py` modules, 2,035 tests collected
(2,033 passing + 2 skipped).

---

## Top Level

```text
E:/Mai_ai
├── run.py                      # CLI / api / daemon entry point
├── run_daemon.py               # desktop app entry (tray + pywebview + hotkeys)
├── agency/                     # tools, agent, goals, dreaming, world model
├── api/                        # FastAPI server, routes, static UI, web/ (entity skeleton)
├── app/                        # ApplicationBuilder, boot phases, validation
├── cache/                      # runtime cache (embedding cache, temp artifacts)
├── config/                     # per-subsystem env-backed settings modules
├── core/                       # Brain, OS kernel, event fabric, emotion, identity
├── data/                       # durable state (profiles, graph, traces, jwt_secret)
├── dist/                       # build output (PyInstaller artifacts)
├── docs/                       # Obsidian vault + evaluation + architecture notes
├── evaluation/                 # M9 transcript / rubric / scenario harness
├── execution/                  # task executor, sandbox, OS/desktop/clipboard/FS actions
├── important/                  # pinned requirements, source snapshots
├── integrations/               # discord_bot.py relay prototype (ex-gateways)
├── knowledge/                  # graphs, beliefs, retriever, vault writers, chunker
├── kyutai STT/                 # local Kyutai 1B weights (never committed)
├── llm/                        # LLMManager + OpenRouter/Ollama providers
├── logs/                       # application logs
├── memory/                     # pipeline, vector store, experience, preferences
├── models/                     # local model assets (embeddings)
├── monitoring/                 # Grafana/Prometheus assets
├── native/                     # tray, hotkeys, notifier, startup, watchdog, window
├── observability/              # health registry, event inspector, tracer
├── plugins/                    # 6 bundled plugins + platform (manifest/lifecycle/signing/…)
├── profiling/                  # dev-only profiling scripts (never imported at runtime)
├── prompt/                     # character / emotion / context / agent prompts
├── reasoning/                  # engine, journal, reflection, learning, ThoughtPacket
├── scripts/                    # install/bench/backfill/sweep/migration tooling
├── temp/                       # scratch space
├── tests/                      # pytest suite + behavior/ harness
├── vector_memory/              # ChromaDB persistence directory
├── voice/                      # wake, VAD, STT, TTS, player, interruption, speaker ID
├── Dockerfile / docker-compose.yml
├── requirements.txt / requirements-docker.txt / requirements-ci.txt
├── pyproject.toml / pytest.ini / alembic.ini
└── AGENTS.md                   # developer/session log (live source of truth for history)
```

---

## Key Sub-areas

### `api/`

```text
api/
├── server.py                 # MaiAPI facade, middleware, app factory
├── auth.py · certs.py · errors.py
├── static_serving.py
├── stream_manager.py         # SSE
├── ws_bridge.py              # WebSocket
├── middleware/rate_limiter.py
├── routes_*.py               # 14 route families (chat, memory, knowledge, voice,
│                             #   system, profile, agency, reasoning, tasks, dashboard,
│                             #   inspector, auth, permissions, plugins)
├── static/                   # 15 HTML pages · 45 JS · 17 CSS · manifest.json · sw.js
└── web/                      # v4.0 entity interface skeleton
    ├── README.md
    └── state/visual-state-adapter.js
```

Static folders follow the project rule: `assets/` (icons only, maintainer-owned),
`css/`, `img/`, `js/`, `os/`, HTML at root.

### `core/`

```text
core/
├── brain.py                  # cognition facade
├── os_kernel.py              # conversation FSM / mission control
├── event_bus.py · event_specs.py · event_registry.py · mai_message.py
├── emotion.py · attention.py · needs_engine.py · scheduler.py
├── application.py            # DI container (see app/ for builders)
├── prompt_builder.py · prompt_orchestrator.py   # compat wrappers
├── plugin_system.py · plugin_marketplace.py
├── profile_store.py · session_manager.py · event_bus_redis.py
├── identity/                 # canonical.py + character/ volumes I–IV
└── state/ · memory_coordinator.py · response_pipeline.py · utils.py · …
```

### `voice/`

```text
voice/
├── voice_manager.py          # state machine, mic callback, listening, speaking
├── vad.py · recorder.py · microphone.py · audio_buffer.py · utterance_segmenter.py
├── stt.py (faster-whisper) · stt_kyutai.py (opt-in)
├── kokoro_tts.py · stream_player.py · realtime.py
├── interrupt.py · wake_detector.py · wake_word.py
├── speaker_identifier.py · speaker/ (manager, encoder, database, profile)
├── emotion_detector.py · diarization.py · prosody.py · speech_style.py · renderer.py
├── full_aec.py (pass-through until fed) · noise_filter.py · adaptive_noise_filter.py
└── events.py · voice_config.py · voice_event.py · voice_state.py · metrics.py
```

### `plugins/`

```text
plugins/
├── cli.py · plugin_manifest.py · lifecycle.py · dependency_resolver.py
├── marketplace_client.py · signing.py · sandbox.py
├── weather/ · news/ · calendar/ · system_monitor/ · web_scraper/ · example_plugin/
```

### `tests/`

```text
tests/
├── conftest.py
├── test_*.py                 # 77 modules
├── behavior/                 # M7 harness (ScenarioDriver, fixtures, parity, conflict)
└── evaluation/               # M9 helpers
```

### `docs/Mai_documentation/`

Obsidian vault with 43 Markdown notes:

```text
00-Overview/       CURRENT_STATE · Project Charter · README
01-Architecture/   01–10 subsystem digests · ADR Presentation Layer Restructure ·
                   Bug_Audit_Report_2026-10-19 · Bug_Summary_and_Fix_Plan_2026-09-21 ·
                   Disconnected_Systems_Audit_and_Remediation_Plan_2026-10-06
02-Subsystems/     Memory Pipeline · Voice Pipeline · Event System · Identity & Canon ·
                   Knowledge Graph · Tool System · Vault Compilation
03-Features/       future-vision-roadmap · Native OS Bridge · Event Fabric · Discord Plan ·
                   MAI Cognitive Entity Interface Plan · Complete Redesign (superseded) ·
                   Character Rename PRD · stt-kyutai-replacement-plan
04-Development/    Testing Strategy · Deployment Guide
05-Reference/      Complete Folder Structure · MERGED_COMPLETE Reference
06-Operations/     README (index) · Monitoring-Alerting · Backup-Disaster-Recovery ·
                   Deployment · Troubleshooting · Maintenance · Incident-Response
```

`05-Reference/Character Prompt Reference` was deleted during consolidation; the
character canon now lives in code at `core/identity/character/volume-01..04.md`.

---

## Wiki Links

**Related:** [[00-Overview/CURRENT_STATE]] — authoritative capabilities •
[[01-Architecture/01-System Overview]] — architecture digest •
[[00-Overview/Project Charter]] — engineering rules
