---
document_type: feature-plan
project: Mai AI
title: MAI Cognitive Desktop Product and Implementation Plan
status: superseded
version: 3.2.0
last_updated: 2026-09-26
superseded_by: "[[MAI Cognitive Entity Interface Plan]]"
superseded_on: 2026-09-26
tags:
  - mai-ai
  - product-strategy
  - frontend
  - cognitive-desktop
  - vanilla-javascript
related:
  - "[[Native OS Bridge Architecture]]"
  - "[[Event Fabric Architecture]]"
  - "[[08-API Native & Surface]]"
  - "[[Memory Pipeline]]"
  - "[[Voice Pipeline]]"
  - "[[Testing Strategy]]"
---

# MAI Cognitive Desktop — Product and Implementation Plan

> **⚠️ SUPERSEDED — 2026-09-26.** The product direction in this document has
> been replaced by [[MAI Cognitive Entity Interface Plan]] (v4.0,
> *Living Intelligence*).
>
> **This document is retained as a record of completed work, not as current
> direction.** Phases 0–4 described here were delivered and verified: 2,068
> backend tests, 15/15 acceptance criteria, a 229-check accessibility contract, a
> formatter contract, a graph performance budget, and a visual sign-off across
> all ten shell pages. That work is the foundation the v4.0 presentation layer
> is built on, and none of it is discarded.
>
> What changes: the **presentation layer only**. New presentation code lives in
> `api/web/` under the rules in that folder's README. The backend, API
> contracts, authentication, memory, reasoning, agency, voice, graph,
> accessibility work, and tests all remain.
>
> See also [[ADR Presentation Layer Restructure]].

## Executive Decision

Adopt the **MAI Cognitive Desktop** direction, but implement it as a calm cognitive workstation rather than a simulated operating system.

The product should expose MAI's memory, relationship state, reasoning, agency, voice, knowledge, and system health through a persistent desktop shell. It should not reproduce a futuristic dashboard, a particle system, a giant AI orb, or a collection of unrelated animated pages.

The design rule is:

> Information first. Personality second. Animation third.

The first useful milestone is a vertical slice containing:

1. Persistent shell
2. Presence
3. Streaming Chat
4. Memory search and detail inspection

The remaining workspaces are delivered incrementally after this core loop is proven.

## 1. Product Discovery

### Problem

MAI has a deep backend, but its capabilities are not yet presented as one coherent operating environment. Users must move between pages and interpret disconnected widgets instead of seeing the current state, conversation context, relevant memory, reasoning, and available actions in one place.

### Primary User

Murtaza as the owner and daily operator of MAI.

### Secondary User

A technically capable user who wants to understand, configure, and operate a persistent AI companion.

### Pain Point

The current experience risks feeling like a website that displays AI-related data rather than a workstation that helps the user converse, remember, reason, and act with an AI system.

### Desired Outcome

The user can:

- Understand MAI's current state at a glance.
- Hold a continuous conversation.
- Inspect the memory and reasoning behind a response.
- See active goals and available tools.
- Act without losing navigation context.
- Trust that displayed values come from real backend data.

## 2. Product Principles

1. **Information first** — expose useful state before visual spectacle.
2. **Personality in behavior** — express MAI through language, timing, memory, and emotional continuity rather than decorative effects.
3. **Persistent context** — navigation must not make the user feel they left the application.
4. **Real data only** — no fabricated metrics, inferred percentages, or fake system states.
5. **Progressive disclosure** — show a useful summary first and reveal detail on demand.
6. **Calm by default** — density is available, but the default experience is composed and readable.
7. **Functional motion** — animation communicates state changes; it does not exist to fill space.
8. **Backend ownership** — the frontend presents and controls existing systems; it does not create parallel AI pipelines.
9. **Graceful degradation** — loading, empty, stale, unauthorized, unavailable, and error states are first-class UI.
10. **Incremental migration** — preserve existing routes and backend behavior until acceptance is complete.

## 3. Product Scope

### In Scope

- Persistent desktop-style shell.
- Grouped navigation across five cognitive areas.
- Presence overview.
- Streaming conversation workspace.
- Context and relationship inspector.
- Memory search, list, detail, provenance, and safe actions.
- Reasoning notebook and reflection views.
- Goals, tasks, tools, and intent queue.
- System health, services, plugins, and configuration.
- Permission modes and audit visibility.
- Backend-owned voice status and controls.
- 2D Canvas knowledge graph.
- Responsive layouts and keyboard accessibility.
- Native browser modules, CSS, and restrained transitions.

### Explicit Non-Goals

- React, React DOM, TypeScript, Tailwind, Framer Motion, Motion, Anime.js, Three.js, Lucide, Zustand, TanStack Query, React Router, Jest, Cypress, or a frontend build framework.
- A giant animated AI orb or particle system.
- Mandatory 3D graph rendering.
- Decorative page transitions.
- A second browser-side voice pipeline.
- Browser microphone capture through `getUserMedia()`.
- Fabricated metrics or placeholder "live" data.
- A claim that the browser interface is a full native operating system.
- Removing legacy routes or pages before the new experience is accepted.

## 4. Information Architecture

The navigation is grouped by cognitive function, while existing routes remain valid for compatibility.

