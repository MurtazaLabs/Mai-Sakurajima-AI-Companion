# Event System Reference

> Complete reference for the Mai AI Event Fabric — `core/event_bus.py`, `core/event_specs.py`, `core/mai_message.py`, `core/event_registry.py`.

---

## Overview

The Event Fabric is the central nervous system of Mai AI. All cross-subsystem communication flows through the `EventBus`.

**Design Spec:** [[03-Features/Event Fabric Architecture]] (v2.1)

---

## Core Components

### EventBus (`core/event_bus.py`)

Central message broker with:

- **Legacy API:** `subscribe(topic, handler)`, `publish(topic, payload)`
- **Fabric API:** `publish_event(bus, SPEC, payload, source)` — envelope-based
- **Advanced:** `publish_wait`, `request`, `stream` (request/response, streaming)
- **Priority queues:** CRITICAL > HIGH > NORMAL > LOW > BACKGROUND
- **Middleware chain:** validation → authorization → metrics → tracing → logging → compression
- **Retry policies:** NEVER / IMMEDIATE / EXPONENTIAL / DEAD_LETTER / IGNORE
- **Correlation IDs:** `correlation_scope()` thread-local → `MaiMessage.cid`
- **Telemetry:** `stats()`, `traces()` for Event Inspector

### MaiMessage (`core/mai_message.py`)

Envelope structure:

```python
@dataclass
class MaiMessage:
    spec: EventSpec           # registered spec (topic, version, retry, etc.)
    payload: dict             # validated payload
    source: str               # publisher identifier
    cid: str                  # correlation ID (thread-local)
    timestamp: float          # epoch seconds
    priority: Priority        # CRITICAL..BACKGROUND
```

Helper: `publish_event(bus, SPEC, payload, source)` — constructs envelope, runs middleware, delivers.

### EventSpecs (`core/event_specs.py`)

**67 registered specs** (auto-registered at import):

| Category | Count | Prefix | Purpose |
|----------|-------|--------|---------|
| Subsystem fabric | 50 | `data.*` | durable record of what happened |
| UI projection | 17 | `state.*` | UI subscribes **exclusively** here |
| Telemetry | 1 | `telemetry.inspector.record` | Event Inspector feed |

All specs define: `topic`, `version`, `retry`, `max_attempts`, `compressed`, `payload_schema` (JSON Schema).

### EventRegistry (`core/event_registry.py`)

- Validates publishers against spec requirements
- Authorization: which components may publish which topics
- Single source of truth for topic definitions

---

## Topic Reference

### `state.*` (UI Projection — UI Subscribes Exclusively Here)

| Topic | Publisher | Payload |
|-------|-----------|---------|
| `state.voice.idle/listening/speaking/wake` | VoiceManager | `{phase, emotion, speaker}` |
| `state.emotion.changed` | Emotion | `{name, intensity, profile, triggers}` |
| `state.memory.updated` | MemoryPipeline | `{count, types, latest_id}` |
| `state.reasoning.busy/complete/reflection` | Brain, PostThinkHooks | `{depth, duration, result}` |
| `state.dreaming.started/finished` | DreamEngine | `{level, report}` |
| `state.goal.updated` | GoalManager | `{goal_id, action, progress}` |
| `state.agent.completed` | Agent | `{task, steps, success}` |
| `state.knowledge.updated` | GraphManager | `{entities, relations, docs}` |
| `state.belief.updated` | BeliefEngine | `{belief_id, confidence, source}` |
| `state.needs.updated` | NeedsEngine | `{need, level, delta}` |
| `state.monologue.generated` | Monologue | `{text, emotion, context}` |

### `data.*` (Subsystem Fabric Record)

