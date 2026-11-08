# 09 — Events & Data Flow

> Source docs `EVENT_REFERENCE.md` / `DATA_FLOW.md` were merged and deleted; this page is the surviving reference. Design spec: [[03-Features/Event Fabric Architecture]] (v2.1). Capability status: [[00-Overview/CURRENT_STATE]].

---

## Event Fabric Overview

- **72 catalog topics** (measured Oct 2026): 50 `data.*` (subsystem fabric record) + 22 `state.*` (UI projection) declared as flat topic constants in `core/event_specs.py` (per-subsystem modules re-export their constants). `telemetry.inspector.record` auto-subscribed by the EventBus. `control.*` reserved (0 in catalog).
- Version=1, retry=NEVER, max_attempts=1, compressed=False (control exceptions documented).

### APIs

| API | Use |
|-----|-----|
| Legacy `bus.subscribe/publish` | older code paths |
| Fabric `publish_event(bus, SPEC, payload, source)` | envelope; preferred |
| `publish_wait` / `request` / `stream` | wait-for-handlers, request/response, streaming |

### Delivery Layers

1. Priority: CRITICAL > HIGH > NORMAL > LOW > BACKGROUND.
2. Middleware chain: validation → authorization → metrics → tracing → logging → compression.
3. Retry policies: NEVER / IMMEDIATE / EXPONENTIAL / DEAD_LETTER / IGNORE.
4. Correlation: `correlation_scope()` thread-local → `MaiMessage.cid`; whole conversation shares one `correlation_id` for tracing.
5. Telemetry → Event Inspector.

## `state.*` (UI Projection — UI Subscribes Exclusively Here)

| Topic | Publisher |
|-------|-----------|
| `state.voice.idle/listening/speaking/wake` | VoiceManager |
| `state.emotion.changed` | Emotion |
| `state.memory.updated` | pipeline/manager |
| `state.reasoning.busy / complete / reflection` | Brain, PostThinkHooks |
| `state.dreaming.started / finished` | DreamEngine |
| `state.goal.updated` | GoalManager |
| `state.agent.completed` | Agent |
| `state.knowledge.updated` | GraphManager |
| `state.belief.updated` | BeliefEngine |
| `state.needs.updated` | NeedsEngine (M-series) |
| `state.monologue.generated` | Monologue (M-series) |
| `state.retrieval.started / completed` | AdvancedRetriever (v4.0 projections — no query/content in payload) |
| `state.tool.started / completed` | ToolRegistry (v4.0 projections — name + success + duration only) |
| `state.user.switched` | Brain / profile switch |

## M6 Additions (`data.*` — Subsystem Fabric Record)

| Topic | Publisher |
|-------|-----------|
| `data.preference.evolved` | PreferenceEvolution |
| `data.experience.recorded` | MemoryPipeline (charged turn ingest) |

Scheduler consumers: `dream_level5` (daily — experience reflection) and `preference_apply` (weekly — overlay refresh); both background-only, registered unconditionally, no-op until `brain.preference_evolution` exists.

## Main Publisher Map

| Publisher | Topics |
|-----------|--------|
| voice | `data.voice.*`, `state.voice.*` |
| Emotion | `data.emotion.changed`, `state.emotion.changed` |
| memory pipeline | `data.memory.*`, `state.memory.updated`, `data.conversation.finished` |
| Brain / response | `data.conversation.finished`, `state.reasoning.busy/complete` |
| Reasoning/Reflection | `data.reasoning.completed`, `data.reflection.generated` |
| BeliefEngine | `data.belief.updated`, `state.belief.updated` |
| GraphManager | `data.graph.updated`, `state.knowledge.updated` |
| Agent | `data.agent.*`, `state.agent.completed` |
| GoalManager | `data.goal.*`, `state.goal.updated` |
| DreamEngine | `data.dream.*`, `state.dreaming.*` |
| PostThinkHooks | `data.graph.updated`, `state.reasoning.reflection`, belief graph sync |

## Subscriber Map

`api/stream_manager.py` + `api/ws_bridge.py` (STREAM_TOPICS), `native/notifier.py`, `core/os_kernel.py` (`data.dream.*`, `state.voice.*`), `api/server.py` (`data.dream.completed`, runtime only), `observability/event_inspector.py` (`telemetry.inspector.record`, auto).

## Four Primary Data Paths

1. **Conversation**: mic → STT → Brain.think → retrieve → prompt → LLM → TTS → speaker.
2. **Memory store**: turn → FastExtractor → Pipeline → journal batch | VectorStore → graph → vault → `state.memory.updated`.
3. **Retrieval**: query → MemoryCoordinator → parallel {vector, beliefs, KG, attention} → rank/merge → PromptBuilder.
4. **Knowledge ingest**: files → DirectoryWatcher → KnowledgeBaseBuilder → chunk → Indexer → DocumentStore + BrainGraph → `state.knowledge.updated`.

### Post-Think Hook Chain (Background)

reflect → beliefs → goals → procedural learn → learning adjust → publish `state.reasoning.reflection`.

## Cross-Cutting Invariants

- Correlation IDs propagate thread-locally; UI reads `cid` for tracing.
- Hot memory writes journaled (`WriteJournal`), flush on shutdown.
- Vault single-writer: StateDumper owns compiled folders; MemoryWriter owns raw records.

---

## Wiki Links

**Previous:** [[08-API Native & Surface]]  
**Next:** [[10-Status & Debt]] — technical debt + implementation status  
**Related:** [[01-Architecture/03-Core Brain Kernel & State]] — event fabric detail • [[03-Features/Event Fabric Architecture]] — full spec v2.1 • [[02-Subsystems/Event System]] — event system detail