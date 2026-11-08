# 01 — System Overview

> Source docs `SYSTEM_ARCHITECTURE.md` / `DIRECTORY_STRUCTURE.md` were merged and deleted; this page is the surviving reference.
> Authoritative capabilities list: [[00-Overview/CURRENT_STATE]].

---

## What Mai AI Is

A production-oriented, modular AI companion (inspired by Mai Sakurajima) built for **long-term personal companionship**: conversational intelligence, persistent memory, voice interaction, emotional consistency, knowledge management, and extensible tooling — designed as a *platform*, not a chatbot. Every subsystem is expected to evolve independently over a multi-year timeline.

## Scale (measured Nov 8 2026)

| Metric | Value |
|--------|-------|
| Python files | 383 — 80,024 lines incl. tests; 295 / 56,366 excl. tests |
| Packages | 19 + 2 root entry points |
| Subsystems | core, memory, knowledge, voice, api, agency, app, config, llm, observability, execution, reasoning, native, plugins, scripts, prompt, integrations, evaluation, profiling |
| Tests | 2,035 collected; 2,033 passing + 2 skipped (0 failures — live-verified Nov 8 2026) |

## Character Layer (M0–M13, complete Aug 9 2026)

The companion layer built on top of the core platform:

- **Canon book** — 4 volumes at `core/identity/character/volume-0X-*.md`: identity, speech/emotion, relationships, rule-resolution (7-tier conflict priority). Registered in `canonical.py` + drift-checked by tests.
- **Behavioral validation harness** — `tests/behavior/` (ScenarioDriver, virtual clock, causal traces, deterministic ThoughtPacket fixtures; LLM stubbed).
- **Milestone gates** — M0 canon → M1 identity → M2 relationship → M3 needs → M4 emotion → M5 greeting-first → M6 experience & preference evolution → M7 behavioral spec → M8 consumers → M9 real-world evaluation (`evaluation/`) → M10 relationship on chat path → M11 envelope-leak guard → M12 experience in speech → M13 conflict coherence.
- **Real-mode evidence** — transcripts + rubric reports were produced during the Aug 2026 runs (praise 4.57/5, jealousy 4.67/5, emotional 4.71/5). The generated `session-*/` folders are artifacts, not checked into the repo.
- **No separate appraisal engine** — "emotion ≠ behavior" is enforced by distributed normative gating (emotion thresholds, prompt-injected canon, `ThoughtPacket.decision`).

## Design Principles

1. **Modularity** — sealed packages (`core/`, `memory/`, `knowledge/`, `voice/`, `agency/`, `api/`, …); few well-defined seams.
2. **Persistence-first** — memory, knowledge graph, beliefs, and character state survive restarts; files are the durable store (`data/`, vault).
3. **Event-driven fabric** — central EventBus carries `data.*`/`state.*` messages; UI + voice observe `state.*` projections.
4. **Single ownership** — every durable artifact has exactly one writer (StateDumper owns compiled vault folders; MemoryWriter owns raw conversation records).
5. **Fail-safe telemetry** — all health stats go through `HealthRegistry`; subsystem failure never crashes the runtime.
6. **Graceful degradation** — STT/TTS/embeddings/LLM unavailability degrades stepwise instead of failing the conversation.

## High-Level Layout

```
run.py / run_daemon.py            ← entry points (thin)
         ↓
ApplicationBuilder (app/builders/, 8 phases)
         ↓
AIApplication (DI container, ~60 subsystem attributes)
         ↓
AIOSKernel (core/os_kernel.py)    ← mission control / main loop
```

The application is a **composition root**: `AIApplication` is a plain container; subsystems are attached via `setattr` in `ApplicationBuilder`. The EntryPoint only picks the mode and calls `ApplicationBuilder.build()`.

## Runtime at a Glance

- `AIOSKernel` drives the conversation state machine (`ConversationPhase`, `KernelMode`).
- `Brain.think()` is the cognition entry point per turn.
- Concurrency: one RLock per subsystem; audio callbacks post to queues; heavy work on background workers (`ThreadPoolExecutor`), with async surfaces fed by unblocking hand-offs.

## Persistence Map

| Store | Location | Writer |
|-------|----------|--------|
| SQLite state DB | `memory/mai.db` | `core/state/database.py` |
| Vector store | `vector_memory/` (ChromaDB) with JSON/SQLite fallback | VectorStore |
| Knowledge graph | `OBSIDIAN_VAULT/graph/graph.json` (+ entity notes) — rebuilt from the vault on boot; `BrainGraph.save()` has no production caller | GraphExporter / VaultCompiler |
| Compiled vault | `OBSIDIAN_VAULT/` (default `~/MaiMemory`, override `MAI_OBSIDIAN_VAULT`) | StateDumper / VaultCompiler |
| Raw conversations | `…/conversation/` | MemoryWriter |
| Profiles | `data/profiles/profiles.db` | ProfileStore |
| Logs / traces | `logs/`, `logs/cognitive_audit/*.json` | logging + Tracer |
| Embedding cache | **in-process LRU** (no on-disk cache) | EmbeddingService |

---

## Wiki Links

**Next:** [[02-Application Boot & Lifecycle]] — how the container builds; then [[03-Core Brain Kernel & State]] for the core package.

**Related:** [[05-Reference/Complete Folder Structure]] — full repository tree • [[00-Overview/Project Charter]] — project constitution • [[03-Features/Native OS Bridge Architecture]] — daemon architecture