---
document_type: feature-plan
project: Mai AI
title: MAI Cognitive Entity Interface — Living Intelligence
status: approved
version: 4.0.0
last_updated: 2026-09-26
supersedes: "[[Complete Redesign Implementation Plan]]"
tags:
  - mai-ai
  - product-strategy
  - frontend
  - entity
  - three-js
  - visual-language
related:
  - "[[Complete Redesign Implementation Plan]]"
  - "[[Event Fabric Architecture]]"
  - "[[Native OS Bridge Architecture]]"
  - "[[08-API Native & Surface]]"
  - "[[Memory Pipeline]]"
  - "[[Voice Pipeline]]"
  - "[[Testing Strategy]]"
---

# MAI Cognitive Entity Interface — Product and Implementation Plan

## 1. Executive Decision

Replace the **MAI Cognitive Desktop — Quiet Intelligence** direction with:

> **MAI Cognitive Entity Interface — Living Intelligence**

MAI must stop feeling like a collection of dashboards exposing backend modules,
and start feeling like a persistent cognitive entity with an interface.

The central visual element is the **MAI Entity Core**: a spherical, volumetric
computational presence representing MAI's current state.

**The entity is not decoration. It is a visual state machine driven by real
backend information.**

The interface communicates presence, emotion, attention, cognition, memory
retrieval, reasoning, voice, tool execution, goals, system health, and
availability through a combination of the entity, workspace UI, contextual
panels, semantic animation, and real backend state.

The goal is something closer to a personal cognitive environment than a
conventional SaaS dashboard — without becoming an anime clone or a generic
glowing AI orb.

## 2. Design Philosophy

The previous principle — *Information first. Personality second. Animation
third.* — is too restrictive.

The new hierarchy:

> **Presence first. Information second. Animation communicates state.**

Animation is part of the information architecture, not decoration:

| Visual behaviour | Means |
|---|---|
| Slow breathing | idle |
| Contracted, attentive surface | listening |
| Concentrated internal motion | thinking |
| Orbiting nodes converging | memory retrieval |
| Synchronised oscillation | speaking |
| Fragmented, desaturated geometry | degraded connectivity |

The user should understand MAI's state without reading a label. Text remains
available for precision.

## 3. Product Vision

MAI is a persistent intelligence occupying a digital environment, not a website
with an AI dashboard. The user should hold this mental model:

```
                 MAI
                  │
        ┌─────────┼─────────┐
        │         │         │
     Memory    Cognition   Agency
        │         │         │
        └─────────┼─────────┘
                  │
                Voice
                  │
               System
```

The Entity Core is the visual representation of that central intelligence, and
it persists while the workspace around it changes.

## 4. Primary Experience

```
MAI Entity → Current state → Current workspace → Relevant information → Available action
```

The entity remains present during navigation. It changes scale, position,
intensity, topology, and behaviour per workspace.

## 5. Visual Direction

**Dark, sophisticated, futuristic, not cyberpunk.**

Avoid: generic neon dashboards, excessive purple glow, hacker-terminal
aesthetics, particle soup, giant gradients, oversized glassmorphism cards,
decorative graphs, constant movement.

Use: deep blacks, violet intelligence accent, restrained blue secondary energy,
translucent surfaces, volumetric depth, fine lines, subtle spatial layering,
controlled bloom, sophisticated typography. Expensive, not flashy.

## 6. Entity Anatomy

Five layers:

| Layer | Represents | Reacts to |
|---|---|---|
| 1 — Core | consciousness, active processing, response generation | presence |
| 2 — Inner field | volumetric surface | emotion, energy, cognitive activity |
| 3 — Information field | information flow structure | reasoning direction |
| 4 — Orbitals | memory, goals, active tools, context, entities | activity |
| 5 — Outer field | environmental distortion and bloom | activity level |

Layer 5 **disappears when MAI is inactive** rather than glowing constantly.

## 7. Entity State Machine

```
IDLE ─┬─ LISTENING
      ├─ THINKING ─┬─ MEMORY_RETRIEVAL
      │             ├─ REASONING
      │             └─ TOOL_EXECUTION
      ├─ SPEAKING
      ├─ EMOTIONAL_TRANSITION
      ├─ DEGRADED
      └─ OFFLINE
```

