# Project Charter — Mai AI

> The project constitution: engineering philosophy, development rules, architecture overview, specialist roles, and session progress log.

---

## Project Overview

**Mai AI** is a production-oriented modular AI assistant inspired by Mai Sakurajima.

The project is designed as a **long-term personal AI companion** that combines:
- Conversational intelligence
- Persistent memory across sessions
- Intelligent memory retrieval
- Emotional consistency
- Voice interaction
- Character consistency
- AI tool usage
- Knowledge management
- Autonomous reasoning
- Long-term project evolution

The primary objective is not simply to build a chatbot, but to develop a **scalable AI platform capable of long-term evolution**.

---

## Core Project Goals

Mai AI should eventually become a complete AI companion capable of:

- ✅ Natural conversation
- ✅ Persistent memory across sessions
- ✅ Intelligent memory retrieval
- ✅ Emotional consistency
- ✅ Voice interaction
- ✅ Character consistency
- ✅ AI tool usage
- ✅ Knowledge management
- ✅ Autonomous reasoning
- 🟡 Long-term project evolution (ongoing)

Every engineering decision should move the project toward these goals.

---

## Engineering Philosophy

**Always prioritize:**
- Maintainability
- Readability
- Scalability
- Modularity
- Performance
- Reliability
- Simplicity
- Production-quality engineering

**Never optimize for short-term convenience if it creates long-term technical debt.**

---

## Development Rules

### Always
- Understand the existing implementation before making changes
- Preserve existing functionality unless explicitly instructed otherwise
- Follow the current project architecture
- Minimize technical debt
- Prefer modular solutions
- Explain engineering trade-offs
- Keep code readable
- Use descriptive naming
- Avoid unnecessary abstractions
- Respect existing coding conventions

### Never
- Remove functionality without approval
- Rewrite working systems unnecessarily
- Introduce unnecessary dependencies
- Duplicate existing logic
- Break backward compatibility without explaining why

---

## Project Architecture

Mai AI is organized into **modular subsystems**:

| Subsystem | Purpose |
|-----------|---------|
| `core/` | Brain, kernel, event fabric, state, emotion, identity (canon) |
| `memory/` | Memory pipeline, vector store, embedding, experience store |
| `knowledge/` | Knowledge graph, vault, retrieval, beliefs, document KB |
| `voice/` | STT/TTS/speaker/wake-word pipeline, interruption, noise filter |
| `agency/` | Tools, agent, goals, dreaming, evolution, preference evolution |
| `reasoning/` | Reasoning engine, reflection, learning, thought journal |
| `llm/` | Multi-provider LLM routing with failover |
| `api/` | FastAPI REST + SSE + WebSocket + static web UI |
| `native/` | Windows daemon: tray, hotkeys, notifications, watchdog |
| `execution/` | Safe tool execution with sandboxing |
| `app/` | Application builder pattern, DI container, orchestration |
| `config/` | Per-subsystem settings (leaf configs) |
| `prompt/` | Prompt architecture (character, emotional, context, agent, builder) |
| `observability/` | Health registry, event inspector, tracer |
| `plugins/` | Runtime-loaded plugin system |
| `evaluation/` | M9 real-world evaluation harness |
| `scripts/` | Maintenance tooling |
| `gateways/` | External platform bots (Discord) |

**Always understand subsystem boundaries before modifying code.**

---

## AI Engineering Workflow

Every request should follow this process:

1. **Understand** the objective
2. **Determine** the affected subsystem
3. **Analyze** existing implementation
4. **Identify** risks
5. **Select** the appropriate specialist
6. **Review** reference documentation
7. **Generate** recommendations
8. **Implement** only after understanding the existing architecture
9. **Validate** changes
10. **Suggest** improvements

**Never skip understanding the existing implementation.**

---

## Mai AI Suite — Specialist Roles

The project uses the **Mai AI Suite** engineering framework with specialized roles:

