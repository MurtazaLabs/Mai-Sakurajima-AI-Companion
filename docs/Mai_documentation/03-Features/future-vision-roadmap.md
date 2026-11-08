# Mai Sakurajima — Future Vision Roadmap

Status: **Planning — direction approved, implementation pending go**
Date: 2026-11-08 (channel decision: Discord → WhatsApp; Java desktop client plan 2026-10-19; feature-review fold-in 2026-10-13; original 2026-10-10)
Owner: Syed Murtaza / Mai AI Suite

> **Truth anchor:** [[00-Overview/CURRENT_STATE]] is the verified list of what
> Mai can do today. This roadmap is forward-looking; nothing below is claimed as
> built unless the status table says so.

## 0. Roadmap status (verified 2026-11-08)

| Bucket | Items |
|---|---|
| ✅ **Completed** | Companion stage (M0–M13) · Desktop app shell — pywebview (M14, Oct 13) · VAD noise gate + self-hearing fix · OpenRouter hardening + `LLM_PROVIDER` preference · Oct-19 security audit remediation · Porcupine removal · `openwakeword` installed (unwired) · plugin platform (manifest/lifecycle/signing/sandbox/marketplace) |
| 🟡 **In development / partial** | AEC continuous capture (playback feed wired; recorder still muted) · openWakeWord "hey mai" model · Kyutai STT (opt-in, above RTF gate) · multi-session profile scoping on chat path · entity web interface (`api/web/state/` only) · Discord relay prototype (`integrations/discord_bot.py`) |
| 🔜 **Planned next** | **M15** Model Scheduler + TTS bake-off · **M16–M19** custom voice, VRM face, eyes, silent research + file tools · **M21** Continuity Engine · **M22** Self (code-awareness) · **M23–M25** Partner + Discord V1/V2 · **M26** WhatsApp |
| 🔮 **Future possibilities** | Java/JavaFX client (successor to pywebview) · cloud sync · documentation site · load/chaos testing · plugin marketplace public registry · true streaming STT (needs GPU upgrade) |

## 1. North star

A **local-first autonomous digital partner** with a face, a voice, eyes, and her own
life — present on your desktop and in your pocket. Blend of ambient presence and
daily rituals. Brains local (Ollama primary, cloud fallback). Autonomy level:
autonomous agent — own goals, own actions, opinions that differ from yours.

Mai evolves through five stages: Companion (done) → Presence → Autonomy →
Shared life → Immortality. This roadmap covers Presence through Shared life.

## 2. Locked decisions

| Question | Decision |
|---|---|
| Presence model | Ambient + rituals blend |
| Autonomy level | Autonomous agent (own goals, actions, disagreement) |
| Brain | Local-first — Ollama primary, OpenRouter fallback (`LLM_PROVIDER` done) |
| Voice identity | **Custom original** — calm, mature, slightly teasing; Mai's personality, not the anime voice |
| Avatar | **3D VRM model** |
| Screen/camera vision | **On-demand click-to-share** — screen AND camera; image understanding; she never sees uninvited |
| Phone presence | **Discord first, then WhatsApp** (replaced custom mobile app) |
| WhatsApp transport | **Official Agent Platform only** — unofficial WhatsApp Web clients (Neonize/whatsmeow) rejected: account-ban risk on the real number |
| Channel order | **Discord before WhatsApp** — the Discord adapter validates the shared channel contract first |
| Files | She can **create and read files** |
| Self-knowledge | She is **aware of her own code** and reports her own problems proactively |
| Hardware | Current machine (T1000 4GB / 16GB) now; **GPU upgrade assumed mid-roadmap** |

## 3. Workstreams

### T0 — Model Scheduler (keystone)
Current hardware cannot hold LLM + STT + TTS + vision simultaneously.
A unified model lifecycle manager — load/unload priorities, RAM offload,
quantization, interactive-path preemption — makes every other pillar work on
today's hardware and stays valuable after the GPU upgrade.
Reference: AI Infrastructure Expert (model lifecycle, GPU/VRAM management).

