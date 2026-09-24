# MAI Cognitive Operating System — Pure HTML/CSS/JS Redesign Implementation Plan

## Task Classification

- **Type**: Complete frontend redesign + frontend architecture + design system + 13 page implementations
- **Implementation**: Pure HTML5 + CSS3 + modern vanilla JavaScript (ES2022+)
- **Backend**: Existing Python/FastAPI architecture remains the source of truth (unchanged)
- **Frontend state**: Native JavaScript ES modules + browser APIs
- **Animations**: Native CSS animations/transitions + Web Animations API + requestAnimationFrame
- **3D graph**: Native Canvas 2D (WebGL only if profiling proves insufficient); no Three.js
- **Routing**: Native History API
- **Server state**: Native fetch() + SSE/WebSocket
- **Build philosophy**: Minimal tooling, zero dependencies, maximum control
- **Motivation**: Operator prefers a new UI — the current UI works but does not feel right for daily use

---

## Selected Specialists (Minimum Required)

| Specialist | Role | Reason |
| --- | --- | --- |
| AI Product Manager | PRIMARY (planning) | MVP gating, roadmap, acceptance criteria, risk |
| UI/UX Designer | PRIMARY (implementation) | Design system, component library, all 13 pages |
| Character/Narrative Designer | SUPPORTING | MAI personality, character visual identity, emotional states in UI |
| Python Codebase Architect | SUPPORTING | Confirm endpoint map, SSE topics, auth refresh contract |
| Voice Architecture Expert | SUPPORTING | Voice page — control + visualization only, backend owns pipeline |
| Memory Architecture Expert | SUPPORTING | Memory page, memory visualization |
| Reasoning Architecture Expert | SUPPORTING | Reasoning page, reasoning flow visualization |
| Performance Engineer | SUPPORTING | Animation performance, Canvas graph optimization |
| Security Engineer | SUPPORTING | Auth flow, CSP vs new assets, no secret leakage in JS |
| Knowledge Base Builder | SUPPORTING | Document frontend architecture + widget-endpoint map |

---

## Technology Decision

### Frontend stack (USE)

| Concern | Use |
| --- | --- |
| Markup | HTML5 |
| Styling | Native CSS3 (design tokens, no Tailwind) |
| Language | JavaScript ES2022+ (native ES modules) |
| Components | HTML + Web Components where genuinely useful |
| Server state | Fetch API |
| Realtime | WebSocket API, EventSource / SSE |
| Routing | History API (pushState / replaceState / popstate) |
| Visualization | Canvas API (2D first), SVG |
| Audio visualization | Web Audio API (visualization of backend-provided signal only — see Voice constraint) |
| Complex animation | Web Animations API |
| Continuous animation | requestAnimationFrame |
| Client persistence | IndexedDB / localStorage (tokens, UI prefs only — not domain data) |

### Prohibited (DO NOT USE)

React, React DOM, TypeScript, Tailwind CSS, Framer Motion / Motion, Anime.js, Three.js, Lucide React, Zustand, TanStack Query, React Router, Cypress, Jest, React Testing Library.

**Rationale**: The objective is a dependency-light Cognitive OS interface, not a JavaScript framework application. The backend is already modular and event-driven; native browser modules keep the UI architecturally close to the Cognitive OS itself.

---

## MAI Frontend Dependency Policy

> The MAI Cognitive OS frontend shall use native browser APIs wherever practical. UI frameworks, CSS frameworks, animation libraries, state-management libraries, routing frameworks, and visualization frameworks are prohibited unless a demonstrated performance or capability requirement cannot reasonably be satisfied using platform APIs.
>
> Any proposed dependency must provide measurable value that cannot reasonably be achieved with HTML, CSS, JavaScript, SVG, Canvas, Web Audio, WebSocket, SSE, or Web APIs.

---

## Three Mandatory Fixes (Locked Before Code)

These three items were identified in product review and are **required before any page work begins**:

### Fix 1 — Voice Page: Control + Visualization Only (No Browser Mic Capture)

**Rule**: The frontend MUST NOT call `navigator.mediaDevices.getUserMedia()` or capture microphone audio.

**Why**: The backend already owns the complete voice pipeline — mic capture, Silero VAD, Faster Whisper STT, speaker recognition/ID, Kokoro TTS, interruption/barge-in, adaptive noise filter, FullAEC, diarization. Browser-side capture would create a second, competing voice pipeline that bypasses wake word, speaker memory, and emotion detection.

**Voice page is allowed to**:
- Read and display state from `GET /api/voice/status` and `GET /api/voice/details`
- Toggle the backend pipeline via `POST /api/voice/toggle`
- Visualize waveform/state driven by backend-provided signals (SSE `state.voice.*` events; audio-level data if the backend later exposes it)
- Show metrics already returned by `/api/voice/details` (VAD threshold, sample rate, STT/TTS/AEC/diarization stats, emotion detector output)

**Voice page is prohibited from**:
- `getUserMedia()` / `AudioContext` microphone capture
- Browser-side STT or wake-word detection
- Any second voice pipeline

### Fix 2 — M0 Must Include State Primitives + JWT Refresh

**State primitives** — `components.css` in M0 ships three mandatory primitives used by every page:

```css
.state-loading { /* orbiting dots / breathing node / progressive line */ }
.state-empty   { /* page-specific empty message + call to action */ }
.state-error   { /* error message + retry button */ }
```

No page may render a blank screen on API failure. Every fetch path renders one of these three states.