| Specialist | Responsibility |
|------------|----------------|
| **Mai Development Orchestrator** | Task classification, workflow coordination, engineering planning, multi-specialist routing |
| **Python Master Engineer** | Python development, debugging, refactoring, optimization, testing, feature implementation |
| **Python Codebase Architect** | Repository understanding, architecture analysis, dependency mapping, technical debt |
| **Mai AI Systems Auditor** | Security reviews, database audits, AI architecture audits, infrastructure reviews, production readiness |
| **Principal Software Advisor** | Code quality, best practices, maintainability, design patterns, engineering mentorship |
| **AI Memory Architect** | Memory systems, retrieval, embeddings, vector databases, RAG, ranking |
| **Prompt Architect** | Prompt engineering, agent prompts, character prompts, prompt optimization |
| **AI Product Manager** | Roadmaps, features, requirements, product planning, prioritization |
| **Knowledge Base Builder** | Documentation, developer guides, knowledge preservation, architecture documentation |

**Always use the minimum number of specialists required.**

---

## Reference Files

Specialist documentation is located in:

```
.opencode/
    skills/
        Mai-AI-Suite/
            references/
                python-master-engineer/
                python-codebase-architect/
                mai-ai-systems-auditor/
                principal-software-advisor/
                ai-memory-architect/
                prompt-architect/
                ai-product-manager/
                knowledge-base-builder/
```

Only consult documentation relevant to the selected specialist. Avoid unnecessary context loading.

---

## Decision Making

When solving engineering problems:
1. Understand first
2. Analyze second
3. Plan third
4. Implement fourth
5. Validate fifth
6. Optimize last

**Always explain major architectural decisions.**

---

## Static File Structure Rules (api/static/)

```
api/static/
├── assets/     ← ICONS ONLY — author adds these manually
├── css/        ← All .css files
├── img/        ← All images (avatars, backgrounds)
├── js/         ← All .js files
├── os/         ← Local OS interface (future)
└── *.html      ← Page HTML files at root level
```

When adding a new page:
1. Create the `.html` file at `api/static/`
2. Add its CSS to `css/` (link from the HTML)
3. Add its JS to `js/` (link from the HTML)
4. Images go in `img/`
5. **Never** create new folders under `css/`, `js/`, `img/`, or `assets/`
6. **Never** add icons to `assets/` — only the author does that

---

## Code Review Standards

When reviewing code, evaluate:

- Correctness
- Readability
- Maintainability
- Performance
- Scalability
- Security
- Modularity
- Error handling
- Documentation
- Testing

Provide both strengths and weaknesses. Always explain reasoning.

---

## Large Codebase Support

Mai AI is expected to grow significantly. Assume repositories may exceed:
- 20,000+ lines
- Hundreds of modules
- Multiple subsystems

**Analyze architecture before making recommendations. Avoid local optimizations that negatively impact the overall project.**

---

## Communication Style

Responses should be:
- Professional
- Direct
- Technical
- Actionable
- Well structured

Prefer engineering terminology. Avoid unnecessary verbosity.

---

## Output Expectations

When performing engineering work, include:

1. Task Classification
2. Selected Specialist(s)
3. Analysis
4. Positive Findings
5. Problems Identified
6. Risks
7. Recommendations
8. Next Steps
9. Implementation Plan (when appropriate)

---

## Long-Term Goal

Every contribution should improve Mai AI as a **long-term production-quality AI companion**.

Optimize for long-term success rather than short-term fixes. The health of the overall architecture always takes priority over isolated improvements.

---

## Session Progress Log

### Phase A–C — Foundation (earlier sessions)
Core AI, basic memory, voice, LLM integration.

### Phase D — Memory Pipeline
- `memory/schema.py` — MemoryObject
- `memory/extractor.py` — FastExtractor
- `memory/consolidation.py` — ConsolidationEngine
- `memory/lifecycle.py` — MemoryLifecycle
- `memory/pipeline.py` — MemoryPipeline

### Phase E — Knowledge Layer
- `knowledge/belief_engine.py` — BeliefEngine
- `knowledge/graph.py` — KnowledgeGraph
- `knowledge/attention.py` — AttentionSystem
- `knowledge/retriever.py` — AdvancedRetriever

### Phase F — Reasoning Pipeline
- `reasoning/engine.py` — ReasoningEngine
- `reasoning/journal.py` — ThoughtJournal
- `reasoning/reflection.py` — ReflectionEngine
- `reasoning/learning.py` — LearningEngine