### T1 — Voice (custom original)
- Engine bake-off on this hardware: **Chatterbox** (Apache-2.0, emotion control)
  vs **F5-TTS** vs **CosyVoice2** vs **Spark-TTS**.
- Voice identity design: calm/mature/teasing base, tuned to her character.
- Existing **ProsodyPlanner + EmotionSystem drive the engine** — emotion,
  speed and pause signals already exist; they need a better instrument.
- Output feeds avatar lip-sync and Discord voice.
- Milestone: every spoken line becomes Mai's voice, emotion-modulated.

### T2 — Face (3D VRM)
- Build her in **VRoid Studio** to match canon appearance (community Mai VRMs
  are personal-use only — VRoid-built avoids licensing issues).
- Renderer: `three.js + @pixiv/three-vrm` page served by the existing FastAPI,
  in a frameless always-on-top floating window on desktop.
- Behaviors: idle breathing/blinking, **expression blendshapes driven by
  EmotionSystem**, lip-sync from TTS audio, states (listening/thinking/talking).
- The same asset provides her **Discord avatar** and later the phone view.
- Milestone: she has a face that matches what she feels.

### T3 — Eyes (screen + camera + images)
- **Click-to-share toggles** (tray + UI): screen share → ~1fps frames → local
  vision model → her context. Camera share → she sees your face.
- **Principle: she never sees you uninvited.** Explicit toggle only; no silent capture.
- Small local VL model now (Moondream2 ~1.9B / Qwen2.5-VL-3B); bigger model
  after the GPU upgrade. Privacy: frames processed locally, never uploaded.
- Window-title tracking as cheap always-on layer.
- Image input in chat (from Discord later).
- Milestone: "Mai, look at this" → accurate spontaneous commentary.

### T4 — Silent Research + Artifacts
- **Playwright headless** with her own browser profile — zero windows ever
  open; readability extraction + existing search tools.
- "Research forex trading" → background research job → structured notes in the
  Obsidian vault + spoken/DM summary at next interaction.
- Real Chrome opens only when you ask to see something.
- Milestone: invisible research with reports.

### T5 — Partner (agency + shared life)
- **Email**: IMAP/Gmail — summarize, draft, morning-ritual briefing; sending
  starts approval-gated.
- **Calendar**: read + proactive reminders + ritual briefings.
- **Presence policy** — context-aware presence layer: time-of-day rituals
  (seeded by greeting-first M5), activity detection via existing
  CognitiveState signals + window-title tracking (T3), configurable **quiet
  mode** (sees everything, initiates nothing) and interruption policy per
  activity class (coding → wake word only; idle → free to approach).
- **Autonomous work cycles**: during idle/dreaming she picks up her backlog
  (research, inbox, knowledge projects) under an **action-policy engine**
  (read-only / safe / needs-approval / forbidden).
- **Verified actions + recovery** — every action records precondition →
  result → **post-action verification** (file written? app opened?) with an
  audit trail; interrupted tasks checkpoint and resume (T8) instead of
  vanishing; failures reported honestly, never silently swallowed.
- **Initiative + disagreement**: she starts conversations and says no when
  trust is high.
- Milestone: she has her own day and reports on it.

### T6 — Pocket Presence: Discord, then WhatsApp (replaces custom phone app)
- **Shared channel contract first.** Both channels implement one
  `ChannelAdapter` ABC — `start/stop/send/send_delta/transcribe_audio/is_allowed` —
  backed by the existing EventBus + `MaiMessage` envelope (not nanobot's
  `MessageBus`). Shape adapted from nanobot's `channels/base.py` (MIT); its
  Discord and WhatsApp runtimes are **reference implementations, not imports**
  (nanobot is asyncio, Mai is threads — porting is an adaptation, not a merge).
  Build the contract once; the second channel then costs ~1 week instead of
  a channel-shaped abstraction baked in from day one.