| Area | Routes | Primary workspace | Typical inspector |
| --- | --- | --- | --- |
| Home | `/`, `/presence` | Current state and recent activity | Selected state or activity item |
| Conversation | `/chat` | Sessions and conversation | Relationship, memory, goals, tools |
| Knowledge | `/memory`, `/graph` | Searchable memory and entity network | Memory or entity detail |
| Cognition | `/reasoning`, `/agency`, `/tasks` | Decisions, goals, tasks, and actions | Selected thought, goal, or task |
| System | `/voice`, `/system`, `/permissions` | Health, voice, configuration, and safety | Selected service, setting, or permission |

### Navigation Rules

- Group navigation by user intent, not by backend module name.
- Keep route paths stable even when labels are reorganized.
- Show only one active shell.
- Never mount the legacy and redesigned shells simultaneously.
- Preserve deep links to pages and selected resources where practical.
- Use the command palette for navigation and safe actions, not as a replacement for clear navigation.

## 5. Persistent Shell

The shell is the stable frame around every workspace.

```text
┌──────────────────────────────────────────────────────────────┐
│ MAI                                  Status       Time      │
├──────────────┬───────────────────────────────┬──────────────┤
│ Navigation   │ Active workspace              │ Inspector    │
│              │                               │              │
│              │                               │              │
│              │                               │              │
├──────────────┴───────────────────────────────┴──────────────┤
│ Connection state · Active goal · Voice state · Version      │
└──────────────────────────────────────────────────────────────┘
```

### Shell Components

- **Sidebar** — grouped navigation, active route, compact status.
- **Topbar** — MAI identity, page context, global actions, connection state.
- **Workspace** — the main task area.
- **Contextual inspector** — details for the selected resource when useful.
- **Command bar** — keyboard-first navigation and safe actions.
- **Status strip** — connection, voice, active goal, and version state.

### Shell Rules

- The shell renders before slow API responses.
- The inspector is contextual; it is not mandatory on every page.
- On narrow screens, the inspector becomes a drawer.
- Page navigation preserves scroll position where practical.
- API failures update the affected workspace without destroying the shell.
- Connection state distinguishes connected, reconnecting, degraded, and offline.

## 6. Page Blueprints

### Presence

Presence is a desktop overview, not a hero section.

Display:

- Current emotion, energy, focus, and relationship summary when available.
- Connection and voice state.
- Active goals.
- Recent memory, reflection, and activity events.
- Small status visualization when it communicates real state.

Do not display invented percentages or duplicate metrics. Every value must be traceable to a backend field or clearly labeled local UI state.

### Chat

Chat is the flagship daily-driver workspace.

Layout:

```text
Sessions │ Conversation │ Context / Relationship / Memory / Goals
```

Required behavior:

- Streaming response.
- Session persistence.
- Retry and cancellation.
- Token refresh during an active session.
- Tool/action feedback.
- Context inspector with relevant memories, goals, and relationship state.
- Voice toggle that controls the backend pipeline only.

### Memory

Memory is a knowledge workstation.

Layout:

- Search and filters.
- Dense memory list.
- Selected memory inspector.
- Provenance, importance, emotional weight, and connections when returned by the backend.

Actions such as archive or forget must be explicit, permission-aware, auditable, and undoable where the backend supports it.

### Knowledge Graph

The graph is a 2D Canvas workspace by default.

Required behavior:

- Zoom and pan.
- Node and edge selection.
- Search-to-expand.
- Type filters.
- Relationship strength.
- Keyboard-accessible list fallback.

Three.js is not required. WebGL or another renderer may be considered only after profiling demonstrates a need.

### Reasoning

Reasoning is an engineering notebook.

Display:

- Current turn input.
- Relevant context.
- Decision and confidence.
- Reflection history.
- Repeated patterns and outcomes.

Internal implementation fields must not leak raw packet JSON, private prompts, or unbounded internal traces into the user-facing response.

### Agency

Agency is a control room.

Display:

- Autonomy mode.
- Active goals and progress.
- Available tools and permissions.
- Intent queue and approval state.
- World entities when useful.

Actions that affect the operating system must show approval and execution state.

### Tasks

Tasks are operational work items.

Display:

- Today, upcoming, in progress, and completed groups.
- Priority, deadline, related goal, and subtasks.
- Detail inspector.
- Clear completion, cancellation, and recovery states.

### Voice

Voice is deliberately minimal and backend-owned.

Display:

- Backend state: idle, listening, thinking, speaking, unavailable.
- STT, TTS, AEC, diarization, emotion, and latency details when available.
- Voice toggle and pipeline test controls.
- Optional state-driven waveform visualization.

Prohibited:

- `navigator.mediaDevices.getUserMedia()`.
- Browser microphone capture.
- Browser-side STT or wake-word detection.
- A second competing voice pipeline.

The control should be labeled **Test voice pipeline**, not **Test microphone**, unless the backend explicitly exposes a daemon-owned microphone test.

### System

System is an engineering control center.

Display:

- Health summary.
- Service status.
- LLM, STT, TTS, memory, and graph health when available.
- Plugins and configuration.
- Clear source and freshness for metrics.

### Permissions

Permissions is a safety and trust surface.

Display:

- Current permission mode.
- Allowed and blocked operations.
- Recent audit events.
- Destructive-action warnings.

Never hide security state behind visual decoration.

## 7. Visual System

### Base Tokens