| Topic | Publisher | Notes |
|-------|-----------|-------|
| `data.voice.*` | VoiceManager | VAD, STT, TTS, interruption events |
| `data.emotion.changed` | Emotion | same as state but for subsystem consumers |
| `data.memory.*` | MemoryPipeline | extraction, consolidation, decay |
| `data.conversation.finished` | Brain | turn complete with full context |
| `data.reasoning.completed` | ReasoningEngine | reasoning trace |
| `data.reflection.generated` | ReflectionEngine | reflection output |
| `data.belief.updated` | BeliefEngine | belief delta |
| `data.graph.updated` | GraphManager | entity/relation changes |
| `data.agent.*` | Agent | tool calls, step results |
| `data.goal.*` | GoalManager | create/progress/complete |
| `data.dream.*` | DreamEngine | dream start/end, task results |
| `data.preference.evolved` | PreferenceEvolution | M6 — preference change |
| `data.experience.recorded` | MemoryPipeline | M6 — charged turn ingested |

---

## Subscriber Map

| Subscriber | Topics Consumed |
|------------|-----------------|
| `api/stream_manager.py` | `STREAM_TOPICS` (all `state.*` + select `data.*`) |
| `api/ws_bridge.py` | `STREAM_TOPICS` (single-source import) |
| `native/notifier.py` | `state.emotion.changed`, `state.dreaming.*`, `state.goal.updated`, `state.voice.wake`, `state.error` |
| `core/os_kernel.py` | `data.dream.started/ended`, `state.voice.*` |
| `api/server.py` | `data.dream.completed` (runtime only) |
| `observability/event_inspector.py` | `telemetry.inspector.record` (auto) |

---

## Publishing Patterns

### Legacy (still supported)
```python
bus.publish("topic.name", {"key": "value"})
```

### Fabric (preferred)
```python
from core.event_specs import SPEC_MEMORY_STORED
from core.mai_message import publish_event

publish_event(bus, SPEC_MEMORY_STORED, {"memory_id": "abc", "type": "episodic"}, "memory_pipeline")
```

### With Correlation (for tracing)
```python
from core.event_bus import correlation_scope

with correlation_scope("conv-123"):
    publish_event(bus, SPEC_MEMORY_STORED, {...}, "memory_pipeline")
# All messages in this scope share cid="conv-123"
```

---

## Middleware Chain

1. **Validation** — payload matches `payload_schema`
2. **Authorization** — publisher allowed for this topic
3. **Metrics** — increment counters, measure latency
4. **Tracing** — add to Event Inspector buffer
5. **Logging** — structured log at DEBUG
6. **Compression** — gzip if `compressed=True` and payload > 1KB

---

## Retry Policies

| Policy | Behavior |
|--------|----------|
| `NEVER` | Fire-and-forget (default) |
| `IMMEDIATE` | Retry once immediately on handler exception |
| `EXPONENTIAL` | Retry with backoff (max `max_attempts`) |
| `DEAD_LETTER` | On final failure, send to dead-letter queue |
| `IGNORE` | Swallow handler exceptions silently |

---

## Correlation IDs

- `correlation_scope(cid)` — context manager sets thread-local CID
- All messages published within scope inherit the CID
- UI reads `cid` for distributed tracing
- Event Inspector groups by CID

---

## Event Inspector (`observability/event_inspector.py`)

Real-time event inspection for dashboard:
- Subscribes to `telemetry.inspector.record`
- Buffers last N events with full envelopes
- Exposes `/api/inspector/events` (REST) + WS stream
- Filters: topic, source, priority, time range, CID

---

## Best Practices

1. **Use fabric API** — `publish_event()` with registered spec
2. **Define specs in `event_specs.py`** — single source of truth
3. **UI only subscribes to `state.*`** — never `data.*`
4. **Dual-publish for state projection** — e.g., VoiceManager publishes both `data.voice.*` and `state.voice.*`
5. **Keep payloads small** — large blobs go to storage, publish reference
6. **Use correlation scopes** — wrap conversation turns

---

## Wiki Links

**Architecture:** [[01-Architecture/09-Events & Data Flow]] — data flow overview • [[01-Architecture/03-Core Brain Kernel & State]] — event fabric in core  
**Spec:** [[03-Features/Event Fabric Architecture]] — full v2.1 spec  
**Subsystems:** [[01-Architecture/07-Voice Subsystem]] — voice events • [[01-Architecture/04-Memory Subsystem]] — memory events • [[01-Architecture/06-Agency Reasoning LLM & Execution]] — agent/goal/dream events