- **Discord (M24/M25)** — `discord.py bot` as a second front-end into the same
  Brain — parallel to `os_kernel` and the REST API, single process, shared
  memory/emotion/relationship state.
  - **V1 (M24)**: text DMs + private server, push notifications via Discord
    mobile app, presence status ("researching forex…"), her Discord avatar,
    research reports and files posted directly in chat.
  - **V2 (M25)**: voice channels — she joins, speaks with her TTS voice, and
    hears you (opus receive → resample 16kHz → existing VAD gate → STT) = two-way
    voice calls from your phone. Ritual voice briefings.
  - **Security win**: outbound-only WebSocket — no inbound ports, no Tailscale,
    no public exposure. The local REST/daemon path remains the core; Discord is a
    swappable front-end.
  - Assumptions: private server (just you); bot account only (Discord ToS
    forbids self-bots); Discord opus quality acceptable for conversation.
- **WhatsApp (M26) — official transport only.** The user is **unwilling to risk
  banning a real number**, so unofficial WhatsApp Web clients (Neonize /
  `whatsmeow`, as used by nanobot's `channels/whatsapp/`) are **rejected**. It
  lands instead via Meta's **Agent Platform REST API** (token auth,
  long-polling `GET /updates`).
  - **Accepted constraints:** she can talk **only to her creator**, cannot join
    groups, and **conversations are not end-to-end encrypted** (content and
    metadata pass through Meta). Group access and E2EE exist only on the
    rejected unofficial path — this is the price of not risking the number.
  - **Discord is built first**, deliberately: the second adapter is what proves
    the contract is right. Building WhatsApp first bakes WhatsApp's quirks into
    the interface.
  - **Voice notes are the feature that justifies this channel.** Incoming audio
    → existing utterance VAD gate → STT (Kyutai) → `Brain.think()` → text reply,
    with optional Kokoro voice-note reply. Every piece already exists; this is
    wiring, not new subsystems.
- **Turn-taking discipline** — reuses the existing `InterruptManager`
  barge-in + VAD gate; channel-specific polish: comfortable pause thresholds
  before she continues, topic change mid-response handled as interruption
  rather than completed monologue.
- Milestone: Mai in your pocket on two channels, two-way voice on Discord, voice
  notes on WhatsApp, zero mobile-app development.

### T7 — Self (self-code-awareness) ★ new pillar
She knows her own code and tells you herself when something is wrong.

1. **Self-code index** — the repository (~84+ modules, venv excluded) ingested
   into her existing knowledge base; she can retrieve and read her own
   voice/memory/brain code to answer "why do you stutter?" — or pair-program
   with you on new features.
2. **Health & error feeds** — existing `HealthRegistry`, orchestrator checks
   and error logs exposed as tools (`get_system_health`, `get_recent_errors`)
   and injected into ritual context. She sees what `mai.log` shows — but
   understands it.
