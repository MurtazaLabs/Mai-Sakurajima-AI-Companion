# 02 — Application Boot & Lifecycle

> Digest of `STARTUP_SEQUENCE.md`. Full detail: [[STARTUP_SEQUENCE]], [[DEPENDENCY_GRAPH]].

---

## Entry Points

| Entry | Mode |
|-------|------|
| `run.py` | CLI / interactive / server / daemon select |
| `run_daemon.py` | native desktop app (M14, Oct 2026): tray, hotkeys, pywebview `AppWindow` (close→hide-to-tray), single-instance focus, install-app shortcut |
| `MaiAPI.bootstrap()` | REST bootstrap (module-level `app` for `run_daemon.py`; sets `mai.app` / `mai.kernel`) |

All converge on `ApplicationBuilder.build()` → `AIApplication`.

## The 8-Phase Boot Pipeline (`app/boot.py`)

```
Infrastructure → Core/Cognition → Memory → Knowledge → Reasoning → Agency → Voice → Runtime
```

| # | Phase | Builder | Key Creations |
|---|-------|---------|---------------|
| 1 | Infrastructure | `builders/infrastructure.py` | EventBus, config, logging, tracer, HealthRegistry, rate limiter |
| 2 | Core/Cognition | `builders/cognition.py` | SharedState, Emotion, PersonalityState, Brain, cognitive graph, brain-graph, tool manager, RelationshipEngineV2 + relationship_engine (M10), experience_store attach |
| 3 | Memory | `builders/memory.py` | VectorStore, EmbeddingService, extractor, pipeline, MemoryManager, ExperienceStore (M6) |
| 4 | Knowledge | `builders/knowledge.py` | KnowledgeGraph, BrainGraph, BeliefEngine, retriever, vault compiler, watcher, indexer |
| 5 | Reasoning | `builders/reasoning.py` | ReasoningEngine, ThoughtJournal, ReflectionEngine (cadence on), LearningEngine |
| 6 | Agency | `builders/agency.py` | ToolRegistry + tools, Agent, GoalManager, ProceduralMemory, WorldModel, DreamEngine (experience_store + PreferenceEvolution wired, M6) |
| 7 | Voice | `builders/voice.py` | VoiceManager, STT, TTS, wake word, speaker manager |
| 8 | Runtime | `builders/runtime.py` | Scheduler (incl. dream_level5 daily + preference_apply weekly, M6), AIOSKernel, plugins (`load_all`), daemon wiring |

**Phase rule:** strictly ordered — later phases may read earlier phases' attributes. The only allowed dependency direction: `infrastructure ← core ← memory ← reasoning ← agency ← voice ← runtime`.

## Validation Gates (`app/validation.py`)

| Check | Failure Mode |
|-------|--------------|
| Event bus alive | log + abort |
| All expected subsystems present as attrs | log + abort |
| HealthRegistry entries for core subsystems | warn |
| LLM provider reachable (probe snapshot under lock) | warn + fallback chain |
| Voice devices present | warn (degrade to text) |

## Startup Timing Notes

- No blocking ChromaDB probe at boot (catch-at-first-use).
- Vault migration idempotent (MD5-keyed dedup of replayed writes).
- Plugins load in phase 8 (after brain exists).
- DirectoryWatcher + DreamEngine start post-boot, non-blocking.
- `HealthRegistry.heartbeat_all()` runs at end of `build()` (post-validation) — boot-end stall-timer reset; with ≥2-heartbeat stalling rule (Aug 9), construction-only components can never be flagged STALLED.

## Shutdown (Reverse Order, With Timeouts)

1. Runtime loop stop → 2. voice thread stop → 3. scheduler stop → 4. watchers stop →
5. journal flush + vector prune → 6. state/profile save → 7. EventBus clear + worker join →
8. logging flush, tracer close.

## Failure Modes

| Failure | Behavior |
|---------|----------|
| LLM provider down | failover chain (OpenRouter → Ollama → static) |
| STT/TTS missing | voice degrades to text |
| Embedding model fails | keyword retrieval fallback |
| Graph/vault write fails | logged, non-fatal |
| Health check fails | warning + dashboard red |

---

## Wiki Links

**Previous:** [[01-System Overview]]  
**Next:** [[03-Core Brain Kernel & State]] — Brain, kernel, state, emotion  
**Related:** [[01-Architecture/09-Events & Data Flow]] — event fabric reference • [[05-Reference/Complete Folder Structure]] — app/builders/ detail