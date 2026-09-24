# MERGED_COMPLETE.md — Master Reference Document

> **Location:** `docs/MERGED_COMPLETE.md` (860 KB, 8,211 lines) — too large for vault, kept at repository root.

---

## Overview

This is the **single source of truth** for all Mai AI architecture documentation. It was created by merging 24 individual audit/architecture documents into one comprehensive reference on Jul 20, 2026.

**Size:** 860 KB | **Lines:** 8,211 | **Format:** Markdown

## Contents Summary

The document contains all of the following merged sections:

### Architecture & Design
- System architecture overview
- Application boot sequence (8 phases)
- Core brain, kernel, state, emotion, identity
- Memory subsystem (pipeline, vector store, experience)
- Knowledge graph, beliefs, vault compilation
- Agency, reasoning, LLM, execution
- Voice pipeline (full duplex, interruption, speaker ID)
- API surface (REST, SSE, WS, security)
- Native OS bridge (daemon, tray, hotkeys, clipboard, FS)
- Event fabric (67 specs, data.* vs state.*)
- Prompt architecture
- Plugin system

### Technical Debt & Audits
- V1 audit (Jul 19) — score 6.1 (C)
- V2 audit (Jul 19) — score 6.7 (C+)
- Post-fix audit (Jul 20) — score 8.2 (B)
- Multi-specialist audit (Jul 20) — score 7.5 (B)
- Ecosystem audit (Aug 6) — score 7.3 (B)
- P0/P1/P2/P3 remediation tracking

### Implementation Status
- Subsystem maturity matrix (17 subsystems)
- Feature completeness per roadmap
- M-series gates (M5–M13) with test counts
- Open technical debt register (D-1 through X-4)

### Session Progress Log
- Phases A–K (foundation through roadmap completion)
- Architecture evolution (ApplicationBuilder pattern)
- Native OS bridge (Phases 1–3)
- Event fabric (Phases 4–5)
- Vault remediation (Aug 6)
- Ecosystem audit + P0 remediation (Aug 6)
- Backlog remediation sprints 1 & 2 (Aug 6)
- Character layer M5–M13 (Aug 9)
- Runtime log remediation (Aug 9)
- TTS fix / boot log fixes (Aug 9)
- OS voice tool path (Aug 9)

---

## How to Use

1. **For quick navigation** — Use the vault's organized summaries ([[01-Architecture]] folder) which link to relevant sections
2. **For deep dives** — Open `docs/MERGED_COMPLETE.md` directly in your editor/IDE and search
3. **For AI-assisted work** — Feed relevant sections to your AI assistant as context

## Wiki Links

**Vault summaries that reference this doc:**
- [[01-Architecture/01-System Overview]]
- [[01-Architecture/02-Application Boot & Lifecycle]]
- [[01-Architecture/03-Core Brain Kernel & State]]
- [[01-Architecture/04-Memory Subsystem]]
- [[01-Architecture/05-Knowledge Graph & Vault]]
- [[01-Architecture/06-Agency Reasoning LLM & Execution]]
- [[01-Architecture/07-Voice Subsystem]]
- [[01-Architecture/08-API Native & Surface]]
- [[01-Architecture/09-Events & Data Flow]]
- [[01-Architecture/10-Status & Debt]]

**External references:**
- `docs/native-bridge-architecture.md` → [[03-Features/Native OS Bridge Architecture]]
- `docs/discord-integration-plan.md` → [[03-Features/Discord Integration Plan]]
- `AGENTS.md` → [[00-Overview/Project Charter]]

---

## Note on Vault Organization

The vault contains **curated, linked summaries** for daily navigation. The `MERGED_COMPLETE.md` remains the authoritative reference for:
- Historical audit trails
- Complete implementation status
- Detailed session progress
- Cross-cutting concerns that span multiple subsystems

When in doubt, **search MERGED_COMPLETE.md first** — it has everything.