```css
:root {
  --bg-primary: #0A0B0F;
  --bg-secondary: #0E1015;
  --bg-panel: #12141A;
  --bg-card: #181B22;
  --bg-elevated: #1D2028;

  --accent-primary: #7C5CFF;
  --accent-soft: #9B86FF;
  --accent-blue: #6EA8FF;

  --success: #72D6A5;
  --warning: #E8B86A;
  --danger: #E87575;

  --text-primary: #F2F5FA;
  --text-secondary: #A6B0BF;
  --text-muted: #6E7785;

  --border-subtle: rgba(255, 255, 255, 0.07);
  --radius-sm: 8px;
  --radius-md: 10px;
  --radius-lg: 12px;

  --transition-fast: 150ms ease-out;
  --transition-normal: 180ms ease-out;
  --transition-slow: 250ms ease-out;

  --font-sans: Inter, Manrope, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", Consolas, monospace;
}
```

### Visual Rules

- Use violet for identity, selection, active state, and intelligence/processing state.
- Use blue as a restrained secondary accent.
- Keep most surfaces neutral.
- Avoid gradients as decoration.
- Avoid glow, particles, oversized orbs, and excessive borders.
- Use thin borders and compact typography to create hierarchy.
- Preserve contrast at all density levels.
- Use semantic colors consistently for healthy, warning, danger, and unavailable states.

### Density Modes

- **Calm** — default; more whitespace and fewer simultaneous details.
- **Compact** — power-user mode; denser rows and metadata.

Persist the preference locally. The product must remain usable in both modes.

## 8. Motion System

Motion is functional and restrained.

### Allowed Uses

- Hover and focus feedback.
- Panel open/close.
- Inspector selection.
- State indicator changes.
- Message insertion.
- Small voice waveform movement when driven by backend state.
- Canvas graph interaction and selection.

### Motion Budget

- Hover/focus: 150ms.
- Panel/inspector transition: 180ms.
- Larger state transition: 250ms maximum.
- No continuous decorative background animation.
- Respect `prefers-reduced-motion`.
- Do not animate critical warnings in a way that delays comprehension.

## 9. Frontend Architecture

### Responsibilities

- **HTML** owns semantic structure and static page regions.
- **CSS** owns layout, hierarchy, responsive behavior, and restrained transitions.
- **JavaScript** owns state, API access, events, dynamic rendering, and interaction.
- **Canvas** is reserved for graph and signal visualization where it provides clear value.
- **Backend** remains the source of truth for AI, memory, voice, goals, and system state.

### Module Boundaries

The frontend must not become one giant `app.js`. Maintain separate responsibilities for:

- Application bootstrap.
- API client and authentication.
- Event bus.
- History router.
- Shell components.
- Command palette.
- Presence state and rendering.
- Chat store, transport, renderer, sessions, context, and voice controls.
- Memory list, search, detail, and actions.
- Reasoning notebook and reflection views.
- Agency, tasks, system, and permissions views.
- Graph model, layout, renderer, camera, interaction, and inspector.
- Voice state and visualization.

The exact directory layout is governed by the repository's `AGENTS.md`. Do not create additional folders under `css/`, `js/`, `img/`, or `assets/` without resolving the existing layout policy conflict.

### State Model

Separate these concerns:

- **Server state** — API responses, SSE events, persistence.
- **Session state** — active conversation, selected memory, selected task, inspector selection.
- **Connection state** — connected, reconnecting, degraded, offline.
- **UI preferences** — density, panel state, theme and accessibility preferences.
- **Ephemeral interaction state** — hover, focus, menu open, input draft.

Do not store domain data in localStorage. Use localStorage only for tokens and UI preferences unless a documented product decision allows more.

### Rendering Rules

- Render loading, empty, stale, unauthorized, unavailable, and error states.
- Preserve the shell when a workspace request fails.
- Escape user-controlled content before inserting it into HTML.
- Use progressive rendering for long lists.
- Batch streaming DOM updates.
- Provide accessible text alternatives for Canvas visualizations.

## 10. Data and API Contract

The frontend is a presentation and control layer. Every displayed value must map to a documented backend field or be clearly labeled as local UI state.

### Contract Rules

1. Inventory every displayed value before implementing a widget.
2. Confirm the endpoint and response field.
3. Handle missing, null, stale, and unauthorized values explicitly.
4. Show provenance and freshness for memory, system, and relationship data where available.
5. Do not invent fallback percentages or health states.
6. If an endpoint is unavailable, show a degraded state rather than fabricated data.
7. Keep API-specific mapping in page modules, not in the generic API client.

### Primary Endpoint Map

| Area | Endpoints |
| --- | --- |
| Authentication | `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/auth/me` |
| Presence | `GET /api/status`, `GET /api/consciousness`, `GET /api/health/metrics`, `GET /api/system/health`, `GET /api/goals`, `GET /api/memory/stats`, `GET /api/inspector/records`, `GET /api/reasoning/reflect/history` |
| Chat | `POST /api/chat`, `POST /api/chat/stream`, `POST /api/chat/wake` |
| Memory | `GET /api/memory`, `GET /api/memory/stats`, `GET /api/memory/timeline` |
| Graph | `GET /api/graph`, `POST /api/graph/prune` |
| Reasoning | `GET /api/reasoning/thoughts`, `GET /api/reasoning/reflect`, `GET /api/reasoning/reflect/history` |
| Agency | `GET /api/goals`, `GET /api/tools`, `GET /api/world/entities` |
| Tasks | `GET /api/tasks`, task create/complete/cancel/activate/subtask routes |
| Voice | `GET /api/voice/status`, `GET /api/voice/details`, `POST /api/voice/toggle` |
| System | `GET /api/system/health`, `GET /api/system/plugins`, `GET /api/system/about`, `GET /api/config`, `POST /api/config/update` |
| Permissions | `GET /api/permissions`, `POST /api/permissions/mode` |
| Realtime | `GET /api/stream` and `WS /ws` where supported |