**JWT refresh** — `js/api-client.js` in M0 ships auth logic:

1. Attach `Authorization: Bearer <access_token>` to every `/api/*` request
2. On `401`: call `POST /api/auth/refresh` with refresh token → retry original request once
3. On refresh failure: clear tokens, redirect to `/login`, preserve intended route
4. Token storage: localStorage (access + refresh); never log tokens

This mirrors the existing backend auth (`api/auth.py`: 15-min access, 7-day refresh, HS256/RS256).

### Fix 3 — MVP-First Roadmap (Not 13 Equal Phases)

The roadmap is gated: **Shell + Presence + Chat is the launchable MVP (~2–3 weeks)**. Remaining pages iterate after MVP. See Roadmap section.

---

## Roadmap (MVP-Gated, ~8 Weeks)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ROADMAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## PHASE 0 — Foundation + Auth (Week 1)
Objective:        Design system, core JS modules, login works
Tasks:
  - Design tokens, reset, typography, layout, components (+ state primitives)
  - api-client (fetch wrapper, bearer, 401-refresh-retry), event-bus, router
  - Login page + token storage + refresh
Deliverables:     One demo page styled entirely with tokens; login → authenticated fetch
Success Criteria: Can log in and call /api/status with a valid JWT; no blank-state
                  path exists; Fix 1 and Fix 2 verified in code review

## PHASE 1 — Shell + Presence MVP (Week 2) ← LAUNCHABLE
Objective:        Navigable OS with live home dashboard
Tasks:
  - Sidebar / topbar / orbit navigation / router (History API)
  - SSE status indicator (voice + reasoning state via /api/stream)
  - Presence page: greeting, state tabs, emotion, goals, activity stream
  - Command palette (Ctrl/Cmd+K) — basic version
Deliverables:     Working app: login → shell → live Presence
Success Criteria: Presence renders real data in <2s; SSE updates state tabs live;
                  all nav routes work; loading/empty/error states demonstrated by
                  stopping the backend

## PHASE 2 — Chat (Week 3) ← DAILY DRIVER
Objective:        Streaming conversation
Tasks:
  - chat.html + chat-stream (fetch ReadableStream / SSE), chat-renderer (markdown)
  - Session handling, keyboard shortcuts, voice toggle integration
Deliverables:     Full chat with token streaming
Success Criteria: Stream renders as tokens arrive; no full-page reload; survives
                  token refresh mid-conversation

## PHASE 3 — Read-Only + CRUD Pages (Week 4-5)
Objective:        Memory, Reasoning, Agency, Tasks, System, Permissions
Tasks:
  - Memory (search / list / detail)
  - Reasoning (journal / flow / reflections)
  - Agency (goals / tools / world entities)
  - Tasks (CRUD + subtasks)
  - System (health / plugins / config)
  - Permissions (view + mode set)
Deliverables:     6 pages functional against real APIs
Success Criteria: Each page: real data, three state primitives, zero fabricated
                  metrics (widget-endpoint audit passed)

## PHASE 4 — Graph + Voice Control (Week 6-7)
Objective:        Canvas graph + voice control (Fix 1 enforced)
Tasks:
  - Graph: Canvas 2D force layout, 200-node default view, search-to-expand,
    type filters, inspector panel; WebGL only if profiling demands it
  - Voice: status / details / toggle from backend; state-driven waveform
    visualization; ZERO getUserMedia calls
Deliverables:     Interactive graph; voice control panel
Success Criteria: Graph ≥30fps at 200 nodes; Voice page makes no mic permission
                  request (verified in devtools)

## PHASE 5 — Cross-Cutting Polish (Week 8)
Objective:        Global search, notifications, a11y, PWA, legacy cleanup
Tasks:
  - Global search (backend-backed), toast / notification center
  - WCAG pass (keyboard, contrast, reduced motion), responsive breakpoints
  - manifest.json + service worker
  - Remove superseded legacy pages after acceptance sign-off
Deliverables:     Production-ready UI
Success Criteria: All acceptance criteria (Success Metrics) checked

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 8 weeks total. MVP launchable at end of Week 2.
 Each phase independently shippable.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Phase Details

### PHASE 0 — Design System Foundation + Auth (Week 1)

**Specialists**: UI/UX Designer (PRIMARY), AI Product Manager (gate review)

**Deliverables**:
- Design tokens (CSS custom properties)
- Reset, typography, layout, component primitives
- **State primitives: `.state-loading`, `.state-empty`, `.state-error` (Fix 2)**
- Core JS modules: api-client (with JWT refresh — Fix 2), event-bus, router, keyboard, accessibility
- Login page + authenticated fetch working end-to-end
- MAI visual identity symbol (3 orbital lines forming M)
- Responsive breakpoints (320, 375, 414, 768, 1024, 1440)
- Accessibility standards (WCAG AA, reduced motion, focus states)

