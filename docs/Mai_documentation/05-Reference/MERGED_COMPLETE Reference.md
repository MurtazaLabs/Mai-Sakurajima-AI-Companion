# MERGED_COMPLETE.md — Master Reference Document

> ⚠️ **Historical snapshot (Jul 20 2026) — source file no longer on disk.** `docs/MERGED_COMPLETE.md` (860 KB, 8,211 lines) was removed during doc consolidation; only this digest survives. Current sources of truth: [[00-Overview/Project Charter]] (session log, mirrors `AGENTS.md`), [[01-Architecture/10-Status & Debt]], and the subsystem notes in this vault.

---

## Overview

This was the **single source of truth** for all Mai AI architecture documentation on Jul 20, 2026 — created by merging 24 individual audit/architecture documents into one comprehensive reference.

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
- Event fabric (72 specs: 50 data.* + 22 state.*)
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

1. **Current truth** — read [[00-Overview/CURRENT_STATE]] first; it is the verified capabilities reference.
2. **For quick navigation** — use the vault's organized summaries ([[01-Architecture/01-System Overview|01-Architecture]] folder).
3. **For history** — the session log in [[00-Overview/Project Charter]] mirrors `AGENTS.md` and carries the dated record (M-series gates, audit scores, sprint outcomes). This digest only lists what the deleted master document used to contain.

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

The vault contains **curated, linked summaries** for daily navigation. This digest is **historical only** — it records what the Jul 2026 master document covered.

For anything current, use:
- [[00-Overview/CURRENT_STATE]] — what is implemented / partial / planned
- [[01-Architecture/10-Status & Debt]] — maturity, debt, gates
- [[00-Overview/Project Charter]] — dated session history

Do not cite this page as the authority for present-day behaviour.