# 03 — Core: Brain, Kernel & State

> Digest of `SUBSYSTEM_DOCUMENTATION/core.md`. Full detail: [[SUBSYSTEM_DOCUMENTATION/core]], [[CLASS_REFERENCE]] §2.

---

## Package Stats

`core/` — 51 files, 10,551 lines (**25% of codebase** — the center of gravity).

## The Brain (`core/brain.py`)

Deliberately a **facade** — heavy lifting is in injected subsystems (`BrainDeps` groups 23 deps into 5 constructor params).

`Brain.think(text, speaker, context)` flow:

```
1. update shared_state cognitive fields
2. MemoryCoordinator.retrieve (vector + beliefs + KG + attention, parallel)
   + experience_context (Dice-relevance-gated, M12)
3. memory store (extract + persist)
4. ReasoningEngine reason over retrieved context
5. relationship sync (deterministic deltas from user reply, M10)
6. PromptBuilder → prompt (personality + emotion + context + agent + identity overlay + experiences)
7. LLM generate → response (envelope leak guard; empty-reply bounded retry)
8. response_pipeline / style_filter
9. PostThinkHooks (background): reflection → beliefs → goals → procedural → learning (9 isolated blocks)
```

## The Kernel (`core/os_kernel.py`)

`AIOSKernel` = mission control. Main loop: IDLE → WAKE_DETECTED → GREETING / IDENTIFYING_SPEAKER → CONVERSATION → PROCESSING_RESPONSE → CLEANUP → IDLE. `ConversationPhase` enum (10 states), `KernelMode`: FOREGROUND / BACKGROUND. Owns child loops (voice thread, scheduler, watchers).

**Greeting-first** (M5): optional boot-time proactive greeting that enters the same wake FSM path (`GREETING_FIRST_ENABLED`, `GREETING_FIRST_DELAY_SECONDS`; once per session).

## Event Fabric (`core/`)

- `EventBus` — central bus: legacy `subscribe/publish` API **and** new envelope API (`publish_message`, `publish_wait`, `request`, `stream`). Priority queues (CRITICAL…BACKGROUND), middleware chain, retry policies, correlation IDs via thread-local, `stats()`/`traces()` for the Event Inspector.
- `event_specs.py` — 64 registered specs: 48 `data.*` + 15 `state.*` + 1 `telemetry.*`.
- `event_registry.py` — validation/authorization of publishers.
- `mai_message.py` — `MaiMessage` envelope + `publish_event()` helper.

## State (`core/state/`)

| Store | Contents |
|-------|----------|
| `SharedState` | thread-safe dict; 10+ cognitive fields (working_memory, current_topic, attention_focus, current_goal, current_reasoning, current_speaker, active_task, conversation_intent, confidence, recent_thoughts) |
| `relationship.py` | trust / affection / closeness / respect / familiarity; **deterministic lexicon deltas** (M10) + LLM deep evaluation |
| `per_person_relationship.py` | per-speaker metrics |
| `db.py` | SQLite durable state |

## Emotion & Personality

- `emotion.py` — 16-line `update()` dispatch + 9 handler methods; RLock; enums (`EmotionName`, `TimeOfDay`, `UserMood`, `EmotionProfile`). Emotion influences retrieval, speech speed, goal priority, interrupt tolerance, word choice.
- `emotion_system.py` — blend / decay / triggers. `emotion_goals.py` — emotion↔goal coupling.
- `personality_state.py` + `identity/*` — traits, values, boundaries, speech style (JSON-backed).
- **Canon book** (`identity/canonical.py` + `identity/character/volume-01..04`) — Vol I identity, Vol II speech/emotion, Vol III relationships, Vol IV rule resolution (7-tier priority: boundaries → values → relationship → honesty → independence → playfulness → expression). Drift-checked by `TestCanonDrift`.
- `identity/identity_core.py` — read-only projections: `get_preferences()` (overlay-aware), `get_current_identity()`, `get_conflict_resolution()` (M13; canon policy, not yet promoted into prompts); `attach_preference_overlay()` — evolved preferences never mutate canon.

## Coordination Adapters

`memory_coordinator.py` (brain↔memory), `reasoning_coordinator.py`, `tool_manager.py` (extracted from Brain), `post_think_hooks.py` (9 blocks, per-subsystem error isolation), `prompt_orchestrator.py` (compat wrapper over `prompt/`).

## Scheduling & Support

- `scheduler.py` — periodic tasks, fully lock-guarded. M6 tasks: `dream_level5` (daily — experience reflection) and `preference_apply` (weekly — preference overlay refresh); both background-only, registered unconditionally, no-op without `brain.preference_evolution`.
- `tasks.py`, `autonomy/engine.py` — task + autonomy layer.
- `plugin_system.py` — Plugin / PluginLoader / HookRegistry.
- `write_journal.py` — async batched writes; `profile_store.py` — user profiles.

---

## Wiki Links

**Previous:** [[02-Application Boot & Lifecycle]]  
**Next:** [[04-Memory Subsystem]] — the memory pipeline  
**Related:** [[01-Architecture/09-Events & Data Flow]] — event fabric detail • [[02-Subsystems/Emotion System]] — emotion detail • [[02-Subsystems/Identity & Canon]] — canon volumes