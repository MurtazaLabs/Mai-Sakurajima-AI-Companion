---
document_type: reference
project: Mai AI
title: Current State — verified implementation reference
status: living
version: 1.0.0
last_updated: 2026-11-08
tags:
  - mai-ai
  - status
  - reference
related:
  - "[[Project Charter]]"
  - "[[01-Architecture/01-System Overview]]"
  - "[[01-Architecture/10-Status & Debt]]"
  - "[[03-Features/future-vision-roadmap]]"
---

# CURRENT_STATE — Mai AI

> **Single source of truth for what Mai AI actually is and can do today.**
> Every other document in this vault must agree with this page. When code and
> docs disagree, the code wins and this page is corrected.
>
> Verified against the codebase **2026-11-08** (`main` @ `2cd6181`).
> Status vocabulary: **Implemented** = shipped and wired · **Partial** = exists
> but incomplete or not wired into the live path · **Planned** = designed, not
> built · **Removed** = deleted from the codebase.

---

## 1. Project Identity

Mai AI is a **long-term, single-user personal AI companion** inspired by Mai
Sakurajima, built as a modular Python platform rather than a chatbot. The
ambition is a companion with persistent memory, emotional continuity, a stable
character, voice conversation, and growing autonomy over a multi-year timeline.

- **What she is today:** a local-first Windows desktop assistant with a real
  voice loop, persistent memory, an Obsidian-readable memory vault, a character
  and relationship layer, an agent/tool layer, a REST/SSE/WebSocket API, a rich
  web UI, and a plugin system.
- **What she is not (yet):** not multi-device, not a cloud service, not on
  Discord/WhatsApp, not self-modifying, not a 3D avatar, not an original-voice
  character (Kokoro neural TTS today).
- **Design stance:** local-first brain, explicit user control, honest failures
  over simulated success, documentation synchronized with implementation.

---

## 2. Current Architecture

**Verified inventory:** 384 Python files / 80,260 lines; excluding `tests/`,
295 files / 56,366 lines. 19 packages + 2 entry points (`run.py`,
`run_daemon.py`). 103 API route decorator sites. 72 catalog event topics
(50 `data.*` + 22 `state.*`).

### Boot chain

```
run.py  |  run_daemon.py  |  uvicorn api.server:app
        └── MaiAPI.bootstrap() ──► ApplicationBuilder.build() (8 phases)
              Infrastructure → Cognition → Memory → Knowledge → Reasoning
              → Agency → Voice → Runtime
```

`app/boot.py` owns phase order; `app/builders/*` each build one cluster;
`AIApplication` owns every subsystem and its lifecycle (`validate()`,
`start()`, `shutdown()`).

### Subsystem map (what actually exists)

| Package | Files / lines | Role today |
|---------|---------------|------------|
| `core/` | 66 / 16,030 | Brain facade, OS kernel FSM, event fabric, emotion, identity canon, attention, scheduler, plugins hooks |
| `memory/` | 28 / 7,378 | Unified pipeline, vector store, embedding cache, experience store, preference evolution |
| `knowledge/` | 29 / 5,853 | Entity graph (3 layers), beliefs, retriever, vault writers, chunker, watcher, janitor |
| `voice/` | 33 / 4,665 | Wake, VAD, recorder, STT (whisper/kyutai), TTS, streaming player, interruption, speaker ID, diarization |
| `api/` | 24 / 4,952 | FastAPI server, 14 route families (11 mixins + auth/profile/plugins routers), SSE, WebSocket, auth, metrics, static UI |
| `agency/` | 12 / 2,540 | Tool registry, agent loop, goals, procedural memory, world model, dreaming, personality evolution |
| `app/` | 18 / 2,329 | Builders, validation, orchestrator/watchdog, config loading |
| `config/` | 21 / 1,303 | Env-backed settings modules (no config objects, plain constants) |
| `llm/` | 4 / 1,489 | Manager + OpenRouter provider + Ollama provider + shared HTTP client |
| `execution/` | 4 / 987 | Task executor, sandboxed executor, OS/desktop/clipboard/filesystem handlers |
| `reasoning/` | 5 / 895 | Reasoning engine, thought journal (JSONL), reflection, learning |
| `native/` | 7 / 610 | Tray, hotkeys, notifier, startup, watchdog, pywebview window |
| `plugins/` | 14 / 3,851 | 6 bundled plugins + manifest, lifecycle, signing, sandbox, dependency resolver, marketplace client, CLI |
| `observability/` | 3 / 796 | Health registry, tracer, dashboard |
| `prompt/` | 7 / 350 | Character, emotion, context, agent prompt modules + builder |
| `evaluation/` | 5 / 768 | M9 transcript/rubric/scenario harness |
| `scripts/` | 8 / 997 | Benchmarks, installers, backfills, junk sweep, migrations |
| `integrations/` | 1 / 82 | Discord relay prototype only |
| `profiling/` | 4 / 108 | Dev-only profiling scripts (not imported by runtime) |
| `tests/` | 89 / 23,894 | 78 test modules, 2,047 tests collected |

