# Event Fabric Architecture (v2.1)

> Design specification for the Mai AI Event Fabric — `core/event_bus.py`, `core/event_specs.py`, `core/mai_message.py`, `core/event_registry.py`, `core/event_metadata.py`.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0 | Jul 2026 | Legacy subscribe/publish only |
| v2.0 | Jul 27 2026 | Phase 4: MaiMessage envelope, semantic topics, registry validation |
| v2.1 | Jul 27 2026 | Phase 5: Reactive UI — state.* projection bus, dual-publish, 15 STATE_* constants |

---

## Core Concepts

### Two-Topic Namespaces

| Namespace | Prefix | Purpose | Consumers |
|-----------|--------|---------|-----------|
| **Subsystem Fabric** | `data.*` | Durable record of what happened | All subsystems |
| **UI Projection** | `state.*` | UI-optimized, denormalized | UI **exclusively** (stream_manager, ws_bridge, notifier) |

**Rule:** UI subscribes **only** to `state.*`. Subsystems publish to both (`dual-publish`) or use `data.*` for internal coordination.

### Envelope: MaiMessage

```python
@dataclass
class MaiMessage:
    spec: EventSpec           # registered spec
    payload: dict             # validated payload
    source: str               # publisher identifier
    cid: str                  # correlation ID (thread-local)
    timestamp: float          # epoch seconds
    priority: Priority        # CRITICAL..BACKGROUND
```

### Correlation IDs

- `correlation_scope(cid)` — context manager sets thread-local CID
- Whole conversation shares one `correlation_id` for tracing
- UI reads `cid` for distributed tracing
- Event Inspector groups by CID

---

## Registered Specs (67 total)

### `state.*` (17 — UI Projection)

| Spec Constant | Topic | Publisher |
|---------------|-------|-----------|
| `STATE_VOICE_IDLE` | `state.voice.idle` | VoiceManager |
| `STATE_VOICE_LISTENING` | `state.voice.listening` | VoiceManager |
| `STATE_VOICE_SPEAKING` | `state.voice.speaking` | VoiceManager |
| `STATE_VOICE_WAKE` | `state.voice.wake` | VoiceManager |
| `STATE_EMOTION_CHANGED` | `state.emotion.changed` | Emotion |
| `STATE_MEMORY_UPDATED` | `state.memory.updated` | MemoryPipeline |
| `STATE_REASONING_BUSY` | `state.reasoning.busy` | Brain |
| `STATE_REASONING_COMPLETE` | `state.reasoning.complete` | Brain |
| `STATE_REASONING_REFLECTION` | `state.reasoning.reflection` | PostThinkHooks |
| `STATE_DREAMING_STARTED` | `state.dreaming.started` | DreamEngine |
| `STATE_DREAMING_FINISHED` | `state.dreaming.finished` | DreamEngine |
| `STATE_GOAL_UPDATED` | `state.goal.updated` | GoalManager |
| `STATE_AGENT_COMPLETED` | `state.agent.completed` | Agent |
| `STATE_KNOWLEDGE_UPDATED` | `state.knowledge.updated` | GraphManager |
| `STATE_BELIEF_UPDATED` | `state.belief.updated` | BeliefEngine |
| `STATE_NEEDS_UPDATED` | `state.needs.updated` | NeedsEngine |
| `STATE_MONOLOGUE_GENERATED` | `state.monologue.generated` | Monologue |

### `data.*` (50 — Subsystem Fabric)

Key M6 additions:
- `DATA_PREFERENCE_EVOLVED` → `data.preference.evolved` (PreferenceEvolution)
- `DATA_EXPERIENCE_RECORDED` → `data.experience.recorded` (MemoryPipeline)

Full list in `core/event_specs.py`.

### `telemetry.*` (1)
- `TELEMETRY_INSPECTOR_RECORD` → `telemetry.inspector.record` (EventBus auto)

---

## Publishing API

### Legacy (deprecated but supported)
```python
bus.publish("topic.name", payload)
```

