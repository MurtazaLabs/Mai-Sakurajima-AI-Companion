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
| **Python files** | ~260 |
| **Lines of code** | ~45,000 |
| **Subsystems** | 18 packages + 2 entry points |
| **Tests** | ~1,900 passing |
| **Overall maturity** | ~82% (B+) |

### ✅ Complete Milestones
- **Character Layer M0–M13** — Canon volumes I–IV, behavioral validation harness, experience store, preference evolution, real-world evaluation, relationship dynamics on chat path, envelope-leak guard, experience-in-speech, conflict coherence
- **Core Platform** — Conversation (text+voice), long-term memory, knowledge graph + beliefs, vault compile, tool calling, multi-step agent, goals + auto-advance, dreaming, personality evolution, world model
- **Interfaces** — REST/SSE/WS, native Windows daemon (tray, hotkeys, watchdog), rate limiting, Docker, HTTPS + JWT auth-by-default, log rotation, graceful shutdown
- **P0/P1 Critical Fixes** — Deadlock risk, data races, belief drift, TOCTOU, bare excepts, thread safety — all P1 items resolved
- **Production Hardening** — HTTPS + JWT auth-by-default, rate limiting, log rotation, graceful SIGTERM handling, log rotation, graceful shutdown

### 🟡 In Progress
- Plugin ecosystem (manifest, lifecycle, marketplace, signing, sandbox)
- Multi-session profiles / cloud sync
- Knowledge enrichment (semantic chunking, chunk metadata)

### ❌ Not Started
- Documentation site (MkDocs)
- Performance profiling & optimization
- Embedding model versioning (fingerprinting)
- Cloud sync for multi-session

---

## Vault Conventions

- **Wiki-links** (`[[Page Name]]`) used throughout for cross-references
- **Numbered prefixes** (01-, 02-) for reading order within folders
- **Tags** for quick filtering: `#architecture`, `#memory`, `#voice`, `#api`, `#character`, `#debt`
- **Related** sections at bottom of each note link to next/previous in sequence

---

## Related External Docs

- `AGENTS.md` → [[00-Overview/Project Charter]]
- `docs/MERGED_COMPLETE.md` — 860KB+ merged reference (source of truth for deep dives)
- `docs/native-bridge-architecture.md` → [[03-Features/Native OS Bridge Architecture]]
- `docs/discord-integration-plan.md` → [[03-Features/Discord Integration Plan]]
- `docs/product/character-rename-prd.md` → [[03-Features/Character Rename PRD]]

---

*Last updated: September 2026 (post-M13, production-hardened)*