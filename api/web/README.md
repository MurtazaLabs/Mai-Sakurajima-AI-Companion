# api/web — MAI Web Interface

Home of the **MAI Cognitive Entity Interface** (v4.0). This is the new
presentation layer. The Python intelligence is unchanged and remains the
authority; nothing in this folder decides anything.

## Why this folder exists

The previous frontend lived under `api/static/`, which the project rules
describe as a flat asset directory (all `.js` in `js/`, all `.css` in `css/`, no
new subfolders). The entity interface needs a real module boundary: vendored
3D libraries, shaders, a state adapter, and per-workspace modules.

This folder is that boundary. It sits under `api/` because the API server is
what serves it, not because the entity is part of the HTTP layer — the entity
renders a sphere and knows nothing about HTTP.

## Layout

```
api/web/
├── entity/          Entity subsystem (v4.0 §24)
│   ├── entity-core.js          lifecycle, mount/unmount, public API
│   ├── entity-state.js         state machine, transitions
│   ├── entity-scene.js         Three.js scene, camera, renderer
│   ├── entity-material.js      surface material
│   ├── entity-shaders.js       GLSL: distortion, Fresnel, internal flow
│   ├── entity-orbitals.js      memory / goal / tool orbitals
│   ├── entity-effects.js       bloom, post-processing
│   ├── entity-transitions.js   GSAP timelines per state change
│   └── entity-performance.js   quality tiers, FPS budget, throttling
├── state/           visual state adapter  ← implemented
│   └── visual-state-adapter.js
├── workspaces/      presence, chat, memory, reasoning, agency,
│                    tasks, system, permissions, voice, graph
├── design/          tokens, motion language, primitives
└── vendor/          three.js, gsap (vendored, not CDN)
```

Only `state/` exists today. It is the foundation: the adapter is pure logic,
runs without a DOM or WebGL, and is unit tested under Node
(`tests/test_entity_state.py`).

## Rules

These are not style preferences. Each one exists because violating it produced
a specific defect.

1. **The entity never invents state.** It renders
   `state/visual-state-adapter.js` and nothing else. A field the backend does
   not report stays `null`; `null` is not `false`, and "unknown" is not "idle".
   *(v4.0 §25, §33, §34, §46)*
2. **No `setInterval` idle animation.** Continuous motion that no backend event
   justifies is the "giant glowing orb" the plan rejects. Motion maps to a
   published state or it does not exist. *(v4.0 §26, §47)*
3. **The entity is additive.** The shell, navigation, command palette, and every
   workspace must remain fully usable with WebGL unavailable, with the entity
   unmounted, and with `prefers-reduced-motion` set. *(v4.0 §28, §44)*
4. **The entity is presentation-only.** No private prompts, no raw
   chain-of-thought, no secrets, no unauthorised memory content. Abstractions
   like "retrieving relevant memories" are preferred over internal traces.
   *(v4.0 §9, §45)*
5. **One animation engine.** GSAP orchestrates, CSS handles UI, Three.js owns
   the entity. No Framer Motion, no Anime.js, no competing rAF loops.
   *(v4.0 §22, §23)*
6. **Vendored dependencies only.** `vendor/` holds Three.js and GSAP so the PWA
   works offline; they are added to the service worker's static list, and the
   cache version is bumped whenever they change.
7. **The backend stays authoritative.** This folder may not add an event
   architecture, a second HTTP client, or a parallel state store. It consumes
   the existing `state.*` event fabric and `api-client.js`. *(v4.0 §35)*

## State the backend provides today

Verified against the running API and `core/event_specs.py`.

| Contract field | Source | Status |
|---|---|---|
| `cognitiveState` | `state.reasoning.busy` / `.complete` | available |
| `emotion` | `state.emotion.changed` | available |
| `voiceState` | `state.voice.listening` / `.speaking` / `.idle` / `.wake` | available |
| `goalActivity` | `state.goal.updated` | available |
| `connection` | `/api/health/metrics` → `degraded` + SSE state | derived |
| `memoryActivity`, `memoryCount` | `state.retrieval.started` / `.completed` | **added for v4.0** |
| `toolActivity`, `activeTool` | `state.tool.started` / `.completed` | **added for v4.0** |
| `energy` | — | **no source. Stays `null`.** |

`energy` is listed in the v4.0 contract but nothing in the backend reports it.
Until a real source exists it stays `null` and the entity must not animate it.
See [[Complete Redesign Implementation Plan]] for the reasoning.

## Related

- [[Complete Redesign Implementation Plan]] — superseded v3.x direction
- [[MAI Cognitive Entity Interface Plan]] — v4.0
- [[Event Fabric Architecture]] — `state.*` vs `data.*` contract
- [[08-API Native & Surface]] — served routes
- [[Testing Strategy]] — gate for every phase