### Data and state

- **Chat path:** `Brain.think()` / `think_stream()` → parallel retrieval
  (vector + beliefs + graph + attention) → prompt assembly (character +
  emotion + context + identity overlay + experiences) → LLM → response
  pipeline → post-think hooks (relationship deltas, reflection, beliefs, goals,
  procedural memory, learning).
- **Memory:** `MemoryPipeline.store()` is the single write entry →
  `MemoryIntelligence.process()` → `WriteJournal` batch or synchronous write →
  vector store + graph + vault raw record.
- **Events:** every cross-subsystem message is a `MaiMessage` envelope on the
  `EventBus`; the UI subscribes only to `state.*` projections.
- **Persistence:** ChromaDB vector index in `vector_memory/` (JSON/SQLite
  fallback), SQLite state in `memory/mai.db`, profiles in
  `data/profiles/profiles.db`, Obsidian vault (`~/MaiMemory`, override
  `MAI_OBSIDIAN_VAULT`) as human-readable memory, JSONL experience/journal
  files, and `logs/cognitive_audit/*.json` traces.

---

## 3. Implemented Capabilities (verified wired)

### Conversation & reasoning
- Multi-turn chat with character-consistent voice, emotion-aware prompting.
- Streaming replies (`LLM_STREAM=True`), envelope/ThoughtPacket parsing, leak
  guard, empty-reply bounded retry, stream guard for structured output.
- Reasoning engine + thought journal (append-only JSONL) + reflection cadence.
- Opinionated pausing: `is_phatic()` skips retrieval for small talk.

### Character & relationship (M0–M13)
- Canon volumes I–IV (`core/identity/character/`), drift-checked against code.
- `IdentityCore` projects identity/preferences/conflict policy read-only.
- Needs engine, emotion engine (valence/arousal + 16 handler paths), speech
  style planner, prosody planner, renderer abstraction.
- `RelationshipEngineV2` (LLM deep eval, voice path) **plus** deterministic
  lexicon deltas on every chat turn (trust/comfort/respect/affection/
  familiarity, clamped, persisted).
- Preference evolution from evidence windows (N≥3, weekly cadence) projected
  into prompts via overlay; canon never mutated.
- Experience layer: charged turns → `EmotionExperience` → dreaming reflects →
  relevance-gated recall into prompts.

### Voice
- Wake word by **STT phrase matching** (`WakeDetector`, phonetic tolerance).
- 16 kHz capture, pre-roll buffer, VAD onset/offset, trailing-silence trim,
  whole-utterance Silero gate before STT (mean ≥ 0.15, ratio ≥ 0.10, voiced
  ≥ 0.20 s; fail-open if VAD unavailable).
- STT backends: `FasterWhisperSTT` (default) and `KyutaiSTT` (opt-in via
  `STT_BACKEND=kyutai`, permanent whisper fallback on any failure).
- Kokoro TTS with emotion-conditioned text, `StreamPlayer`, sentence-level
  streaming from `brain.think_stream()`.
- Barge-in via `InterruptManager` (mic RMS over threshold during playback).
- Speaker identification (SpeechBrain + torch.amp compat shim) and diarization
  (dominant-speaker labelling; never slices the clip).
- Self-hearing fix: recorder is muted while `_speaking`, queue drained at
  listen entry, greeting playback marks speaking.