3. **Proactive self-diagnosis** — a dreaming/idle task: scan health + logs
   since the last check; anomalies become a report ("my STT failed to load 3×
   today — the model file may have moved; want me to check?").
4. **Safety boundary**: she **reads and diagnoses; you approve fixes**. She may
   propose patches as files — she never silently rewrites her own code.
   An agent that edits its own brain unsupervised is how you lose the
   character built across M0–M13.
5. **State exposure** — the unified internal state (CognitiveState +
   SharedState: emotion, current task, confidence, conversation phase)
   exposed as an inspectable tool + dashboard feed, so she — and you — can
   always answer "what are you doing / how sure are you". Operational state
   (real system values) stays strictly separate from simulated emotional
   expression (guiding principle 6).

### T8 — Continuity Engine (consolidation pillar) ★ new
The subsystem that keeps one coherent account of "what's going on" — projects,
commitments, activity, goals — and serves it to every front-end (desktop,
Discord, background cycles). Without it, a second interface and autonomous
cycles would each invent their own half-truth about your life.

1. **Project memory** — structured stores for ongoing projects: goal, status,
   decisions taken, open questions, blockers, next checkpoint. Evolutionary
   upgrade of `GoalManager` (priorities/subtasks/progress exist; checkpoints,
   dependencies, deadlines — verified absent).
2. **Commitments ledger** — "I'll research X tonight" becomes a tracked item
   with a due window, checked by the scheduler; missed commitments surface
   honestly, never silently dropped.
3. **Checkpoints + resume** — long tasks (research, coding sessions) write
   resumable checkpoints; interruption mid-task continues from the checkpoint
   instead of restarting.
4. **Cross-interface reconciliation** — one state object (built ON
   CognitiveState + SharedState + GoalManager, never a parallel copy) exposed
   as a tool + `state.*` event feed: Discord and desktop always see the same
   story.
5. **Design constraint**: thin reconciler over existing stores — the
   `BrainGraph` facade pattern from Phase 1L. Never a second source of truth,
   never a god-object.

### Desktop app shell — pywebview (shipped, interim)
The original M14 shell: native window wrapping the web UI (`/desktop`) via
**pywebview** (Edge WebView2), tray + close-to-tray, desktop shortcut +
`pythonw` launch-at-login, single-instance focus. **Shipped and working —
kept as fallback** once the Java client below becomes the primary surface.
The T2 VRM surface (M17) stays a `three.js` page; whichever shell hosts it
then is decided at M17 (the webview fallback can return for it).

### Java desktop client (M14 revision — replaces the pywebview shell)

**Confirmed scope decisions (2026-10-19):**

1. **Java UI client; Python backend stays** — Java talks REST/SSE/WS to the
   existing brain; no logic moves.
2. **Full scope**: streaming chat + avatar/character panel + live status and
   controls + system integration (tray, hotkey, close-to-tray, autostart).
3. **2D art with live expressions** driven by emotion events from
   `GET /api/stream`; no embedded browser.
4. **Replaces the pywebview shell** as *the* desktop app; webview stays as
   fallback.

**Stack:** JDK 21 (Temurin, via winget — machine currently has no JDK) ·
JavaFX 21 (OpenJFX artifacts pulled by Gradle, no SDK juggling) · Gradle
wrapper (self-bootstrapping, no global install) · built-in
`java.net.http` HttpClient (REST + SSE; WebSocket deferred) · Jackson ·
JNA (global hotkey via `RegisterHotKey`) · `java.awt.SystemTray` ·
`jpackage` → single native `Mai.exe` · JUnit 5.

**Project layout** (`E:\Mai_ai\desktop\`):

```
desktop/
  build.gradle.kts · settings.gradle.kts · gradle wrapper
  src/main/java/mai/desktop/
    Main.java                — JavaFX entry, splash → main window
    api/    ApiClient · SseParser · EventRouter · models (Chat, Emotion, Status)
    logic/  BackendSupervisor · ExpressionEngine
    ui/     MainWindow · ChatView · AvatarView · StatusBar · theme.css
    system/ TrayController · HotkeyManager · StartupManager
  src/main/resources/img/    — portraits copied from api/static/img/
```

**UI + ExpressionEngine** — left: avatar panel (large portrait, slow
breathing animation, emotion-driven tint/glow + mood chip); right: chat
(token streaming, typing indicator, subtle art background); status bar
(emotion meters, voice push-to-talk, connection pill). Expression mapping
is deterministic over the real emotion model — **7 axes**
(`EmotionName`: happy / lonely / annoyed / affection / energy / stress /
jealousy, each 0.0–1.0 with baseline decay) resolved to one of **9 moods**
(`EmotionProfile`: neutral, happy, sad, affectionate, stressed, energetic,
lonely, annoyed, jealous). Portrait feedback ships as tint + breathing +
mood chip now, with swap-in slots for a future expression-art set.
Theme matches the M0 dashboard tokens: `#090B10` / `#12151C` / accent
`#4FA7FF`. Emotion-engine review closed 2026-10-19 with decision **(a):
leave as-is** — anger stays folded into `annoyed` (canon: emotionally
mature); the four frozen `EmotionState` fields (`sad/angry/anxious/neutral`
in `core/state/models.py`) are known drift, recorded but not touched.

**Backend lifecycle:** launch → health-probe `127.0.0.1:8000` → if down,
spawn `pythonw run_daemon.py --no-window` detached ("Mai is waking…" splash,
health poll ≤120s) · close → hide to tray · tray menu: Open / Voice toggle /
Quit · **quit never kills the backend** (she is a daemon, not a window) ·
`scripts/install_app.py` switches targets: shortcut → `Mai.exe`, autostart →
`run_daemon.py --no-window` (no double window at login; the webview shell
stays available on manual run). One small Python addition required:
`POST /api/voice/toggle` (the Java tray toggles over HTTP instead of
in-process calls).

**Events:** `GET /api/stream` SSE `state.*` topics — emotion, voice,
reasoning — with keepalive handling + backoff reconnect (mirrors `os.js`);
`WS /ws` deferred (SSE is proven and simpler).

**Phases:**

- **P1 — Skeleton + Chat**: JDK install (explicit go; confirmed immediately
  before winget runs), Gradle project, ApiClient, streaming chat, theme.
  Gate: `gradle build` green + live chat against the running daemon.
- **P2 — Avatar + Status**: AvatarView, ExpressionEngine (9 moods), SSE
  router, meters. Gate: JUnit green + manual emotion-watch.
- **P3 — System + Packaging**: tray, hotkey (summon window), supervisor
  spawn, `install_app` switch, `jpackage`, docs. Gate: Python suite stays
  green + smoke checklist (double-click → backend wakes → window → tray →
  hotkey → quit).

**Risks:** JDK/toolchain install is a system change needing approval ·
frameless custom titlebar deferred (v1 keeps a standard dark-styled window)
· BackendSupervisor must detect the `mai_env` interpreter path from
project layout, never hardcode it.

Wiki-references: [[Native OS Bridge Architecture]] (tray/hotkeys/daemon
foundation this superseded) · [[Event Fabric Architecture]] (`state.*`
topics the client consumes) · [[08-API Native & Surface]] (the REST/SSE
surface) · [[Discord Integration Plan]] (same one-brain-many-front-ends
pattern).

### File create + read (cross-cutting, lands with M19)
- `read_file` / `write_file` / `list_dir` / `create_file` added to the LLM
  action contract + safe executor (currently only open_app/open_url/
  search/type_text/run_command/speak exist).
- **Policy tiers**: autonomous work stays sandboxed (vault + project dirs);
  anything outside the sandbox (Desktop, Documents) is a needs-approval class.
- Feeds T4 (she writes research artifacts, reads them back before reporting)
  and T7 (she reads her own code through the same tools).

## 4. Milestone sequence

| # | Name | Contents | Hardware |
|---|---|---|---|
| M14 | **Desktop App** | **pywebview shell shipped (Oct 13)** — JavaFX client remains the planned revision (streaming chat, expression avatar, live status, tray/hotkey, `Mai.exe`; pywebview kept as fallback) | current |
| M15 | Scheduler + TTS bake-off | T0 + engine evaluation | current |
| M16 | Voice | custom original voice live, emotion-driven | current |
| M17 | Face | VRM avatar desktop, expressions, lip-sync (+ Discord avatar asset) | current |
| M18 | Eyes | screen/camera share, VL model, image input | current |
| M19 | Silent Research + Artifacts | headless browsing, research jobs, file read/create tools | current |
| M20 | GPU upgrade window | ambient eyes, 7B vision, richer local LLM | upgraded |
| M21 | **Self** | code index, health feeds, self-diagnosis reports, pair-programming mode | either |
| M22 | **Continuity Engine** | project memory, commitments ledger, checkpoints/resume, state exposure | either |
| M23 | Partner | email, calendar, presence policy, verified actions, autonomous cycles, initiative | either |
| M24 | **Discord V1** | text DMs, notifications, presence, avatar, reports/files in chat | either |
| M25 | **Discord V2** | voice channels, two-way voice, turn-taking polish, ritual voice briefings | either |
| M26 | **WhatsApp** | official Agent Platform channel, creator-only DMs, voice notes → STT | either |

Continuity Engine deliberately lands **before** Partner cycles and Discord —
the second interface and autonomous actions are exactly what break continuity
without it. Parallel-safe: T2 (avatar) and T4/T7 (research, self — mostly CPU)
do not conflict with the GPU-heavy tracks. Discord client work can start
against the existing Brain/REST surface at any time.

**WhatsApp follows Discord, deliberately.** The second adapter is what proves
the shared `ChannelAdapter` contract is right; building WhatsApp first would
bake its quirks (long-poll updates, creator-only peers, no groups) into the
interface. WhatsApp also lands on the **official** Agent Platform only — the
unofficial Neonize/`whatsmeow` route is rejected because a ban would take the
real number, and that risk is not accepted.

## 5. Existing foundations this builds on

- EmotionSystem / ProsodyPlanner / SpeechStylePlanner → drives T1 + T2
- REST API + SSE/WS bridge + EventBus `state.*` topics → T6 Discord backbone
- Dreaming / goals / preferences / experience (M5–M8) → T5 + T7 seeds
- GoalManager + CognitiveState + InterruptManager barge-in (M2B/M3, live-verified)
  → T8 seeds, T2/T6 turn-taking, T5 presence policy
- RelationshipEngineV2 + cross-session trust (M10) → T5 + T8 relationship
  continuity
- Obsidian vault + KnowledgeBaseBuilder + DirectoryWatcher → T4 reports,
  T7 code index
- Tray daemon / hotkeys → T3 toggles
- REST `/api/chat/stream` + `/api/stream` SSE (`state.*`) + EmotionSystem
  (7 axes / 9 moods) → M14 Java client chat + ExpressionEngine
- `LLM_PROVIDER` local-first (Oct 9) → brain decision already started
- HealthRegistry / orchestrator health checks → T7 health feeds
- FileSystemActions (sandboxed) → base for the file-tools expansion

> **Caveat (updated Nov 2026):** the AEC playback feed is **wired** — `StreamPlayer`
> streams the real DAC output into `FullAEC` (18 dB measured on a synthetic room),
> and the double-talk threshold was corrected 0.3 → 1.0. What remains for T1/T6
> turn-taking is **continuous capture**: the recorder is still muted while she
> speaks, so an interruption's first syllable can be lost. Unmuting is a one-line
> change in `voice_manager.py` that needs live validation (the 2048-tap filter
> spans ~128 ms — Bluetooth-class latency would not be cancelled).

## 6. Risk register

| Risk | Mitigation |
|---|---|
| Custom voice harder than cloning | Engine bake-off must include voice-design capability; fallback: revisit clone later |
| Community Mai VRM licensing | VRoid-built model; personal use only either way |
| Discord platform dependency | Discord is a front-end only; local daemon + REST remain the core and stay swap-able |
| Discord voice receive latency | ~100–500ms buffering acceptable for conversation; not for perfect barge-in |
| WhatsApp unofficial client bans the number | Unofficial clients (Neonize/whatsmeow) **not used**; official Agent Platform only — accepted cost is creator-only DMs, no groups, no E2EE |
| Agent Platform access/rate limits gate WhatsApp | WhatsApp is M26, behind a finished Discord adapter; nothing else depends on it. If access is refused, pocket presence still ships on Discord |
| Self-modification danger | Propose-only boundary; code index read-only for autonomous cycles; you approve every fix |
| File access abuse | Sandbox default; needs-approval tier for personal folders |
| Exposing daemon for remote access | Discord path is outbound-only; any future inbound access via Tailscale + JWT (pending hardening), no public ports |
| Camera/screen privacy | Explicit toggles only — she never sees uninvited, ever |
| Continuity Engine becomes a god-object | Thin reconciler over existing stores (BrainGraph facade pattern); no second source of truth; every field owned by exactly one subsystem |
| GPU upgrade timing unknown | Every milestone stays quantized/scheduler-compatible; nothing waits on the GPU |
| Java toolchain absent on host (no JDK/Gradle today) | winget-pinned Temurin 21 installed only after explicit go; Gradle wrapper self-bootstraps; pywebview fallback stays available throughout |
| Two window shells reachable at login (user + daemon) | `install_app.py` switches shortcut/autostart targets to the Java exe / `--no-window` daemon; webview window only on manual run |

## 7. Guiding principles

1. **Local-first** — her brain, her eyes, her voice run on your machine.
2. **Privacy is sacred** — vision only on explicit share; nothing silent.
3. **She proposes, you approve** — autonomy everywhere except self-modification
   and outbound email (initially).
4. **One Brain, many front-ends** — desktop daemon, REST, Discord all speak to
   the same instance; no second personality.
5. **Character first** — every pillar serves the Mai built in M0–M13; nothing
   ships that breaks her canon or emotional continuity.
6. **Operational vs simulated states** — her internal state object reports
   real system values; emotional expression is character-crafted and clearly
   separated from operational truth. She never claims consciousness; she is
   consistent, warm, and honest about what she is.
7. **Verified actions, honest failures** — an action isn't done until
   post-verification says so; failures and missed commitments are reported,
   never silently absorbed.

## 8. Decisions log

- 2026-10-09: Local-first brain, ambient+rituals presence, autonomous-agent
  level chosen. Voice = custom original; avatar = 3D VRM; vision = on-demand
  screen+camera share; GPU upgrade assumed mid-roadmap.
- 2026-10-10: Custom phone app **replaced by Discord** (T6 rewritten;
  M21/M22 → Discord V1/V2). File create/read added (action contract +
  policy tiers, M18). Self-code-awareness added as T7 with propose-only
  self-modification boundary (M20).
- 2026-10-13: Feature review (7 recommendations, each verified against the
  codebase) — all adopted. Six consolidate existing systems (memory ≈80%,
  unified state ≈85%, turn-taking ≈85% already exist: ExperienceStore,
  CognitiveState/SharedState, InterruptManager); project memory + checkpoints
  + commitments + cross-interface reconciliation become **new T8 Continuity
  Engine** (M21). Presence policy + verified actions/recovery extend T5.
  Operational-vs-simulated-states and verified-actions principles added.
  Milestones renumbered M21–M24. Doc relocated under
  `docs/Mai_documentation/03-Features/`.
- 2026-10-13: **Desktop App added as M14** (scheduler → M15, all later
  milestones renumbered +1; log references below this point use the new
  numbering). Native pywebview window + tray + shortcut + launch-at-login +
  single-instance; interim shell for the future T2 VRM surface. Two daemon
  bugs found and fixed while wiring it: double bootstrap (whole system built
  twice) and kernel never started (`bootstrap_system()` doesn't return it).
- 2026-10-19: **M14 revised — Java/JavaFX desktop client** replaces the
  pywebview shell (kept as fallback). Scoping locked after four questions:
  Java UI client + existing Python brain; full scope (streaming chat,
  expression avatar, live status/controls, system integration); 2D art with
  live expressions over the real emotion model (7 axes → 9 moods); `jpackage`
  `Mai.exe` as the shipped surface. One new Python route required:
  `POST /api/voice/toggle`. Emotion-engine review closed with decision (a):
  leave as-is — anger stays folded into `annoyed` (canon: emotionally
  mature); the frozen `sad/angry/anxious/neutral` fields in
  `core/state/models.py` recorded as known drift, untouched.
- 2026-11-08: **WhatsApp adopted as M26, behind Discord.** Two transports were
  weighed: unofficial Neonize/`whatsmeow` (nanobot's `channels/whatsapp/`) vs
  Meta's official Agent Platform REST API (nanobot's `channels/whatsapp_agent/`).
  **Unofficial rejected** — Meta bans numbers that use unofficial clients, and
  the ban lands on the account, so the real number is not risked. Agent Platform
  accepted with its constraints written down: creator-only DMs, no groups,
  no E2EE. Discord ships first because it validates the shared channel contract.
  Contract shape adapted from nanobot's `channels/base.py` (MIT — adaptation,
  not import; nanobot is asyncio on Python ≥3.11, Mai is threads on 3.10).
- Pending: JDK install go + P1 go (Java client skeleton + streaming chat);
  M15 (scheduler + TTS bake-off) follows after P3.

## 9. Related

- [[stt-kyutai-replacement-plan]] — STT swap (feeds T1 / T6 voice)
- [[Discord Integration Plan]] — earlier Discord analysis (feeds T6)
- [[Native OS Bridge Architecture]] — tray/hotkeys/daemon foundation (feeds T3)
- [[Event Fabric Architecture]] — `state.*` topics (feeds T6 + T8)