### Phase G — Agency / Tool Calling
- `agency/registry.py` — ToolRegistry
- `agency/tools.py` — 12 built-in tools
- `agency/agent.py` — Agent
- `agency/planner.py` — Planner

### Phase H — Knowledge Base Builder
- `knowledge/chunker.py` — TextChunker
- `knowledge/document_store.py` — DocumentStore
- `knowledge/indexer.py` — Indexer
- `knowledge/builder.py` — KnowledgeBaseBuilder

### Phase I — Prompt Architecture
- `prompt/` — 5 modules: CharacterPrompt, EmotionalPrompt, ContextPrompt, AgentPrompt, PromptBuilder
- `core/prompt_builder.py` — backward-compat wrapper

### Phase J — Full System Integration
- Brain wired with ToolRegistry, Agent, AdvancedRetriever, ReasoningEngine, ReflectionEngine, LearningEngine
- Full boot sequence in `run.py`

### Phase K — Roadmap Completion
- `agency/goals.py` — GoalManager
- `agency/procedural.py` — ProceduralMemory
- `agency/world.py` — WorldModel
- `agency/dreaming.py` — DreamEngine
- `agency/evolution.py` — PersonalityEvolution
- `observability/dashboard.py` — DashboardServer

### V4.3 — Deferred Items + Integration
- 5 deferred items built and integrated (memory hierarchy, voice emotion detector, adaptive noise filter, diarization, full AEC)
- 10 audit issues fixed, docs updated, all tests pass

### Phase 1 (L) — Brain Graph Engine
BrainGraph facade with 7 typed node types, full bridge to all 8 knowledge stores, backward-compatible wrappers.

### Phase 2 (M) — Thought Continuity + Cognitive State + World Model
- 2A: Auto-wire pipeline (reflection → belief → goals → procedural → learning)
- 2B: Cognitive State (10+ fields, dashboard integration, prompt injection)
- 2C: World Model (11 category constants, dashboard breakdown, BrainGraph bridge)

### Phase 3 (N) — Voice Pipeline Depth + Emotion Breadth + Goal Depth
- 3A: Interruption detection, emotion-based response timing, emotion label to KokoroTTS
- 3B: All 5 influence() dimensions verified, emotion snapshots as BrainGraph nodes
- 3C: Goal subtasks, progress, auto-advance, completion reflection, BrainGraph storage

### Phase 4 (O) — Code Smell Remediation + Audit Fixes
- 6 code smell remediations (silent error swallowing, duplicate _safe_*, deep nesting, primitive obsession, god classes, feature envy)
- 5 high-severity audit issues fixed
- 6 remaining audit items fixed
- All 1,121 tests pass

### Architecture Evolution — ApplicationBuilder Pattern
- Phase 1: Container extraction — `Application.build()` wraps construction logic, `run.py` becomes thin (~20 lines)
- Phase 2-4 planned: Split into `_create_*` methods, formalize lifecycle, validation gates

### Phase 5 — V2 Audit Remediation (Jul 20)
- Fresh audit report, 24 docs merged into MERGED_COMPLETE.md
- **P0**: 9 Critical items fixed (bare excepts, global logger suppression, RLock on 5 files, verify_consistency fixes, syntax error)
- **P1**: 23 bare excepts in knowledge/, 6 in agency/, RLock on EmbeddingService, app whitelist, destructive hotkey filter, SHA-256 VAD model, consolidation orphan fix
- **P2**: RLock on all VectorStore methods, echo_canceller removed, emotion.py split, obsidian_writer split, VoiceManager constructor reduced, TaskExecutor extracted
- **All 1,171 tests pass**

### Phase 6 — Multi-Specialist System Audit (Jul 20)
- Comprehensive audit of all 14 subsystems by 4 specialists
- **Overall score: B (7.5)** — improved from V2's C+ (6.7)
- **3 P0 Critical**: Emotion._sync() deadlock, VoiceManager._speaking data race, triple belief storage drift
- **16 P1 High**: RateLimiter thread-unsafe, InterruptManager lock exposed, TOCTOU in DreamEngine, 10 bare excepts in knowledge/, 27+ debug-level errors, indexer counter race, etc.
- **16 P2 Medium**: Layer breaches, dead code, duplicate code, formatting, etc.

