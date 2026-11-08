# 10 — Implementation Status & Open Debt

> Source docs `IMPLEMENTATION_STATUS.md` / `TECHNICAL_DEBT.md` were merged and deleted; this page is the surviving reference. Refreshed against verified ground truth **Nov 8 2026** (2,045 tests passing / 2 skipped, 384 py files / 80,260 lines). Capability status: [[00-Overview/CURRENT_STATE]].

---

## Subsystem Maturity (counts Nov 8 2026, 2,045 tests passing)

| Subsystem | Files | Lines | Maturity | Notes |
|-----------|-------|-------|----------|-------|
| core/ | 66 | 16,030 | 88% | Brain/kernel/fabric mature; P0 deadlock + belief drift resolved; stream guard on `think_stream`; Attention RLock added |
| memory/ | 28 | 7,378 | 82% | strong pipeline; layer breach narrowed (3 lazy imports, 2 files); embedding cache now model-fingerprinted |
| knowledge/ | 29 | 5,853 | 82% | vault pipeline strong; D-1 belief drift **resolved**; graph 3-layer overlap remains |
| voice/ | 33 | 4,665 | 84% | full duplex + Phase 0 utterance gate; Kyutai opt-in; self-hearing fixed; AEC feed wired (recorder still muted) |
| api/ | 24 | 4,952 | 88% | 103 route sites; HTTPS dev certs, metrics endpoint, Oct-19 security fixes |
| agency/ | 12 | 2,540 | 92% | cleanest subsystem; dreaming TOCTOU fixed; dead wrappers removed |
| app/ | 18 | 2,329 | 96% | builder pattern gold standard |
| llm/ | 4 | 1,489 | 80% | `LLM_PROVIDER` preference, bounded retry budget, mid-stream failover with history |
| observability/ | 3 | 796 | 84% | HealthRegistry gold standard; heartbeat-count stalling; PII-redacting tracer |
| execution/ | 4 | 987 | 92% | sandbox + whitelists solid; confirm gate injectable |
| reasoning/ | 5 | 895 | 85% | journal JSONL, cadence-gated reflection, ThoughtPacket leak guard |
| native/ | 7 | 610 | 85% | tray/hotkeys/watchdog + M14 AppWindow shipped |
| scripts/ | 8 | 997 | 70% | maintenance tooling + M9 eval runner + installer + Kyutai bench + junk sweep |
| plugins/ | 14 | 3,851 | 75% | manifest, lifecycle, dependency resolver, Ed25519 signing, sandbox, marketplace client + CLI + 6 bundled plugins |
| config/ | 21 | 1,303 | 96% | leaf settings (`LLM_PROVIDER`, `STT_BACKEND`, gate thresholds) |
| prompt/ | 7 | 350 | 94% | clean stateless |
| evaluation/ | 5 | 768 | 88% | M9 real-world harness |
| integrations/ (ex-gateways) | 1 | 82 | 35% | Discord relay prototype; not wired as a channel |

**Overall: ~83% (B+)** — production-ready core with P0/P1 issues resolved.

## Open Technical Debt (Priority Map — verified Nov 8 2026)

| Priority | Items |
|----------|-------|
| Fix this sprint | ~~**AEC live feed**~~ (Nov 2026 — `StreamPlayer` taps the DAC stream into `FullAEC`; threshold 0.3 → 1.0 corrected), **AEC continuous capture** (recorder still muted while speaking — needs live validation), D-2 `memory/→knowledge/` breach (3 lazy imports, 2 files), P-3 belief fan-out in retriever, P-4 age-cap flattening, prompt token budgeting (no compaction; turn-count truncation only) |
| Next quarter | D-3 graph 3-layer collapse, X-2 import-time side effects, openWakeWord "hey mai" model |
| Backlog | M-1 dead `MemoryObject.lock`, M-2 unused `embeddings` field, M-3 `MemoryNode` duplication, M-4 `_text_overlap`, K-3 MD5→SHA-256, O-3 `stats.md` reflections, X-4 `_result()` duplication |
| **Resolved since Sep** | ~~D-1 belief drift~~ (Aug 12 — BrainGraph delegates to BeliefEngine), ~~P-5 embedding cache fingerprinting~~ (SHA-256 model fingerprint + LRU), ~~P-3 journal quadratic rewrites~~ (JSONL append), ~~V-1 `listen()` refactor~~ (5-line wrapper / 51-line `_listen_impl`), ~~Legacy Memory `Lock()`~~ (RLock verified), ~~L-1 `generate_with_tools()` dead passthrough~~ (was mislabeled — live on the Brain path), ~~Attention zero locking~~ (RLock added), ~~rate-limiter unbounded buckets~~ (bounded LRU) |