Each state has a distinct visual language. **THINKING is the most important
state** — the user must immediately understand that MAI is processing.

- **Idle** — slow breathing, minimal surface movement, low energy, almost
  imperceptible orbital movement. Alive but relaxed.
- **Listening** — contracts slightly, attentive surface, subtle inward motion.
  *No fake microphone animation*; the state comes from the backend voice pipeline.
- **Thinking** — internal energy accelerates, surface deformation increases,
  orbitals activate, core brightens, directional information flow.

## 8. Memory Retrieval State

Memory representations appear around the entity and move toward the core.

On completion: irrelevant nodes disappear, relevant memories stay briefly
highlighted, and the entity returns to reasoning.

This makes retrieval visible **without exposing private internal reasoning**.

> **Backend dependency:** this state requires `state.retrieval.started` and
> `state.retrieval.completed`. Both were added for v4.0 — see §19.

## 9. Reasoning State

The entity visualises safe cognitive structure:

```
Context → Evidence → Decision → Action
```

The page shows user-facing reasoning summaries. The entity communicates *"MAI is
evaluating information"* — never *"here is MAI's hidden chain of thought."*

> **Backend dependency:** requires `state.reasoning.busy` / `.complete`
> (available) and `state.tool.started` / `.completed` (added for v4.0).

## 10. Speaking State

Synchronised with backend TTS state: core oscillation, surface deformation,
controlled radial pulses, and audio-reactive movement only where backend state
permits it. The visualiser must never imply browser microphone capture.

## 11. Emotional State

Emotion affects the entity subtly — calm is low amplitude; focused is tighter
geometry and faster internal movement; curious is more orbital activity; excited
is higher energy and stronger expansion; concerned is reduced brightness and
altered movement; unavailable collapses toward a minimal state.

**No cartoon emotions. No faces. No emoji-like visual states.**

## 12–21. Workspaces

| Page | Direction |
|---|---|
| **Presence** (12) | Home of the entity. Not a dashboard. Largest visual area, with emotion, goals, activity, memory and system state supporting it. |
| **Chat** (13) | A conversation with the entity. Sessions rail plus the thread; the entity transitions compactly and reacts to thinking, responding, and retrieval. |
| **Memory** (14) | A knowledge environment, not a list. The entity stays visible; the selected memory connects to it. Inspector shows content, provenance, importance, emotional relevance, timestamp, related entities, safe actions. **No raw internal identifiers.** |
| **Knowledge Graph** (15) | The existing Canvas graph, restyled into the same visual language. Stays 2D. **The 3D budget is reserved for MAI itself.** |
| **Reasoning** (16) | Interactive cognitive workspace: current turn, context, evidence, decision, confidence, reflection, outcomes. Raw private chain-of-thought remains prohibited. |
| **Agency** (17) | The action layer around MAI. On an approved action the entity enters an execution state, progress is shown, completion or error is shown, and the entity returns to normal. |
| **Tasks** (18) | Timeline / operational workspace. Entity may stay compact in a corner. Tasks connect to goals, memories, conversations, and actions. |
| **Voice** (19) | One of the strongest uses of the entity. The page exposes backend voice state, STT, TTS, AEC, diarization, emotion, latency, and pipeline availability. `navigator.mediaDevices.getUserMedia()` remains prohibited. |
| **System** (20) | A MAI systems core. Services orbit the entity; clicking one opens conventional, precise diagnostics. |
| **Permissions** (21) | **Deliberately less animated.** The entity becomes visually subdued when permissions are restricted, but security information stays text-first: mode, allowed, blocked, recent audit events, destructive-action warnings. |

## 22. Animation Technology Stack

| Technology | Responsibility |
|---|---|
| HTML | semantic application structure |
| CSS | layout, responsive, typography, UI transitions, accessibility, panels, controls |
| JavaScript | application state and orchestration |
| **GSAP** | primary animation engine — page/entity/panel transitions, timeline choreography, micro-interactions |
| **Three.js** | primary 3D rendering for the Entity only — volumetric sphere, dynamic geometry, camera, lighting, shader materials, post-processing |
| **GLSL** | surface distortion, energy fields, Fresnel, procedural patterns, internal flow, state-dependent deformation |
| Canvas 2D | knowledge graph and lightweight visualisation |
| Web Audio API | audio visualisation only, where backend state makes it meaningful — never a competing microphone pipeline |