- `VoiceManager.toggle()` start/stop flip; `FullAEC` fed from the real playback
  stream (see §4 — wired, not yet used for continuous capture).

### Memory & knowledge
- Unified memory pipeline, importance scoring, decay/consolidation cycle,
  reinforcement counting, cross-day dedup in the vault writer.
- Vector search with MMR-style diversification, metadata filters, periodic
  prune, cap enforcement.
- Embedding cache keyed by SHA-256 model fingerprint + LRU (model changes
  invalidate cleanly).
- `AdvancedRetriever` queries 4 sources concurrently with early exit;
  `user_id` filter supported end-to-end.
- Knowledge graph: `KnowledgeGraph` (entities/relations), `BrainGraph` facade
  (11 typed node types bridging all stores), `CognitiveGraph` beliefs.
- Belief engine with versioned updates; attention system with RLock.
- Document KB: semantic chunking (embedding cosine boundaries, 64-token
  overlap), `DocumentStore`, `Indexer`, directory watcher.
- Obsidian vault: single-writer ownership (raw writes redirect to
  `conversation/`), GraphExporter/StateDumper/MemoryWriter split, junk-entity
  gate + `VaultJanitor` sweep, resolvable-link filtering.

### Agency & tools
- `ToolRegistry` (RLock) with 16 built-in tools; character whitelist and
  destructive-hotkey filter on execution.
- `Agent` multi-step loop with `_plan_next()`, one synthesis pass for analysis
  tasks, and honest failure when all steps fail.
- Goal manager (subtasks, progress, auto-advance, priority-aware pause,
  completion reflection), procedural memory, world model (11 categories),
  dreaming engine (5 levels incl. experience reflection), personality evolution.
- Natural-language OS actions: `open_app` with resolved Windows paths, URLs,
  typing, commands, clipboard, sandboxed filesystem, task scheduling.

### API & interfaces
- FastAPI app with 14 route families — 11 mixins on `MaiAPI` + 3 standalone routers (auth, profile, plugins) — ~103 endpoint decorator sites: chat,
  memory, knowledge, voice, system, agency, reasoning, tasks, dashboard,
  inspector, plugins, profile, auth/permissions.
- Auth: JWT (access+refresh), static token, OIDC, SAML scaffolding; auto JWT
  secret persisted to `data/jwt_secret`; middleware enforces auth on every
  `/api/*` route when required (env flag or non-loopback bind).
- Rate limiting (per-bucket, bounded LRU), CORS, trusted hosts, security
  headers, HTTPS dev certs (`api/certs.py`).
- SSE event stream + WebSocket bridge with thread-safe loop handoff and
  reconnect backoff.
- Prometheus `/metrics` endpoint (auth-gated in production; 503 when metrics
  unavailable).
- Web UI: 15 HTML pages, 45 JS modules, 17 CSS files, PWA manifest + service
  worker, offline overlay, command palette, accessibility layer.
- Desktop app (M14): pywebview window, close-to-tray, tray menu, global
  hotkeys, launch-at-login, watchdog, single-instance focus.

### Platform
- Desktop shortcut installer with interpreter dependency probe
  (`scripts/install_app.py`).
- Docker single-replica deployment (CPU torch, no mic), GitHub Actions CI
  (tests, lint, security scan, GHCR publish).
- Plugin platform: manifest, lifecycle states, dependency resolver, Ed25519
  signing (signature required by default), sandboxed execution, marketplace
  client + 11 marketplace endpoints, CLI.
- Configuration: `.env`-driven constants re-exported through
  `config/settings.py`; hot-reload safe keys exposed to the UI.
- Observability: health registry (heartbeat-count-aware stall detection),
  tracer with PII redaction, dashboard, event inspector, structured logs.

---

## 4. Incomplete Capabilities (partial, or present but not wired)