### Fabric (preferred)
```python
from core.event_specs import SPEC_MEMORY_STORED
from core.mai_message import publish_event

publish_event(bus, SPEC_MEMORY_STORED, {"memory_id": "abc", "type": "episodic"}, "memory_pipeline")
```

### Advanced
```python
# Wait for handlers (request/response)
result = await publish_wait(bus, SPEC, payload, source, timeout=5.0)

# Streaming
async for chunk in stream(bus, SPEC, payload, source):
    process(chunk)
```

---

## Delivery Guarantees

| Property | Value |
|----------|-------|
| Ordering | Per-topic FIFO |
| Priority | CRITICAL > HIGH > NORMAL > LOW > BACKGROUND |
| Retry | Per-spec: NEVER / IMMEDIATE / EXPONENTIAL / DEAD_LETTER / IGNORE |
| Compression | gzip if payload > 1KB and `compressed=True` |
| Correlation | Thread-local CID propagated |

---

## Middleware Chain

1. **Validation** — payload matches `payload_schema` (JSON Schema)
2. **Authorization** — `EventRegistry` checks publisher allowed for topic
3. **Metrics** — latency, throughput, error rates
4. **Tracing** — Event Inspector buffer
5. **Logging** — structured DEBUG log
6. **Compression** — optional gzip

---

## Phase 5: Reactive UI (State Projection Bus)

### Dual-Publish Pattern

Subsystems that drive UI state **must** dual-publish:

```python
# In VoiceManager
publish_event(bus, SPEC_DATA_VOICE_LISTENING, payload, "voice_manager")  # data.*
publish_event(bus, SPEC_STATE_VOICE_LISTENING, ui_payload, "voice_manager")  # state.*
```

### UI Consumers (state.* only)

| Consumer | Topics |
|----------|--------|
| `api/stream_manager.py` | all `state.*` via `STREAM_TOPICS` |
| `api/ws_bridge.py` | all `state.*` via `STREAM_TOPICS` (single-source import) |
| `native/notifier.py` | `state.emotion.changed`, `state.dreaming.*`, `state.goal.updated`, `state.voice.wake`, `state.error` |
| `api/static/js/os.js` | SSE → UI state updates |
| `api/static/js/notifications.js` | SSE → toast notifications |
| `api/static/js/presence.js` | SSE → presence indicators |

### Exceptions (Runtime Subscriptions)

These remain `data.*` subscribers (not migrated to `state.*`):

- `api/server.py` → `data.dream.completed` (runtime only)
- `core/os_kernel.py` → `data.dream.started/ended` (runtime only)

---

## VoiceManager Fix (Phase 5)

Removed duplicate `VOICE_STOPPED` publish in `voice_manager.py:stop()` — was publishing both `data.voice.stopped` and `state.voice.idle` for same transition.

---

## Testing

```python
# Register specs on real bus for tests
from core.event_specs import register_event_specs
register_event_specs(bus)

# Use publish_message helper in tests
from core.mai_message import publish_message
publish_message(bus, "data.memory.stored", {"id": "abc"}, "test")
```

---

## Migration Guide (Legacy → Fabric)

| Legacy | Fabric |
|--------|--------|
| `bus.subscribe("topic", handler)` | `bus.subscribe(SPEC.topic, handler)` |
| `bus.publish("topic", payload)` | `publish_event(bus, SPEC, payload, source)` |
| Ad-hoc topic strings | Registered specs in `event_specs.py` |
| No payload validation | JSON Schema validation |
| No publisher auth | `EventRegistry` authorization |
| No correlation | `correlation_scope()` + `MaiMessage.cid` |

---

## Wiki Links

**Architecture:** [[01-Architecture/09-Events & Data Flow]] — data flow overview • [[01-Architecture/03-Core Brain Kernel & State]] — event fabric in core  
**Subsystems:** [[02-Subsystems/Event System]] — complete topic reference • [[01-Architecture/07-Voice Subsystem]] — voice events • [[01-Architecture/04-Memory Subsystem]] — memory events