## 23. Library Policy

Use a library where it produces a genuinely better experience, not because it
exists.

**Approved:** Three.js (entity), GSAP (orchestration), GLSL (entity effects),
Canvas (graph), Web Audio (where appropriate), native CSS (UI).

**Avoid by default:** Framer Motion, Anime.js, Three.js for every
visualisation, giant particle libraries, unnecessary UI component frameworks,
multiple animation engines.

We do not want GSAP + Framer Motion + Anime.js + CSS animations fighting each
other.

## 24. Entity Architecture

A dedicated entity subsystem owns visual behaviour. The rest of the application
sends it state and never touches Three.js objects directly.

```
api/web/
├── entity/
│   ├── entity-core.js          lifecycle, mount/unmount, public API
│   ├── entity-state.js         state machine, transitions
│   ├── entity-scene.js         scene, camera, lighting, renderer
│   ├── entity-material.js      surface material
│   ├── entity-shaders.js       GLSL
│   ├── entity-orbitals.js      memory / goal / tool orbitals
│   ├── entity-effects.js       bloom, post-processing
│   ├── entity-transitions.js   GSAP timelines
│   └── entity-performance.js   quality tiers, throttling
├── state/
│   └── visual-state-adapter.js   ← implemented
├── workspaces/
├── design/
└── vendor/                       three.js, gsap
```

```js
maiEntity.setState({
  mode: "thinking",
  emotion: "focused",
  energy: null,        // no backend source — stays null
  voice: "idle",
  memoryRetrieval: true,
});
```

The entity decides how that state looks. See [[MAI Cognitive Entity Interface Plan]]
and the boundary rules in `api/web/README.md`.

## 25. State Contract

```json
{
  "presence": "active",
  "cognitiveState": "thinking",
  "emotion": "focused",
  "energy": null,
  "voiceState": "idle",
  "connection": "connected",
  "memoryActivity": true,
  "toolActivity": false,
  "goalActivity": true
}
```

**This is an adapter over actual backend information, not fabricated frontend
state. Missing backend values remain `null` rather than invented numbers.**

## 26. Animation Rules

Animation is state-driven. Never:

```js
setInterval(() => { sphere.rotation.y += 0.01; }, 16);
```

Instead:

```
backend state → visual state adapter → entity state machine → animation timeline → renderer
```

## 27. Performance Architecture

A beautiful entity that destroys GPU performance is not acceptable.

Targets: 60 FPS on supported desktop hardware, graceful reduction on weaker
hardware, reduced-motion support, automatic quality levels.

| Level | Configuration |
|---|---|
| Ultra | high shader quality, higher particle count, post-processing |
| High | default desktop |
| Medium | reduced effects |
| Low | simplified material, minimal particles |

> ⚠️ **Unverified in this environment.** WebGL is present but
> software-rendered (`Microsoft Basic Render Driver` via ANGLE D3D11), so the
> 60 FPS target cannot be validated here. Requires real GPU hardware.

## 28. Reduced Motion

`prefers-reduced-motion` remains mandatory. When enabled: no continuous orbital
movement, no camera movement, no large transitions, minimal breathing, no rapid
flashing. State changes are represented through static visual differences. The
product remains fully usable.

## 29. Responsive Strategy

Desktop is primary. **Tablet** reduces the entity and reorganises panels.
**Mobile** makes the entity a compact presence element that never consumes the
entire interface.

## 30. Navigation

Quieter navigation. The user always knows where they are, what MAI is doing,
and what they can do next. Navigation must not compete with the entity.

```
MAI
├─ Presence, Chat
├─ Knowledge — Memory, Graph
├─ Cognition — Reasoning, Goals, Tasks
└─ System — Voice, System, Permissions
```

The entity provides identity. Navigation provides orientation.

## 31. Page Transitions

One continuous environment. The entity acts as a visual continuity anchor; GSAP
handles the transition. Maximum normal transition **250–400ms**. No cinematic
three-second transitions.

## 32. Command System

The command palette remains and supports navigation, memory search, task
creation, goal selection, safe actions, and authorised system operations — but
does not replace normal navigation.

## 33. Backend Ownership

The backend remains authoritative. The frontend does not create emotions,
memories, goals, reasoning, voice states, system health, or fake cognitive
metrics. **The entity merely visualises state.** This distinction is critical.