Endpoint availability must be verified during implementation. The table is a contract map, not permission to assume every response shape is stable.

### Event Topics

Use the existing event fabric and `state.*` projection topics for UI state. Do not create a second event vocabulary in the frontend.

Relevant categories include:

- `state.voice.*`
- `state.emotion.changed`
- `state.memory.updated`
- `state.reasoning.*`
- `state.goal.updated`
- `state.agent.completed`
- `state.knowledge.updated`
- `state.belief.updated`

See [[Event Fabric Architecture]] for the event model.

## 11. Current Implementation Checkpoint

> **⚠️ The checkpoint below describes work that is NOT in the current tree.**
> On 2026-09-26 the v3.x presentation layer was reverted and `api/static/` was
> restored to the M0 foundation (`fa36089`). The entire v3.x frontend — the
> redesigned shell and pages, the accessibility contract, `format.js`, and the
> Canvas graph work — lives on branch **`cognitive-desktop-v3`** (commit
> `a2ac347`), not on `master`.
>
> What **did** survive on `master`: all backend work, the `state.retrieval.*` and
> `state.tool.*` projections, and `api/web/`. See
> [[ADR Presentation Layer Restructure]].
>
> Read the rest of this section as a record of verified work, useful as a
> reference for anything lifted forward — not as a description of the current
> frontend.

The redesign is not starting from zero. Preserve and validate the work already completed:

- M0 design tokens, reset, typography, layout, utilities, and state primitives.
- API client with bearer authentication and refresh handling.
- Event bus, History API router, keyboard utilities, accessibility utilities, and login page.
- Static shell and redesigned Presence, Chat, Memory, Reasoning, Agency, Tasks, System, Permissions, and Voice pages.
- Chat feature modules and real API-backed page controllers.
- Authenticated router guard using the shared API client and bearer headers.
- Static-page navigation with one router start and full-page route transitions.
- EventBus detail payload contract aligned with shell and Chat consumers.
- Chat SSE parsing aligned to the backend `token` frame, with in-memory message updates, one refresh retry, cancellation, and no fallback after partial output.
- Memory timeline/search response contracts normalized for list and detail views.
- Tasks now consume the existing Goal response contract and submit the supported description/priority fields.
- Reasoning now boots through the canonical app shell, uses `thoughts`/`history` envelopes, renders actual trace fields, normalizes Unix timestamps, and provides explicit page states.
- Reasoning REST routes now require the shared auth dependency and return bounded public DTOs without private monologue/speech-plan fields.
- Reasoning, Memory, and Tasks now react to shared `workspace:refresh` invalidation events.
- Agency now renders real goals/tools/entities, marks unsupported autonomy and intent-queue controls honestly, and reacts to refresh events.
- System now renders verified health, plugin, configuration, and about data with working plugin load/unload actions.
- Permissions now uses the backend `safe`/`advanced`/`admin` contract and renders read-only policy/audit data.
- Voice now has a redesigned backend-owned control page with no browser microphone capture; the browser only reads status/details and toggles the daemon.
- Agency, System, Permissions, and Voice routes now boot through the canonical app shell and protected read endpoints.
- Graph now boots through the canonical shell with a native 2D Canvas view, pan/zoom/selection, type filters, an accessible node list, and an inspector.
- Service worker now uses a versioned static cache and never caches API, SSE, or WebSocket responses; manifest identity matches the Cognitive Desktop.
- Presence defaults now show unavailable state instead of fabricated values; emotion, goals, health, activity, and memory stats use verified response fields.
- Backend configuration and runtime fixes already made during the redesign.
- Backend hardening pass: the knowledge chunker no longer spins on a degenerate overlap/size combination, the retriever preserves explicitly named sources during phatic-query short-circuiting, the voice stream player degrades when `sounddevice` is unavailable, and the health metrics endpoint returns structured nulls when `psutil` is unavailable.
- JWT signing keys are now lazily initialized, so tokens can be minted from any entry point (including test clients that skip the lifespan) instead of raising `No key found for kid`.
- The legacy shell is isolated: `/desktop` redirects to `/presence`, and `graph`/`consciousness`/`inspector`/`marketplace` legacy pages redirect to their canonical routes.
- Accessibility review closed: skip link on every shell page, focusable main region, real buttons for the avatar and state chips, keyboard-operable canvas graph, WCAG AA text and link colours, and explicit reduced-motion rules.
- Graph render path profiled and de-quadratified: cached type colours, cached visible-node projection, and a stable canvas backing store.
- `/api/graph` now exports the live knowledge graph instead of a throwaway `CognitiveGraph()`. The live payload is 765 nodes / 558 edges across 11 types, and the node count matches `type_breakdown` exactly.
- Headless Chrome smoke validation for all redesigned pages.
- Import and JavaScript syntax checks for the new frontend modules.

Current validation status:

- **Full backend suite: 1808 passed, 0 failed (240s).** The previous 10-minute timeout was caused by the chunker spin now fixed.
- Frontend contract tests: 29 passed.
- Accessibility contract tests: 229 passed (`tests/test_frontend_a11y.py`).
- Graph performance gate: 4 passed (`tests/test_graph_performance.py`).
- Reasoning API, Phase 3 auth, and profile/auth regression tests: passed.
- Direct Chat SSE contract harness: passed with backend-shaped `token` frames.
- Browser navigation smoke test: Presence → Chat passed with the Chat workspace mounted.
- All 11 redesigned pages (Presence, Chat, Memory, Reasoning, Graph, Agency, Tasks, System, Permissions, Voice, Login) load in headless Chrome with no JavaScript console errors.
- Memory browser smoke test: real timeline data renders without the previous response-shape failure.
- Tasks browser smoke test: the Goal response renders without the previous object-iteration failure.
- Reasoning browser smoke test: canonical app shell, journal, trace, and reflection views render with real response fields.
- Reasoning API tests: public DTO redaction and auth dependency passed.
- Phase 3 browser smoke tests: Agency, System, Permissions, and redesigned Voice pages load without JavaScript console errors.
- Phase 3 auth tests: protected Agency, Voice, System, and Permissions read routes return 401 when the dependency denies access.
- Phase 4 graph smoke test: Canvas, accessible node list, and explicit empty state render without JavaScript console errors.
- Phase 4 hardening checks: service worker excludes API/SSE/WebSocket caching; manifest identity is updated; graph route is authenticated.
- Accessibility browser verification: skip link focus/reveal/focus-move confirmed in headless Chrome under both default and `--force-prefers-reduced-motion` profiles; emotion ring animation resolves to `none` under reduced motion.
- Graph profile: 5,000 nodes / 9,995 edges redraw in 1.30ms average (1.31ms p95) against a 250ms budget; was 406ms before the fix.
- Live graph verification: the production payload (765 nodes, 558 edges, 292KB) normalizes and renders in 0.25ms average with 0 dangling edges.
- Live restart validation: `/api/health` returns 200, full bootstrap succeeds, and legacy-route redirects resolve as expected.

The product plan should refine this checkpoint, not restart it.

## 12. MVP Architecture

### Must Have

- Persistent shell.
- Grouped navigation.
- Presence summary.
- Streaming Chat.
- Session persistence.
- Context inspector.
- Memory search and list.
- Memory detail inspector.
- Loading, empty, stale, unauthorized, unavailable, and error states.
- JWT refresh and retry.
- Keyboard navigation.
- Responsive inspector drawer.
- Real data only.
- Backend-owned voice control.

### Should Have

- Reasoning journal and decision history.
- Goals and task quick actions.
- Relationship summary in Chat context.
- Density preference.
- Memory provenance and freshness.
- Archive/forget confirmation and audit behavior.
- SSE connection state and reconnect feedback.

### Could Have

- 2D graph.
- Detailed system metrics.
- Plugin management.
- Permission editor.
- Voice latency details.
- Compact density mode.

### Future Vision

- Native daemon shell.
- Multi-window workspace.
- Multi-user profiles.
- Cloud synchronization.
- Mobile companion application.
- WebGL graph only after measured need.
- Richer offline and native bridge capabilities.

## 13. Roadmap

The sequence is more important than the calendar. Dates are planning targets, not commitments.

| Phase | Objective | Status |
|-------|-----------|--------|
| 0 | Product Contract and Data Integrity | Complete |
| 1 | Shell + Presence + Chat MVP | Complete |
| 2 | Memory + Reasoning + Tasks | Complete |
| 3 | Agency + System + Permissions + Voice | Complete |
| 4 | Graph and Hardening | Complete |

### Phase 0 — Product Contract and Data Integrity — Complete

**Objective:** Make the workstation direction implementable and truthful.

Tasks:

- Confirm the five-area information architecture.
- Verify endpoint and response contracts.
- Define page and inspector state contracts.
- Resolve Voice wording and backend test behavior.
- Define memory action permissions and audit requirements.
- Freeze the real-data and no-browser-mic rules.

Deliverables:

- Approved route map.
- Widget-to-endpoint matrix.
- Inspector interaction contract.
- Updated acceptance criteria.

Success criteria:

- No page requirement depends on an unverified metric.
- Voice ownership is unambiguous.
- Destructive memory actions have a defined safety model.

### Phase 1 — Shell + Presence + Chat MVP — Complete

**Objective:** Deliver the first daily-driver loop.

Tasks:

- Finish persistent shell behavior.
- Complete grouped navigation.
- Finish Presence real-data summary.
- Complete streaming Chat.
- Add session persistence and reconnect states.
- Add context inspector.
- Add Calm density default.

Deliverables:

- Login → shell → Presence → Chat workflow.
- Loading, empty, error, stale, and reconnect states.
- Responsive narrow-screen layout.

Success criteria:

- A user can complete a conversation without a blank screen or route failure.
- A user can inspect context relevant to the active conversation.
- Chat remains usable after token refresh and transient stream failure.

### Phase 2 — Memory + Reasoning + Tasks — Complete

**Objective:** Make continuity and action inspectable.

Tasks:

- Memory search and filters.
- Memory list and detail inspector.
- Provenance and freshness labels.
- Reasoning notebook and reflection history.
- Goals and task list.
- Safe memory actions.

Success criteria:

- A user can find, understand, and safely act on a memory.
- A user can understand why a decision or task exists.
- No destructive action occurs without the required confirmation and audit behavior.

### Phase 3 — Agency + System + Permissions + Voice — Complete

**Objective:** Expose control and safety surfaces.

Tasks:

- Agency control room.
- System health and services.
- Permission mode and audit view.
- Voice pipeline status and controls.
- Degraded-state behavior for unavailable services.

Success criteria:

- Every control maps to a real backend operation.
- Users can understand what autonomy and permissions currently allow.
- Voice controls never request browser microphone access.

### Phase 4 — Graph and Hardening — Complete

**Objective:** Add advanced visualization only after the core loop is proven.

Tasks:

- 2D Canvas graph.
- Graph list fallback.
- Performance profiling.
- PWA/offline strategy.
- Accessibility audit.
- Security audit.
- Legacy route retirement after sign-off.

Success criteria:

- Graph is usable at the target node count on supported hardware.
- The application remains usable without Canvas.
- Legacy and redesigned shells are never active simultaneously.

## 14. Requirements

### Functional Requirements

- The shell MUST remain available when a page request fails.
- Every page MUST render loading, empty, stale, unauthorized, unavailable, and error states as applicable.
- Every displayed data value MUST be traceable to a backend field or explicitly labeled local state.
- Chat MUST support streaming, cancellation, retry, and token refresh.
- Memory selection MUST show provenance when available.
- Destructive memory actions MUST be permission-aware, confirmed, and auditable.
- Voice MUST use the backend-owned pipeline.
- System metrics MUST expose source and freshness where possible.
- Inspector selections SHOULD be keyboard accessible and deep-linkable where practical.
- The shell MUST preserve navigation context across route changes.

### Non-Functional Requirements

- No blank-screen failure path.
- No uncaught JavaScript error during normal page navigation.
- Initial shell response target: under 2 seconds when the backend is healthy.
- Chat first-token target: under 1 second after request acceptance when the provider is healthy.
- SSE UI update target: under 500ms.
- Keyboard navigation and visible focus states are mandatory.
- Text contrast must meet WCAG AA.
- `prefers-reduced-motion` must be respected.
- No raw secrets, tokens, private prompts, or unbounded internal traces in the frontend.
- Browser microphone permission must never be requested by the redesigned Voice page.

## 15. Testing and Validation

### Static and Module Checks

- Verify every local ES module import resolves.
- Verify every named import has a matching export.
- Run JavaScript syntax checks with Node.
- Verify all HTML asset references resolve.
- Verify no forbidden browser voice capture call exists.

### Browser Smoke Tests

Use the installed headless Chrome or an explicitly approved browser test runner.

For each redesigned page:

- Load with a healthy backend.
- Confirm shell, navigation, workspace, and inspector render.
- Confirm no JavaScript console errors.
- Confirm loading, empty, error, and unauthorized behavior.
- Confirm responsive drawer behavior at narrow width.

### Product Validation

- Login → shell → Presence → Chat.
- Start and complete a streaming conversation.
- Refresh the access token during a session.
- Search and inspect a real memory.
- Trigger a backend outage and confirm no blank screen.
- Disconnect and reconnect SSE.
- Inspect a goal, task, and reasoning record.
- Toggle backend voice state.
- Verify the browser never requests microphone permission.
- Render a graph response and measure interaction performance.
- Verify every widget against its documented endpoint.

### Performance Checks

- Initial page load target: under 2 seconds.
- Chat first token target: under 1 second.
- SSE state update target: under 500ms.
- Graph target: at least 30 FPS at the supported default node count.
- Long lists must paginate, virtualize, or progressively render.
- Streaming updates must not block input or navigation.

### Accessibility Review (Phase 4 — complete)

Enforced by `tests/test_frontend_a11y.py` (229 checks) rather than a one-time manual pass.

| Area | Finding | Resolution |
|------|---------|------------|
| Keyboard | No skip link; `A11y.skipToMain()` existed with no trigger | Skip link is the first child of `<body>` on all 10 shell pages, styled in `shell-new.css`, wired through `A11y.initSkipLink()` |
| Keyboard | `<main>` was not programmatically focusable | `tabindex="-1"` added; focus moves to `shell-main` on activation |
| Keyboard | User avatar was a clickable `<div>` | Converted to `<button type="button" aria-label="User menu" aria-haspopup="true">` on all 10 pages |
| Keyboard | Presence state chips used `role="tab"` with no tab panels and click-only handling | Replaced with `role="group"` + `aria-pressed` toggle buttons; `A11y`/CSS kept intact |
| Keyboard | Graph canvas was pointer-only | `tabindex="0"`, `role="img"`, arrow-key pan, `+`/`-` zoom, `0` reset, `Enter`/`Space` select, with `announce()` feedback |
| Focus | No visible ring guarantee per page | Every page is asserted to load a stylesheet containing `:focus-visible`; focus ring is 2px accent (3.96:1 against elevated surfaces, above the 3:1 non-text bar) |
| Contrast | `--color-text-muted: #6E7785` measured 3.60:1 on cards — failed AA | Replaced with `#828C9A` (4.78:1 worst case) |
| Contrast | Links used `--color-accent-primary` (3.96:1) — failed AA | `typography.css`, `layout.css` (`.link-btn`), `layout-new.css` (`.text-accent`), and `.tab-active` now use `--color-accent-soft` (5.95:1) |
| Reduced motion | Emotion rings and status dot animated forever | Explicit `@media (prefers-reduced-motion: reduce)` block in `presence.css` sets `animation: none` |
| Reduced motion | Skip-link reveal depended on a transition completing | Verified in-browser: the global 0.01ms transition rule left the focused link off-screen; `shell-new.css` now disables the transition under reduced motion |
| Reduced motion | Legacy rAF loops (`graph3d.js`, `orb.js`, `motion.js`, `mai-symbol.js`) | Unreachable from redesigned routes; the gate asserts no redesigned module calls `requestAnimationFrame` |
| Structure | Redundant `role="navigation"` on `<nav>` | Removed from all 10 shell pages |
| Structure | `chat.html` had no `<h1>` and an unlabelled `<nav>` | Added `<h1 class="sr-only">` and `aria-label="Conversation context"` |
| Structure | `role="listitem"` applied directly to `<button>` in the graph list | Wrapped each entry in a `role="listitem"` element |