| Capability | State | Evidence |
|------------|-------|----------|
| **AEC (echo cancellation)** | **Wired — recorder still muted** | `StreamPlayer` streams playback through an `OutputStream` and feeds each block to `FullAEC` (`VoiceManager.attach_playback_tap()`, wired in `app/builders/voice.py`); `end_playback()` clears the reference between clips. Verified 18 dB on a synthetic two-path room; `FULL_AEC_DOUBLE_TALK_THRESHOLD` corrected 0.3 → 1.0. Not yet used to keep the mic live during playback — that needs live validation. |
| **Kyutai STT** | **Partial — opt-in** | Runs (RTF 1.17–2.97 on the 4 GB T1000), above the 0.7 promotion gate. `.env` on this machine sets `STT_BACKEND=kyutai`; config default stays `whisper`. |
| **openWakeWord** | **Installed, not wired** | `openwakeword==0.6.0` in `requirements.txt`; no import under `voice/`. No pretrained “hey mai” model exists — needs a custom verifier or synthetic training. |
| **Discord** | **Prototype** | `integrations/discord_bot.py` (82 lines) relays to `POST /api/chat`; `discord` package not installed; no `ChannelAdapter`, no voice, not M24. |
| **WhatsApp** | **Not started** | Official Meta Agent Platform only (no unofficial client). M26. |
| **Entity web interface (v4.0)** | **Skeleton** | `api/web/` holds only `state/visual-state-adapter.js` + README; entity/, workspaces/, design/, vendor/ planned. Current UI is the `api/static/` pages. |
| **Java/JavaFX client** | **Not started** | No JDK, no `ui/` module. pywebview is the desktop shell. |
| **Cloud sync** | **Not started** | No `sync/` package, no S3/B2 code. |
| **Project/commitment memory (T8)** | **Not started** | `GoalManager` has no checkpoints; no ProjectStore anywhere. |
| **Context budgeting** | **Partial** | No token-budget/compaction layer; short-term context is truncated by turn count (`memory_coordinator` keeps the last 20 turns). |
| **Multi-user memory scoping** | **Partial** | `user_id` filter plumbed through the retriever + `ProfileStore` (SQLite, tenant-aware) + `SessionManager`; the chat path itself is single-user in practice. |
| **Plugin marketplace** | **Partial** | Full client + routes + signing exist; installs require a configured trusted key (`MAI_ALLOW_UNSIGNED_PLUGINS=1` for dev). No public registry is operated. |
| **Frozen desktop build** | **Partial** | PyInstaller script exists but the exe still needs the repo runtime (venv, models, `.env`); the shortcut path is the supported launch. |
| **Voice in Docker** | **Blocked by design** | Single replica because one process must own the mic; container ships without voice devices. |
| **Redis event bus** | **Available, unused** | `core/event_bus_redis.py` + config exist; default deployment is in-memory. |

---

## 5. Technical Stack

| Layer | Technology |
|-------|-----------|
| Language / runtime | Python 3.10.11 inside `mai_env/` (base Python lacks the voice stack) |
| Web/API | FastAPI + Starlette, uvicorn, SSE, WebSocket |
| LLM | OpenRouter (cloud, default `openrouter/free`) with Ollama failover; `LLM_PROVIDER` selects preference; **no local model installed on this machine** |
| STT | faster-whisper (default) / Kyutai 1B via transformers (opt-in) |
| TTS | Kokoro (`kokoro`, `misaki`) with emotion-conditioned text |
| VAD / audio | Silero VAD (SHA-256-verified download), sounddevice, soundfile |
| Speaker | SpeechBrain embeddings + torch.amp compatibility shim |
| ML runtime | torch 2.3.0+cu121, torchvision 0.18.0+cu121, numpy 1.26.4 (pinned), transformers 4.57.6 |
| Vector store | ChromaDB (optional) + SQLite + JSON fallback |
| Embeddings | Sentence-Transformers (all-MiniLM-L6-v2, local) |
| Memory vault | Obsidian-compatible Markdown (`~/MaiMemory` by default, override `MAI_OBSIDIAN_VAULT`) |
| Desktop | pywebview 6.x (Edge WebView2), pystray, Pillow, keyboard, pyperclip, plyer, pywin32 |
| Frontend | Vanilla ES modules + CSS (no framework, no bundler), Three.js only for the graph view |
| Deployment | Docker (CPU torch, single replica), GitHub Actions CI, Inno/PyInstaller scripts |
| Testing | pytest (78 modules, 2,047 tests), M7 behavior harness, M9 evaluation harness |

