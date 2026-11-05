# 10 — Implementation Status & Open Debt

> Digest of `IMPLEMENTATION_STATUS.md` + `TECHNICAL_DEBT.md`. Refreshed against verified ground truth **Oct 25 2026** (1,990 tests live, 376 py files / 66,767 lines).

---

## Subsystem Maturity (counts Oct 25 2026, 1,990 tests passing)

| Subsystem | Files | Lines | Maturity | Notes |
|-----------|-------|-------|----------|-------|
| core/ | 66 | 13,729 | 88% | Brain/kernel/fabric mature; P0 deadlock + belief drift resolved; stream guard on `think_stream` |
| memory/ | 28 | 5,886 | 82% | strong pipeline; layer breach narrowed (3 lazy imports, 2 files) |
| knowledge/ | 29 | 5,144 | 82% | vault pipeline strong; D-1 belief drift **resolved**; graph 3-layer overlap remains |
| voice/ | 32 | 3,526 | 84% | full duplex + Phase 0 utterance gate; former P2s (listen(), AEC feed, `_valid_audio`, dead param) all resolved |
| api/ | 24 | 4,084 | 88% | ~100 endpoints; HTTPS-by-default (auto dev certs), metrics endpoint, Oct-19 security fixes |
| agency/ | 12 | 2,264 | 92% | cleanest subsystem; dreaming TOCTOU fixed |
| app/ | 18 | 2,021 | 96% | builder pattern gold standard |
| llm/ | 4 | 1,262 | 80% | `LLM_PROVIDER` preference, bounded retry budget, mid-stream failover with history |
| observability/ | 3 | 702 | 84% | HealthRegistry gold standard; heartbeat-based stalling |
| execution/ | 4 | 744 | 92% | sandbox + whitelists solid; confirm gate injectable |
| reasoning/ | 5 | 735 | 85% | journal JSONL, cadence-gated reflection, ThoughtPacket leak guard |
| native/ | 7 | 516 | 85% | tray/hotkeys/watchdog + M14 AppWindow shipped |
| scripts/ | 7 | 773 | 65% | maintenance tooling + M9 eval runner + installer |
| plugins/ | 14 | 3,505 | 65% | ecosystem growing (web_scraper SSRF-guarded, marketplace, signing) |
| config/ | 21 | 1,181 | 96% | leaf settings (`LLM_PROVIDER`, `STT_BACKEND`, gate thresholds) |
| prompt/ | 7 | 280 | 94% | clean stateless |
| evaluation/ | 5 | 662 | 88% | M9 real-world harness |
| integrations/ (gateways) | 1 | 63 | 35% | experimental Discord bot |

**Overall: ~83% (B+)** — production-ready core with P0/P1 issues resolved.

## Open Technical Debt (Priority Map — verified Oct 25 2026)

| Priority | Items |
|----------|-------|
| Fix this sprint | D-2 `memory/→knowledge/` breach (3 lazy imports, 2 files), P-3 belief fan-out in retriever, P-4 age-cap flattening, P-5 embedding-clearing cache fingerprinting (chunk `embedding_hash` already shipped) |
| Next quarter | D-3 graph 3-layer collapse, X-2 import-time side effects |
| Backlog | M-1 dead `MemoryObject.lock`, M-2 unused `embeddings` field, M-3 `MemoryNode` duplication, M-4 `_text_overlap`, K-3 MD5→SHA-256, O-3 `stats.md` reflections, X-4 `_result()` duplication |
| **Resolved since Sep** | ~~D-1 belief drift~~ (Aug 12 — BrainGraph delegates to BeliefEngine), ~~P-5 chunker fingerprinting~~ (embedding_hash per chunk), ~~P-3 journal quadratic rewrites~~ (JSONL append), ~~V-1 `listen()` refactor~~, ~~V-4 AEC live feed~~ (`add_playback` wired), ~~Legacy Memory `Lock()`~~ (RLock verified), ~~L-1 `generate_with_tools()` dead passthrough~~ (was mislabeled — it is live on the Brain path) |

Key pillars to avoid regressions: RLock discipline everywhere, HealthRegistry fail-safe, graceful degradation at every boundary.

## Feature Maturity Per Roadmap