Browser-verified with headless Chrome (default and `--force-prefers-reduced-motion`): skip link is the first focusable element, reveals on focus with a 2–3px ring, moves focus to the main region, and the emotion ring animation is `none` under reduced motion.

Known non-blocking finding: 54 shell/page-toolbar `<button>` elements outside any `<form>` omit an explicit `type`. They carry accessible names and have no submit behaviour, so the gate only requires an explicit type inside forms (all of which already declare one).

### Graph Performance Profile (Phase 4 — complete)

`scripts/bench_graph.mjs` runs the real render path under Node with a stubbed 2D context; `tests/test_graph_performance.py` fails the build if the p95 redraw exceeds 250ms.

| Nodes | Edges | Before (avg) | After (avg) | After (p95) |
|-------|-------|--------------|-------------|-------------|
| 500 | 995 | 6.63ms | 0.19ms | 0.20ms |
| 1,000 | 1,995 | 18.63ms | 0.37ms | 0.46ms |
| 2,000 | 3,995 | 65.03ms | 0.56ms | 0.57ms |
| 5,000 | 9,995 | 406.49ms (over budget) | 1.30ms | 1.31ms |

Root causes fixed in `api/static/js/pages/graph.js`:

- `colorFor()` rebuilt the sorted unique-type list for every node on every redraw — now an O(1) `Map` lookup.
- `visibleNodes()` ran the search/filter predicate repeatedly per frame — now cached and invalidated only on input, filter change, or reload.
- The canvas backing store was reallocated on every draw — now only resized when the viewport or device pixel ratio changes.

Scaling is linear (~0.26ms per 1,000 nodes) and comfortably inside the 30 FPS budget at the 5,000-node target.

The profile also exposed a data defect: the page was being asked to render one node next to a 776-node summary, because `api/routes_dashboard.py::dashboard_graph()` constructed a throwaway `CognitiveGraph()` instead of reading `self.brain_graph`. The export now reads the same store it counts, merges world entities without duplicates, drops relations pointing at unknown nodes, and reports a `truncated` flag at the 5,000-node export cap. `scripts/render_graph_payload.mjs` replays the live payload through the client pipeline to confirm the page renders what the API sends.


## 16. Success Metrics

### Primary Metrics

- Successful chat turns: target 95% without manual recovery.
- Long-term memory retrieval usefulness: target 8/10 scripted recall checks.
- Supported task completion: target 90%.
- Cross-session continuity: target 90% on scripted continuity checks.
- Redesigned page load success: target 99%.
- Uncaught frontend errors during smoke tests: target 0.

### Secondary Metrics

- Time to locate a memory.
- Time to resume a conversation.
- Inspector use rate.
- Voice pipeline control success.
- Page response time.
- Accessibility violations.
- Stale-data incidents.
- User-reported trust and continuity.

### Failure Indicators

- A value cannot be traced to a backend field.
- A user cannot tell whether data is live, cached, or stale.
- Navigation loses active context.
- Memory actions cannot be audited or recovered.
- Browser microphone permission is requested.
- Chat streaming fails without a recoverable state.
- The interface becomes visually noisy during ordinary use.
- System displays invented health or performance values.

## 17. Risk Assessment

| Risk | Category | Severity | Mitigation |
| --- | --- | --- | --- |
| OS metaphor creates unmet native-window expectations | Product | High | Use workstation language; defer native window manager claims. |
| Contextual inspector reduces usable workspace width | UX | Medium | Inspector is optional and becomes a drawer on narrow screens. |
| Dense interface harms calmness | UX | High | Calm default and Compact opt-in. |
| Frontend/backend contract drift | Technical | High | Widget-to-endpoint matrix and contract validation per page. |
| Relationship or memory display feels invasive | Trust | High | User visibility controls, provenance, privacy settings, restrained presentation. |
| Archive/forget actions cause data loss | Technical | High | Confirmation, permissions, audit trail, undo where supported. |
| Vanilla modules become inconsistent | Maintainability | Medium | Clear ownership, import checks, browser smoke tests, no giant app module. |
| Stale service-worker assets persist | Reliability | Medium | Versioned cache and explicit invalidation strategy. |
| Voice wording conflicts with backend ownership | Technical | High | Use backend pipeline terminology and enforce no `getUserMedia()`. |
| Legacy and redesigned routes conflict | Reliability | High | Single active shell, route aliases, sign-off before retirement. |

Overall risk posture after the locked constraints: **Medium**, primarily because the backend is rich and the UI must not misrepresent its state.

## 18. Specialist Handoff

| Sequence | Specialist | Deliverable |
| --- | --- | --- |
| 1 | AI Product Manager | Approve scope, MVP, metrics, and acceptance criteria. |
| 2 | UI/UX Designer | Shell, grouped navigation, inspector patterns, density modes, accessibility. |
| 3 | Python Codebase Architect | Verify route, API, auth, and event contracts. |
| 4 | Memory Architecture Expert | Define memory inspector, provenance, retrieval feedback, and safe actions. |
| 5 | Reasoning Architecture Expert | Define safe reasoning visibility and user-facing explanations. |
| 6 | Voice Architecture Expert | Define backend-owned voice controls and test behavior. |
| 7 | Security Engineer | Review auth, permissions, privacy, destructive actions, and sensitive state. |
| 8 | Performance Engineer | Profile chat streaming, SSE, memory lists, and Canvas graph. |
| 9 | Knowledge Base Builder | Maintain this plan and related architecture documentation. |