Key pillars to avoid regressions: RLock discipline everywhere, HealthRegistry fail-safe, graceful degradation at every boundary.

## Feature Maturity Per Roadmap

✅ **Complete** — conversation (text+voice, noise-gated), long-term memory, knowledge graph + beliefs, vault compile, tool calling, multi-step agent, goals + auto-advance, dreaming, personality evolution, world model, REST/SSE/WS, native daemon, **desktop app shell (pywebview, M14)**, rate limiting, Docker, HTTPS auto-gen by default + JWT auth opt-in on loopback / forced on non-loopback, metrics endpoint, log rotation, graceful shutdown, **plugin platform (manifest, lifecycle, signing, sandbox, marketplace)**.

✅ **Complete** — **character layer M0–M13** (canon volumes I–IV, behavioral validation harness, experience store + preference evolution, real-world evaluation harness + rubric, relationship dynamics on chat path, envelope-leak guard, experience-in-speech, conflict coherence).

🟡 **Partial** — AEC fed but recorder still muted during playback, Kyutai STT (opt-in, above latency gate), openWakeWord (installed, unwired), plugins (marketplace requires trusted keys; no public registry), multi-session profiles (`ProfileStore` + `SessionManager` exist; chat path single-user), entity web interface (state adapter only), Discord (relay prototype).

❌ **Not started** — cloud sync, WhatsApp (M26), Continuity Engine (M21), Java/JavaFX client, screen/camera share, documentation site, roadmap M15+ (see [[03-Features/future-vision-roadmap]]).

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
| Voice stabilisation (Oct 27–29) | pre-roll capture, trailing-silence trim, dynamo off, self-hearing fix, greeting speaking flag | 25 |
| Wake / packaging (Oct 31) | Porcupine vestige removal, openWakeWord installed (unwired, requirements only) | 0 |

Cumulative: **2,045 tests pass + 2 skipped, 0 failures** — live-verified Nov 8 2026 (2,047 collected; pre-M5 baseline 1,594 + ~451).

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
| **Current** | **Nov 8** | **~8.2 (B+)** — no formal re-audit since the P1 pass; security sprint independently verified; voice pipeline stabilised |

## Next Milestones (Roadmap)

The live plan is [[03-Features/future-vision-roadmap]] (M14–M26, decisions locked):

1. **M14 — Desktop app shipped (Oct 13, pywebview).** Java/JavaFX client remains a planned successor (pending JDK install go).
2. **M15 — Model Scheduler + TTS engine bake-off** (next).
3. **M16–M19** — custom voice, VRM face, eyes (screen/camera), silent research + file tools.
4. **M21–M22** — Continuity Engine (project memory, commitments, checkpoints) + Self (code-awareness).
5. **M23–M26** — Partner (email/calendar/presence) + Discord V1/V2 + WhatsApp (official Agent Platform only).
6. Parallel backlog — AEC continuous capture (feed is wired), openWakeWord model, prompt token budgeting, multi-session profiles / cloud sync, performance profiling, documentation site.

---

## Wiki Links

**Previous:** [[09-Events & Data Flow]]  
**Index:** [[01-System Overview]] · [[02-Application Boot & Lifecycle]] · [[03-Core Brain Kernel & State]] · [[04-Memory Subsystem]] · [[05-Knowledge Graph & Vault]] · [[06-Agency Reasoning LLM & Execution]] · [[07-Voice Subsystem]] · [[08-API Native & Surface]] · [[09-Events & Data Flow]] · [[10-Status & Debt]]

**Related:** [[00-Overview/Project Charter]] — session progress log • [[03-Features/Native OS Bridge Architecture]] — daemon status • [[04-Development/Testing Strategy]] — test suite detail