✅ **Complete** — conversation (text+voice, noise-gated), long-term memory, knowledge graph + beliefs, vault compile, tool calling, multi-step agent, goals + auto-advance, dreaming, personality evolution, world model, REST/SSE/WS, native daemon, **desktop app shell (pywebview, M14)**, rate limiting, Docker, HTTPS auto-gen by default + JWT auth opt-in on loopback / forced on non-loopback, metrics endpoint, log rotation, graceful shutdown.

✅ **Complete** — **character layer M0–M13** (canon volumes I–IV, behavioral validation harness, experience store + preference evolution, real-world evaluation harness + rubric, relationship dynamics on chat path, envelope-leak guard, experience-in-speech, conflict coherence).

🟡 **Partial** — plugins (no marketplace), multi-session profiles (single-user partial), cloud sync (not started).

❌ **Not started** — cloud sync, documentation site, roadmap M15+ (scheduler/voice/face/eyes — see [[03-Features/future-vision-roadmap]]).

## M-Series Gates (Sep 15 2026)

| Gate | Scope | Tests Added |
|------|-------|-------------|
| M5 | greeting-first conversation experience | 8 |
| M6 | experience store + preference evolution | 46 |
| M7 | behavioral validation (6 scenarios, renderer parity) | 30 |
| M8 | replay dedup + preference/experience consumers | 12 |
| M9 | real-world evaluation harness (stub + real mode) | 20 |
| M10 | relationship dynamics on chat path (deterministic deltas) | 23 |
| M11 | ThoughtPacket leak remediation | 7 |
| M12 | experience in speech (relevance gate) | 18 |
| M13 | conflict coherence (Volume IV, 10 scenarios) | 45 |
| Follow-up | empty-reply retry + stream guard | 9 |
| Phase 0 (Oct 9) | whole-utterance VAD gate + full-clip diarization + OpenRouter sanitization + provider preference | 21 |
| M14 (Oct 13) | desktop app — pywebview shell, tray, autostart, single-instance, installer | 13 |
| Security sprint (Oct 19) | bug-audit remediation + independent verification + DNS-peer hardening | 60 |

Cumulative: **1,990 tests pass + 2 skipped, 0 failures** — live-verified Oct 25 2026 (pre-M5 baseline 1,594 + ~396).

## Audit Trajectory

| Audit | Date | Score |
|-------|------|-------|
| V1 | Jul 19 | 6.1 (C) |
| V2 | Jul 19 | 6.7 (C+) |
| Post-fix | Jul 20 | 8.2 (B) |
| Multi-specialist | Jul 20 | 7.5 (B) |
| Ecosystem | Aug 6 | 7.3 (B) |
| P1 Remediation | Aug 12 | 8.0 (B+) |
| Security Bug Audit | Oct 19 | 10/10 findings verified + fixed; re-gated 1,986 → 1,990 tests |
| **Current** | **Oct 25** | **~8.2 (B+)** — no formal re-audit since the P1 pass; security sprint independently verified |

## Next Milestones (Roadmap)

The live plan is [[03-Features/future-vision-roadmap]] (M14–M25, decisions locked):

1. **M14 revision — Java/JavaFX desktop client** (pending JDK install go + P1 go; pywebview shell shipped and kept as fallback).
2. **M15 — Model Scheduler + TTS engine bake-off** (next after M14 P3).
3. **M16–M19** — custom voice, VRM face, eyes (screen/camera), silent research + file tools.
4. **M21–M22** — Self (code-awareness) + Continuity Engine (project memory, commitments, checkpoints).
5. **M23–M25** — Partner (email/calendar/presence) + Discord V1/V2.
6. Parallel backlog — plugin ecosystem, multi-session profiles / cloud sync, embedding-cache fingerprinting, performance profiling, documentation site.

---

## Wiki Links

**Previous:** [[09-Events & Data Flow]]  
**Index:** [[01-System Overview]] · [[02-Application Boot & Lifecycle]] · [[03-Core Brain Kernel & State]] · [[04-Memory Subsystem]] · [[05-Knowledge Graph & Vault]] · [[06-Agency Reasoning LLM & Execution]] · [[07-Voice Subsystem]] · [[08-API Native & Surface]] · [[09-Events & Data Flow]] · [[10-Status & Debt]]

**Related:** [[00-Overview/Project Charter]] — session progress log • [[03-Features/Native OS Bridge Architecture]] — daemon status • [[04-Development/Testing Strategy]] — test suite detail