## 34. Data Integrity

Every visual state has a provenance chain:

```
Backend → API/Event → State adapter → Entity state → Visual behaviour
```

For example `state.voice.speaking` → `voiceState = "speaking"` → speaking
animation. Never a random animation timer pretending MAI is speaking.

## 35. Event Integration

Reuse the existing event fabric; do not create another event architecture.
Relevant topics: `state.voice.*`, `state.emotion.changed`,
`state.memory.updated`, `state.reasoning.*`, `state.goal.updated`,
`state.agent.completed`, `state.knowledge.updated`, `state.belief.updated`,
plus the retrieval and tool projections described in §19.

## 36. Migration Strategy

Keep everything already built: authentication, routing, chat, memory, reasoning,
tasks, agency, system, permissions, voice, graph, event infrastructure, API
contracts, accessibility work, performance work, and tests.

**Replace the visual/product layer, not the backend architecture.**

> **Current tree state.** The v3.x Cognitive Desktop presentation layer was
> reverted on 2026-09-26; `api/static/` is the M0 foundation (`fa36089`) and the
> M0 dashboard at `/desktop` is the active interface. The v3.x work is preserved
> on branch `cognitive-desktop-v3`. The backend projections in §19 and the
> `api/web/` boundary survive the revert, so this plan starts from the M0
> interface rather than replacing v3.x. Treat v3.x as a reference
> implementation of accessibility, formatter, and graph-performance contracts
> that can be lifted selectively, not as the thing being replaced.

## 19. Backend Gaps Closed for v4.0

Two of the plan's most distinctive behaviours had no state-bus signal. The UI
subscribes exclusively to `state.*`, while retrieval and tool activity existed
only as post-hoc `data.*` records — which cannot express *"MAI is retrieving
right now."*

Added in `core/event_specs.py` and published from the owning subsystems:

| Topic | Publisher | Payload | Published by |
|---|---|---|---|
| `state.retrieval.started` | `memory` | — | `knowledge/retriever.py` |
| `state.retrieval.completed` | `memory` | `count` | `knowledge/retriever.py` |
| `state.tool.started` | `agency` | `name` | `agency/registry.py` |
| `state.tool.completed` | `agency` | `name`, `success`, `duration` | `agency/registry.py` |

Payloads are deliberately minimal. Retrieval never carries the query or
retrieved content; tool events never carry arguments, results, or the error
string that `data.tool.called` carries for diagnostics. Phatic queries and empty
queries emit nothing, so greetings do not make the entity flicker.

Covered by `tests/test_knowledge.py::TestRetrievalStateProjections` and
`tests/test_agency.py::TestToolStateProjections`.

## 37–43. Implementation Phases

Ordered by dependency and value. Each phase is independently shippable and must
keep every existing gate green.

### Phase 5 — Entity Foundation
Three.js scene, camera, lighting, base sphere, shader material, entity state
machine, GSAP integration, quality management, reduced-motion behaviour, static
fallback, and the visual state adapter (already delivered).

**Success:** MAI visibly transitions between idle, listening, thinking,
speaking, degraded, and offline — and the full backend suite still passes with
the entity mounted and with WebGL disabled.

### Phase 6 — MVP: Entity in Presence *(MVP — the highest-value slice)*
Replace the Presence page around the entity: large entity, real presence state,
emotion, goals, recent activity, memory activity, system state.

**Success:** "Presence feels like encountering MAI rather than opening a
dashboard," with all v3.2 gates still passing.

### Phase 7 — Chat + State Plumbing
Compact persistent entity, state synchronisation, streaming animation, memory
retrieval visualisation, tool execution visualisation, conversation UI, context
inspector.

**Success:** "Chat feels like interacting with an intelligent entity rather than
submitting messages to a web form."

### Phase 8 — Memory + Knowledge
Memory visualisation, retrieval animations, entity relationships, graph
integration, selected-memory connection to MAI.

**Success:** "The relationship between MAI and its memory becomes visually
understandable."

### Phase 9 — Cognition
Redesign Reasoning, Agency, and Tasks around the entity as the central
reference.

**Success:** "Cognitive state and action state feel like parts of one system."

