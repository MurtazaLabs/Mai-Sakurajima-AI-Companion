---
document_type: architecture-decision-record
project: Mai AI
title: Presentation layer restructure and entity-as-presentation-only
status: accepted
version: 1.0.0
last_updated: 2026-09-26
tags:
  - mai-ai
  - adr
  - architecture
  - frontend
  - entity
related:
  - "[[MAI Cognitive Entity Interface Plan]]"
  - "[[Complete Redesign Implementation Plan]]"
  - "[[Event Fabric Architecture]]"
  - "[[08-API Native & Surface]]"
  - "[[09-Events & Data Flow]]"
  - "[[Testing Strategy]]"
---

# ADR — Presentation Layer Restructure and Entity-as-Presentation-Only

**Status:** Accepted · **Date:** 2026-09-26 · **Supersedes:** the v3.x
"Quiet Intelligence" presentation direction in [[Complete Redesign Implementation Plan]]

## Context

A v3.x "Cognitive Desktop" presentation layer was built and verified on 2026-09-26:
2,100 tests passing, 15/15 acceptance criteria, a 231-check accessibility
contract, a formatter contract, a graph performance budget, and a visual
sign-off across all ten shell pages.

**On the same day the dashboard direction was abandoned and `api/static/` was
restored to the M0 foundation (`fa36089`).** The v3.x work is not lost — it is
committed on branch `cognitive-desktop-v3` (commit `a2ac347`) and can be
restored in one command. It is simply not in the tree.

What this ADR governs is therefore forward-looking: it decides where the *next*
presentation layer lives, and it records the backend work that survives the
revert.

A new product direction — [[MAI Cognitive Entity Interface Plan]] — replaces
the presentation layer with a persistent 3D entity built on Three.js, GLSL, and
GSAP.

Two decisions were open at the time of this ADR:

1. **Where the new frontend lives.** A proposal was made to build
   *"everything in the API folder."*
2. **How the entity learns MAI's state.** Two of the plan's most distinctive
   behaviours — memory retrieval and tool execution — had no signal on the
   `state.*` bus the UI is required to consume.

## Decision 1 — A dedicated `api/web/` boundary, not a repository restructure

New presentation code lives in **`api/web/`**, governed by
`api/web/README.md`.

The Python subsystems (`core/`, `memory/`, `knowledge/`, `voice/`, `agency/`,
`app/`, `config/`, `reasoning/`, `prompt/`, `llm/`, `execution/`,
`observability/`, `native/`, `plugins/`) are **not** relocated.

### Why the "everything in API folder" proposal was rejected

Measured at the time of the decision:

```
api/         24 py + 132 static files   ← HTTP interface + served frontend
core/        72 py    memory/   27 py    knowledge/ 28 py    voice/   33 py
agency/      12 py    config/   21 py    app/       18 py    plugins/ 19 py
prompt/       7 py    reasoning/ 5 py    llm/        4 py    native/   6 py
```

1. **It conflates the interface with the intelligence.** `api/` is the HTTP
   adapter layer. The entity renders a sphere and has no relationship to HTTP.
   Moving `core/` beneath `api/` makes that boundary *less* clear, not more.
2. **It violates the project's own architecture rules.** AGENTS.md defines
   `api/` as the API layer and the fourteen subsystems as separate modules with
   explicit boundaries.
3. **It costs roughly 250 file moves with the entire test suite as the
   regression surface, for no product value.** Cohesion is a goal; a
   fourteen-subsystem migration is not how it is achieved.
4. **It amplifies an unresolved governance conflict.** AGENTS.md states that no
   new subfolders are created under `api/static/{css,js,img,assets}` — a rule
   the existing `js/shell/`, `js/pages/`, and `js/features/chat/` already
   violate. A dedicated `api/web/` root resolves that conflict by giving the
   new code a legitimate home, rather than adding a tenth exception.

### Why `api/web/` and not a repository-root `web/`

A root-level `web/` was considered and remains defensible. `api/web/` was chosen
because the API server already owns static delivery: `api/static_serving` and
the `StaticFiles` mount serve the frontend, so putting the new interface under
`api/` keeps one delivery path, one CSP, and one service-worker scope. The
entity is namespaced as a distinct module inside that path, so the logical
boundary is preserved even though the physical one is nested.

`api/README.md` states the separation explicitly so the nesting is not mistaken
for a claim that the entity is HTTP-related.

### Revisit trigger: a build step, not reader confusion

The one concern with nesting the interface under `api/` is that a future
contributor may read the entity as part of the HTTP layer. That is a
documentation problem, and `api/README.md` plus `api/web/README.md` resolve it.

The condition that would make this decision **wrong** is structural:

> **If the interface gains a build step — a bundler, a transpiler, or any
> pipeline that generates `api/web/` output — relocate it to a repository-root
> `web/`.**

A build pipeline wants to own its source and output directories outright, and
generating files inside a Python package creates artifacts that packaging,
test collection, and static mounts all have to be taught to ignore. Until then,
a bundler would be the only reason to move, and adding one is itself a decision
that should be argued on its own merits.

**This trigger is recorded so the question is reopened by evidence rather than
re-argued from memory.** Moving later is contained: at the time of writing,
`api/web/` is referenced by one module import in
`tests/test_entity_state.py` and by documentation, so relocation is a directory
move plus an import path — provided it happens before Phase 5 spreads references
across workspaces.

## Decision 2 — The entity is presentation-only

The entity renders a normalised visual state and **decides nothing**. All
behaviour flows one way:

```
Backend → API/Event → visual state adapter → entity state → visual behaviour
```

Rules, each traceable to a defect or a rejection in v4.0:

| Rule | Source |
|---|---|
| Never invent a value; unknown stays `null` | v4.0 §25, §33, §34 |
| No `setInterval` animation that no event justifies | v4.0 §26, §46, §47 |
| Entity is additive; shell and workspaces work without it | v4.0 §28, §44 |
| No private prompts, chain-of-thought, secrets, or unauthorised memory | v4.0 §9, §45 |
| One animation engine: GSAP orchestrates, Three.js owns the entity, CSS owns UI | v4.0 §22, §23 |
| Vendored dependencies only, so the PWA keeps working offline | v4.0 §29, [[Event Fabric Architecture]] |
| No new event architecture or parallel state store | v4.0 §35 |

`null` and `false` are deliberately different. "Unknown" is not "idle", and
collapsing them would let the entity present a state the backend never reported.

## Decision 3 — Retrieval and tool execution are projected onto the state bus

`state.retrieval.*` and `state.tool.*` were added to `core/event_specs.py` and
are published from the owning subsystems (`knowledge/retriever.py`,
`agency/registry.py`).

**Why.** The UI consumes `state.*` exclusively, a rule established when the
event fabric was built. Retrieval and tool activity existed only as `data.*`
records — `data.retriever.results`, `data.tool.called`, `data.agent.step` —
which are retrospective. They can report that retrieval *happened* but cannot
express *"MAI is retrieving right now"*, which is precisely the distinction the
entity needs in order to show progress honestly.

**Why not the alternative.** Building the memory-retrieval visualisation on the
existing `data.*` events would have required either subscribing the UI to
`data.*` — breaking the fabric's separation — or inferring activity from
timestamps, which is fabrication. Both are prohibited by v4.0 §33.

### Payload minimisation

The projections carry the minimum a presentation layer needs:

| Topic | Payload | Deliberately excluded |
|---|---|---|
| `state.retrieval.started` | — | query text |
| `state.retrieval.completed` | `count` | query text, retrieved content |
| `state.tool.started` | `name` | arguments, results |
| `state.tool.completed` | `name`, `success`, `duration` | arguments, results, **error string** |

`data.tool.called` continues to carry the error string for diagnostics; the
state projection deliberately does not, so internal failure detail cannot reach
the interface.

Phatic and empty queries publish nothing, so ordinary greetings do not make the
entity flicker a retrieval.

## Consequences

**Positive**
- The entity can be built truthfully, with no fabricated state.
- The Python architecture and its backend tests are untouched.
- The `api/static/` folder-rule conflict stops growing.
- Retrieval and tool events also serve the existing text-first UI, so the
  projections are not entity-specific.

**Negative / accepted**
- `api/web/` nests the frontend under the API layer; a reader may expect the
  entity to be HTTP-related. Mitigated by `api/README.md`, the boundary README,
  and the build-step revisit trigger above.
- Four new event types must stay in sync with the event registry and the
  metadata contract.
- The 60 FPS target cannot be validated in the current environment, where WebGL
  is software-rendered. Requires real GPU hardware.

**Neutral**
- `energy` has no backend source and remains `null`. If a real source is added
  later it must be measured, not chosen for visual effect.

## Decision 4 — The repository manifest states the real stack

The root `package.json` previously declared the **rejected** v1/v2 stack —
`@react-three/fiber`, `@react-three/drei`, nine `@radix-ui/*` packages,
`animejs`, and `motion` — while **omitting `three` entirely** and never
declaring `gsap`, the one animation engine v4.0 §22 requires.

That state was an active hazard rather than untidy bookkeeping. Anyone opening
the repository would reasonably conclude the frontend stack was React plus
Three.js, and an agent would reach the same conclusion. `node_modules` made it
worse: 68 installed packages meant `animejs` and `motion` were importable, and
the install was itself broken because `@react-three/fiber` requires `react` as
a peer that was not present.

v4.0 §23 exists specifically to prevent GSAP, Framer Motion, Anime.js, and CSS
animations competing over the same properties. The manifest was making the
violating path the path of least resistance.

The manifest now declares exactly the two approved runtime dependencies —
`three@^0.170.0` and `gsap@^3.15.0` — and carries a `maiStackPolicy` block
naming the absent packages and the reason. The rejected packages were removed
and the tree verified:

```
$ npm ls --depth=0
mai-ai@4.0.0
+-- gsap@3.15.0
`-- three@0.170.0
```

**Why this is an ADR and not a chore.** A dependency manifest is a statement of
architectural intent that every future contributor reads before writing code.
Leaving it contradicting the architecture document is how a policy stops being
enforced.

Note that `three@0.170.0` is pinned to what was verified present; `0.186.1` is
current. The bump is deliberately not taken here — the entity does not exist yet,
so there is nothing to verify a newer major-minor against.

## Verification

| Concern | Gate |
|---|---|
| Projections registered and authorised | `core/event_specs.py` catalog, `tests/test_event_registry.py` |
| Retrieval lifecycle, phatic exclusion, cache hits, no payload leak | `tests/test_knowledge.py::TestRetrievalStateProjections` |
| Tool lifecycle, failure path, no error-string leak | `tests/test_agency.py::TestToolStateProjections` |
| Adapter never invents, never strands, never leaks | `tests/test_entity_state.py` |
| Declared frontend stack matches the architecture | `npm ls --depth=0` shows only `gsap` and `three` |
| No regression | full suite: 1,830 passing |

## Related

- [[MAI Cognitive Entity Interface Plan]] — v4.0 product and implementation plan
- [[Complete Redesign Implementation Plan]] — superseded v3.x direction
- [[Event Fabric Architecture]] — `state.*` versus `data.*` contract
- [[08-API Native & Surface]] — served routes and static delivery
- [[09-Events & Data Flow]] — event pipeline
- [[Testing Strategy]] — gate every phase must keep green