**Hardware envelope:** 4 GB VRAM (Quadro T1000) — constrains local LLM and
Kyutai throughput; no Triton on Windows, so `torch.compile` is disabled for
Kyutai.

---

## 6. Current Development Stage

| Area | Stage |
|------|-------|
| Core conversation, memory, character, voice, API, desktop | **Production-shaped and in daily use** |
| Character/behavior milestones M0–M13 | **Complete and validated** |
| Desktop app (M14) | **Shipped** (pywebview shell) |
| Roadmap M15–M26 | **Not started** (scheduler + TTS bake-off, projects/continuity, Discord, WhatsApp, Java client) |
| Documentation | **Being synchronized to code as of 2026-11-08** (this page is the anchor) |

Latest commits: `2cd6181 deployment passed` and `37584f5 new update`
(2026-11-05). Working tree is clean apart from documentation edits.

---

## 7. Known Issues

1. **Echo cancellation is fed but not yet exploited.** `StreamPlayer` now routes
   the real playback stream into `FullAEC` (verified: 18 dB echo cancellation on
   a synthetic room) and `FULL_AEC_DOUBLE_TALK_THRESHOLD` was fixed from 0.3 to
   1.0 — at 0.3 the detector latched into permanent double-talk and the filter
   never adapted. The recorder is still muted while she speaks, so continuous
   capture during playback (barge-in without losing the first syllable) is a
   one-line change that needs live hardware validation.
2. **Wake word is a transcription check, not a wake model.** Every wake attempt
   costs an STT pass (measured ~1.7 s floor on this GPU); openWakeWord would cut
   that but has no “hey mai” model.
3. **STT latency is the conversation bottleneck.** Kyutai RTF 1.17–2.97 exceeds
   the 0.7 gate; whisper is comparable or better on short clips. True streaming
   STT needs RTF < 1 and is hardware-blocked.
4. **Cloud LLM dependency.** No Ollama/model installed; if OpenRouter is
   unavailable, generation fails over to a dead local endpoint.
5. **No context-token budget.** Long sessions rely on turn-count truncation;
   no summarization/compaction of the prompt window.
6. **Three-layer graph overlap** (`KnowledgeGraph` / `BrainGraph` /
   `CognitiveGraph`) — belief writes must be kept consistent by convention.
7. **`memory/` → `knowledge/` layer breach** — three lazy imports inside
   memory modules.
8. **Vault junk is swept manually** (`scripts/sweep_graph_junk.py`, dry-run by
   default); the live gate prevents new junk but does not clean history.
9. **Docker cannot do voice** and must stay single-replica (mic ownership +
   single Chroma writer).
10. **Frozen exe is not self-contained** — it still needs the repo runtime.
11. **`tests/test_doc_system.py` is environment-gated** and skips unless the
    developer's OpenCode/Obsidian paths exist; it is not a docs validator.
12. **`MemoryObject.lock` is unused** (dead field) and the relationship
    lexicon deltas are intentionally simple; LLM deep evaluation runs only on
    the voice kernel path.

---

## 8. Next Priorities

Ordered by the project roadmap and current evidence:

1. **M15 — Model scheduler + TTS bake-off.** Make the 4 GB VRAM budget
   explicit: one model resident at a time (LLM / STT / TTS), measured
   alternatives for voice quality.
2. **Voice latency + echo.** Wire `send_playback_audio()` into the playback
   path and validate AEC live; then re-measure STT on real sessions.
3. **Wake word.** Train an openWakeWord verifier for “hey mai” (few-shot on
   recorded clips) and drop the per-wake STT cost.
4. **M21 — Continuity Engine.** Project/commitment store, checkpoints/resume,
   cross-interface reconciliation (must land before any second interface).
5. **M24/M25 — Discord** with the shared `ChannelAdapter`, then text channels,
   then voice.
6. **M26 — WhatsApp** via the official Meta Agent Platform only.
7. **Entity interface + Java client.** Finish `api/web/` (entity, workspaces,
   design) before the Java/JavaFX shell.
8. **Housekeeping debt.** Collapse the graph layers to two, remove the
   memory→knowledge imports, delete dead `MemoryObject.lock`, add prompt
   token budgeting.

**Documentation rule:** update this page and the affected docs after every
significant milestone — not at the end of a release cycle.