**Design Tokens**:

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

    --border-subtle: rgba(255,255,255,0.07);

    --radius-sm: 8px;
    --radius-md: 10px;
    --radius-lg: 12px;

    --shadow-sm: 0 1px 2px rgba(0,0,0,.3);
    --shadow-md: 0 4px 12px rgba(0,0,0,.4);
    --shadow-lg: 0 8px 32px rgba(0,0,0,.5);

    --transition-fast: 150ms ease-out;
    --transition-normal: 250ms ease-out;
    --transition-slow: 500ms ease-out;

    --font-sans: Inter, Manrope, system-ui, sans-serif;
    --font-mono: "JetBrains Mono", Consolas, monospace;
}
```

No Tailwind. No CSS-in-JS. No component framework.

**Files to Create**:
- `api/static/css/reset.css`
- `api/static/css/design-tokens.css`
- `api/static/css/typography.css`
- `api/static/css/layout.css`
- `api/static/css/components.css` — includes `.state-loading`, `.state-empty`, `.state-error`
- `api/static/css/animations.css`
- `api/static/css/utilities.css`
- `api/static/js/api-client.js` — fetch wrapper + bearer + 401→refresh→retry (Fix 2)
- `api/static/js/event-bus.js`
- `api/static/js/history-router.js` — History API (legacy `MaiRouter` preserved)
- `api/static/js/keyboard.js`
- `api/static/js/accessibility.js`
- `api/static/login.html`

---

### PHASE 1 — Application Shell + Presence (Week 2) — MVP GATE

**Specialists**: UI/UX Designer (PRIMARY), Character/Narrative Designer (SUPPORTING)

**Shell structure**:

```html
<body>
    <div id="mai-app">
        <aside id="sidebar">...</aside>
        <header id="topbar">...</header>
        <main id="main-content">...</main>
        <aside id="context-panel">...</aside>
        <footer id="command-bar">...</footer>
    </div>
</body>
```

**Deliverables**:
- AppShell (persistent OS shell, semantic HTML)
- Sidebar navigation rail (72px default → 220px expanded)
- TopBar with MAI status indicator (driven by SSE)
- Orbit navigation — clickable nodes per page (navigation + live status ring via SSE)
- Command Palette (Ctrl/Cmd+K) — basic version
- Page transition system (CSS + Web Animations API)
- Presence page: greeting, state tabs, emotion, goals, activity stream
- SSE connection to `/api/stream` driving voice/reasoning state tabs

**Native routing** (no React Router):

```js
history.pushState(state, title, url);
window.addEventListener("popstate", handler);
```

Routes: `/`, `/chat`, `/memory`, `/graph`, `/reasoning`, `/agency`, `/voice`, `/tasks`, `/system`, `/permissions`, `/login`

**Presence page — real API mapping (zero fabricated metrics)**:

| Widget | API Endpoint |
| --- | --- |
| Greeting (time-aware) | Local time logic (`_time_of_day()` pattern) |
| State tabs (Idle/Listening/Thinking/Speaking) | SSE `state.voice.*`, `state.reasoning.busy/complete` |
| Uptime | `GET /api/health/metrics` → `uptime_seconds` |
| Health badge (Nominal) | `GET /api/system/health` → summary |
| Emotion / mood / energy | `GET /api/consciousness` → `emotion`, `cognitive` |
| Confidence | `GET /api/consciousness` → `cognitive.confidence` |
| Active goals count + goal card | `GET /api/status` → `goals`; `GET /api/goals` |
| Activity stream | `GET /api/inspector/records` + SSE `state.*` |
| Memory count | `GET /api/memory/stats` |
| Sidebar badges | `GET /api/goals` / `GET /api/tasks` active counts |
| Introspective reflection | `GET /api/reasoning/reflect/history` |

**Presence widgets REMOVED (no backend data — do not implement)**:

- Flow State %, Cognitive Friction %, Empathy Resonance % (unless wired to `relationship.affection`)
- Loop/Cadence metric, "Activity: High" duplicate, "1 Active Sub-agents"
- "100% COHERENT" badge, "Last State Shift", "Subagent Execution: Synchronized"
- Fake "Rel: %" relevance scores on activity items
- "Autonomous Core: ON" footer
- Any metric not traceable to a listed endpoint

**Orbit**: Keep as interactive navigation hub (nodes = pages, click = navigate). Optional: color-code node status from SSE (`state.voice.*`, `state.reasoning.*`). Not a fake knowledge-graph render — wire to `GET /api/graph` only if showing real entities.

**Backend API requirements** (all exist — no backend changes):

- `GET /api/status`
- `GET /api/consciousness`
- `GET /api/health/metrics`
- `GET /api/system/health`
- `GET /api/goals`
- `GET /api/inspector/records`
- `GET /api/memory/stats`
- `GET /api/stream` (SSE)
- `POST /api/auth/login`, `POST /api/auth/refresh`

**Files to Create**:
- `api/static/presence.html` (or served as `/` landing — resolve route swap with legacy UI)
- `api/static/js/app.js`
- `api/static/js/shell/app-shell.js`
- `api/static/js/shell/sidebar.js`
- `api/static/js/shell/topbar.js`
- `api/static/js/shell/command-bar.js`
- `api/static/js/shell/context-panel.js`
- `api/static/js/shell/mai-status.js`
- `api/static/js/components/command-palette.js`
- `api/static/js/pages/presence.js`
- `api/static/js/features/presence/mai-orb.js`
- `api/static/js/features/presence/goals-panel.js`
- `api/static/js/features/presence/activity-stream.js`
- `api/static/css/shell-new.css`
- `api/static/css/pages/presence.css`

---

### PHASE 2 — Chat (Week 3)

**Specialists**: UI/UX Designer (PRIMARY), Character/Narrative Designer (SUPPORTING)

**Deliverables**:
- Three-panel layout: Sessions | Conversation | Context
- Session list with grouping (Today, Yesterday, 7 days)
- Message rendering with markdown, code blocks, tables
- **Streaming via native `fetch()` + `ReadableStream` + `TextDecoder`, or `EventSource` for SSE — no TanStack Query, no React state**
- MAI thinking state driven by SSE `state.reasoning.busy`
- Tool execution display in chat
- Floating input: Attach / Voice toggle / Command / Send
- Keyboard shortcut indicator (Ctrl/Cmd+K)
- Session persistence (localStorage for UI prefs only; server state via API)

**Module architecture (do NOT build one giant chat.js)**:

```
js/features/chat/
    chat-store.js        — state (native JS store)
    chat-stream.js       — transport (fetch ReadableStream / SSE)
    chat-renderer.js     — DOM rendering + markdown
    chat-session.js      — session manager
    chat-context.js      — right context panel
    chat-voice.js        — voice toggle (backend pipeline control only — Fix 1)
    markdown-renderer.js — lightweight native markdown
