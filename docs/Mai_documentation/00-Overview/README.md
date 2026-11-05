# Mai AI Documentation Vault

> **Obsidian Vault** for the Mai AI project — a production-oriented, modular AI companion inspired by Mai Sakurajima.

---

## Quick Navigation

### 📖 Start Here
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
- [[01-Architecture/09-Events & Data Flow]] — Event fabric (67 specs), state.* vs data.*, four data paths, post-think hooks
- [[01-Architecture/10-Status & Debt]] — Subsystem maturity, technical debt register, M-series gates, audit trajectory

### 🚀 Features & Integrations
- [[03-Features/Native OS Bridge Architecture]] — Daemon, tray, hotkeys, WS bridge, clipboard, FS, packaging
- [[03-Features/Discord Integration Plan]] — Bot architecture, message flow, deployment
- [[03-Features/Character Rename PRD]] — Trademark clearance, candidate scoring, migration roadmap

### 🛠️ Development
- [[04-Development/Testing Strategy]] — Test suite overview, behavior harness, evaluation framework
- [[04-Development/Deployment Guide]] — Docker, daemon installer, production hardening checklist

---

## Project Status (Sep 2026)

| Metric | Value |
|--------|-------|
| **Python files** | 376 (measured Oct 25 2026) |
| **Lines of code** | 66,767 |
| **Subsystems** | 19 packages + 2 entry points |
| **Tests** | 1,990 passing + 2 skipped, 0 failures (live-verified Oct 25 2026, mai_env) |
| **Overall maturity** | ~83% (B+) |

### ✅ Complete Milestones
- **Character Layer M0–M13** — Canon volumes I–IV, behavioral validation harness, experience store, preference evolution, real-world evaluation, relationship dynamics on chat path, envelope-leak guard, experience-in-speech, conflict coherence
- **Core Platform** — Conversation (text+voice), long-term memory, knowledge graph + beliefs, vault compile, tool calling, multi-step agent, goals + auto-advance, dreaming, personality evolution, world model
- **Interfaces** — REST/SSE/WS, native Windows daemon (tray, hotkeys, watchdog), rate limiting, Docker, **desktop app shell (pywebview — M14, Oct 2026)**, HTTPS auto-gen by default + JWT auth opt-in on loopback / forced on non-loopback hosts, log rotation, graceful shutdown
- **P0/P1 Critical Fixes** — Deadlock risk, data races, belief drift, TOCTOU, bare excepts, thread safety — all P1 items resolved
- **Post-M13 sprints (Aug–Oct 2026)** — Vault remediation + ecosystem audit (Aug 6), P1 security remediation (Aug 12), Phase 0 whole-utterance VAD noise gate + live calibration (Oct 9), `LLM_PROVIDER` local-first + Ollama `think:false` + OpenRouter retry budget/model sanitization (Oct 9), Prometheus/OTel metrics endpoint (Oct 7), M14 desktop app (Oct 13), Oct-19 security bug audit remediated in full (SSRF, sandbox eval, auth cookies, XSS, redirect allowlist) with independent verification
- **Production Hardening** — Rate limiting, HTTPS auto-gen by default + JWT auth opt-in on loopback / forced on non-loopback hosts, log rotation, graceful shutdown

### 🟡 In Progress
- Java/JavaFX desktop client (M14 revision — replaces pywebview shell; pending JDK install + P1 go)
- STT → Kyutai 1B (Phase 1 RTF benchmark pending go/​no-go)
- Plugin ecosystem (manifest, lifecycle, marketplace, signing, sandbox)
- Multi-session profiles / cloud sync
- Roadmap M15–M25 — see [[03-Features/future-vision-roadmap]]

### ❌ Not Started
- Documentation site (MkDocs)
- Performance profiling & optimization
- Embedding-service **cache** fingerprinting (chunk-level `embedding_hash` already shipped in the chunker)

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

*Last updated: October 25 2026 — refreshed against verified ground truth (1,990 tests live, 376 py files / 66,767 lines). Covers post-M13 sprints through the Oct 19 security remediation.*