### Phase 10 — Voice + System
Speaking and listening entity states, voice diagnostics, system orbitals,
service visualisation.

**Success:** "Voice and system health feel native to the MAI environment."

### Phase 11 — Final Visual Polish
Only after functionality works: shader refinement, lighting, transitions,
sound/visual synchronisation, responsive refinement, GPU profiling,
accessibility, visual consistency.

> **Do not polish shaders before the state model works.**

## 44. Testing

Existing testing remains. Add entity tests for state transitions, missing state,
rapid state changes, reconnect, degraded state, reduced motion, and quality
switching.

Browser tests verify: the entity loads, does not block the shell, the page stays
functional if WebGL fails, the Canvas fallback works, no console errors, no
microphone request, and navigation preserves state.

**If WebGL is unavailable the application must never become unusable** — a
static representation is shown instead.

## 45. Security

The entity must never reveal private prompts, raw chain-of-thought, secrets,
tokens, internal credentials, or unauthorised private memory content. Visual
abstraction is a security feature: *"Retrieving relevant memories"* is
preferable to displaying internal retrieval traces.

## 46. What We Explicitly Reject

❌ Generic AI dashboard (cards everywhere) · ❌ Anime clone · ❌ Particle
wallpaper · ❌ Giant glowing orb that only rotates · ❌ Cyberpunk control panel ·
❌ Fake consciousness (invented emotions, energy percentages, intelligence
meters) · ❌ Cinematic UI · ❌ 3D everywhere

## 47. The Design Test

Every major animation must answer: **what does this animation tell me about MAI?**

- *"Nothing, it just looks cool"* → remove it.
- *"MAI is retrieving memories"* → keep it.
- *"MAI is speaking"* → keep it.
- *"MAI's system connection degraded"* → keep it.

## 48. Final Product Structure

```
                         MAI
                          ◉
              ┌───────────┼───────────┐
              │           │           │
           Memory      Cognition    Agency
              │           │           │
              └───────────┼───────────┘
                          │
                        Voice
                          │
                       System

       ┌──────────────────────────────────────┐
       │              WORKSPACE               │
       │   Information appropriate to         │
       │        current context               │
       └──────────────────────────────────────┘
```

**The workspace changes. The MAI entity persists.** That is the key design
decision.

## 49. Architecture Decision

| | |
|---|---|
| Previous | MAI Cognitive Desktop — Quiet Intelligence |
| **New** | **MAI Cognitive Entity Interface — Living Intelligence** |

The product is no longer primarily a desktop dashboard. It is a visual
environment around MAI itself.

The completed backend, API contracts, authentication, memory, reasoning, agency,
voice, graph, accessibility, and testing work remain the foundation. The major
change is the presentation layer — Three.js + GLSL + GSAP + HTML/CSS/JavaScript
— with the MAI Entity as the persistent visual representation of the
intelligence.

New presentation code lives in `api/web/`, governed by the boundary rules in
`api/web/README.md`. The Python subsystems are **not** relocated.

## Success Metrics

**Primary**
- Existing gates never regress: the full backend suite (1,830 passing today), plus
  whatever frontend contracts the interface phase introduces.
- Entity frame time p95 under budget on supported hardware.
- Every entity state is traceable to a `state.*` event (audited, not asserted).

**Secondary**
- Time to first meaningful state on Presence.
- WebGL initialisation failure rate.
- Pages passing all gates with the entity unmounted.

**Failure indicators**
- Any fabricated value reaching the entity — a non-null field with no backend
  source.
- The entity blocking shell interaction or navigation.
- A stuck active state after a dropped completion event.
- Users describing the entity as decoration rather than information.

**Acceptance criteria**
- [ ] MAI transitions visibly between all nine entity states
- [x] Retrieval and tool execution are observable as in-progress work
- [x] The state adapter never invents a value
- [x] The application is fully usable with WebGL unavailable
- [ ] `prefers-reduced-motion` fully suppresses continuous motion
- [ ] Entity frame time meets budget on supported hardware

## Related

- [[Complete Redesign Implementation Plan]] — superseded v3.x direction
- [[Event Fabric Architecture]] — `state.*` versus `data.*`
- [[Testing Strategy]] — the gate every phase must keep green
- [[Memory Pipeline]], [[Voice Pipeline]] — backend authority
- [[08-API Native & Surface]] — served routes