```

Consistent with backend's modular architecture: `ChatState`, `ChatTransport`, `ChatRenderer`, `ChatSessionManager`, `ChatVoice`.

**Backend API requirements** (exist):
- `POST /api/chat` — send message
- `POST /api/chat/stream` — streaming (SSE)
- `POST /api/chat/wake` — wake greeting
- Session endpoints as exposed by backend (ProfileStore / SessionManager routes)

**Files to Create**:
- `api/static/chat.html`
- `api/static/js/pages/chat.js`
- `api/static/js/features/chat/*` (modules above)
- `api/static/css/pages/chat.css`

---

### PHASE 3 — Memory, Reasoning, Agency, Tasks, System, Permissions (Week 4-5)

**Specialists**: UI/UX Designer (PRIMARY); Memory / Reasoning / Security experts SUPPORTING per page

#### Memory Page

**Deliverables**:
- Header stats (Total, Important, Recent, Emotional) from `/api/memory/stats`
- Search with filters (All, People, Projects, Events, Preferences, Knowledge, Emotional, Recent)
- Memory cards: title, preview, date, importance bar, emotional weight bar, source, tags
- Right-side detail panel — **CSS transition only, no animation library**:

```css
.memory-detail { transform: translateX(100%); transition: transform 250ms ease-out; }
.memory-detail.is-open { transform: translateX(0); }
```

**API**: `GET /api/memory`, `GET /api/memory/stats`, `GET /api/memory/timeline` (all exist)

**Files**: `memory.html`, `js/pages/memory.js`, `js/features/memory/{memory-store,memory-search,memory-list,memory-detail,memory-viz}.js`, `css/pages/memory.css`

#### Reasoning Page

**Deliverables**:
- Header: "REASONING — How MAI arrived at decisions"
- Decision history, reflections journal, confidence indicators
- Visual flow: INPUT → CONTEXT → CONSIDERATIONS → DECISION → OUTCOME
- **Connectors via SVG** (no animation library)
- Reflection journal with personal journal feel

**API**: `GET /api/reasoning/thoughts`, `GET /api/reasoning/reflect`, `GET /api/reasoning/reflect/history` (exist)

**Files**: `reasoning.html`, `js/pages/reasoning.js`, `js/features/reasoning/{reasoning-store,reasoning-flow,decision-history,reflection-journal,patterns}.js`, `css/pages/reasoning.css`

#### Agency Page

**Deliverables**:
- Agency status, autonomy segmented control (native HTML):

```html
<div class="segmented-control">
    <button data-level="0">Manual</button>
    <button data-level="1">Assisted</button>
    <button data-level="2">Semi-Autonomous</button>
    <button data-level="3">Autonomous</button>
</div>
```

- Goals with priority/progress, tools, world entities, intent queue
- No component library

**API**: `GET /api/goals`, `GET /api/tools`, `GET /api/world/entities` (exist)

**Files**: `agency.html`, `js/pages/agency.js`, `js/features/agency/{agency-store,autonomy-control,goals,tools,entities,intent-queue}.js`, `css/pages/agency.css`

#### Tasks Page

**Deliverables**:
- Sections: Today, Upcoming, In Progress, Completed
- Task cards: checkbox, title, priority, deadline, related goal
- Detail panel; completion animation via **CSS only**:

```css
.task.is-complete .task-checkbox { animation: checkbox-complete 250ms ease-out; }
```

**API**: `GET /api/tasks`, `POST /api/tasks/create`, `POST /api/tasks/{id}/complete`, `/cancel`, `/activate`, `/subtasks` (exist)

**Files**: `tasks.html`, `js/pages/tasks.js`, `js/features/tasks/{task-store,task-list,task-detail,task-animation}.js`, `css/pages/tasks.css`

#### System Page

**Deliverables**:
- System health (CPU, memory, components) with minimal charts (thin lines, subtle grid)
- Plugin cards: icon, name, status, permissions
- Configuration editor: AI, Memory, Voice, Autonomy, Security, Appearance, System
- Professional toggles, selects, inputs

**API**: `GET /api/system/health`, `GET /api/system/plugins`, `GET /api/health/metrics`, `GET /api/config`, `POST /api/config/update` (exist)

**Files**: `system.html`, `js/pages/system.js`, `js/features/system/{health,plugins,configuration,metrics}.js`, `css/pages/system.css`

#### Permissions Page

**Deliverables**:
- Security status badge, mode selector (STRICT / BALANCED / AUTONOMOUS)
- Whitelist display, blocked commands, destructive hotkeys
- Audit log with timestamps
- **Deliberately conservative, professional security aesthetic**

**API**: `GET /api/permissions`, `POST /api/permissions/mode` (exist)

**Files**: `permissions.html`, `js/pages/permissions.js`, `js/features/security/{permission-mode,whitelist,audit-log}.js`, `css/pages/permissions.css`

---

### PHASE 4 — Knowledge Graph + Voice Control (Week 6-7)

**Specialists**: UI/UX Designer (PRIMARY), Memory Architecture Expert + Voice Architecture Expert (SUPPORTING), Performance Engineer (SUPPORTING)

#### Graph Page

**Architecture decision — Canvas 2D first, WebGL only if profiled necessary**:

```js
const canvas = document.querySelector("#graph");
const ctx = canvas.getContext("2d");

function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    drawEdges();
    drawNodes();
    requestAnimationFrame(render);
}
render();
```

**Deliverables**:
- Force-directed graph, Canvas 2D
- **200-node default view** with search-to-expand (virtualization threshold: if >500 visible nodes or <30fps in profiling, paginate before considering WebGL)
- Node types (8): Memory, Person, Project, Goal, Concept, Event, Location, Task — colors within MAI palette
- Zoom, pan (mouse + touch); rotate optional (2D tilt)
- Node selection + expansion, search with highlight, type filters
- Relationship edges with strength
- Right-side inspector panel (CSS slide)
- Subtle node pulses via CSS/rAF (no Anime.js)
- Level-of-detail for performance

**API**: `GET /api/graph` (exists — nodes, edges, type_breakdown); entity detail via graph data; prune via `POST /api/graph/prune`

**Files**: `graph.html`, `js/pages/graph.js`, `js/features/graph/{graph-store,graph-model,graph-layout,graph-renderer,graph-camera,graph-interaction,graph-inspector,graph-search}.js`, `css/pages/graph.css`

#### Voice Page — Fix 1 Enforced

**Deliverables (control + visualization ONLY)**:
- Center state display: "MAI SPEAKING" / "MAI LISTENING" / "MAI THINKING" / "MAI IDLE" — driven by SSE `state.voice.*`
- Metrics panel from `GET /api/voice/details`: VAD threshold, silence timeout, sample rate, STT/TTS/AEC/diarization/emotion-detector/noise-filter stats
- Controls: Toggle mic pipeline (`POST /api/voice/toggle`), stop, test voice (backend TTS)
- Voice profile display from details endpoint
- Waveform visualization: **state-driven animation** (CSS/rAF visualization of backend state, or backend-provided audio levels if later exposed). NOT live browser-captured audio.
- Latency/state transitions with smooth CSS animations

**PROHIBITED (Fix 1)**:
- `navigator.mediaDevices.getUserMedia()`
- `AudioContext` microphone capture / browser STT
- Any second voice pipeline

**API**: `GET /api/voice/status`, `GET /api/voice/details`, `POST /api/voice/toggle`, SSE `state.voice.*` (all exist)

**Files**: `voice.html`, `js/pages/voice.js`, `js/features/voice/{voice-store,voice-state,voice-waveform,voice-metrics,voice-controls}.js`, `css/pages/voice.css`

---

### PHASE 5 — Cross-Cutting Concerns (Week 8)

**Specialists**: UI/UX Designer (PRIMARY), Performance Engineer, Security Engineer, Knowledge Base Builder

**Deliverables**:
- Command Palette full version (Ctrl/Cmd+K) — native keyboard handling:

```js
document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key === "k") {
        event.preventDefault();
        openCommandPalette();
    }
});
```

- Global Search — **use existing backend search infrastructure, do not implement a second search engine in the frontend**
- Notification system (small elegant surfaces / toasts)
- Loading / empty / error states audit across all pages (Fix 2 verification)
- Page transitions (fade + slight movement via Web Animations API)
- Micro-interactions for all components (CSS)
- Responsive design (320px, 768px, 1024px, 1440px)
- Accessibility audit (keyboard, screen reader, contrast, reduced motion)
- PWA: manifest.json, service worker, offline fallback
- Performance optimization (virtualization, lazy loading)
- Dark mode only (per design spec)
- **Legacy UI cleanup**: remove superseded legacy pages only after acceptance sign-off; never mount old and new shell simultaneously (avoids double SSE + global conflicts)

**Files**:
- `api/static/js/components/{modal,dropdown,tabs,toast,progress,tooltip}.js`
- `api/static/js/{store,notifications,responsive,global-search}.js`
- `api/static/sw.js` (updated)
- `api/static/manifest.json` (updated)
- `api/static/css/animations.css` (extended)
- `api/static/css/utilities.css`

---

## Revised Frontend Architecture (Canonical Directory Structure)

**Per AGENTS.md static file rules: Never create new folders under `css/`, `js/`, `img/`, or `assets/`. All files live flat in their respective directories.**

```
api/static/
│
├── login.html
├── presence.html          (or / landing — resolve with legacy route swap)
├── chat.html
├── memory.html
├── graph.html
├── reasoning.html
├── agency.html
├── voice.html
├── tasks.html
├── system.html
├── permissions.html
│
├── css/
│   ├── reset.css
│   ├── design-tokens.css
│   ├── typography.css
│   ├── layout.css
│   ├── components.css        (includes .state-loading/.state-empty/.state-error)
│   ├── animations.css
│   ├── utilities.css
│   ├── presence.css
│   ├── chat.css
│   ├── memory.css
│   ├── graph.css
│   ├── reasoning.css
│   ├── agency.css
│   ├── voice.css
│   ├── tasks.css
│   ├── system.css
│   └── permissions.css
│
├── js/
│   ├── app.js
│   ├── api-client.js      (bearer + 401 refresh + retry — Fix 2)
│   ├── event-bus.js
│   ├── history-router.js   (History API — legacy MaiRouter preserved)
│   ├── keyboard.js
│   ├── accessibility.js
│   ├── store.js
│   ├── notifications.js
│   ├── global-search.js
│   ├── app-shell.js
│   ├── sidebar.js
│   ├── topbar.js
│   ├── command-bar.js
│   ├── context-panel.js
│   ├── mai-status.js
│   ├── command-palette.js
│   ├── modal.js
│   ├── dropdown.js
│   ├── tabs.js
│   ├── toast.js
│   ├── progress.js
│   ├── tooltip.js
│   ├── presence.js
│   ├── chat.js
│   ├── memory.js
│   ├── graph.js
│   ├── reasoning.js
│   ├── agency.js
│   ├── voice.js
│   ├── tasks.js
│   ├── system.js
│   └── permissions.js
│
├── img/
├── assets/
│   ├── icons/
│   └── fonts/
│
├── manifest.json
└── sw.js
```

**Entry**:

```html
<script type="module" src="/static/js/app.js"></script>
```

```js
import { HistoryRouter } from "./history-router.js";
import { api } from "./api-client.js";
import { EventBus } from "./event-bus.js";
```

**Warning — do not over-engineer vanilla JS**: Pure HTML/CSS/JS does not mean one giant `app.js` (e.g., 8,000 lines). The browser already provides a module system. You don't need React to achieve modularity.

---

## Animation Architecture (3 Layers)

| Layer | Technology | Use For |
| --- | --- | --- |
| **Layer 1 — CSS** | transitions, transforms, keyframes | hover, focus, opacity, panels, buttons, status changes, breathing effects, orbital animations |
| **Layer 2 — Web Animations API** | `element.animate()` | complex component sequences, page transitions, staged entrances, timeline animations |
| **Layer 3 — requestAnimationFrame** | rAF loop | waveform, Canvas graph, particles, orbital visualization, real-time visuals |

Example (Layer 2):

```js
element.animate(
    [
        { opacity: 0, transform: "translateY(8px)" },
        { opacity: 1, transform: "translateY(0)" }
    ],
    { duration: 300, easing: "ease-out", fill: "forwards" }
);
```

This is enough for MAI. No Anime.js. No Framer Motion.

---

## Backend API Map (All Endpoints Exist — No Backend Rewrite Required)

The frontend is a thin presentation/control layer. Every widget maps to a real endpoint.

| Page | Endpoints |
| --- | --- |
| Auth | `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/register`, `GET /api/auth/me` |
| Shell / Presence | `GET /api/status`, `GET /api/consciousness`, `GET /api/health/metrics`, `GET /api/system/health`, `GET /api/goals`, `GET /api/inspector/records`, `GET /api/memory/stats`, `GET /api/reasoning/reflect/history` |
| Chat | `POST /api/chat`, `POST /api/chat/stream`, `POST /api/chat/wake` |
| Memory | `GET /api/memory`, `GET /api/memory/stats`, `GET /api/memory/timeline` |
| Graph | `GET /api/graph`, `POST /api/graph/prune` |
| Reasoning | `GET /api/reasoning/thoughts`, `GET /api/reasoning/reflect`, `GET /api/reasoning/reflect/history` |
| Agency | `GET /api/goals`, `GET /api/tools`, `GET /api/world/entities` |
| Voice | `GET /api/voice/status`, `GET /api/voice/details`, `POST /api/voice/toggle` |
| Tasks | `GET /api/tasks`, `POST /api/tasks/create`, `POST /api/tasks/{id}/complete`, `/cancel`, `/activate`, `/subtasks` |
| System | `GET /api/system/health`, `GET /api/system/plugins`, `GET /api/system/about`, `GET /api/config`, `POST /api/config/update` |
| Permissions | `GET /api/permissions`, `POST /api/permissions/mode` |
| Inspector | `GET /api/inspector/records`, `/record/{id}`, `/trace/{id}`, `/subscribers`, `/queues`, `/dead_letters`, `/latency`, `/health`, `/summary` |
| Plugins | `GET /api/plugins/installed`, `/marketplace/search`, install/enable/disable |
| Realtime | `GET /api/stream` (SSE — 15 `state.*` topics), `WS /ws` |

**Known backend gaps to confirm (Python Codebase Architect)**: global search endpoint (`/api/search/global`) may not exist — use existing backend search routes instead of inventing one; audio-level events for waveform may not exist — waveform stays state-driven until confirmed.

---

## Widget-to-Endpoint Audit Rule

**Every displayed value must be traceable to a listed endpoint.** Before marking any page done:

1. List every displayed value on the page
2. curl the claimed endpoint
3. Confirm the value appears in the response
4. Fail any widget you cannot trace

This eliminates the fabricated-metric problem (Flow State %, Cognitive Friction, fake Rel %, etc.) permanently.

---

## Design System Migration Strategy (Current → New Tokens)

| Current | New | Notes |
| --- | --- | --- |
| `--bg-deep-midnight: #090B10` | `--bg-primary: #0A0B0F` | Primary background |
| `--bg-charcoal: #12151C` | `--bg-secondary: #0E1015` | Secondary background |
| `--glass: rgba(255,255,255,0.08)` | `--bg-panel: #12141A` | Panels |
| `--glass-strong: rgba(255,255,255,0.12)` | `--bg-card: #181B22` | Cards |
| `--accent: #4FA7FF` | `--accent-primary: #7C5CFF` | Signature MAI purple |
| `--accent-highlight: #9D7BFF` | `--accent-soft: #9B86FF` | Soft purple |
| `--accent-secondary: #67E8F9` | `--accent-blue: #6EA8FF` | Subtle blue |
| `--success: #3DDC97` | `--success: #72D6A5` | Updated success |
| `--warning: #FFC857` | `--warning: #E8B86A` | Updated warning |
| `--danger: #FF5D73` | `--danger: #E87575` | Updated danger |

---

## Risk Assessment

| Risk | Category | Severity | Probability | Mitigation |
| --- | --- | --- | --- | --- |
| Voice page captures browser mic (bypasses backend pipeline) | Technical | 🔴 Critical | Certain if plan uncorrected | **Fix 1 locked**: control + visualization only; no getUserMedia; verify in devtools |
| Blank screens on API failure (no state primitives) | User | 🟠 High | Likely | **Fix 2 locked**: `.state-loading/.state-empty/.state-error` in M0; every fetch path renders one |
| Auth/token refresh missing from frontend | Security | 🟠 High | Possible | **Fix 2 locked**: api-client 401→refresh→retry in M0; login page in M1 |
| 14-week equal-phase roadmap, no MVP, motivation fatigue | Product | 🟠 High | Likely | **Fix 3 locked**: MVP-gated 8-week roadmap; launchable at Week 2 |
| Canvas 2D <30fps at 1000+ nodes | Technical | 🟡 Medium | Possible | 200-node default, search-to-expand, virtualize >500 nodes before WebGL |
| Legacy + new UI both serving same route (double SSE, global conflicts) | Technical | 🟡 Medium | Possible | Separate entry routes; never mount both shells; delete legacy only after sign-off |
| Fabricated widgets creep back in | Product | 🟡 Medium | Possible | Widget-to-endpoint audit as acceptance gate per page |
| Streaming text animation performance | Technical | 🟡 Medium | Medium | rAF, batch DOM updates, virtualize long conversations |
| Font loading (Inter/Manrope/JetBrains Mono) | Technical | 🔵 Low | Low | Preload, system fallback, `font-display: swap`; CSP allows self + cdn.jsdelivr + unpkg |
| Service worker cache invalidation | Technical | 🟡 Medium | Medium | Versioned cache names; cache-first static, network-first API |

**Summary**: 1 critical (now locked via Fix 1), 3 high (now locked via Fixes 2-3), 5 medium, 1 low. **Overall risk posture after fixes: Low-Medium.**

---

## Testing Strategy

**Remove**: Jest, React Testing Library, Cypress.

**Use**:

### Backend (existing — must stay green)
- `pytest` (1,832 tests), `mypy`, `ruff`
- Zero backend regressions: full suite must pass after any (expected: no) backend touch

### Frontend logic
- Keep important logic as plain, importable JS modules (testable without a browser harness where possible)

### Browser integration
- **Playwright as the single frontend testing dependency** (recommended — not a UI framework, does not dictate architecture)
- If extreme dependency-minimization is preferred: browser-native/manual integration tests + existing Python API integration suite

### Widget-to-endpoint audit (manual or Playwright script)
- Per page: displayed values → curl endpoint → confirm presence

### State-primitive test
- Kill backend mid-session per page → confirm `.state-error` renders (not blank) → restart → confirm recovery

### Auth flow test
- Let access token expire (15 min) → silent refresh; force refresh fail → redirect to login preserving route

### Voice architecture test (Fix 1)
- Load Voice page → assert `getUserMedia` never called

### Performance tests
- Lighthouse (Performance > 90)
- Bundle size < 200KB gzipped initial
- Graph FPS ≥ 30 at 200 nodes (stretch: 1000)
- Animation frame rate ≥ 55fps
- Time to Interactive < 2s
- Chat first token < 1s after POST
- SSE state update latency < 500ms

---

## Success Metrics

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SUCCESS METRICS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Primary Metrics:
  - Page load (Presence, cold) — <2s — browser devtools
  - SSE state update latency — <500ms — event→DOM timestamp diff
  - Chat first token — <1s after POST — stream timing
  - All 13 pages show real API data (0 fabricated widgets) — widget-endpoint audit

Secondary Metrics:
  - Initial JS (gzipped) — <200KB
  - Animation FPS (Presence orbit, graph) — ≥55fps / ≥30fps graph
  - Accessibility: keyboard-navigable, contrast ≥4.5:1 — axe/Lighthouse
  - 0 console errors during normal navigation

Failure Indicators:
  - Any page shows a metric with no backing endpoint
  - Operator disables auth to avoid login friction
  - Voice page triggers browser mic permission prompt
  - Blank screen on API failure (missing state primitive)
  - Legacy and new UI both serving same route

Acceptance Criteria:
  - [ ] Login → shell → Presence works with JWT; refresh silent
  - [ ] Every page has loading/empty/error state, verified by stopping backend
  - [ ] SSE stream drives voice/reasoning state tabs with <500ms latency
  - [ ] Chat streams tokens; survives token refresh mid-stream
  - [ ] Graph renders 200 nodes ≥30fps Canvas 2D; no Three.js in project
  - [ ] Voice page makes zero getUserMedia calls (Fix 1)
  - [ ] Widget-to-endpoint audit: 100% of displayed data traced to real API
  - [ ] Legacy UI removed or unreachable after final acceptance
  - [ ] 1,832 backend tests still pass (no backend regressions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Validation Plan

**How to Test**:
1. Widget-endpoint audit per page (list values → curl endpoint → confirm)
2. State-primitive test (kill backend per page → `.state-error` → restart → recover)
3. Auth flow test (expire access token → silent refresh; fail refresh → login redirect preserving route)
4. SSE test (disconnect 30s → reconnect UI → no false "all good")
5. Voice architecture test (devtools → no `getUserMedia`)
6. Performance (Lighthouse + devtools FPS on orbit and graph at 200/500/1000 nodes)
7. Regression (full pytest after any backend touch — expect zero touch)

**Test Scenarios**:
1. Happy path: login → browse all 13 pages → chat stream → voice toggle
2. Edge: 5,000-node graph response; empty memory; zero goals
3. Degraded: backend down; SSE down; expired refresh token

**Success Means**: All acceptance criteria checked; widget audit 100%; state primitives verified on every page.

**Failure Means**: Any fabricated widget ships; any blank-screen path; browser mic invoked; auth bypass needed to proceed.

---

## Performance Targets

| Target | Threshold |
| --- | --- |
| Initial load | < 2 seconds |
| Initial JS | < 200 KB gzipped |
| Animation | 55–60 FPS |
| Graph | 30+ FPS at 200 nodes (1000 stretch via virtualization) |
| Voice UI visual response | < 100 ms (state display; backend voice E2E < 2s) |
| Chat first token | < 1s |
| SSE update latency | < 500ms |

---

## Specialist Assignments (Implementation Sequence)

| Sequence | Specialist | Scope |
| --- | --- | --- |
| 1 | AI Product Manager | Plan, MVP gate, acceptance criteria (this document) |
| 2 | UI/UX Designer | Design tokens, component primitives, state primitives, per-page visual specs, a11y |
| 3 | Python Codebase Architect | Confirm endpoint map, SSE topic list, auth refresh contract; flag backend gaps (global search, audio-level events) |
| 4 | Python Master Engineer | Only if backend gaps confirmed (likely minimal) |
| 5 | UI/UX Designer + Operator | Implement M0→M5 per roadmap (AI Studio or direct) |
| 6 | Security Engineer / Systems Auditor | Pre-launch pass: CSP vs new assets, auth coverage, no secrets in JS |
| 7 | Knowledge Base Builder | Document frontend architecture + widget-endpoint map in `04-Development/` |

---

## Documentation Updates Required

Per documentation protocol, after implementation:

| Document | Folder | Action |
| --- | --- | --- |
| Frontend Architecture | 01-Architecture/ | Create new |
| Design System | 02-Subsystems/ | Create new |
| Component Library | 02-Subsystems/ | Create new |
| Animation System | 02-Subsystems/ | Create new |
| Widget-Endpoint Map | 04-Development/ | Create new |
| Voice Interface | 02-Subsystems/ | Update (control-only constraint) |
| Presence System | 02-Subsystems/ | Update |
| Design Tokens | 05-Reference/ | Create new |
| Complete Redesign Implementation Plan | 03-Features/ | This document — updated |

---

## Next Steps

**Immediate (before any page code)**:
1. Confirm Fix 1, Fix 2, Fix 3 in this document are accepted (they are locked as mandatory)
2. Python Codebase Architect: confirm endpoint map + auth refresh contract + flag `/api/search/global` and audio-level gaps

**Week 1 (M0)**: Design tokens, state primitives, api-client with JWT refresh, router, event-bus, login page

**Week 2 (M1 — MVP)**: Shell (sidebar/topbar/orbit/command palette), SSE status, Presence page with real data only → **launchable MVP**

**Week 3 (M2)**: Chat with native streaming

**Week 4-5 (M3)**: Memory, Reasoning, Agency, Tasks, System, Permissions

**Week 6-7 (M4)**: Canvas graph + Voice control (Fix 1 verified)

**Week 8 (M5)**: Global search, notifications, a11y, PWA, legacy cleanup, final acceptance

---

## Confidence Scoring

| Area | Confidence | Notes |
| --- | --- | --- |
| Design System | 🟢 HIGH | Clear token specification; state primitives locked in Fix 2 |
| Page Implementations | 🟢 HIGH | Detailed specs; all endpoints confirmed to exist |
| Native Stack Fit | 🟢 HIGH | Matches modular event-driven backend; dependency policy principled |
| Auth Flow | 🟢 HIGH | Backend auth exists; refresh contract known (15min/7d) |
| Canvas Graph Performance | 🟡 MEDIUM | 200-node default de-risked; 1000-node stretch needs profiling |
| Streaming Chat | 🟢 HIGH | Backend SSE already proven; native ReadableStream well-supported |
| Voice Control Page | 🟢 HIGH | Fix 1 removes architectural risk; endpoints exist |
| Animation Coordination | 🟡 MEDIUM | 3-layer approach sound; requires discipline (no library fallback) |
| Legacy Migration | 🟡 MEDIUM | Route-swap strategy needed; double-SSE risk flagged |
| Timeline (8 weeks) | 🟡 MEDIUM | MVP at Week 2 realistic; later pages may slip if Graph/Voice expand |

---

## Final Recommendation

**Build now — MVP-first, with the three mandatory fixes locked.**

The native HTML/CSS/JS architecture is the right fit for Mai's modular backend. Fix 1 eliminates the Voice architectural error, Fix 2 eliminates blank-screen and auth gaps, and Fix 3 delivers a usable product in 2 weeks instead of 14. Start with M0 (design system + api-client with JWT refresh), gate on Shell + Presence, then iterate pages with the widget-to-endpoint audit as the per-page acceptance bar.