## 19. Acceptance Criteria

The redesign is accepted only when:

- [x] Login → shell → Presence → Chat works with the real backend.
- [x] Grouped navigation covers all five cognitive areas.
- [x] Existing route paths remain usable.
- [x] Every redesigned page has explicit loading, empty, stale, unavailable, unauthorized, and error behavior as applicable.
- [x] Chat streams, retries, cancels, and survives token refresh.
- [x] Memory search, detail, provenance, and safe actions work against real data.
- [x] Reasoning and goals expose meaningful state without leaking internal artifacts.
- [x] Voice controls operate on the backend pipeline only.
- [x] No redesigned page calls `getUserMedia()` or browser-side microphone capture.
- [x] Every displayed data value passes the widget-to-endpoint audit.
- [x] Keyboard navigation, focus states, contrast, and reduced motion pass review.
- [x] The graph has a usable non-Canvas fallback.
- [x] No legacy and redesigned shells are active at the same time.
- [x] Relevant frontend checks and the full backend test suite pass before release.
- [x] The graph stays inside its frame budget at the target node count.

### Visual Sign-Off (complete)

`scripts/visual_check.py` drives Chrome over the DevTools Protocol, waits for each page to be genuinely ready, and only then captures. This replaced `chrome --dump-dom` / `--screenshot`, which snapshot before module JavaScript renders and made correct pages look broken.

Reviewed at 1440x900 and 390x wide: Presence, Chat, Memory, Reasoning, Graph.

| Defect | Root cause | Resolution |
|--------|------------|------------|
| Graph canvas rendered nothing useful | `.graph-layout` inherited the 100-row node list's height, stretching the canvas to 8,072px and pushing the cloud below the fold | The workspace owns the row height (`clamp(520px, 66vh, 760px)`) |
| Graph was an unreadable hairball | Nested-ring placement plus every edge drawn | Deterministic force layout with grid-bucketed repulsion, zoom-to-fit, and edge decluttering above 150 nodes |
| Graph listed `mem:<uuid>` identifiers | Node names are knowledge-graph keys | `labelFor()` prefers metadata text |
| Graph legend leaked `entity_from_link` | Raw type keys | `humanizeType()` |
| Presence showed `20701d ago` | `new Date(seconds)` read as milliseconds | `toDate()` normalises epoch units |
| Command bar floated bottom-right, clipped | `grid-area: command` with no `command` area in the grid template | Shell grid areas corrected; the context panel became a real right column that occupies zero width until opened |
| Chat showed a blank void on a new conversation | `renderMessages` had no empty branch | Explicit empty state |
| Chat context panel dumped raw vault triples | Backend text rendered verbatim | `memoryLabel()` |
| Memory cards showed the same sentence twice | `title` and `content` are the same vault text | Preview suppressed when the two are redundant, including backend-truncated titles |
| Reasoning leaked `mem:<uuid>` into DECISION and EVIDENCE | Raw LLM output rendered as-is | `humanizeReasoningText()` and `evidenceLink()` |
| Labels cut mid-word (`hello wonder…`) | Truncation fell back to a hard cut | `truncateWords()` always prefers a word boundary |

The shared formatters live in `api/static/js/format.js` and are covered by `tests/test_frontend_format.py` (20 checks), which asserts no raw identifier reaches the UI.

## 20. Post-Completion Release Work

All Phase 0–4 work is complete, the accessibility review and visual sign-off are closed, the graph is profiled, and the full backend suite is green. The items below sit outside this plan's scope:

1. Browser smoke test of the legacy-route redirects under an authenticated session.
2. Resolve the `AGENTS.md` rule that forbids subfolders under `api/static/js/` while the shell ships `js/shell/`, `js/pages/`, and `js/features/chat/`.
3. Release build, deployment, and rollback checklist.

## 21. Decision Record

### Decision

Adopt **MAI Cognitive Desktop — Quiet Intelligence** as the frontend product direction.

### Context

MAI's backend contains memory, relationships, emotions, reasoning, experience, dreaming, agency, tools, goals, voice, and knowledge systems. A highly animated dashboard would hide this depth and add implementation burden without improving daily use.

### Options Considered

1. Continue the React and animation-heavy concept.
2. Replace the visual components with static HTML while preserving the original dashboard structure.
3. Build a calm, dense, native-browser cognitive workstation.

### Chosen Option

Option 3.

### Consequences

- The frontend becomes easier to deploy and maintain.
- The visual language becomes calmer and more durable.
- Backend capabilities can be exposed more directly.
- The frontend must establish stronger module, state, accessibility, and data-contract discipline.
- The product remains a workstation metaphor until native daemon capabilities are implemented.

### Related Notes

- [[Native OS Bridge Architecture]]
- [[Event Fabric Architecture]]
- [[08-API Native & Surface]]
- [[Memory Pipeline]]
- [[Voice Pipeline]]
- [[Testing Strategy]]

## Documentation Status

- **Status:** Complete (v3.2.0) — all five phases delivered, 15/15 acceptance criteria met, 2,068 tests passing, visual sign-off complete
- **File:** `docs/Mai_documentation/03-Features/Complete Redesign Implementation Plan.md`
- **Architecture impact:** High
- **Related notes:** [[Native OS Bridge Architecture]], [[Event Fabric Architecture]], [[08-API Native & Surface]], [[Memory Pipeline]], [[Voice Pipeline]], [[Testing Strategy]]