### Native OS Bridge — Phases 1-3 Complete (Jul 24)
- Phase 1: TrayDaemon, Notifier, WSBridge, API endpoints
- Phase 2: HotkeyManager, ClipboardActions, FileSystemActions, API routes
- Phase 3: StartupManager, HealthMonitor, run_daemon.py, PyInstaller build, Inno installer, SSE reconnection
- Async I/O: Parallel retrieval in AdvancedRetriever

### Event Fabric — Phases 4-5 Complete (Jul 27)
- Phase 4: 53 publish sites migrated to MaiMessage envelope + semantic topics + registry validation
- Phase 5: Reactive UI — UI subscribes exclusively to state.*; dual-publish for state projection; 15 STATE_* constants

### Vault Remediation (Aug 6)
- Fix 1: Broken memory links (~89 [[links]] to absent notes) — link filtering
- Fix 2: Stats & relationship drift — first_met from vault, real conversation turn counts, relationship integrity guard
- Fix 3: Graph entity pollution — junk gate (confidence < 0.25), VaultJanitor sweep
- Fix 4: Cross-day memory duplication — hash_cache reset fix, cross-day dedup, reinforcement bump
- **1,443 tests pass**

### Ecosystem Audit + P0 Remediation (Aug 6)
- 6 parallel subsystem audits + runtime verification
- **P0s fixed**: Daemon boot crash, FileSystemActions dead, dual-writer vault clobber, SSE/WS event drop, LLM probe under lock
- **1,445 tests pass**

### Backlog Remediation Sprint (Aug 6)
- **P1s fixed**: logger NameErrors, Emotion.get() misuse, dedup signature mismatch, /api/system/config auth, Agent single-step loop + honest failure, goal-pause priority inverted, tool contract mismatch, FS sandbox everywhere
- **P2s fixed**: chat.js XSS, RateLimiter buckets unbounded, VoiceManager toggle() + mic callback accumulation, _version_mismatches race, scheduler lock discipline
- **1,466 tests pass**

### Backlog Remediation Sprint 2 (Aug 6)
- **P2s fixed**: _bump_reinforcement quote corruption, journal path entity links, VaultJanitor short-entity false positives, ThoughtJournal quadratic rewrites (→ JSONL), VAD failure latching, ReflectionEngine cadence write-only, tracer PII redaction, CORS + duplicate sources, str(e) leak in error responses, streaming failover, OpenRouter unbounded retry
- **1,491 tests pass**

### Character Layer M-series — M5 & M6 Complete (Aug 9)
- **M5**: Greeting-first conversation (gate passed)
- **M6**: Emotional experience/growth — ExperienceStore, PreferenceEvolution, dreaming L5 task, wiring audit (scheduler, scan_turn, preference_apply)
- **1,648 tests pass**

### M7 — Character Behavioral Validation (Aug 9)
- Validation-only: proves M0–M6 chain behaves like Mai
- Harness: ScenarioDriver with virtual clock, causal traces, deterministic ThoughtPacket fixtures
- 6 scenarios green, renderer parity, trace isolation
- **Production bug found + fixed**: evolved_preferences() shape mismatch in attach_preference_overlay()
- **1,678 tests pass**

### M8 — Finding Remediation (Aug 9)
- Experience replay dedup (md5 fingerprint)
- Preference consumer gap fixed (Brain._identity_data() → orchestrator → prompt)
- Experience consumer (MemoryCoordinator.experience_context() → prompt)
- **1,690 tests pass**

### M9 — Real-World Conversation Evaluation (Aug 9)
- Validation-only: unscripted LLM-driven sessions, persisted transcripts, mechanical rubric + human review
- Harness: transcript.py, rubric.py (7 axes), scenarios.py, runner.py (FakeLLM + build_stub_brain)
- **1,710 tests pass**

### M10 — Relationship Dynamics on Chat Path (Aug 9)
- Chosen from M9 evidence: relationship was frozen on chat path
- config/relationship.py (delta constants + signal lexicons), core/state/relationship.py (deterministic deltas + apply)
- Wired into Brain → PostThinkHooks (synchronous block before bg cycle)
- **1,733 tests pass**

