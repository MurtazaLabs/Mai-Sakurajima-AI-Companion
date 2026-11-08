# Mai AI Documentation Vault

> **Obsidian Vault** for the Mai AI project — a production-oriented, modular AI companion inspired by Mai Sakurajima.

---

## Quick Navigation

### 📖 Start Here
- [[00-Overview/CURRENT_STATE]] — **Central reference: what Mai actually is and can do today (read this first)**
- [[00-Overview/Project Charter]] — Project constitution, engineering philosophy, specialist roles
- [[01-Architecture/01-System Overview]] — High-level architecture, scale, design principles
- [[01-Architecture/02-Application Boot & Lifecycle]] — 8-phase boot pipeline, validation, shutdown
- [[05-Reference/Complete Folder Structure]] — Full repository tree with file counts

### 🏗️ Core Architecture
- [[01-Architecture/01-System Overview]] — High-level architecture, scale, design principles
- [[01-Architecture/02-Application Boot & Lifecycle]] — 8-phase boot pipeline, validation, shutdown
- [[01-Architecture/03-Core Brain Kernel & State]] — Brain facade, OS kernel, event fabric, emotion, identity canon
- [[01-Architecture/04-Memory Subsystem]] — Pipeline, vector store, experience layer, retrieval
- [[01-Architecture/05-Knowledge Graph & Vault]] — Three-layer graph, beliefs, vault single-writer
- [[01-Architecture/06-Agency Reasoning LLM & Execution]] — Tools, agent, goals, dreaming, LLM failover, execution sandbox
- [[01-Architecture/07-Voice Subsystem]] — Full duplex pipeline, wake word, VAD, STT, TTS, interruption
- [[01-Architecture/08-API Native & Surface]] — REST/SSE/WS, security, native bridge, observability, prompt, plugins

### ⚡ Systems & Data Flow
- [[01-Architecture/09-Events & Data Flow]] — Event fabric (72 specs: 50 data.* + 22 state.*), state.* vs data.*, four data paths, post-think hooks
- [[01-Architecture/10-Status & Debt]] — Subsystem maturity, technical debt register, M-series gates, audit trajectory

### 🚀 Features & Integrations
- [[03-Features/Native OS Bridge Architecture]] — Daemon, tray, hotkeys, WS bridge, clipboard, FS, packaging
- [[03-Features/Discord Integration Plan]] — Bot architecture, message flow, deployment
- [[03-Features/Character Rename PRD]] — Trademark clearance, candidate scoring, migration roadmap

### 🛠️ Development
- [[04-Development/Testing Strategy]] — Test suite overview, behavior harness, evaluation framework
- [[04-Development/Deployment Guide]] — Docker, daemon installer, production hardening checklist

---

## Project Status (Nov 2026)

| Metric | Value |
|--------|-------|
| **Python files** | 383 — 80,024 lines incl. tests; 295 files / 56,366 lines excl. tests (measured Nov 8 2026) |
| **Subsystems** | 19 packages + 2 entry points |
| **Tests** | 2,035 collected; 2,033 passing + 2 skipped, 0 failures (live-verified Nov 8 2026, mai_env) |
| **Overall maturity** | ~83% (B+) |

### ✅ Complete Milestones
- **Character Layer M0–M13** — Canon volumes I–IV, behavioral validation harness, experience store, preference evolution, real-world evaluation, relationship dynamics on chat path, envelope-leak guard, experience-in-speech, conflict coherence
- **Core Platform** — Conversation (text+voice), long-term memory, knowledge graph + beliefs, vault compile, tool calling, multi-step agent, goals + auto-advance, dreaming, personality evolution, world model
- **Interfaces** — REST/SSE/WS, native Windows daemon (tray, hotkeys, watchdog), rate limiting, Docker, **desktop app shell (pywebview — M14, Oct 2026)**, HTTPS auto-gen by default + JWT auth opt-in on loopback / forced on non-loopback hosts, log rotation, graceful shutdown
- **P0/P1 Critical Fixes** — Deadlock risk, data races, belief drift, TOCTOU, bare excepts, thread safety — all P1 items resolved
- **Post-M13 sprints (Aug–Nov 2026)** — Vault remediation + ecosystem audit (Aug 6), P1 security remediation (Aug 12), Phase 0 whole-utterance VAD noise gate + live calibration (Oct 9), `LLM_PROVIDER` local-first + Ollama `think:false` + OpenRouter retry budget/model sanitization (Oct 9), Prometheus/OTel metrics endpoint (Oct 7), M14 desktop app (Oct 13), Oct-19 security bug audit remediated in full (SSRF, sandbox eval, auth cookies, XSS, redirect allowlist) with independent verification, voice latency stabilisation + self-hearing fix (Oct 27–29), Porcupine removal + openWakeWord install (Oct 31)
- **Production Hardening** — Rate limiting, HTTPS auto-gen by default + JWT auth opt-in on loopback / forced on non-loopback hosts, log rotation, graceful shutdown

### 🟡 In Progress / Partial
- **Echo cancellation** — `FullAEC` exists but has no playback feed; live mitigation is muting the recorder while speaking (see [[00-Overview/CURRENT_STATE]] §4)
- **openWakeWord** — installed, not wired; no "hey mai" model exists yet
- **Multi-session profiles / cloud sync** — `ProfileStore` + `SessionManager` exist; cloud sync not started
- **Discord (M24/M25)** — 82-line relay prototype only; `discord` package not installed
- **Entity web interface (v4.0)** — only `api/web/state/visual-state-adapter.js` exists
- **STT → Kyutai 1B** — built, but failed the RTF ≤ 0.7 gate (1.17–2.97 on the T1000); opt-in via `STT_BACKEND=kyutai`
- Roadmap M15–M26 — see [[03-Features/future-vision-roadmap]]

### ❌ Not Started
- Documentation site (MkDocs)
- Java/JavaFX desktop client
- WhatsApp integration (M26, official Agent Platform only)
- Continuity Engine (projects/commitments/checkpoints — M21)
- Cloud sync, screen/camera share, TTS voice bake-off (M15)

---

## Vault Conventions

- **Wiki-links** (`[[Page Name]]`) used throughout for cross-references
- **Numbered prefixes** (01-, 02-) for reading order within folders
- **Tags** for quick filtering: `#architecture`, `#memory`, `#voice`, `#api`, `#character`, `#debt`
- **Related** sections at bottom of each note link to next/previous in sequence

---

## Related External Docs

- `AGENTS.md` → [[00-Overview/Project Charter]] — **live source of truth for the session progress log**
- [[03-Features/Native OS Bridge Architecture]] · [[03-Features/Discord Integration Plan]] · [[03-Features/Character Rename PRD]]

---

*Last updated: November 8 2026 — refreshed against verified ground truth (2,033 tests passing / 2 skipped live, 383 py files / 80,024 lines). Covers post-M13 sprints through the Oct 31 voice/packaging changes. See [[00-Overview/CURRENT_STATE]] for the authoritative capabilities list.*