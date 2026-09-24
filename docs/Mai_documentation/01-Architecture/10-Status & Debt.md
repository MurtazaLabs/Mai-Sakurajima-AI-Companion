# 10 — Implementation Status & Open Debt

> Digest of `IMPLEMENTATION_STATUS.md` + `TECHNICAL_DEBT.md`. Full detail: [[IMPLEMENTATION_STATUS]], [[TECHNICAL_DEBT]].

---

## Subsystem Maturity (counts Sep 15 2026, ~1,900 tests passing)

| Subsystem | Files | Lines | Maturity | Notes |
|-----------|-------|-------|----------|-------|
| core/ | 52 | 11,200 | 88% | Brain/kernel/fabric mature; P0 deadlock fixed; belief drift resolved |
| memory/ | 28 | 7,800 | 80% | strong pipeline; layer breach being addressed |
| knowledge/ | 29 | 5,800 | 80% | vault pipeline strong; graph 3-layer overlap; TOCTOU fixed |
| voice/ | 36 | 4,800 | 82% | full duplex; listen() refactor + AEC feed; _speaking race fixed |
| api/ | 24 | 3,400 | 85% | rich surface; auth enforced on config; rate limiter hardened; JWT auth-by-default |
| agency/ | 13 | 2,600 | 92% | cleanest subsystem; dreaming TOCTOU fixed |
| app/ | 19 | 2,300 | 96% | builder pattern gold standard |
| llm/ | 4 | 1,100 | 72% | failover good; dead passthrough + duck-typing |
| observability/ | 4 | 950 | 82% | HealthRegistry gold standard; telemetry fabric |
| execution/ | 4 | 1,050 | 92% | sandbox + whitelists solid |
| reasoning/ | 6 | 1,100 | 85% | journal/reflection hardened + ThoughtPacket |
| native/ | 8 | 750 | 78% | tray/hotkeys/watchdog operational |
| scripts/ | 6 | 800 | 65% | maintenance tooling + M9 eval runner |
| plugins/ | 8 | 620 | 65% | ecosystem growing (manifest, lifecycle, marketplace, signing, sandbox) |
| config/ | 20 | 1,100 | 96% | leaf settings |
| prompt/ | 8 | 400 | 94% | clean stateless |
| evaluation/ | 6 | 950 | 88% | M9 real-world harness |
| gateways/ | 2 | 180 | 35% | experimental Discord bot + native bridge |

**Overall: 82% (B+)** — production-ready core with P0/P1 issues resolved.

## Open Technical Debt (Priority Map)

| Priority | Items |
|----------|-------|
| Fix this sprint | D-2 `memory/→knowledge/` breach, P-3 belief fan-out, V-1 `VoiceManager.listen()`, L-1 `generate_with_tools()` dead passthrough |
| Next quarter | D-3 graph 3-layer collapse, P-4 age-cap flattening, P-5 embedding fingerprint, V-4 AEC feed, X-1 `E:\MaiMemory` hardcode (fixed) |
| Backlog | M-1 dead `MemoryObject.lock`, M-2 unused `embeddings`, M-3 `MemoryNode` duplication, M-4 `_text_overlap`, K-3 MD5→SHA-256, K-5 semantic chunking, O-3 `stats.md` reflections, X-2 import-time side effects, X-4 `_result()` duplication |

Key pillars to avoid regressions: RLock discipline everywhere, HealthRegistry fail-safe, graceful degradation at every boundary.

## Feature Maturity Per Roadmap

✅ **Complete** — conversation (text+voice), long-term memory, knowledge graph + beliefs, vault compile, tool calling, multi-step agent, goals + auto-advance, dreaming, personality evolution, world model, REST/SSE/WS, native daemon, rate limiting, Docker, HTTPS + JWT auth-by-default, log rotation, graceful shutdown.

✅ **Complete** — **character layer M0–M13** (canon volumes I–IV, behavioral validation harness, experience store + preference evolution, real-world evaluation harness + rubric, relationship dynamics on chat path, envelope-leak guard, experience-in-speech, conflict coherence).

🟡 **Partial** — plugins (no marketplace), multi-session profiles (single-user partial), cloud sync (not started).

❌ **Not started** — cloud sync, HTTPS (done), docs site.

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

Cumulative: **~1,900 tests pass, 0 failures** (pre-M5 baseline 1,594 + ~306).

## Audit Trajectory

| Audit | Date | Score |
|-------|------|-------|
| V1 | Jul 19 | 6.1 (C) |
| V2 | Jul 19 | 6.7 (C+) |
| Post-fix | Jul 20 | 8.2 (B) |
| Multi-specialist | Jul 20 | 7.5 (B) |
| Ecosystem | Aug 6 | 7.3 (B) |
| P1 Remediation | Aug 12 | 8.0 (B+) |
| **Current** | **Sep 15** | **~8.2 (B+)** |

## Next Milestones (Roadmap)

1. Production hardening (HTTPS, auth-by-default, rate limits — **done**).
2. Multi-session profiles / cloud sync.
3. Knowledge enrichment (semantic chunking, chunk metadata).
4. Embedding model versioning (fingerprinting).
5. Plugin ecosystem (manifest, lifecycle, marketplace, signing, sandbox).
6. Mobile/web companion (PWA).
7. Performance (async I/O, pooling, caching).
8. Documentation site (MkDocs from this suite).

---

## Wiki Links

**Previous:** [[09-Events & Data Flow]]  
**Index:** [[01-System Overview]] · [[02-Application Boot & Lifecycle]] · [[03-Core Brain Kernel & State]] · [[04-Memory Subsystem]] · [[05-Knowledge Graph & Vault]] · [[06-Agency Reasoning LLM & Execution]] · [[07-Voice Subsystem]] · [[08-API Native & Surface]] · [[09-Events & Data Flow]] · [[10-Status & Debt]]

**Related:** [[00-Overview/Project Charter]] — session progress log • [[03-Features/Native OS Bridge Architecture]] — daemon status • [[04-Development/Testing Strategy]] — test suite detail