### M9 Real-Mode Evidence (Aug 9)
- Three scenarios run against real application + configured LLM
- Trust persisted cross-session in master_state.json
- Boundary_consistency issue found (ThoughtPacket JSON leak)

### M11 — ThoughtPacket Leak Remediation (Aug 9)
- reasoning/thought_packet.py: _strip_leaked_json(), had_envelope flag, honest empty reply fallback
- **1,740 tests pass**
- Real-mode rerun: jealousy-real 4.67/5, emotional-real 4.71/5 (both boundary 5/5)

### M12 — Experience in Speech (Aug 9)
- MemoryCoordinator.experience_context() relevance-gated (Dice coefficient ≥ 0.10)
- Character instruction: "refer to it the way Mai would remember it: lightly, never announcing the memory itself"
- Real-mode: experience referenced in speech for first time
- **1,758 tests pass**

### Empty-Reply Retry + Stream Guard (Aug 9)
- Brain._retry_empty_reply() — one bounded speech-only retry
- Brain._safe_stream() — stream guard for think_stream, buffers envelope JSON
- Real-mode: shared_history 4.83/5, no empty turns
- **1,767 tests pass**

### M13 — Character Coherence / Conflict Validation (Aug 9)
- Canon artifact: Volume IV Rule Resolution (7-tier priority grounded in Volumes I–III)
- core/identity/identity_core.py: get_conflict_resolution() read-only projection (not yet promoted to prompts)
- 10 conflict scenarios validated through real pipeline
- No mechanism leakage across all scenarios
- **1,812 tests pass**

### Runtime Log Remediation (Aug 9)
- ChromaDB multi-key delete fixed (VectorStore._build_metadata_where with $and)
- Speaker embedding dead — torch 2.3 compat shim (custom_fwd/custom_bwd with device_type)
- False "service unhealthy" burst — HealthRegistry tracks heartbeat_count, check_stalled requires ≥2 heartbeats
- **1,819 tests pass**

### TTS Fix — blis DLL Corruption (Aug 9)
- Root cause: corrupt blis .pyd files (no MZ/PE header)
- Fix: pip force-reinstall blis==1.3.3 + numpy==1.26.4 restore
- End-to-end verified: KokoroTTS generates real audio

### Boot Log Remediation 2 (Aug 9)
- Speaker embedding: custom_fwd device_type kwarg handled
- Health stall false positives: single-heartbeat components never STALLED
- **1,821 tests pass**

### OS Voice Tool Path — "open chrome" Refusal (Aug 9)
- Voice path never executed actions (think_stream now routes through _safe_stream → _try_stream_action)
- Prompt gave no JSON contract (explicit example, allowed types, "never say you cannot")
- os.startfile("chrome") fails — _APP_PATH_TEMPLATES + _resolve_app_path() fallback
- Envelope normalization for agent-style tool calls
- **1,832 tests pass**

