# 01 — System Overview

> Digest of `SYSTEM_ARCHITECTURE.md`. Full detail: [[SYSTEM_ARCHITECTURE]], [[DIRECTORY_STRUCTURE]].

---

## What Mai AI Is

A production-oriented, modular AI companion (inspired by Mai Sakurajima) built for **long-term personal companionship**: conversational intelligence, persistent memory, voice interaction, emotional consistency, knowledge management, and extensible tooling — designed as a *platform*, not a chatbot. Every subsystem is expected to evolve independently over a multi-year timeline.

## Scale (measured Aug 9 2026)

| Metric | Value |
|--------|-------|
| Python files | 256 |
| Lines | 42,395 |
| Packages | 18 + 2 root entry points |
| Subsystems | core, memory, knowledge, voice, api, agency, app, config, llm, observability, execution, reasoning, native, plugins, scripts, prompt, gateways, evaluation |
| Tests | 1,812 (all passing) |

## Character Layer (M0–M13, complete Aug 9 2026)

The companion layer built on top of the core platform:

- **Canon book** — 4 volumes at `core/identity/character/volume-0X-*.md`: identity, speech/emotion, relationships, rule-resolution (7-tier conflict priority). Registered in `canonical.py` + drift-checked by tests.
- **Behavioral validation harness** — `tests/behavior/` (ScenarioDriver, virtual clock, causal traces, deterministic ThoughtPacket fixtures; LLM stubbed).
- **Milestone gates** — M0 canon → M1 identity → M2 relationship → M3 needs → M4 emotion → M5 greeting-first → M6 experience & preference evolution → M7 behavioral spec → M8 consumers → M9 real-world evaluation (`evaluation/`) → M10 relationship on chat path → M11 envelope-leak guard → M12 experience in speech → M13 conflict coherence.
- **Real-mode evidence** — transcripts + rubric reports in `docs/evaluation/session-*/`.
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
| Vector store | `data/memory/` (+ ChromaDB) | VectorStore |
| Knowledge graph | `data/graph/` | BrainGraph |
| Compiled vault | `OBSIDIAN_VAULT/` | StateDumper / VaultCompiler |
| Raw conversations | `…/conversation/` | MemoryWriter |
| Profiles | `data/profiles/` | ProfileStore |
| Logs / traces | `logs/`, `data/traces/` | logging + Tracer |
| Embedding cache | `data/cache/` | EmbeddingService |

---

## Wiki Links

**Next:** [[02-Application Boot & Lifecycle]] — how the container builds; then [[03-Core Brain Kernel & State]] for the core package.

**Related:** [[05-Reference/Complete Folder Structure]] — full repository tree • [[00-Overview/Project Charter]] — project constitution • [[03-Features/Native OS Bridge Architecture]] — daemon architecture