### P1 Critical Fixes Complete (Aug 12)
- **Deadlock risk** — Emotion/Brain lock ordering: Emotion._sync() marks dirty only; Brain._sync_emotion() pulls under Emotion.lock then writes under SharedState.lock (consistent ordering) — `core/emotion.py:412-417`, `core/brain.py:477-496`
- **_speaking data race** — VoiceManager audio callback re-verifies _speaking under lock before clearing — `voice/voice_manager.py:242-255`
- **Triple belief storage drift** — BrainGraph delegates to BeliefEngine as single source of truth; legacy fallbacks removed — `knowledge/brain_graph.py:31-68`
- **RateLimiter thread-safety** — RLock on all bucket operations (already implemented) — `api/middleware/rate_limiter.py:37`
- **InterruptManager lock privacy** — Already uses `_lock` (already implemented) — `voice/interrupt.py:24`
- **Legacy Memory Lock→RLock** — Already uses RLock (already implemented) — `memory/memory.py:37`
- **Bare excepts in knowledge/** — 6 locations fixed to capture `as e` + log — `knowledge/chunker.py:132`, `memory_writer.py:61,91`, `state_dumper.py:182,200,222`
- **GraphExporter counter lock** — Already has RLock on _write_count/_delete_count (already implemented) — `knowledge/graph_exporter.py:20`
- **TOCTOU on _dreaming flag** — _dreaming_lock held in finally block when clearing flag — `agency/dreaming.py:112-113`
- **MemoryWriter TOCTOU** — _link_target_exists() uses atomic open/read instead of exists() check — `knowledge/memory_writer.py:52-63`
- **indexer._indexed_count** — Already under RLock (already implemented) — `knowledge/indexer.py:125-126`
- **_safe_execute char whitelist** — Already URL-safe regex (already implemented) — `agency/tools.py:134`
- **Path traversal in tracer** — Already sanitizes filename (already implemented) — `observability/tracer.py:164-166`
- **Unvalidated plugin name** — Already validated with regex (already implemented) — `api/routes_system.py:55`
- **Static file mount / MemoryIntelligence try/except / dead loop** — Invalid/already fixed

- **1,827 tests pass, 0 failures**

### Phase 0 — Noise Gate + Voice/LLM Response-Path Fixes (Oct 9)
- **Whole-utterance VAD gate** before any `stt.transcribe()` (`VAD.utterance_score`, thresholds live-calibrated 0.15 mean / 0.10 ratio, fail-open) in wake-audio, `_transcribe()` and the kernel `return_audio` path — killed Whisper hallucinations on fan/hiss noise
- **Diarization full-clip fix** (P0): speaker label from the full clip; regions never sliced before STT ("stops responding" root cause)
- **OpenRouter** — default model `openrouter/free`, sanitized failover list, permanent-status codes break the attempt loop, bounded retry budget (45s); removed `model:"None"` 400-ladder on every call
- **`LLM_PROVIDER` preference** (default `openrouter`; `ollama` = local-first ordering, cached probes, exception→dead) + Ollama payloads send `think: false`
- **1,905 tests pass**

### Roadmap + M14 Desktop App + STT Plan (Oct 9–13)
- STT replacement plan (Kyutai 1B; Phase 0 model download complete, Phase 1 pending go)
- **Future roadmap** documented ([[future-vision-roadmap]] — T0–T8 workstreams, M14–M25 milestones, locked decisions); feature-review fold-in (all 7 recommendations adopted/merged)
- **M14 Desktop App** — `run_daemon.py` rewritten (single bootstrap fixes double-boot + missing kernel), `native/app_window.py` pywebview (close→tray), `scripts/install_app.py` shortcut/autostart with voiceless-interpreter guard, `build_daemon.py` `--add-data` fix
- **1,930 tests pass**

### Security Bug Audit Remediation + Verification (Oct 19)
- **10/10 findings verified against code, then fixed**: Brain response cache removed (cross-user leak + state-chain skips), request-local user_id, pre-chat hook append-not-replace, web scraper hardening + SSRF guard (public-target, connected-peer, proxy bypass), sandbox path containment + eval lockdown, marketplace signatures required (env opt-in), SafeExecutor injectable confirm gate, stream fallback history retention, auth cookies (HttpOnly/SameSite/Secure) + redirect-target allowlist + base64 NameError
- **Independent verification pass** closed all 5 channels; DNS-peer hardening added same day
- **1,986 → 1,990 tests pass, 2 skipped** — re-verified live Oct 25 (mai_env, 4m04s)

---

## Active File Count (Oct 25 2026)
- **376 py files / 66,767 lines** | **19 packages** + `run.py`/`run_daemon.py` | tests: 83 py files / 19,281 lines (72 test modules)
- Packages: core/, memory/, knowledge/, reasoning/, agency/, voice/, llm/, execution/, api/, app/, native/, config/, observability/, prompt/, plugins/, evaluation/, scripts/, profiling/, integrations/ (ex-gateways)

---

## Wiki Links

- [[01-Architecture/01-System Overview]] — High-level architecture
- [[01-Architecture/02-Application Boot & Lifecycle]] — Boot pipeline
- [[01-Architecture/03-Core Brain Kernel & State]] — Core package
- [[05-Reference/Complete Folder Structure]] — Full file tree
- [[03-Features/Native OS Bridge Architecture]] — Daemon architecture
- [[03-Features/Discord Integration Plan]] — Discord bot plan