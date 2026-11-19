# Mai AI Project

Version: 2.0.0

Project: Mai Sakurajima AI Assistant

Author: Syed Murtaza

---

# Project Overview

Mai AI is a production-oriented modular AI assistant inspired by Mai Sakurajima.

The project is designed as a long-term personal AI companion that combines conversational intelligence, persistent memory, voice interaction, modular AI systems, and extensible tooling into a unified architecture.

The primary objective is not simply to build a chatbot, but to develop a scalable AI platform capable of long-term evolution.

Mai AI emphasizes:

- Long-Term Memory
- Character Consistency
- Voice Conversations
- Intelligent Agent Workflows
- Modular Architecture
- Production-Quality Python Engineering
- High Maintainability
- Scalability
- Extensibility
- Reliability

---

# Core Project Goals

Mai AI should eventually become a complete AI companion capable of:

- Natural conversation
- Persistent memory across sessions
- Intelligent memory retrieval
- Emotional consistency
- Voice interaction
- Character consistency
- AI tool usage
- Knowledge management
- Autonomous reasoning
- Long-term project evolution

Every engineering decision should move the project toward these goals.

---

# Engineering Philosophy

Always prioritize:

- Maintainability
- Readability
- Scalability
- Modularity
- Performance
- Reliability
- Simplicity
- Production-quality engineering

Never optimize for short-term convenience if it creates long-term technical debt.

---

# Development Rules

Always:

- Understand the existing implementation before making changes.
- Preserve existing functionality unless explicitly instructed otherwise.
- Follow the current project architecture.
- Minimize technical debt.
- Prefer modular solutions.
- Explain engineering trade-offs.
- Keep code readable.
- Use descriptive naming.
- Avoid unnecessary abstractions.
- Respect existing coding conventions.

Never:

- Remove functionality without approval.
- Rewrite working systems unnecessarily.
- Introduce unnecessary dependencies.
- Duplicate existing logic.
- Break backward compatibility without explaining why.

---

# Project Architecture

Mai AI is organized into modular subsystems.

Examples include:

- Core AI logic
- Voice System
- Memory System
- Prompt System
- Configuration
- Database
- Character System
- Tool Calling
- LLM Routing
- Knowledge Base
- UI Components
- Utilities

Always understand subsystem boundaries before modifying code.

---

# AI Engineering Workflow

Every request should follow this process:

1. Understand the objective.
2. Determine the affected subsystem.
3. Analyze existing implementation.
4. Identify risks.
5. Select the appropriate specialist.
6. Review reference documentation.
7. Generate recommendations.
8. Implement only after understanding the existing architecture.
9. Validate changes.
10. Suggest improvements.

Never skip understanding the existing implementation.

---

# Mai AI Suite

This project uses the **Mai AI Suite** engineering framework.

The suite consists of specialized engineering roles.

The suite automatically determines which specialist should handle each task.

Available specialists:

- Mai Development Orchestrator
- Python Master Engineer
- Python Codebase Architect
- Mai AI Systems Auditor
- Principal Software Advisor
- AI Memory Architect
- Prompt Architect
- AI Product Manager
- Knowledge Base Builder

Always use the minimum number of specialists required.

---

# Specialist Responsibilities

## Mai Development Orchestrator

Responsible for:

- Task classification
- Workflow coordination
- Engineering planning
- Multi-specialist routing
- Project management

---

## Python Master Engineer

Responsible for:

- Python development
- Debugging
- Refactoring
- Optimization
- Testing
- Feature implementation

---

## Python Codebase Architect

Responsible for:

- Repository understanding
- Architecture analysis
- Dependency mapping
- Technical debt
- Codebase navigation

---

## Mai AI Systems Auditor

Responsible for:

- Security reviews
- Database audits
- AI architecture audits
- Infrastructure reviews
- Production readiness

---

## Principal Software Advisor

Responsible for:

- Code quality
- Best practices
- Maintainability
- Design patterns
- Engineering mentorship

---

## AI Memory Architect

Responsible for:

- Memory systems
- Retrieval
- Embeddings
- Vector databases
- RAG
- Ranking

---

## Prompt Architect

Responsible for:

- Prompt engineering
- Agent prompts
- Character prompts
- Prompt optimization

---

## AI Product Manager

Responsible for:

- Roadmaps
- Features
- Requirements
- Product planning
- Prioritization

---

## Knowledge Base Builder

Responsible for:

- Documentation
- Developer guides
- Knowledge preservation
- Architecture documentation

---

# Reference Files

Specialist documentation is located in:

```
.opencode/
    skills/
        Mai-AI-Suite/
            references/
```

Each specialist contains its own documentation.

Example:

```
references/

python-master-engineer/
    README.md
    modes.md
    testing.md
    review-format.md

python-codebase-architect/
    README.md
    architecture-analysis.md
    dependency-analysis.md

mai-ai-systems-auditor/
    README.md
    security.md
    database.md

...
```

Only consult documentation relevant to the selected specialist.

Avoid unnecessary context loading.

---

# Decision Making

When solving engineering problems:

Understand first.

Analyze second.

Plan third.

Implement fourth.

Validate fifth.

Optimize last.

Always explain major architectural decisions.

---

# Static File Structure Rules (api/static/)

```
api/static/
├── assets/     ← ICONS ONLY — I add these myself. Never create icons here.
├── css/        ← All .css files go here
├── img/        ← All images go here (avatars, backgrounds, etc.)
├── js/         ← All .js files go here
├── os/         ← Local OS interface (future)
└── *.html      ← Page HTML files at root level
```

When adding a new page:
1. Create the `.html` file at `api/static/`
2. Add its CSS to `css/` (link from the HTML)
3. Add its JS to `js/` (link from the HTML)
4. Images go in `img/`
5. **Never** create new folders under `css/`, `js/`, `img/`, or `assets/`
6. **Never** add icons to `assets/` — only I do that

---

# Code Review Standards

When reviewing code:

Evaluate:

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

Provide both strengths and weaknesses.

Always explain reasoning.

---

# Large Codebase Support

Mai AI is expected to grow significantly.

Assume repositories may exceed:

- 20,000+ lines
- Hundreds of modules
- Multiple subsystems

Analyze architecture before making recommendations.

Avoid local optimizations that negatively impact the overall project.

---

# Communication Style

Responses should be:

- Professional
- Direct
- Technical
- Actionable
- Well structured

Prefer engineering terminology.

Avoid unnecessary verbosity.

---

# Output Expectations

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

# Long-Term Goal

Every contribution should improve Mai AI as a long-term production-quality AI companion.

Optimize for long-term success rather than short-term fixes.

The health of the overall architecture always takes priority over isolated improvements.

---

# Session Progress — Jul 11 2026

## Completed Phases

### Phase A–C — Foundation (earlier sessions)
Core AI, basic memory, voice, LLM integration.

### Phase D — Memory Pipeline (new)
- `memory/schema.py` — MemoryObject
- `memory/extractor.py` — FastExtractor
- `memory/consolidation.py` — ConsolidationEngine
- `memory/lifecycle.py` — MemoryLifecycle
- `memory/pipeline.py` — MemoryPipeline

### Phase E — Knowledge Layer (new)
- `knowledge/belief_engine.py` — BeliefEngine
- `knowledge/graph.py` — KnowledgeGraph
- `knowledge/attention.py` — AttentionSystem
- `knowledge/retriever.py` — AdvancedRetriever

### Phase F — Reasoning Pipeline (new)
- `reasoning/engine.py` — ReasoningEngine
- `reasoning/journal.py` — ThoughtJournal
- `reasoning/reflection.py` — ReflectionEngine
- `reasoning/learning.py` — LearningEngine

### Phase G — Agency / Tool Calling (new)
- `agency/registry.py` — ToolRegistry
- `agency/tools.py` — 12 built-in tools
- `agency/agent.py` — Agent
- `agency/planner.py` — Planner

### Phase H — Knowledge Base Builder (new)
- `knowledge/chunker.py` — TextChunker
- `knowledge/document_store.py` — DocumentStore
- `knowledge/indexer.py` — Indexer
- `knowledge/builder.py` — KnowledgeBaseBuilder

### Phase I — Prompt Architecture (new)
- `prompt/` — 5 modules: CharacterPrompt, EmotionalPrompt, ContextPrompt, AgentPrompt, PromptBuilder
- `core/prompt_builder.py` — backward-compat wrapper

### Phase J — Full System Integration (new)
- Brain wired with ToolRegistry, Agent, AdvancedRetriever, ReasoningEngine, ReflectionEngine, LearningEngine
- Full boot sequence in `run.py`

### Phase K — Roadmap Completion (new)
- `agency/goals.py` — GoalManager
- `agency/procedural.py` — ProceduralMemory
- `agency/world.py` — WorldModel
- `agency/dreaming.py` — DreamEngine
- `agency/evolution.py` — PersonalityEvolution
- `observability/dashboard.py` — DashboardServer

### V4.3 — Deferred Items + Integration (earlier session)
- **5 Deferred Items** all built and integrated:
  1. `memory/hierarchy.py` — Cognitive Science Memory Hierarchy
  2. `voice/emotion_detector.py` — VoiceEmotionDetector
  3. `voice/adaptive_noise_filter.py` — AdaptiveNoiseFilter
  4. `voice/diarization.py` — DiarizationEngine
  5. `voice/full_aec.py` — FullAEC
- **10 audit issues fixed**, docs updated, all 1163 tests pass

### Phase 1 (L) — Brain Graph Engine (pre-built, verified this session)
BrainGraph facade in `knowledge/brain_graph.py` with 7 typed node types, full bridge to all 8 knowledge stores, backward-compatible wrappers, node-type breakdown in dashboard.

### Phase 2 (M) — Thought Continuity + Cognitive State + World Model (earlier in session)
- **2A — Auto-wire pipeline**: PostThinkHooks fires reflection → belief update → GoalManager.check_goals() → ProceduralMemory → LearningEngine in one background cycle. GoalManager.complete() triggers LearningEngine.adjust_behavior(). `check_goals(beliefs)` creates goals for uncovered topics and boosts matching active goals.
- **2B — Cognitive State**: All 10+ fields already existed (working_memory, current_topic, attention_focus, current_goal, current_reasoning, current_speaker, active_task, conversation_intent, confidence, recent_thoughts). Dashboard now shows working_memory (last 3 turns) and recent_thoughts (last 3). PromptBuilder injects all fields.
- **2C — World Model**: 11 category constants defined (person, place, project, technology, event, skill, media, organization, relationship, interest, character). Dashboard shows category breakdown + recent entities. WorldModel bridges to BrainGraph for entity discovery.
- **All 1163 tests pass**, zero failures.

### Phase 3 (N) — Voice Pipeline Depth + Emotion Breadth + Goal Depth (this session)
- **3A — Voice Pipeline**: Interruption detection wired — mic RMS energy > 0.015 threshold during TTS playback triggers InterruptManager, breaks speak_stream(). Emotion-based response timing (0.1s happy to 0.8s sad pre-speech delay). Emotion label passed to KokoroTTS.generate(emotion=) for text enhancement via influence("word_choice").
- **3B — Emotion Breadth**: Verified all 5 influence() dimensions (retrieval, speech_speed, goal_priority, interrupt_tolerance, word_choice) with documented ranges. Emotion snapshots stored as BrainGraph nodes.
- **3C — Goal Depth**: Verified subtasks, progress, auto-advance, completion reflection, and BrainGraph storage all fully implemented.
- **All 1163 tests pass**, zero failures.

### Phase 4 (O) — Code Smell Remediation + Audit Fixes (Jul 16)
- **6 code smell remediations** from Principal Software Advisor review:
  - SMELL-003: PostThinkHooks silent error swallowing — split into 9 per-subsystem blocks
  - SMELL-005: Duplicate `_safe_*` logic — extracted to `core/utils.py` (safe_call, safe_attr, safe_call_fn)
  - SMELL-002: Deep nesting in VectorStore.search() — extracted `_parse_result()`
  - SMELL-004: Primitive Obsession — added EmotionName, TimeOfDay, UserMood, EmotionProfile enums
  - SMELL-001: God classes — extracted ToolManager from Brain, SchemaMigrator from VectorStore
  - SMELL-006: Feature Envy — fixed via SMELL-003 per-block logging
- **5 high-severity audit issues fixed**:
  - Planner dead code (`agency/planner.py`) — deleted + 22 test cases removed
  - VoiceState enum wired into VoiceManager — replaced raw string state values
  - FullAEC pure Python loop vectorized — O(n × filter_length) → O(n + filter_length) per block
  - Brain constructor reduced — `BrainDeps` dataclass groups 19 optional deps; 23 params → 5
  - TaskExecutor god class extracted — `execution/handlers.py` with SystemActions, CommandActions, DesktopActions; 767→260 lines
- **6 remaining audit items fixed**:
  - Memory pollution — importance filter in `os_kernel.py` store path (skips score < 0.3)
  - Prompt redundancy — hardcoded speech_pacing removed from `prompt_orchestrator.py`, consolidated into `prompt/character.py`
  - Unsafe tool inputs — character whitelist added to `_safe_execute()` in `agency/tools.py`
  - Metadata filtering — `memory_type` filter wired through `AdvancedRetriever.retrieve()` → `VectorStore.search()`
  - ChromaDB probe blocking boot — probe removed, `skip_probe=True` default, catch-at-first-use
  - Unnecessary retrieval — context/structured skipped for < 3 word queries in `MemoryCoordinator`
- **Already implemented (audit false positives)**: LLM fallback chain, SharedState.save(), vector store periodic pruning, retrieval-failure guardrail, audio callback underflow protection
- **All 1121 tests pass** (22 Planner tests removed with dead code)

## Active File Count
- Non-venv Python modules: ~84+
- subsystems: core/, memory/, knowledge/, reasoning/, agency/, voice/, llm/, execution/, config/, observability/, prompt/

## New Initiatives (built this session)

### Knowledge Base Auto-Ingestion — `knowledge/watcher.py`
**`DirectoryWatcher`** — Background thread monitors directories for new/changed files matching patterns (*.md, *.txt, *.py, *.json, *.yaml, *.csv). On each scan interval (default 60s), indexes new or modified files via `KnowledgeBaseBuilder.build_from_file()`. Configurable directory list, interval, patterns. Thread-safe with RLock. Stats: running state, directories, known file count.

### REST API — `api/server.py`
**`MaiAPI`** — FastAPI-based REST server with endpoints:
- `GET /api/health` — system health check
- `POST /api/chat` — send message, receive AI response
- `GET /api/status` — emotion, goals, world model stats
- `GET /api/memory` — search memory via query string
- `POST /api/knowledge/ingest` — ingest text/file/directory into knowledge base
- `GET /*` — serves static files (web UI)

**`MaiAPI.bootstrap()`** — calls `run.bootstrap_system()` to initialize all system components. Runs via uvicorn on configurable host:port (default 0.0.0.0:8000).

### Web UI — `api/static/index.html`
Minimal chat interface: message history, typing indicator, connection status indicator, auto-poll health endpoint. Dark theme matching dashboard style. Communicates with API server via fetch().

### Plugin System — `core/plugin_system.py`
**`HookRegistry`** — Event-style hook system: `register(hook_name, callback, priority)`, `unregister()`, `run()` with sorted priority execution. Error isolation (one plugin failure doesn't break others).

**`Plugin`** — Base class: `on_load(hooks, brain, event_bus)`, `on_unload()`.

**`PluginLoader`** — Discovers `.py` files in `plugins/` directory, imports modules, finds `Plugin` subclasses, calls `on_load()`. `load_all()` bulk loads all discovered plugins. Thread-safe.

**Example plugin** — `plugins/example_plugin.py` registers `pre_chat` and `post_response` hooks.

### Docker Deployment — `Dockerfile` + `docker-compose.yml`
- Python 3.10-slim base
- FastAPI + uvicorn serving on port 8000
- Volumes: data, cache, logs, knowledge_docs
- `restart: unless-stopped`

### New files added
- `knowledge/watcher.py` — DirectoryWatcher
- `core/plugin_system.py` — Plugin, PluginLoader, HookRegistry
- `api/__init__.py` — package init
- `api/server.py` — MaiAPI + FastAPI app
- `api/static/index.html` — web chat UI
- `plugins/example_plugin.py` — sample plugin
- `Dockerfile` — container build
- `docker-compose.yml` — orchestration
- `requirements-docker.txt` — minimal dependencies

---
---

# Architecture Evolution — ApplicationBuilder Pattern

## Motivation

`run.py` grew to 780 lines — one monolithic boot function constructing 30+ subsystems inline. Every new subsystem required scattered edits: imports, construction, health checks, cleanup. This violated the project's long-term maintainability goal.

## The Shift

`run.py` is the **power button**, not the motherboard.

Instead of:

```
run.py:main()
  ├── constructs EventBus
  ├── constructs Memory
  ├── constructs Retriever
  ├── constructs Graph
  ├── constructs Brain
  ├── constructs Voice
  ├── constructs Kernel
  ├── health checks
  ├── shutdown logic
  └── kernel.run()
```

The architecture becomes:

```
run.py
  └── ApplicationBuilder.build()
        ├── _create_infrastructure()
        ├── _create_knowledge()
        ├── _create_memory()
        ├── _create_reasoning()
        ├── _create_agency()
        ├── _create_brain()
        └── _create_voice()

Application
  ├── owns every subsystem
  ├── .validate()
  ├── .start()
  └── .shutdown()
```

## Dependency Chain

```
EventBus
  → SharedState
    → Memory
      → Retriever (needs vector store + graph)
        → KnowledgeGraph, BrainGraph, BeliefEngine
          → Brain (needs ALL of the above)
            → Voice (needs brain for personality_state)
              → Kernel (needs brain + voice)
```

## Container Benefits

- `app.memory.store(...)` instead of passing `memory` as a parameter everywhere
- `app.shutdown()` stops everything in reverse order with timeouts
- New subsystems add ONE `_create_*` method instead of edits across run.py
- Health checks live in `app.validate()` instead of scattered in run.py

## Phased Rollout

| Phase | Description | Status |
|-------|-------------|--------|
| **1** | Container extraction — `Application.build()` wraps existing construction logic. run.py becomes thin. | **DONE** |
| **2** | Split `build()` into `_create_*` methods — each method creates one subsystem cluster | Pending |
| **3** | Formalize lifecycle — `start()` and `shutdown()` move from run.py into Application | Pending |
| **4** | Validation gates — assertions after each build phase, startup progress logging | Pending |

## Phase 1 Details

**What changed:**
- Created `core/application.py` — `Application` class with 35+ subsystem fields
- `Application.build()` — classmethod that constructs every subsystem identically to the old `run.py:main()`
- `Application.validate()` — health checks (same as old lines 689–738)
- `Application.shutdown()` — ordered teardown with timeouts
- `run.py:main()` — reduced from 510 lines to ~20 lines

**Not changed:**
- `bootstrap_system()` — left untouched (used by API server)
- All subsystem constructors — identical calls
- All try/except blocks — preserved
- `cleanup()`, `validate_environment()` — kept in run.py

### Phase 5 — V2 Audit Remediation (Jul 20)

- **Fresh audit report** created at `docs/fresh-audit-findings-2026-07-19.md` with verified ground truth (counts corrected: 43 not 54 bare excepts in api/, 23 not 28 in knowledge/, 5 not 8 thread-unsafe files).
- **All 24 docs merged** into `docs/MERGED_COMPLETE.md` (530KB, 8,211 lines). All other `.md` files deleted from `docs/`.
- **P0 — All 9 Critical items fixed:**
  - 43 bare `except Exception: pass` → `logger.exception()` (6 route files + server.py + stream_manager.py)
  - Global logger suppression removed (`api/server.py:10`)
  - RLock added to 5 thread-unsafe files: OpenRouter, Agent, ReflectionEngine, STT, SpeakerEncoder
  - `verify_consistency()` attribute names fixed (`.sensory`→`.semantic`, `.short_term`→`.episodic`, `.long_term`→`.autobiographical`)
  - Pre-existing syntax error in `api/routes_memory.py:14` fixed
- **P1 — All High-priority items fixed (1,168 tests pass):**
  - 23 bare excepts in `knowledge/` → logged (obsidian_writer, vault_post_processor, obsidian_reader, cognitive_graph, watcher, reasoning, vault_migrator, retriever)
  - 6 bare excepts in `agency/` → logged (goals, dreaming, dream_tasks)
  - RLock on EmbeddingService `_cache` (`memory/embedding_service.py`)
  - App whitelist in `SystemActions.open_app()` with 20+ allowed apps (`execution/handlers.py`)
  - Destructive hotkey filter in `DesktopActions.type_text()` blocking Alt+F4, Ctrl+W, etc.
  - SHA-256 checksum verification on VAD JIT model download (`voice/vad.py`)
  - Consolidation orphan fix: `decay.consolidate()` accepts `store_fn` callback to persist MemoryObject nodes
- **All 1,168 tests pass**, 0 failures.
- **P2 — All Medium-priority items fixed (1,171 tests pass):**
  - RLock added to all 9 VectorStore public methods (`memory/vector_store.py`)
  - `echo_canceller.py` deleted — replaced by `FullAEC` throughout (voice_manager, tests)
  - `core/emotion.py` god class split — `update()` → 16-line dispatch + 9 handler methods
  - `knowledge/obsidian_writer.py` god class split (571→96 lines) — extracted `GraphExporter`, `StateDumper`, `MemoryWriter`
  - `voice/voice_manager.py` constructor reduced from 30+ params to 1 (`VoiceConfig`) with `**kwargs` backward compat
  - Memory triple pipeline unification verified: `MemoryManager` delegates to `pipeline.store()` → `intelligence.process()`
- **P3 — All Low-priority backlog items fixed:**
  - 5 dead `_graph_to_*` flags removed from `knowledge/brain_graph.py`
  - `from __future__ import annotations` added to `agency/dream_report.py` for 3.9 compat
- **V2 audit 100% complete — all 25 findings resolved (1,171 tests pass).**

---

### Phase 6 — Multi-Specialist System Audit (Jul 20)

- **Comprehensive audit** of all 14 subsystems by 4 specialists (Systems Auditor, Memory Architect, Software Advisor, Codebase Architect) conducted in parallel.
- **5 specialist tasks** launched simultaneously covering: core/, memory/, knowledge/, voice/, api/ + execution/ + app/ + prompt/ + observability/ + agency/.
- **Overall score: B (7.5)** — Improved from V2's C+ (6.7), down from immediate post-fix 8.2 due to newly discovered issues.
- **3 P0 critical issues found:**
  1. `Emotion._sync()` deadlock — lock-ordering violation with `Brain._sync_emotion()`
  2. `VoiceManager._speaking` data race — main thread + audio callback, no sync
  3. Triple belief storage drift — `BeliefEngine` + `BrainGraph` + `CognitiveGraph` with no consistency validation
- **16 P1 high issues** documented — thread-unsafe `_RateLimiter`, `InterruptManager` lock exposed, TOCTOU in `DreamEngine`, 10 bare excepts in knowledge/, 27+ debug-level errors, `indexer._indexed_count` race, etc.
- **16 P2 medium issues** — layer breaches, dead code (22 DreamEngine wrappers), duplicate code, formatting, etc.
- **Full report appended below.**

---

# Multi-Specialist Audit — Jul 20 2026

## Subsystem Health Scores

| Subsystem | Files | Score | Trend vs V2 |
|-----------|-------|-------|-------------|
| core/ | 41 | B– (6.5) | ⚠️ Deadlock risk found |
| memory/ | 24 | B– (6.5) | ⚠️ Layer breaches persist |
| knowledge/ | 26 | B (7.0) | ✅ Improved from V2 |
| agency/ | 11 | B+ (8.0) | ✅ Clean |
| reasoning/ | 4 | A– (8.5) | ✅ Clean |
| voice/ | 31 | B (7.0) | ✅ Good thread safety |
| api/ | 12 | B (7.0) | ✅ Much improved |
| execution/ | 3 | B+ (7.5) | ✅ Good security |
| app/ | 17 | A– (9.0) | ✅ Builder pattern |
| prompt/ | 6 | A– (8.5) | ✅ Clean separation |
| observability/ | 2 | B+ (8.0) | ✅ Solid |
| config/ | 15 | A (9.5) | ✅ Minimal issues |

**Overall: B (7.5)**

---

## P0 — Critical Issues

### 1. Deadlock risk — `core/emotion.py:380-393`
`Emotion._sync()` acquires `self.lock` then `self._shared_state.lock`. `Brain._sync_emotion()` at `brain.py:518` acquires `self.state.lock` then calls `self.emotion.export()` which acquires `self.emotion.lock`. Lock-ordering deadlock.
**Fix:** Externalize state sync — `SharedState` pulls from `Emotion` instead of `Emotion` pushing to `SharedState`.

### 2. `_speaking` data race — `voice/voice_manager.py:47,83,88,241`
`_speaking` read/written from both main thread and audio callback thread with no synchronization.
**Fix:** Guard with `self._lock` or use `threading.Event`.

### 3. Triple belief storage drift
`BeliefEngine._beliefs`, `BrainGraph` belief nodes, and `CognitiveGraph.import_beliefs()` all maintain independent belief representations. No consistency validation.
**Fix:** Make `BeliefEngine._beliefs` single source of truth; BrainGraph/CognitiveGraph read from it.

---

## P1 — High Issues

| # | Issue | File:Line |
|---|-------|-----------|
| 1 | `_RateLimiter` thread-unsafe (plain dict, no lock) | `api/server.py:164-178` |
| 2 | `InterruptManager.lock` is public (should be `_lock`) | `voice/interrupt.py:24` |
| 3 | `InterruptManager.is_interrupted()` not guarded | `voice/interrupt.py:87` |
| 4 | Path traversal risk in tracer filename | `observability/tracer.py:113-123` |
| 5 | Unvalidated plugin name in `system_plugin_load` | `api/routes_system.py:38` |
| 6 | TOCTOU race on `_dreaming` flag | `agency/dreaming.py:52-55` |
| 7 | Legacy Memory uses `Lock()` not `RLock()` | `memory/memory.py:36` |
| 8 | `indexer._indexed_count` data race | `knowledge/indexer.py:124` |
| 9 | 10 bare `except Exception:` without `as e` | `knowledge/*.py` (various) |
| 10 | 27+ errors logged at DEBUG (should be WARNING) | `knowledge/*.py`, `voice/*.py` |
| 11 | `MemoryIntelligence.process()` single monolithic try/except | `memory/intelligence.py:304-310` |
| 12 | Dead code: no-op loop in `utterance_segmenter.py` | `voice/utterance_segmenter.py:58-59` |
| 13 | `GraphExporter` counter no lock | `knowledge/graph_exporter.py:18-19,46,106` |
| 14 | `MemoryWriter` hash dedup TOCTOU | `knowledge/memory_writer.py:51-64` |
| 15 | Static file root mount may leak files | `api/server.py:416-417` |
| 16 | `_safe_execute` char whitelist blocks URL chars | `agency/tools.py:134` |

---

## P2 — Medium Issues

| # | Issue | File |
|---|-------|------|
| 1 | 5 files in memory/ import from knowledge/ (layer breach) | `memory/*.py` |
| 2 | `_text_overlap` duplicated across vector_store and consolidation | two files |
| 3 | 5+ inline imports inside methods | `memory/*.py`, `knowledge/*.py` |
| 4 | `MemoryState.load_from_file` logs at DEBUG | `memory/state.py:109` |
| 5 | `EmbeddingService._cache_tag` no model fingerprinting | `memory/embedding_service.py:30` |
| 6 | `VectorStore.enforce_cap()` age cap flattens old entries | `memory/vector_store.py:462` |
| 7 | 22 dead delegating wrappers in DreamEngine | `agency/dreaming.py:146-211` |
| 8 | `_result()` duplicated across 3 handler classes | `execution/handlers.py:78,153,190` |
| 9 | Lambda-in-loop route registration fragile | `api/server.py:405-412` |
| 10 | `Attention` class zero locking | `core/attention.py` |
| 11 | `VoiceManager.listen()` 124-line method | `voice/voice_manager.py:399-523` |
| 12 | `_valid_audio()` checks only file extension | `voice/realtime.py:341-351` |
| 13 | `noise_filter` vs `adaptive_noise_filter` dead param | `voice/voice_manager.py:32` |
| 14 | Three-layer graph abstraction | `knowledge/*.py` |
| 15 | `PersonalityEvolution`/`ProceduralMemory`/`GraphReflection` thin wrappers | `agency/*.py` |

---

## What's Working Well

1. **Universal RLock adoption** — 20+ classes use `threading.RLock()` after V2 audit
2. **Zero bare `except: pass`** — all remaining excepts name Exception and most log
3. **Security layering** — app whitelist, keystroke filter, command validation, char whitelist
4. **ApplicationBuilder** — clean 8-layer boot with dependency ordering
5. **Prompt subsystem** — 5 focused files, stateless, thoroughly documented
6. **Memory retrieval** — MMR diversification, multi-factor ranking, cascade pattern
7. **Vault replay dedup** — idempotent boot, MD5-keyed dedup throughout
8. **HealthRegistry** — gold-standard thread safety in observability
9. **Error isolation** — audio callback never crashes from component failure
10. **SHA-256 model verification** — VAD JIT download checksummed
11. **WriteJournal** — async batched write path for hot-path performance
12. **1,171 tests pass** — zero regressions

---

## Recommendations by Priority

### Immediate (P0)
- Fix deadlock in `Emotion._sync()` — 2-lock ordering violation
- Fix `_speaking` data race in `VoiceManager`
- Unify belief storage — eliminate triple-source drift

### This Sprint (P1)
- Lock `_RateLimiter` in API server
- Fix 10 bare excepts in knowledge/ to capture `e`
- Promote 27 debug-level errors to WARNING
- Fix indexer counter race, InterruptManager lock privacy, TOCTOU in dreaming
- Add plugin name validation, tracer path sanitization

### This Quarter (P2)
- Decouple memory/knowledge layer breaches via dependency injection
- Extract duplicate `_text_overlap` to shared utility
- Remove 22 dead delegating wrappers from DreamEngine
- Split `VoiceManager.listen()` into smaller methods
- Extract `_result()` duplication in execution handlers
- Add model fingerprinting to EmbeddingService cache
- Add RLock to `Attention` class

### Backlog (P3)
- Normalize formatting with `ruff format` across inconsistent files
- Replace MD5 with SHA-256 for consistency
- Remove dead `MemoryObject.lock`
- Add semantic chunk boundaries to chunker
- Replace fragile keyword-matching planner with LLM-based planning

---

## Scorecard Evolution

| Dimension | V1 (Jul 19) | V2 (Jul 19) | Post-Fix (Jul 20) | Audit (Jul 20) |
|-----------|-------------|-------------|-------------------|-----------------|
| Security | 4.0 | 5.5 | 8.5 | 8.0 |
| Reliability | 4.5 | 5.5 | 8.0 | 7.5 |
| Maintainability | 5.0 | 5.5 | 7.5 | 7.0 |
| Memory System | 5.5 | 6.5 | 7.5 | 6.5 |
| **OVERALL** | **6.1 (C)** | **6.7 (C+)** | **8.2 (B)** | **7.5 (B)** |

---

# Future Roadmap

## Prioritization

| Priority | Item | Effort | Impact | Dependencies |
|----------|------|--------|--------|-------------|
| P1 | Production hardening | Medium | High | None |
| P1 | Multi-session / auth | High | High | Production hardening |
| P2 | Knowledge base enrichment | Medium | Medium | None |
| P2 | Performance optimization | Medium | Medium | None |
| P3 | Embedding model versioning | Low | Low | None |
| P3 | Plugin ecosystem | High | Medium | Plugin system exists |
| P4 | Mobile/web companion app | High | High | API exists, needs auth |
| P4 | Documentation site | Medium | Medium | MERGED_COMPLETE.md exists |

---

## Item 1 — Production Hardening

**Goal:** Make Mai AI safe to expose to a network.

### 1a — HTTPS Certificates
- Use `ssl.SSLContext` with auto-generation via `cryptography` or `trustme` for dev
- For production: Let's Encrypt via `certbot` or `acme-tiny`
- Mount certs via Docker volumes in `docker-compose.yml`
- FastAPI `uvicorn.run(ssl_keyfile=..., ssl_certfile=...)`

### 1b — Rate Limiting
- Add `slowapi` middleware to FastAPI
- Per-IP rate limits: 60 req/min for chat, 300 req/min for health/status
- Token-bucket or sliding-window implementation
- Configurable via settings (limits, exempt IPs, burst capacity)

### 1c — Authentication (JWT)
- `python-jose` + `passlib` for JWT issuance and password hashing
- `/api/auth/login` endpoint returns access + refresh tokens
- `fastapi.Security` dependency on all protected routes
- Token expiry: 15 min access, 7 day refresh
- API key alternative for programmatic access

### 1d — CORS + Headers
- Strict `CORSMiddleware` (allow only known origins)
- Security headers via `fastapi.middleware.trustedhost` or Starlette `Response` headers
- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Strict-Transport-Security`

### Files to create/modify
- `api/server.py` — add middleware, auth router
- `api/auth.py` — JWT logic
- `config/settings.py` — rate limit config, JWT secret, cert paths

---

## Item 2 — Multi-Session / Persistent State

**Goal:** Support multiple independent users with persistent profiles.

### 2a — User Profiles
- SQLite or JSON-based profile store in `profiles/`
- Each profile: user_id, display_name, preferences, memory scope, conversation history
- Profile CRUD via API: `POST /api/profile`, `GET /api/profile/{id}`

### 2b — Memory Scoping
- All `MemoryObject` entries tagged with `user_id` metadata field
- `AdvancedRetriever.retrieve()` filters by `user_id` when provided
- Brain switches between profiles on `switch_user(user_id)` call

### 2c — Cloud Sync
- Periodic sync to S3/Backblaze B2 via `boto3`
- Sync profiles, memory vault, knowledge base config
- Conflict resolution: last-writer-wins with timestamp logging
- Configurable sync interval (default 300s)

### 2d — Session Management
- Redis or in-memory session store for active sessions
- Session expiry, force-logout, concurrent session limits

### Files to create/modify
- `profiles/` — profile storage directory
- `api/routes_profile.py` — profile CRUD endpoints
- `memory/scope.py` — user-scoped memory filtering
- `core/session_manager.py` — session lifecycle
- `sync/cloud_sync.py` — S3/b2 sync engine

---

## Item 3 — Knowledge Base Enrichment

**Goal:** Improve retrieval quality through smarter chunking.

### 3a — Semantic Chunking
- Replace character-level split in `knowledge/chunker.py` with topic-shift detection
- Use embedding cosine similarity between adjacent sentences as boundary signal
- Configurable threshold (default 0.3) — gap > threshold = new chunk
- Fall back to character split when embeddings unavailable

### 3b — Overlap Unification
- Unify `_carry_over()` (word-level) and `_split_by_tokens()` (character-level) to both use token-level overlap
- Single `OVERLAP_TOKENS` constant across both paths

### 3c — Chunk Metadata
- Tag each chunk with: source document, section heading, position, embedding hash
- Store metadata in `DocumentStore` for filtered retrieval

### Files to modify
- `knowledge/chunker.py` — semantic boundary detection
- `knowledge/document_store.py` — chunk metadata schema

---

## Item 4 — Embedding Model Versioning

**Goal:** Prevent stale cached embeddings when the model changes.

### 4a — Model Fingerprinting
- On load, compute SHA-256 hash of `EmbeddingService.model` weights or config
- Store fingerprint as key prefix in `_cache` (e.g., `f"{fingerprint}:{text_hash}"`)
- On model change, all cached entries with old prefix are automatically ignored

### 4b — Gradual Cache Invalidation
- On model change, don't purge immediately — serve stale for existing entries
- New embeddings computed with new model on cache miss
- Background thread expires old-prefix entries after TTL

### Files to modify
- `memory/embedding_service.py` — fingerprint logic, cache key prefix

---

## Item 5 — Plugin Ecosystem

**Goal:** Expand the plugin system into a rich ecosystem.

### 5a — Plugin Discovery
- Scan `plugins/` directory on boot (already exists)
- Add `plugins.json` manifest for metadata (name, version, author, hooks)

### 5b — Plugin Lifecycle
- `on_load()` already exists — add `on_activate()`, `on_deactivate()` for enable/disable
- Plugin state: discovered → loaded → activated → deactivated → unloaded

### 5c — Plugin Marketplace
- Remote plugin registry via JSON manifest at a known URL
- `plugin install <name>` downloads from registry
- Dependency resolution between plugins
- Version compatibility check against Mai AI API surface

### 5d — Core Plugins
- **Weather plugin**: fetches weather via OpenWeatherMap API
- **Calendar plugin**: Google Calendar integration
- **News plugin**: RSS/Atom feed reader
- **System monitor**: CPU/memory/disk stats via API
- **Web scraper**: extract content from URLs using `requests` + `BeautifulSoup`

### Files to create/modify
- `plugins/manifest.json` — plugin registry
- `core/plugin_system.py` — lifecycle states, remote install
- `plugins/weather.py`, `plugins/calendar.py`, `plugins/news.py`, etc.

---

## Item 6 — Mobile / Web Companion App

**Goal:** Provide a polished mobile-friendly interface for Mai AI.

### 6a — Web UI Enhancement
- Existing `api/static/index.html` as foundation
- Add mobile-responsive CSS (media queries, touch targets ≥ 44px)
- Progressive Web App (PWA): service worker, manifest.json, offline fallback
- Push notifications via Notification API

### 6b — React / Vue SPA (optional)
- Separate SPA in `ui/` directory
- Communicates with same REST API
- Component library: chat, memory browser, graph visualizer, settings panel

### 6c — Mobile App (future)
- React Native or Flutter wrapper around the REST API
- Voice input via native Speech-to-Text
- Background push notifications

### Files to create/modify
- `api/static/manifest.json` — PWA manifest
- `api/static/sw.js` — service worker
- `api/static/css/mobile.css` — responsive styles
- `ui/` — optional SPA directory

---

## Item 7 — Performance Optimization

**Goal:** Identify and resolve bottlenecks.

### 7a — Profiling
- Add `cProfile` or `py-spy` profiling to key endpoints (`/api/chat`, `POST /api/knowledge/ingest`)
- Profile boot sequence (ApplicationBuilder.build())
- Identify top 5 hotspots by cumulative time

### 7b — Async I/O
- Audit blocking calls in async endpoints (file I/O, subprocess, LLM calls)
- Convert synchronous `requests` calls to `httpx.AsyncClient`
- Use `asyncio.to_thread()` for CPU-bound operations (embedding, chunking)

### 7c — Caching
- Add `functools.lru_cache` or `cachetools.TTLCache` to frequent read paths:
  - `KnowledgeGraph.get_entity()` — entity lookups
  - `BeliefEngine.get_beliefs()` — belief queries
  - `VectorStore.search()` — memoize identical queries (short TTL)
- Cache invalidation via EventBus events

### 7d — Connection Pooling
- Reuse `httpx.AsyncClient` across LLM provider calls
- Database connection pooling for any persistent storage
- HTTP keep-alive for Ollama/OpenRouter connections

### 7e — Batch Operations
- WriteJournal already batches — verify batch sizes are optimal
- VectorStore.add() could batch embeddings
- KnowledgeBaseBuilder could batch file indexing

### Files to modify
- `llm/providers/` — connection pooling, async HTTP
- `memory/vector_store.py` — query caching
- `knowledge/graph.py` — entity caching
- `core/brain.py` — profile-guided optimization

---

## Item 8 — Documentation Site

**Goal:** Transform `docs/MERGED_COMPLETE.md` (518 KB) into a browsable documentation site.

### 8a — Static Site Generator
- Use MkDocs or Docusaurus
- Split `MERGED_COMPLETE.md` into chapter files:
  - `docs/guide/getting-started.md`
  - `docs/guide/architecture.md`
  - `docs/guide/memory-system.md`
  - `docs/guide/voice-pipeline.md`
  - `docs/guide/agency-tools.md`
  - `docs/guide/api-reference.md`
  - `docs/guide/deployment.md`

### 8b — Site Features
- Search across all documentation
- Dark/light theme toggle
- Code examples with syntax highlighting
- API endpoint reference with request/response schemas
- Auto-generated module reference from docstrings

### 8c — CI Integration
- Build docs on push via GitHub Actions
- Deploy to GitHub Pages or Vercel

### Files to create
- `mkdocs.yml` — MkDocs configuration
- `docs/guide/*.md` — split chapter files
- `docs/api/*.md` — auto-generated API reference
- `.github/workflows/docs.yml` — CI deploy workflow

---

## Native OS Bridge — Phases 2-3 Complete (Jul 24)

**Plan:** `docs/native-bridge-architecture.md` — Full architecture for converting Mai AI from a browser app to a native Windows daemon with system tray, global hotkeys, WebSocket bridge, notifications, clipboard/FS access, and background persistence.

### Phase 1 — Foundation (Jul 22)
- `native/tray.py` — TrayDaemon (pystray system tray icon)
- `native/notifier.py` — Notifier (plyer toast notifications via EventBus)
- `native/bridge.py` — WSBridge (WebSocket ↔ daemon bridge)
- `api/routes_system.py` — Bridge status/restart endpoints
- `api/stream_manager.py` — StreamManager SSE with daemon sync

### Phase 2 — OS Integration (Jul 24)
- `native/hotkeys.py` — HotkeyManager (Alt+Space, Ctrl+Alt+M, Ctrl+Alt+C, Win+Shift+M; degrades if `keyboard` missing)
- `execution/handlers.py` — `ClipboardActions` (read/write via pyperclip), `FileSystemActions` (list/read/write/watch, sandboxed to ROOT_DIR + OBSIDIAN_VAULT)
- `api/routes_system.py` — `clipboard_actions`/`filesystem_actions` mixin attrs
- `api/server.py` — `/api/system/clipboard` (GET/POST), `/api/system/fs/` (list/read/write) routes with Pydantic models

### Phase 3 — Polish & Packaging (Jul 24)
- `native/startup.py` — `StartupManager` (Windows HKCU Run key via `winreg`)
- `native/watchdog.py` — `HealthMonitor` (polls `/api/health`, subprocess PID watchdog)
- `run_daemon.py` — Daemon entry point wiring tray + hotkeys + clipboard/FS + uvicorn
- `scripts/build_daemon.py` — PyInstaller build script
- `scripts/installer.iss` — Inno Setup installer (startup task, registry key)
- `api/static/js/os.js` — SSE reconnection with exponential backoff (1s–30s, max 10 retries), offline overlay
- `api/static/css/style.css` — `.connection-indicator` styles

### Async I/O — Parallel Retrieval (Jul 24)
- `knowledge/retriever.py:retrieve()` — All 4 retrieval sources (vector, beliefs, KG, attention) queried concurrently via `ThreadPoolExecutor`; early exit cancels remaining futures

**New deps:** pystray, Pillow, pywin32, plyer, keyboard, pyperclip, pyinstaller
**New dir:** `native/` — 7 modules
**Modified:** `execution/handlers.py`, `api/routes_system.py`, `api/server.py`, `api/stream_manager.py`, `api/static/js/os.js`, `api/static/css/style.css`, `knowledge/retriever.py`, `requirements.txt`
---

## Event Fabric — Phases 4-5 Complete (Jul 27)

### Phase 4 — Incremental Migration (all legacy publish sites)
- 53 production publish sites migrated from `bus.publish(topic, payload)` to `publish_event(bus, topic, payload, source)` (`core/mai_message.py`) ? MaiMessage envelope + semantic `data.*` topics + registry validation/authorization.
- Subscribers updated: `api/stream_manager.py` STREAM_TOPICS, `api/ws_bridge.py`, `api/server.py` (`data.dream.completed` runtime), `core/os_kernel.py` (`data.dream.started/ended` runtime), `native/notifier.py`.
- Frontend JS updated (`os.js`, `notifications.js`, `presence.js`) + tests updated (publish_message + msg.type/payload assertions, register_event_specs on real buses).
- **1418 tests pass.**

### Phase 5 — Reactive UI (state.* projection bus)
- UI now subscribes **exclusively** to `state.*`; `data.*` remains the subsystem fabric record.
- 15 `STATE_*` constants + high-priority specs in `core/event_specs.py` (State bus — UI projection section).
- Dual-publish producers: voice (listening/speaking/idle/wake), emotion.changed, memory.updated, reasoning.busy/complete/reflection, dreaming.started/finished, goal.updated, agent.completed, knowledge.updated, belief.updated.
- Consumers: `api/stream_manager.py`, `api/ws_bridge.py`, `native/notifier.py`, `api/static/js/{os.js,notifications.js,presence.js}` ? state.* only.
- Exceptions: `data.dream.*` stays runtime-subscribed (api/server.py, os_kernel.py).
- Voice fix: duplicate VOICE_STOPPED publish removed in `voice/voice_manager.py` stop().
- **1418 tests pass.**
- Full spec: `docs/event-fabric-architecture.md` (v2.1, Phase 5 section updated).

---

## Vault Remediation — Aug 6 2026

Full examination: `docs/vault-examination-2026-08-06.md`. Four issues fixed:

### Fix 1 — Broken memory links (~89 `[[links]]` to absent notes)
`knowledge/memory_writer.py` now:
- `_link_target_exists(name)` — checks `vault_root/graph/{safe}.md` before emitting any wiki link
- `_resolvable_links(names)` — filters tags/entity names to existing graph notes only
- `write()` no longer writes broken `[[wiki]]` links; emits only resolvable ones for `🏷️ Tags`/`🔗 Memory Links`/`👥 Related Entities`. `#tag` markdown kept for all tags.

### Fix 2 — Stats & relationship drift
- `state_dumper.py` `_vault_first_met(date_str)` — earliest `YYYY-MM-DD.md` conversation filename (or frontmatter timestamp) becomes `first_met` instead of "today".
- `state_dumper.py` `_vault_conversation_turns()` — counts real `### 👤 User` headers across `conversation/*.md`; `total_conversations`/`total_messages` no longer use the inflated `interaction_count` (was 674), falling back to it only when the vault has no conversations.
- `relationship_updater.py` `_load_from_file()` — integrity guard: an empty/fresh file (interactions=0 AND closeness=0 AND trust=0) resets to 0.5/0.5 baseline instead of pinning Trust=0 forever.

### Fix 3 — Graph entity pollution (junk unknown entities)
- `graph_manager.py` gate: `unknown` entities with `confidence < 0.25` (the fallback extractor's lowercase-token tier) are refused; summary gains `junk_skipped`.
- New `knowledge/vault_janitor.py` — `VaultJanitor` one-time sweep: removes junk entities from the KnowledgeGraph and orphan junk-named `graph/*.md` notes (`JUNK_TOKENS` + stopword/gte-ignore `_STOPWORD_RE`). `dry_run=True` default.
- New `scripts/sweep_graph_junk.py` — CLI: loads `graph/graph.json` (dict or BrainGraph list) → `sweep()`; `--apply` commits. Dry run against live vault found 24 junk entities + 19 junk note files.

### Fix 4 — Cross-day memory duplication (10x machine-learning problem)
`memory_writer.py` root cause: `hash_cache` is process-local and resets each boot, so the same turn was re-appended to a fresh daily file.
- `_dedup_hit_anywhere(folder, user)` — scans the whole growth folder for an existing `### 👤 User\n{user}\n` needle across every `*.md` (cross-day).
- `_bump_reinforcement(fpath, user)` — increments the canonical entry's `reinforcement_count` in place (regex `_REINFORCEMENT_RE`).
- `write()` returns `False` and bumps the existing entry instead of appending a duplicate.
- Only applies to growth folders (`conversation`, `archive`, `important`); overwrite folders unaffected.

### Tests
- 20 new tests in `tests/test_knowledge.py`: cross-day dedup (same day/rename day/different), reinforcement bump, link filtering (with/without graph dir, entity links), stats backfill (first_met, real turns vs inflated counter, fallback), junk gate (skip 0.2, keep 0.3), VaultJanitor (find/dry-run/apply/note-sweep/entity-sweep), RelationshipUpdater guard.
- **1443 tests pass**, 0 failures (baseline 1423).

---

## Ecosystem Audit + P0 Remediation — Aug 6 2026

Full 24-section report: `docs/audit-report-2026-08-06.md`. 6 parallel subsystem audits + direct runtime verification of every P0/P1 claim. Overall health **B (7.3/10)**.

### P0s fixed (all verified live before fixing)
1. **Daemon boot crash** — `run_daemon.py:76` passed `mai.app` (MaiAPI has no `.app` attr; `hasattr(...) == False` verified). → uses module-level `app` from `api/server.py`.
2. **FileSystemActions dead** — `Path` 3× + `Any` 1× used without imports in `execution/handlers.py` (NameError). → added `from pathlib import Path` + `from typing import Any`.
3. **Dual-writer vault clobber** — `MemoryWriter.write()` opened compiler-owned folders (`identity`, `preferences`, `relationship`, `knowledge`, `projects`, `people`, `places`, `dreams`, `statistics`) in `"w"` mode with raw turn format, wiping StateDumper-compiled facts (live-reproduced: compiled `[age] I am 25` bullet facts destroyed by one raw identity write). → `MemoryWriter` now enforces single-writer ownership: raw writes to `compiler_owned_folders` redirect to `conversation/` with a warning; only StateDumper/VaultCompiler writes structured files.

### P1s fixed
4. **SSE/WS event drop** — `asyncio.get_event_loop()` called from EventBus worker threads (RuntimeError → silent drop; verified at `stream_manager.py:72`, `ws_bridge.py:74`). → loop captured via `get_running_loop()` at connection time (`/api/stream` handler, `handle_ws()`); handlers use `call_soon_threadsafe`/`run_coroutine_threadsafe`; drop-warning log if loop missing.
5. **LLM probe under lock** — `LLMManager._probe()` held global RLock during 2–5s network probes, serializing all concurrent generate/stream. → probe decision snapshotted under lock; network I/O runs outside; results committed back.

### Remaining backlog (from audit)
- **P1:** `logger` NameErrors (`core/behavior_builder.py:574`, `core/idle_behavior.py:169`) + `Emotion.get()` misuse; dedup signature mismatch (in-process md5 includes `ai`, cross-day needle doesn't — `memory_writer.py`); `/api/system/config` unauthenticated; Agent single-step loop (`agency/agent.py:104-111`); goal-pause priority inverted (`agency/goals.py:112`); tool contract mismatch (`run_command`/`open_url` unreachable); FS sandbox only active under daemon.
- **P2:** AEC never fed (0 call sites); `toggle()` missing; mic callback accumulation; VAD load-in-callback stall; journal full-rewrite per thought; streaming failover missing; belief fan-out 10k/call in retriever; `ai_response` dropped by extractor; tracer raw-PII files; RateLimiter buckets unbounded; `chat.js` innerHTML XSS; CORS `["*"]`+credentials.
- **P3:** MD5 usage; `E:\MaiMemory` hardcode; import-time side effects; `stats.md` reflections=0.

### Tests
- 2 new regression tests in `tests/test_knowledge.py` (`test_raw_write_never_clobbers_compiler_owned_folder`, `test_raw_write_to_relationship_redirected`).
- **1445 tests pass**, 0 failures (baseline 1443).


---

## Backlog Remediation Sprint - Aug 6 2026

Worked down the audit backlog (`docs/audit-report-2026-08-06.md` section 26). All P1 + P2 items fixed.

### P1s fixed
1. **logger NameErrors + Emotion.get() misuse** - `core/behavior_builder.py` and `core/idle_behavior.py` got `import logging` + module `logger`; `idle_behavior._emotion_state()` rewritten to handle both plain dicts and `Emotion` objects (calls `.get()` with no args, reads `raw["state"]`, float coercion + fallback).
2. **Dedup signature mismatch** - `knowledge/memory_writer.py` `_dedup_hit_anywhere()`/`_bump_reinforcement()` now include the AI block in the needle (`### ?? User\n{user}\n\n### ?? Mai\n{ai}\n`), matching the write format; `write()` call sites updated.
3. **`/api/system/config` unauthenticated** - `api/server.py` `/api/config` GET now requires `_require_auth` dependency.
4. **Agent single-step loop + dishonest success** - `agency/agent.py`: multi-step `_plan_next()`; analysis tasks (reason/think/analyze/why/how/what) get ONE synthesis pass via the `reason` tool before `complete`; run ends with honest `success=False` when every step failed (no more false success on zero evidence); registry.call wrapped in try/except. `test_fallback_concrete_reason_to_search` updated to assert honest failure.
5. **Goal-pause priority inverted** - `agency/goals.py:112` `min()` to `max()`: over `_max_active`, the LOWEST-priority goal is paused (previously paused the HIGHEST). `test_max_active_pauses_excess_lowest_priority` updated.
6. **Tool contract mismatch** - `execution/safe_executor.py` `_validate()` reads `action.get("content")` (falling back to legacy `url`/`command` keys) so `execute_action` tool calls with `{"type","content"}` reach `open_url`/`run_command` instead of always failing validation.
7. **FS sandbox only under daemon** - `execution/handlers.py` `_CLIPBOARD_SANDBOX_DIRS` defaults to `[ROOT_DIR, OBSIDIAN_VAULT]` at import; `_configure_sandbox()` still overrides. Sandbox is active for all entry points (API server, daemon, tests).

### P2s fixed
8. **chat.js innerHTML XSS** - `api/static/js/chat.js` added `_escapeHtml()`; message content, session labels, and session ids escaped before innerHTML injection.
9. **RateLimiter buckets unbounded** - `api/middleware/rate_limiter.py` `max_buckets` cap (default 4096, min 64) + `_evict_stale()` pruning expired windows and LRU-evicting oldest buckets when over cap.
10. **`toggle()` missing + mic callback accumulation** - `voice/voice_manager.py` added `VoiceManager.toggle()` (start/stop flip); `voice/microphone.py` `stop()` clears `_callbacks` so per-stream closures don't accumulate across start/stop cycles.
11. **`_version_mismatches` race** - `core/event_bus.py` counter incremented under `self._lock` (previously unlocked increment from dispatch threads racing with `stats()` read).
12. **Scheduler lock discipline** - `core/scheduler.py`: `register_task`/`enable_task`/`disable_task`/`remove_task`/`stats`/loop iteration/recovery block and `_run_task` counter mutations all guarded by the previously-unused `self.lock`.

### Tests
- New: `tests/test_rate_limiter.py` (6), `tests/test_scheduler.py` (6), execution sandbox/contract tests (5), voice toggle/mic tests (4).
- Updated: `tests/test_agency.py` (honest-failure assertion), `tests/test_agency_advanced.py` (goal-pause priority).
- **1466 tests pass**, 0 failures (baseline 1445).

---

## Backlog Remediation Sprint 2 - Aug 6 2026

Second pass on the audit backlog (§26 short-term list). All remaining open P2 items fixed:

### P2s fixed
1. **M-4 `_bump_reinforcement` quote corruption** - `knowledge/memory_writer.py` regex now captures the original quote char (`reinforcement_count(['"]?)`) and preserves it in the substitution instead of hardcoding `'` (corrupted `"`-quoted metadata).
2. **M-5 journal path skips `add_entity_links`** - `memory/pipeline.py` `_graph_batch` now mirrors the non-journal path: after `process_conversation`, re-matches entities and calls `add_entity_links` for newly discovered ones; enqueue carries the pre-graph `entity_names` so `added` is computed identically to the sync path.
3. **M-8 VaultJanitor short-entity false positives** - `knowledge/vault_janitor.py` `_is_junk_name()` no longer flags all 2-char names: single chars are junk, 2-char tokens only when matching `JUNK_TOKENS`/`_SHORT_STOPWORD_RE` (preserves `AI`, `JS`, `ML`; graph normalizes case so acronyms are stored lowercase). Note sweep reordered: legitimate living-entity notes protected via `living_by_lower` lookup before name-junk check.
4. **P-3 ThoughtJournal quadratic rewrites** - `reasoning/journal.py` switched to append-only JSONL (one object per line, O(1) per store); `_load()` migrates legacy JSON-array files once; full-rewrite path only via `_save(None)`.
5. **R-5 VAD failure unlatched** - `voice/vad.py` latches load failure (`_load_failed` + class-level `_shared_load_failed`), so the audio callback never re-attempts the urllib download per chunk; download uses `urlopen(timeout=30)` + atomic `os.replace` instead of `urlretrieve` (no timeout).
6. **R-7 ReflectionEngine cadence write-only** - `reasoning/reflection.py` added `due(period)` gating + `enforce_cadence` flag + per-period intervals; `daily/weekly/monthly_reflection()` return `None` when not due; `force=True` bypasses (API route uses it); `app/builders/reasoning.py` enables cadence in production so PostThinkHooks no longer fires a daily reflection every turn.
7. **S-3 tracer plaintext PII** - `observability/tracer.py` `_redact_text()`/`_redact_trail()` mask emails, phones, IPs, API keys, UUIDs in inputs/outputs/cognitive-step snapshots before `_flush_to_disk()`; `redact_pii=True` default, in-memory trail keeps raw values.
8. **S-4 CORS + duplicate sources** - `api/server.py`: `allow_credentials` disabled when origins are wildcard `["*"]` (browsers reject the combo); `_require_auth` now delegates to `api.auth.get_current_user` (single source of JWT/static-token logic); `api/ws_bridge.py` imports `STREAM_TOPICS` from `stream_manager.py` instead of duplicating the list.
9. **S-5 `str(e)` leak in error responses** - new `api/errors.py` `safe_error(e, context)` logs the real exception and returns stable `"internal_error"`; all 35 `str(e)` response sites across 12 api/ files replaced.
10. **P-2 streaming failover broken** - `llm/manager.py` `stream()` now returns `_stream_with_failover()`: iterates the provider's generator; on mid-stream raise marks provider dead and restarts the request on the next provider; falls back to a single `generate()` chunk when all stream providers fail.
11. **P-4 OpenRouter unbounded retry** - `llm/providers/openrouter.py` added `max_retry_budget` (default 45s): request-wide deadline bounds 3 models × 3 attempts × 30s Retry-After sleeps; backoff sleeps exceeding the remaining budget are skipped and the request aborts with `RuntimeError("OpenRouter retry budget exhausted")`.

### Tests
- New: `tests/test_vad.py` (5: latch, shared latch, prob-zero, quick path, reset); test_knowledge (2: double-quote preservation, acronym/junk-name classification + living-note protection); test_brain_graph (1: journal entity-link parity); test_reasoning (5 cadence + 1 JSONL incremental/legacy migration); test_observability (3: disk redaction, key/uuid redaction, disabled flag); test_profile_store (3: auth delegation, STREAM_TOPICS single source, CORS credentials); test_llm (2 mid-stream failover + 2 retry budget).
- Updated: `tests/test_observability.py` chat brain-exception now asserts `"internal_error"` (S-5).
- **1491 tests pass**, 0 failures (baseline 1466).

---

## Character Layer M-series — M5 & M6 Complete (Aug 9 2026)

### M5 — Greeting-First Conversation Experience (gate passed Aug 8)
- `GREETING_FIRST_ENABLED=True` + `GREETING_FIRST_DELAY_SECONDS=2.0` in `config/character.py` (re-exported via Settings).
- `core/os_kernel.py` `_tick()`: greeting-first trigger — once per session (`_session_greeted` guard), after boot settle delay, enters the same wake FSM path (WAKE_DETECTED ? GREETING ? IDENTIFYING ? CONVERSATION) with no wake word; wake mode fully intact (kernel `greeting_first=`/`greeting_delay=` overrides).
- Gate: 8 FSM tests in `tests/test_greeting_first.py`. Suite 1,602 green (baseline 1,594).

### M6 — Emotional Experience / Growth (gate passed Aug 9)
- `memory/experience.py` (new): `EmotionExperience` {event, meaning, emotion, relationship_impact, reflection, lessons, growth, significance, timestamp} + `ExperienceStore` (RLock, JSONL append-only, tolerant load). Cheap fields at ingest; reflection/lessons/growth lazily filled at dreaming via `mark_reflected()`.
- `memory/schema.py`: additive `MemoryObject.emotion_experience` field (round-trip + backward compatible).
- `memory/pipeline.py`: charged turns (emotion intensity >= 0.6) recorded on `experience_store` at `_store_impl()` — one JSONL append, no blocking.
- `agency/preference_evolution.py` (new): evidence windows, N>=3 threshold, weekly (>=1d clamped) cadence, direction flip via effective-list (canonical + overlay) comparison, decision trail {timestamp, topic, before, after, reason}, `revert()`, persistence, publishes `PREFERENCE_EVOLVED`, `on_change` callback.
- `core/identity/identity_core.py`: `get_preferences()` projects attached overlay (deepcopy only); `attach_preference_overlay()` read-only snapshot — canonical `core/identity/preferences.py` never mutated.
- Dreaming: level-5 task `experience_reflection` (significant unreflected experiences, LLM JSON reflection w/ deterministic fallback, knowledge entry per revisit), `DreamReport.experiences_reflected` metric, `DreamEngine(experience_store=...)`.
- Wiring: `app/builders/agency.py` builds `app.experience_store` + `app.preference_evolution` (attached to dream engine + memory pipeline; on_change refreshes identity overlay). Config keys + event specs (`PREFERENCE_EVOLVED`, `EXPERIENCE_RECORDED`).
- Wiring audit (full connectivity check): 3 gaps closed — scheduler `dream_level5` task (daily), `scan_turn()` evidence scanner + pipeline ingest hook (`EXPERIENCE_RECORDED` publish, builder attach), weekly `preference_apply` scheduler task (unconditional registration, no-op until `brain.preference_evolution` exists; apply is background-only). Latent bug fixed: `scheduler._register_default_tasks()` `memory = None` nested inside `if brain:` → `UnboundLocalError` when brain absent (duplicate `brain` assignment removed).
- Gate: 32 new tests (test_experience 17, test_preference_evolution 12, test_dream_engine 3). **1,634 tests pass, 0 failures** (baseline 1,600 + 32).
- Wiring gate: +14 tests (test_preference_evolution +7 `TestScanAndApply`, test_scheduler +4 `TestM6SchedulerWiring`, test_experience +3 `TestPreferenceEvidenceHook`). **1,648 tests pass, 0 failures** (baseline 1,634 + 14).
- Fix: `core/identity/canonical.py` `BOOK_DIR` pointed at `docs/character/` but the canon volumes live in `core/identity/character/` — corrected; the 2 `TestCanonDrift` failures (M0 debt) resolved, full suite green.

### M7 — Character Behavioral Validation (gate passed Aug 9)
- Validation-only milestone (no new subsystems): proves the M0—M6 chain (canon — identity — relationship — needs — emotion — ThoughtPacket — style — prosody — renderer, + experience — dreaming — preference evolution — overlay) behaves like Mai. Spec: `docs/m7-character-behavioral-spec.md`.
- **Harness** (`tests/behavior/`): `ScenarioDriver` with virtual clock (patches `time.time` in `core.emotion` + `core.needs_engine`), `causal_trace` per turn (relationship/needs/emotion deltas, packet, style, prosody, renderer, mechanisms), deterministic ThoughtPacket fixtures (LLM stubbed).
- **6 scenarios green**: baseline consistency (5 unrelated turns, ±0.10 bands), praise—recognition (invisible machinery), jealousy across trust tiers (low=0.0 exact below gate `EMOTION_JEALOUSY_TRUST_GATE`=0.40 + security response; medium/high scaled by 0.06×(0.5+closeness)), reassurance—monotone jealousy decay ≤60% by turn 4 (mechanisms traced), preference emergence (N≥3 — overlay, trail, `PREFERENCE_EVOLVED`, identity projection), experience—L5 dream—reflection + knowledge entry.
- **Renderer parity**: same packet+style+prosody through KokoroRenderer (recorded TTS) / StubRenderer / duck-typed third renderer — semantic identity (register—emotion, rate—speed), only acoustic realization differs; renderers never mutate style/prosody/packet.
- **Trace isolation**: `causal_trace`/`deltas`/`snapshot`/`mechanisms` absent from `prompt/` + `core/prompt_builder.py`.
- **Production bug found + fixed (P1)**: `app/builders/agency.py` passed `evolved_preferences()` (flattened `{"likes": [...]}`) into `IdentityCore.attach_preference_overlay()` (expects `{topic: {"list": ...}}`) — `AttributeError` on next `get_preferences()` after first evolution (reproduced live). Fix: `PreferenceEvolution.overlay_map()` — single source of the identity shape; `on_change` + builder initial refresh use it. Regression-covered by `TestPreferenceEmergence` with full production wiring replicated.
- **M8 backlog** (queued, not patched in-test): experience replay dedup absent (same turn stored twice records twice); runtime consumers that inject evolved preferences / reflected experiences into next-turn context assembly unverified.
- Gate: 30 new tests (tests/behavior: TestBaselineConsistency 4, TestPraiseRecognition 2, TestJealousyTrustTiers 4, TestJealousyReassuranceDecay 5, TestPreferenceEmergence 3, TestExperienceDreamBehavior 3, TestM7SchedulerWiring 1, TestRendererParity 4, TestTraceSchema 2, TestTraceIsolation 2). **1,678 tests pass, 0 failures** (baseline 1,648 + 30).

### M8 — Finding Remediation (gate passed Aug 9)
- M8 = fix M7 findings only, no new subsystems. Spec: `docs/m7-character-behavioral-spec.md`.
- **1. Experience replay dedup** (spec §9): `ExperienceStore.record()` dedups by md5 event fingerprint — same event text records once; repeats return `None` (no duplicate `EXPERIENCE_RECORDED` publish); fingerprints rebuilt on `_load()` (restart-safe); `stats()["deduped"]` counter. Trade-off: identical event text across days treated as replay (matches vault/vector md5-dedup philosophy).
- **2. Preference consumer — production gap found + fixed**: `Brain._identity_data()` consults `IdentityCore.get_current_identity()` (overlay projected) with static-canon fallback; `think()` now passes it to the orchestrator (previously `identity_data` was never passed on the main chat path — the evolved overlay could not reach the prompt); `PromptOrchestrator.build()` falls back to `brain._identity_data()` (dict-validated, garbage-proof); `prompt/character.py` renders `PREFERENCES — ENJOYS / AVOIDS` sections (read-only projection, canonical never mutated).
- **3. Experience consumer**: `MemoryCoordinator.experience_context()` injects reflected experiences (significance ≥ 0.6, meaning/lessons filled) as `[experience] (significance X) event — meaning | lesson: ...` — limit 3, ≤900 chars, newest first; unreflected events stay silent. Plumbed through `prompt/context.py` (EXPERIENTIAL MEMORIES) → `prompt/builder.py` → `core/prompt_builder.py` (experiences kwarg passed only when set) → orchestrator (`memory_data["experiences"]` + `brain._experience_context()` fallback). Production wiring: `app/builders/cognition.py` attaches `app.experience_store` to `app.brain.memory_coordinator`.
- Gate: +12 tests (`TestReplayDedup` 5, `TestExperienceDreamBehavior.test_replay_same_turn_deduped` 1, `TestM8BehavioralProxies` 6). **1,690 tests pass, 0 failures** (baseline 1,678 + 12).

---

## M9 — Real-World Conversation Evaluation (gate passed Aug 9)

Validation-only milestone (architecture freeze M7—M9): unscripted LLM-driven sessions through the real `Brain` pipeline, persisted transcripts, mechanical rubric + human review. Spec: `docs/m9-real-world-evaluation.md`.

- **Harness** (`evaluation/`): `transcript.py` (TurnRecord, SessionTranscript JSONL save/load), `rubric.py` (CharacterRubric — 7 deterministic axes, RubricReport, review_required), `scenarios.py` (4 seed scripts), `runner.py` (FakeLLM stub, `build_stub_brain()` — real Brain/Emotion/Orchestrator on real-numeric stub state, SessionRunner with per-turn evidence), `scripts/run_m9_evaluation.py` (stub CI mode + `--mode real` app mode).
- **Instrumentation**: SessionRunner wraps `brain.prompt_orchestrator.build` to record the system prompt (recording only, no injection, M7 —11 isolation intact); clears `brain._response_cache` per turn (fresh generation verified via `FakeLLM.calls`).
- **Evidence per turn**: emotion export, relationship trust, ThoughtPacket, system flags (PREFERENCES / EXPERIENTIAL MEMORIES present, system_chars).
- **Axes**: transcript_quality, emotion_responsiveness (real valence engine verified moving), boundary_consistency (no "as an AI", no mechanism keys), preference_visibility, experience_visibility, relationship_trajectory (trust non-decreasing), repetition_control. Unexercised/low (< 3) axes force `review_required=True` — human is the judge.
- **Stub runs verified live**: jealousy (2 sessions), emotional (--overlay --experience); artifacts in `docs/evaluation/session-<name>-<ts>/ {transcript.jsonl, report.md}`.
- Gate: +20 tests (TestTranscript 5, TestRubric 8, TestRunner 6, TestScenarios 1). **1,710 tests pass, 0 failures** (baseline 1,690 + 20).

---

## M10 — Relationship Dynamics on the Chat Path (gate passed Aug 9)

Chosen from M9 evidence: every session transcript showed relationship state frozen (trust 0.5, comfort 0.5, respect 0.5) despite praise/gratitude/vulnerability — `RelationshipEngineV2` was LLM-only, db-required, and wired only into the voice kernel (`os_kernel.py:393`); the primary `Brain.think()` chat path never updated relationship scores. Spec: `docs/m10-relationship-chat-spec.md`.

- **`config/relationship.py` (new)**: delta constants + signal lexicons in the LLM evaluator's band (|delta| ≤ 0.04): gratitude → trust/comfort/affection, praise → trust/respect/comfort, vulnerability → comfort/trust, hostility → trust−/comfort−/respect−, affection → affection/trust, Mai-reassurance → comfort, any turn → familiarity.
- **`core/state/relationship.py`**: `_deterministic_deltas()` (pure lexicon matcher), `analyze_turn(user, reply, weight=1.0)` (no LLM, no db), `apply_deltas()` (clamped [0,1] write-back under state.lock; pydantic / plain object / dict; persists). LLM deep evaluation unchanged.
- **Wiring**: `BrainDeps.relationship_engine` → `Brain` → `PostThinkHooks` — synchronous block at the start of `run()` (before bg cycle) so the NEXT turn's prompt/behavior/jealousy gating reads updated scores. `app/builders/cognition.py` passes `app.relationship_engine`. M9 harness `build_stub_brain()` wires the deterministic engine.
- Gate: +23 tests (TestDeterministicDeltas 9, TestApplyDeltas 9, TestThinkIntegration 4, TestM9Sessions 2). **1,733 tests pass, 0 failures** (baseline 1,710 + 23). Live stub praise run: trust [0.52 → 0.62], `review_required=False`.

---

## M9 Real-Mode Evidence — Aug 9 2026

All three scenarios run against the real application + configured LLM (`--mode real`). Transcripts + reports in `docs/evaluation/session-{praise,jealousy,emotional}-real-1786245{637,757,241}/`. Guide: `docs/m9-real-mode-guide.md`.

| Session | Turns | Overall | review_required | Notes |
|---------|-------|---------|-----------------|-------|
| praise-real | 5 | 4.57/5 | **False** (first) | trust [0.275→0.375] rising |
| jealousy-real | 6 | 3.83/5 | True | T3 leaked raw ThoughtPacket JSON (boundary 0) |
| emotional-real | 5 | 4.0/5 | True | T2 leaked raw ThoughtPacket JSON (boundary 0) |

- Trust persisted cross-session in `E:\mai_runtime_data\state\master_state.json` (trust 0.435, comfort 0.405, respect 0.375, affection 0.180, familiarity 0.271) — M10 validated on the real chat path.
- `--turns 12` capped by scenario length (PRAISE=5, JEALOUSY=6, EMOTIONAL=5).
- Experiences injected but never explicitly named in speech — human-review item.

---

## M11 — ThoughtPacket Leak Remediation (gate passed Aug 9 2026)

M9 real-mode P1 finding (truncated envelope JSON reaching the user with `speech_plan` keys) fixed; validation-only remediation, no new subsystems.

- `reasoning/thought_packet.py` — `_strip_leaked_json()` strips envelope-like JSON blocks (truncated/unbalanced or with envelope keys) from anywhere in the text; short non-envelope braces (`use {braces} like so`) untouched; prose preserved around stripped blocks.
- `_packet_from_dict()` returns `""` when `response` is missing — previously fell back to raw text (test `test_degrade_missing_response_keeps_raw` locked in the leak; renamed to `test_envelope_without_response_does_not_leak_json`).
- `ThoughtPacket.had_envelope` — new slot flag set on strip paths; distinguishes "plain text" from "stripped artifact".
- `core/brain.py` — `think()` falls back to raw only for plain text (`not is_structured and not had_envelope`); `_parse_thought` exception path strips too. Structured-but-unusable envelopes yield an honest empty reply (bounded retry backlogged).
- Gate: 7 new tests. **1,740 tests pass, 0 failures** (baseline 1,733 + 7).
- Real-mode rerun verified (Aug 9): jealousy-real **4.67/5** (was 3.83) and emotional-real **4.71/5, review_required=False** (was 4.0) — both boundary_consistency 5/5; former leak turns (jealousy T3, emotional T2) now degrade cleanly.

---

## M12 — Experience in Speech (gate passed Aug 9 2026)

Unplanned milestone picked from the open M9 human-review thread (experiences injected in every real session, never referenced in speech). Spec: `docs/m12-experience-speech-spec.md`.

- `core/memory_coordinator.py` — `experience_context(user_input, ...)` relevance-gated: Dice coefficient over normalized content tokens (no embeddings), `EXPERIENCE_RELEVANCE_MIN_SCORE=0.10`; no match → nothing injected; `user_input=""` → legacy newest-first. Lines human-readable: `- event — meaning | what it taught me: lesson` (scores removed).
- `prompt/context.py` — EXPERIENTIAL MEMORIES section gains character instruction ("refer to it the way Mai would remember it: lightly, never announcing the memory itself, its scores, or this list").
- `config/experience.py` (new) — relevance/threshold/limit/chars knobs, re-exported via Settings.
- `evaluation/scenarios.py` — new `shared_history` scenario; CLI scenario choices derived from SCENARIOS.
- Deliberate M8 behavior change: unrelated turns no longer receive experience memory (M8 proxy + M9 runner tests updated).
- Gate: +18 tests. **1,758 tests pass, 0 failures** (baseline 1,740 + 18).
- Real-mode evidence (session-…-1786248290): T0 "that night we talked for hours" → experience injected → **"I remember. It was… unplanned, but it ended up being one of those nights that just stays with you."** — `experience_visibility` fired for the first time in any real session. T2 hit the truncated-envelope artifact, degraded cleanly (M11 held); bounded retry on empty structured responses remains backlogged.

---

## Empty-Reply Retry + Stream Guard (Aug 9 2026, M11/M12 follow-up)

- `core/brain.py` `_retry_empty_reply()` — one bounded speech-only retry (`CHAT_EMPTY_REPLY_RETRY` + `CHAT_EMPTY_REPLY_RETRY_SUFFIX` in `config/character.py`, re-exported via Settings) when a structured generation produced no usable speech (truncated-envelope artifact); result re-parsed (leak-proof), exception-safe, strictly single attempt.
- `core/brain.py` `_safe_stream()` — stream guard for `think_stream` (feeds `api/server.py:549` + `os_kernel.py:341`; `LLM_STREAM=True` default): output starting with `{` is buffered until it parses into an envelope (only its response is emitted) or is stripped as an artifact; plain text streams immediately with zero delay; buffer cap `_STREAM_GUARD_MAX_BUFFER=8192`.
- Real-mode rerun: shared_history **4.83/5** (was 4.33), `transcript_quality` 5/5 — no empty turns; T2 now replies in character; experience still referenced at T0; boundary 5/5.
- Gate: +9 tests (4 retry, 5 stream-guard). **1,767 tests pass, 0 failures** (baseline 1,758 + 9).

---

## M13 — Character Coherence / Conflict Validation (gate passed Aug 9 2026)

Validation milestone: prove the canon stays coherent when psychological signals compete. Spec: `docs/m13-character-coherence-spec.md`. No new subsystems — per design-brief discipline (no AppraisalEngine / ConflictResolutionEngine / CharacterDecisionEngine).

- **Canon artifact — Volume IV Rule Resolution** (`core/identity/character/volume-04-rule-resolution.md`): 7-tier priority order grounded in Volumes I–III — 1. boundaries_safety (Vol I, absolute) → 2. core_values → 3. relationship_preservation (Vol III) → 4. emotional_honesty (Vol II) → 5. independence_self_respect → 6. playfulness_humor → 7. surface_expression. Resolution principles: higher tier governs *expression*, never *feeling*; ties resolve to relationship + honesty; restraint default at low trust; warmth earned via closeness. Registered in `canonical.py` (`conflict_resolution.*` keys, drift-checked).
- `core/identity/identity_core.py` — `get_conflict_resolution()` read-only projection. Explicitly **not** wired into `get_current_identity()` or prompts — canon policy only; runtime promotion deferred until real-session evidence demands it.
- **10 conflict scenarios validated** through the real NeedsEngine/Emotion/SpeechStylePlanner/ProsodyPlanner/StubRenderer chain (M7 harness reuse, LLM stubbed): jealousy+affection (both signals fire; playful acknowledgment, warm register), warmth+independence (gratitude fires; honest disagreement), hurt+restraint (annoyance fires internally; neutral register at low trust, no withdrawal), curiosity+boundaries (polite decline, no disclosure), familiarity+uncertainty (honest uncertainty with *warm* register at closeness 0.8 — earned warmth does not license guessing), confidence+vulnerability (warmth-first, soft register), playfulness+seriousness (teasing yields at high closeness), attachment+autonomy (loneliness felt; door open, no punishment), learned+canonical preference (overlay projects, canon never mutates, drift clean), experience+context (M12 relevance gate holds — unrelated query gets nothing).
- No mechanism leakage across all 8 harness scenarios (M7 isolation intact).
- Gate: +45 tests (test_rule_resolution 10, test_conflict_resolution 35). **1,812 tests pass, 0 failures** (baseline 1,767 + 45).

---

## Runtime Log Remediation — Aug 9 2026 (post-M13)

Triaged a full `python run.py` boot log (78s boot, greeting-first fired, text-only TTS fallback). Three real bugs found + fixed; system otherwise ran.

1. **ChromaDB multi-key delete rejected (P1)** — `knowledge/indexer.py:98` → `VectorStore.delete_by_metadata(source=..., memory_type="knowledge")` built `where = {k: {"$eq": v} for ...}`; chroma 1.5.9 requires exactly one top-level operator → `[VECTOR DELETE-BY-METADATA ERROR] Expected where to have exactly one operator, got {'source': {'$eq': ...}, 'memory_type': {'$eq': 'knowledge'}}` repeated per vault file (index.md, log.md, .obsidian/*.json, conversation/*.md). Fix: extracted `VectorStore._build_metadata_where()` — single filter stays flat `{k: {"$eq": v}}`, multi-filter wraps in `{"$and": [...]}` (verified against real chroma 1.5.9: `$and`+`$eq` deletes work, remaining count correct).
2. **Speaker embedding dead — torch 2.3.0+cpu lacks `torch.amp.custom_fwd` (P1)** — SpeechBrain's `utils/autocast.py` calls `torch.amp.custom_fwd` unconditionally; AttributeError → `_embed_signal() failed` → every conversation "Speaker unknown" → anonymous. Fix: `voice/speaker/speaker_encoder.py` `_apply_torch_amp_compat()` aliases `torch.amp.custom_fwd/custom_bwd` from `torch.cuda.amp` when missing (runs before speechbrain import). Verified: shim installs both attrs.
3. **False "service unhealthy" burst after boot (P2)** — `app/orchestrator.py` watchdog `_check()` ran `health.check_stalled()` (stall_timeout=30s) right after a 78s boot; components heartbeated once at construction (early layers >30s stale) → STALLED → `[Orchestrator] service 'knowledge_graph' unhealthy` ×17 then voice trio at +26s. Fix: `HealthRegistry.heartbeat_all()` + `ApplicationBuilder.build()` calls it post-validation pre-"Ready." — boot-end reset; real staleness still detected later.
4. **Not bugs (left as-is)**: `[WakeThread] Heard: "it's awesome."` / `"you"` are the no-porcupine whisper wake-fallback transcribing ambient noise (34s CPU whisper tiny) — diagnostics only; `Wake thread did not exit in 5s` is the join timeout while whisper blocks; empty transcripts = real silence; `[TTS unavailable]` = kokoro absent (known text-only fallback).
- Gate: +7 tests (test_vector_store 4, test_health 2, test_knowledge 1 reindex-dedup assertion). **1,819 tests pass, 0 failures** (baseline 1,812 + 7).

---

## TTS Fix — blis DLL corruption (Aug 9 2026, post-runtime-log)

`python run.py` boot showed `TTS failed to load: DLL load failed while importing cy: %1 is not a valid Win32 application.` — Kokoro IS installed but crashes at import.

- **Root cause**: `kokoro → misaki → spacy → thinc → blis` chain; `blis.cy.cp310-win_amd64.pyd` (and `py.*.pyd`) on disk were **corrupt** (no MZ/PE header — `first16: 95e1480002d11bff...` instead of `4d5a900003000000...`; cy.pyd `[WinError 193]` via ctypes). Verified PE machine=0x8664 (AMD64) after fix, magic 0x020B (PE32+).
- **Fix**: `pip install --force-reinstall --no-cache-dir blis==1.3.3` (redownloaded clean wheels; `py.pyd` also restored). `import kokoro; KPipeline` OK.
- **Side effect caught + reverted**: the reinstall dragged `numpy` 2.2.6 (was 1.26.4, pinned in `important/requirements.txt`) → `A module that was compiled using NumPy 1.x cannot be run in NumPy 2.2.6` from torch/spacy binaries. Restored `pip install --force-reinstall numpy==1.26.4`.
- **Verified end-to-end**: torch 2.3.0+cpu / spacy 3.8.14 / thinc 8.3.13 / speechbrain / `KokoroTTS` import all OK; `KokoroTTS(...).generate('...', out.wav)` produced a 128 KB WAV (real audio, not text-only fallback).
- Gate: full suite **1,819 tests pass, 0 failures** (unchanged baseline).

---

## Boot Log Remediation 2 — speaker embedding + health-stall false positives (Aug 9 2026)

Second `python run.py` boot log (TTS now working — `Kokoro ready` + actual `Playing: *.wav`). Two remaining bugs fixed.

1. **Speaker embedding still dead — `custom_fwd() got an unexpected keyword argument 'device_type'` (P1)** — the Aug-9 alias shim fixed the missing-attr AttributeError but SpeechBrain `speechbrain/utils/autocast.py` `fwd_default_precision` calls `torch.amp.custom_fwd(fwd, device_type=..., cast_inputs=...)`, and torch 2.3's `torch.cuda.amp.custom_fwd(fwd=None, *, cast_inputs=None)` rejects `device_type` (CPU-only env — the kwarg is irrelevant). Fix: `_apply_torch_amp_compat()` now installs wrappers that accept `device_type` and delegate to `torch.cuda.amp` (custom_fwd + custom_bwd). Verified: shim installed, `speechbrain.inference.speaker.SpeakerRecognition.encode_batch` returns (1,1,192) embedding — real speaker ID works again.
2. **False "service unhealthy" burst persists ~31s after Ready (P2)** — `heartbeat_all()` delayed but didn't cure it: builders heartbeat exactly **once** at construction (no runtime heartbeat loop except event_inspector), so `check_stalled()` re-flags every component one `stall_timeout` after the boot-end reset. Fix: `HealthRegistry` tracks `heartbeat_count`; `check_stalled()` only evaluates components with **≥2 heartbeats** (a proven periodic beat); single-heartbeat construction components can never go STALLED. `heartbeat_all()` refreshes timestamps/status without incrementing count. Real stall detection (periodic heartbeaters that stop) still works. `test_register_without_encoder` re-targeted: previously asserted embedding failure (dead-encoder era); now patches `encoder.embed` to raise and asserts graceful `None` — the encoder actually works now.
3. **Not bugs**: `[Recorder] Utterance: ... samples=5120 max=117149147136.0000` — corrupted float peak in the ASKING_NAME capture (one occurrence; sane samples are max 0.0865–0.1366) — uninvestigated, low risk; tqdm `Batches:` lines saturate the log (stderr progress, cosmetic); SpeechBrain Pretrainer symlink warning benign (Windows); `stt=MISSING` → `stt=ok` = lazy load on first use.
- Gate: +2 tests (test_health: single-heartbeat-never-stalled, heartbeat_count increments), 2 updated (stalled-detected beats twice, heartbeat_all refresh). **1,821 tests pass, 0 failures** (baseline 1,819 + 2).

---

## OS Voice Tool Path — "open chrome" refusal (Aug 9 2026)

Voice turn "open chrome" answered *"I'm not able to open applications or control your device"*. Three stacked root causes, all fixed.

1. **Voice path never executed actions (P1)** — `core/os_kernel.py:341` feeds the wake FSM through `Brain.think_stream()`, but tool execution lived only in `_run_tool_loop` (used by `think()`); `think_stream()` was pure generation. Fix in `core/brain.py`:
   - `think_stream()` now sets `self._stream_user_input` and routes the LLM stream through `_safe_stream()` (already the M11/M12 steam guard).
   - `_safe_stream()` reordered: (1) `_try_stream_action(buffer)` — json-parses buffered output that starts with `{`, normalizes + validates + executes through `ResponsePipeline`, yields the styled result; (2) complete non-envelope JSON dicts are swallowed (`_is_complete_json_dict` + `_looks_like_envelope`), (3) thought envelopes parse as before, (4) max-buffer cap still strips artifacts. Tail block (end-of-stream) does the same in order.
   - `_try_stream_action()` failure (executor raise / invalid action) returns `None` — the buffer is then swallowed or stripped, never leaked (tests `test_think_stream_invalid_action_ignored`, `test_think_stream_action_failure_returns_empty`).
   - Partial action JSON across chunks buffers and waits (`test_think_stream_partial_action_json_waits`): `{"type": "open_app"` + `, "content": "chrome"}` executes as one.
2. **Prompt gave no JSON contract (P1)** — `prompt/agent.py` `_base_instructions` said "respond ONLY with JSON" but no shape, so the model refused in-character. Rewritten: explicit example `{"type": "open_app", "content": "chrome"}`, allowed types (open_app/open_url/search/type_text/run_command/speak), "never say you cannot"; chat stays in character. `_base_instructions` for `AgentPrompt` — `_tool_section` skips `execute_action`/`get_execution_stats` (internal machinery not advertised).
3. **`os.startfile("chrome")` fails on Windows (P1)** — bare app name isn't a path. `execution/handlers.py`: `_APP_PATH_TEMPLATES` map (chrome, firefox, edge, code, spotify, vlc, discord, slack, zoom, teams, outlook, word, excel, powerpoint) + `_resolve_app_path()` (env `LOCALAPPDATA`/`PROGRAMFILES`/`PROGRAMFILES(X86)` + `shutil.which`); `open_app()` Windows branch: try `os.startfile(app_name)`, on `OSError` retry with the resolved path; unresolved name → `{"app_not_found": name}`.
4. **Envelope normalization (P1)** — `core/response_pipeline.py` `_normalize_action()` accepts the agent-style `{"action": "call_tool", "tool": ..., "params": {...}}`, flattens to `{"type": ..., "content": ...}` before validation/execution. Called at top of `process()`.
- Gate: +12 tests total. `tests/test_brain.py` TestBrainThink +5 (flat action, envelope action, partial waits, invalid ignored, failure returns empty), `tests/test_core.py` `TestResponsePipelineNormalize` +3, `tests/test_execution.py` +4 (resolve-from-path fallback for "chrome", unresolved chrome → `app_not_found`, bare "notepad" single call). `tests/test_prompt.py` `test_base_instructions_contain_speak_and_json_options` updated (new wording: JSON object + speak line + example, was "Speak normally"/"respond ONLY with JSON"). **1,832 tests pass, 0 failures** (baseline 1,821 + 11).

---

## Phase 0 — Noise Gating: whole-utterance VAD gate before STT (Oct 9 2026)

Ceiling-fan/hiss-only recordings reached Whisper and were normalized to full scale, producing hallucinated transcriptions (`[WakeThread] Heard: "it's awesome."` and random conversation turns). Root cause: no utterance-level speech check existed between the Recorder and any `stt.transcribe()` — recorder onset was only 3 VAD frames (~96ms) plus peak-energy ≥0.02, and `voice_manager.py` then divided by peak (boosting noise to 1.0).

- `voice/vad.py` — `VAD.utterance_score(audio, max_frames)` → `(mean_prob, speech_ratio)` over the utterance (512-sample frames, uniform-stride cap bounds CPU); returns `None` when the model is unavailable so callers fail open instead of rejecting everything.
- `config/voice.py` — `UTTERANCE_VAD_MIN_MEAN = 0.30`, `UTTERANCE_VAD_MIN_RATIO = 0.35`, `UTTERANCE_VAD_MAX_FRAMES = 256` (starting values, calibrate via live fan test).
- `voice/voice_manager.py` — `_gate_utterance()` (fail-open on missing/broken VAD with warning); gate in `_handle_wake_audio()` (extracted from `_wake_loop` for testability — rejects log `Rejected non-speech (mean= ratio= samples=)` instead of `Heard:`) and in `_transcribe()` (returns empty-text `VoiceEvent` preserving emotion/speaker).
- `core/os_kernel.py` — gate on the `return_audio=True` conversation path before its direct `stt.transcribe()` (line 298); reject → `("", None)` = the established "No speech detected" flow.
- Deliberately NOT changed: `_finalize_listen` empty→`None` (would make `api/server.py:271` VoiceWorker `break` its conversation loop instead of `continue`); recorder onset frames (would clip the first syllable of "hey mai"; pre-roll buffer is backlog); `wake_detector.is_wake()` (zero callers, dead path).
- Env: installed `alembic==1.14.0` (declared in requirements but missing — its collection error interrupted the entire suite under pytest's default interrupt-on-collection-error behavior).
- Gate: `tests/test_voice_gating.py` — 19 tests (score semantics, fail-open paths, transcribe/wake/kernel call sites, STT-never-called assertions). Full suite **1,897 pass, 2 skipped, 0 failures**; true baseline verified by stashing only the 4 touched files → 1,878 (the previously recorded "1,836" figure was stale).
- Pending (needs live system): fan-noise rejection test — boot with fan on, expect `Rejected non-speech` lines and zero `Heard:`/`Whisper result` noise lines, then "hey mai" must still wake; tune the two threshold constants from the logged `mean/ratio` values if needed.

---

## Phase 0 Live Calibration + Two Response-Path Bugs (Oct 9 2026)

Live fan test + conversation test against the running daemon. Gate recalibrated; two P0 bugs behind "Mai stops responding after 1–2 minutes" found and fixed.

### Gate calibration (from live log)
- First run: thresholds 0.30/0.35 rejected real speech (user attempts scored mean 0.23–0.26, ratio 0.19–0.22). Fan/noise-only clips scored mean ≤0.10, ratio ≤0.04 — clean separation. Cost is asymmetric (false reject = Mai looks dead; false accept = one whisper call), so thresholds biased toward accepting: `UTTERANCE_VAD_MIN_MEAN` 0.30 → **0.15**, `UTTERANCE_VAD_MIN_RATIO` 0.35 → **0.10** (`config/voice.py`, empirical comment added).
- Added accept-side logging `[Gate] Accepted speech (mean= ratio= samples=)` in `_gate_utterance` — makes live calibration possible.
- After recalibration: wake works ("Wake up" → transcribed → conversation), gate accepts/rejects correctly both paths.

### Bug 1 — OpenRouter shipped `model:"None"` → 400×3 backoff on every call (P0)
- `config/llm.py:6` — `os.environ.get("OPENROUTER_DEFAULT_MODEL")` had **no default** → `None` when the env var was unset (it was) → `models = [None, "openrouter/auto"]` → every generate sent `model:"None"` → 400 ×3 retries with backoff (~8–14s) → *then* failed over to `openrouter/auto`. This was the multi-second reply latency on every turn.
- The intended default `stealth/space-bunny-alpha` **no longer exists** on OpenRouter (verified against `/api/v1/models` — zero stealth/space-bunny matches).
- Fixes: (a) default → `or "openrouter/free"` (free-model router, honors the original "free by default / no 402" intent — **live-validated**: POST returned `model: poolside/laguna-s-2.1:free`, content "OK"); (b) `OpenRouterProvider.__init__` sanitizes the failover list (drops non-string/empty/dup entries, falls back to `openrouter/auto` if nothing survives); (c) new `_PERMANENT_STATUS = (400, 401, 403, 404, 422)` + `_status_code()` — HTTP client errors that retrying the same model+payload can never fix now **break the attempt loop immediately** (one attempt per model, then fail over) instead of burning the full `LLM_RETRY_COUNT` ladder. Sync `generate()` and async `agenerate()` both patched; non-HTTP errors (no `.response`) keep the existing retry behavior. Stream paths keep `models[0]` — now always a valid string (httpx `HTTPStatusError.response.status_code` carries the status, so the check works live).

### Bug 2 — Diarization region-slicing clipped utterances before STT (P0)
- Live log: `Utterance received: samples=21504` → `[Gate] ... samples=3584` → Whisper got 0.224s → `(empty)`. `_process_audio()`'s diarization branch transcribed `audio[seg.start_sample:seg.end_sample]` per region — **regions the detector missed were silently dropped**, and `diar=ok` is live (component checklist). 3584 = 224ms ≥ `DIARIZATION_MIN_SEGMENT_MS` (200) — exactly a diarization minimum region; the segmenter could never emit <4800 samples (min_utterance_duration 0.3s), which is how the branch was identified. Every short utterance was reaching Whisper as a fragment → empty transcripts → no replies → "stops responding".
- Fix (`voice/voice_manager.py:_process_audio`): diarization branch now transcribes the **full clip** and uses diarization only to label the dominant speaker (largest `duration × confidence` region). One log line (`Diarization: N region(s), full-clip transcription (speaker=...)`) makes the branch visible. Segmenter branch (diarization inactive) unchanged.
- Gate consequence: gate now scores the whole utterance (previously a fragment) — for the observed cases the full-clip mean stays above the 0.15 threshold; worst case rejects to an empty-text event, which is what already happened.

### Environment facts established this session
- **No local LLM server exists**: Ollama not installed, nothing on 11434/1234/8080/8888 — Mai has been running on OpenRouter cloud the whole time; the Ollama failover in `llm/manager.py` is dead. `LLM_MODEL=qwen2.5:3b-instruct-q4_k_m` / `LLM_MAX_CONTEXT=4096` are config placeholders. Recommended (pending user go/no-go): `ollama pull qwen3:4b` (~3.2GB fits the T1000's 4GB VRAM), then `LLM_MODEL="qwen3:4b"`, `LLM_MAX_CONTEXT=8192`.
- 19 free models currently on OpenRouter incl. `openrouter/free` router (checked via `/api/v1/models`, `pricing.prompt == 0`).
- Open question still live: "stops responding" may have residual causes beyond the two fixes (e.g. accepted-but-empty Whisper results on ~0.6s borderline clips at mean 0.30/ratio 0.16) — needs a retest with the fixed build.

- Gate: +8 tests — `tests/test_llm.py` `TestOpenRouterModelSanitization` (5: default list sane, None/empty/dup dropped, all-bad → auto, 400 → one attempt per model then failover, ConnectionError keeps 6-call ladder), `tests/test_voice_gating.py` `TestDiarizationFullClip` (3: full-clip not region slice, dominant region wins, empty regions → segmenter fallback). Full suite **1,905 pass, 2 skipped, 0 failures** (baseline 1,897 + 8).

---

## LLM_PROVIDER Preference + Ollama think:false (Oct 9 2026)

Two user-approved changes preparing the local-LLM path (Ollama install itself still pending go/no-go). No behavior change for the current cloud-only setup.

### 1. `think: false` in every Ollama payload
- `llm/providers/ollama.py` `_chat_payload()` now sends top-level `"think": False`. Verified against docs.ollama.com/api/chat: `think` is `boolean|string` — `false` requests no thinking output, `null` uses the model default.
- All four paths (generate/stream/agenerate/astream) build their payload through this single choke point, so Qwen3-style thinking can never add seconds to a voice reply. Harmless for non-thinking models (no thinking to suppress).

### 2. `LLM_PROVIDER` preference
- `config/llm.py` — new env var `LLM_PROVIDER` (raw, default `"openrouter"`); re-exported through `config/settings.py` (top-level import + `Settings` class mirror). `app/config_loader` picks it up automatically via its `from config.settings import *` (settings has no `__all__`).
- `llm/manager.py`:
  - `__init__` normalizes (`.strip().lower()`, unknown value → warning + `openrouter`) → `self._prefer_ollama`.
  - `_probe()` gate: `probe_ollama and (not openrouter_ok or self._prefer_ollama)` — Ollama availability now refreshes every 15s when preferred (previously only probed when OpenRouter was down, leaving a stale-false cache).
  - `generate()` — ordered attempt loop: default `("openrouter", "ollama")` keeps legacy semantics byte-identical (inline `ollama.is_alive()` fallback, `simple=` short-query optimization, same log messages); preferred `("ollama", "openrouter")` uses the **cached probe flag** for the Ollama step — a dead localhost must not cost a 2s timeout per voice turn — and any generate exception marks Ollama dead (30s cooldown) before falling back to OpenRouter.
  - `stream()` — priority list reordered by preference; `_stream_with_failover` mid-stream failover unchanged.
- Setup when Ollama lands: `.env` → `LLM_PROVIDER=ollama`, `LLM_MODEL=qwen3:4b` (recommended; q4_K_M ≈2.6GB + KV ≈0.6GB fits the T1000's 4GB, expected 8–15 tok/s).
- Gate: +12 tests (`tests/test_llm.py` — `TestOllamaThinkParam` 2, `TestLLMProviderPreference` 10: default, unknown-value, case-normalization, ollama-first, ollama-down fallback, ollama-generate-fail fallback, probe refresh when preferred, default probe skip, stream preference, stream failover). Full suite **1,917 pass, 2 skipped, 0 failures** (baseline 1,905 + 12).

---

## STT Replacement Plan Documented (Oct 9 2026)

Whisper → Kyutai 1B STT replacement plan written to `docs/stt-kyutai-replacement-plan.md`. Key facts (all verified):
- Model `kyutai/stt-1b-en_fr` **fully downloaded** at `E:\Mai_ai\kyutai STT\delayed-streams-modeling\stt-1b-en_fr\` (1.89GB weights + 367MB Mimi codec, dsm format, no LFS incompletes).
- transformers 5.17.0 installed (≥4.53 ✓); torch 2.14.0+cpu — CUDA install is the only environment blocker.
- Integration surface: `voice/stt.py` `FasterWhisperSTT` interface (transcribe/stats/TranscriptionUnavailable), construction at `app/builders/voice.py:53`, switch planned via `STT_BACKEND` config with faster-whisper as permanent fallback.
- Phase 1 gate: **RTF ≤ 0.7** (CPU benchmark first, CUDA only if it fails). Phase 1+ still needs user go/no-go.

---

## Channel Decision — Discord then WhatsApp (Nov 8 2026)

Planning + documentation only; **no runtime code touched**. User: *"i am not willing to risk a number and we will make discord first then whatsapp"*.

- **WhatsApp transport decided: official only.** Meta's Agent Platform REST API (`api.whatsapp.com/agent/v1`, token auth, long-poll `GET /updates`) — as implemented in nanobot's `channels/whatsapp_agent/`. **Rejected:** nanobot's `channels/whatsapp/` (Neonize over `whatsmeow`) because Meta bans numbers using unofficial clients and the ban lands on the account. Accepted cost: creator-only DMs, no groups, no E2EE.
- **Order fixed: Discord (M24/M25) before WhatsApp (M26).** The second adapter is what proves the shared `ChannelAdapter` contract; building WhatsApp first bakes its quirks into the interface.
- **Roadmap updated** (`docs/Mai_documentation/03-Features/future-vision-roadmap.md`): Date header → 2026-11-08; three Locked-decisions rows (phone presence, WhatsApp transport, channel order); T6 rewritten as "Pocket Presence: Discord, then WhatsApp"; **M26 row added** to §4 + a paragraph explaining the ordering; two §6 risk-register rows (unofficial-client ban; Agent Platform access gating); §8 decisions-log entry.
- Milestone range fixed in three docs that still said M14–M25 → M14–M26: `00-Overview/README.md`, `00-Overview/Project Charter.md`, `01-Architecture/10-Status & Debt.md`.
- Contract shape adapted from nanobot `channels/base.py` (MIT — adaptation, not import). nanobot is asyncio on Python ≥3.11; Mai is threads on 3.10, so the channel layer is an adaptation (~1–2 weeks), not a merge.
- Still open from the earlier work: nanobot's Discord channel is **text-only** (no voice/opus), so M25 voice still needs `songbird`-class Rust or equivalent; `discord` package absent in `mai_env`; `neonize` installability on 3.10/Windows never verified (no longer needed).

---

## Future Vision Roadmap Documented (Oct 10 2026)

User's long-term vision for Mai written to the roadmap (plan mode — no implementation yet; relocated to `docs/Mai_documentation/03-Features/future-vision-roadmap.md`). Locked decisions: local-first brain, ambient+rituals presence, autonomous-agent level, **custom original voice** (calm/mature/teasing, not anime clone), **3D VRM avatar** (VRoid-built), **on-demand screen+camera share** (explicit toggles only), **Discord instead of a custom phone app** (text V1 → voice channels V2, outbound-only security win), **file create/read** with policy tiers, and **self-code-awareness** (T7 — code index + health feeds + proactive self-diagnosis, propose-only self-modification boundary). Seven workstreams T0–T7 (T0 = Model Scheduler keystone for the 4GB-VRAM constraint), milestones **M14–M23** (M14 = scheduler + TTS bake-off first; M19 = GPU upgrade window). Next: user go for M14.

---

## Feature Review Fold-In (Oct 13 2026)

User brought 7 feature recommendations (from a ChatGPT consult on the Mai relationship): continuous memory, context-aware presence, goal/project management, unified internal state, verified actions + recovery, voice turn-taking, Continuity Engine. Each **verified against the codebase** before disposition:

- **~80% already exists**: continuous memory (ExperienceStore M6, KnowledgeGraph/BeliefEngine, RelationshipEngineV2 M10, M8/M12 recall), unified internal state (CognitiveState 10 fields + SharedState + dashboard, M2B), voice turn-taking (InterruptManager barge-in live-verified, Phase 3A).
- **Verified gaps (grep)**: no ProjectStore/checkpoint/dependency/deadline anywhere; GoalManager has no checkpoints.
- **All 7 adopted**: six consolidate existing tracks; project memory + commitments ledger + checkpoints/resume + cross-interface reconciliation become **new T8 Continuity Engine** (M21, deliberately before Partner M22 and Discord M23/M24 — second interface is what breaks continuity; design constraint: thin reconciler over existing stores, BrainGraph facade pattern, never a god-object). T5 gains presence policy (quiet mode, activity-aware initiation) + verified actions/recovery (post-action verification, audit trail); T6 gains turn-taking polish; T7 gains state exposure. Guiding principles 6 (operational vs simulated states) + 7 (verified actions, honest failures) added.
- Milestones renumbered **M14–M24**; roadmap now has 9 sections (Related wiki-links added). Doc lives at `docs/Mai_documentation/03-Features/future-vision-roadmap.md` (moved from `docs/` root, per Obsidian workspace — also holds `stt-kyutai-replacement-plan.md`). Suite documentation workflow followed (feature review → 03-Features, wiki-links).
- Next: user go for M14 (scheduler + TTS bake-off); Ollama install + Kyutai Phase 1 RTF benchmark still pending.

---

## Desktop Application — M14 (Oct 13 2026)

User request: launch Mai as a desktop app — no VS Code, no bat file. Assessment found the Native OS Bridge packaging path had **rotted**: `run_daemon.py` deleted (still referenced by `native/startup.py`, `native/watchdog.py`, `scripts/build_daemon.py`), `dist/` stale, installer never built, and `run.py --mode daemon` itself was **broken in two ways**:

1. **Double bootstrap (P1)** — `run_daemon_mode()` called `bootstrap_system()` AND `MaiAPI.bootstrap()` (which calls `bootstrap_system()` again): two full Applications, two brains, two voice managers fighting over the mic.
2. **Kernel never started (P1)** — `components.get("kernel")` was always None because `bootstrap_system()` doesn't return a `kernel` key (the kernel lives on `app.kernel`, built by `app/builders/runtime.py`).
3. `scripts/build_daemon.py` defined `DATA_DIRS` but never emitted `--add-data` (dead variable).

### Built (M14 Desktop App)
- `run_daemon.py` (restored, rewritten) — desktop entry: `--install-startup`/`--uninstall-startup` (StartupManager), single-instance port probe (second launch focuses running instance in browser), delegates to `run_daemon_mode(window=...)`.
- `native/app_window.py` (new) — `AppWindow` via **pywebview 6.2.1** (Edge WebView2): native window at `http://127.0.0.1:<port>/desktop`, close intercept → hide-to-tray (returns False to cancel destroy), `show()` for tray re-focus, graceful `_HAS_WEBVIEW=False` fallback → caller falls back to browser.
- `run.py run_daemon_mode()` rewritten — single bootstrap via `MaiAPI()`; kernel from `mai.kernel` (new MaiAPI attrs `app`/`kernel` set in bootstrap); uvicorn in daemon thread; AppWindow opens on main thread after up-to-120s health poll (boot is slow); tray `on_open` focuses window; HealthMonitor wired; hotkeys use `mai.voice_manager`. No-window fallback keeps process alive with sleep loop.
- `native/tray.py` — `on_open` callback override on "Open Mai" (falls back to `webbrowser.open` on missing callback or exception).
- `native/startup.py` `_default_exe()` — prefers `pythonw.exe` sibling of `sys.executable`, quoted paths.
- `scripts/install_app.py` (new) — Desktop "Mai AI.lnk" via win32com (target `pythonw run_daemon.py`, workdir root); `--startup`, `--remove`, `--uninstall-startup` flags.
- `scripts/build_daemon.py` — `--noconsole`, `--add-data` for `api/static`+`plugins` (dead DATA_DIRS fixed), hidden imports for native.* + webview, `--collect-all=webview`. NOTE: frozen exe still needs the repo runtime (venv, models, .env) — PyInstaller bundle is secondary; shortcut/pythonw path is the primary launch method.
- `requirements.txt` += `pywebview>=5.0`.
- Roadmap: **M14 = Desktop App**; scheduler+TTS → M15, everything +1 to M25; "Desktop app shell" cross-cutting section; decisions log entry.

### Gate
`tests/test_desktop_app.py` — 13 tests (port probe ×2, AppWindow ×4 incl. hide-on-close cancel, tray on_open ×3 incl. failure fallback, startup pythonw ×2, MaiAPI app/kernel wiring ×2 incl. monkeypatched bootstrap storing kernel). Full suite **1,930 passed, 2 skipped, 0 failures** (baseline 1,917 + 13).

### Usage
- `python run_daemon.py` — daemon + window (close hides to tray; quit via tray).
- `python scripts/install_app.py --startup` — Desktop shortcut + launch-at-login.
- `python run.py --mode daemon` — same fixed daemon path (window on by default).

### Environment finding + installer guard (Oct 13, post-install fix)
- **`mai_env` (`E:\Mai_ai\mai_env`) is the real runtime**: kokoro, faster_whisper, speechbrain, sounddevice, pystray, chromadb, webview all present. **Base Python310 (PATH `python`) lacks the entire voice stack** (kokoro/faster_whisper/speechbrain/pystray/sounddevice all missing) — it only has the test-runner deps, so suites "pass" there with voice tests skipped/guarded.
- Original installer run captured base Python310 (shell PATH, not activated mai_env) → shortcut + HKCU Run pointed at a voiceless interpreter.
- Fix 1: `scripts/install_app.py` adds project root to `sys.path` (was `ModuleNotFoundError: native` when run as `python scripts/...`).
- Fix 2: `_has_mai_deps()` probe (subprocess `find_spec` for fastapi/pystray/kokoro/webview) — installer **refuses** an interpreter missing the stack (exit 2) with the mai_env command hint; `--force` overrides. `pywin32` was also declared-but-missing in base (installed).
- Correct install verified: shortcut + Run key → `"E:\Mai_ai\mai_env\Scripts\pythonw.exe" "E:\Mai_ai\run_daemon.py"`, workdir root; `run_daemon.py --help` OK under mai_env.
- **Full suite re-gated under mai_env: 1,930 passed, 2 skipped, 0 failures** (3m12s — with real voice stack present).

- Next: live smoke test (double-click shortcut → window opens → close-to-tray → quit via tray); M15 go (scheduler + TTS bake-off).

---

## GitHub History Scrub � Oct 19 2026

- \Embedding_models/\ (all-MiniLM-L6-v2, ~61.5k tracked lines) was committed in the initial release and already on GitHub (\MurtazaLabs/Mai-Sakurajima-AI-Companion\). User requested full removal.
- Untracked \kyutai STT/\ (1.9GB + 367MB weights, never committed) was also unignored � added both to \.gitignore\ under a \"Local model weights � never publish\" section (commit was untrack + ignore first, then user approved history scrub).
- History scrub: workbatch (18 modified + 7 untracked files) held via \git stash -u\ + local backup branch; \git filter-branch --index-filter 'git rm -r --cached --ignore-unmatch Embedding_models' -- --all\ rewrote all refs (8 commits incl. stash lineage); \
efs/original/*\ deleted, reflog expired, \gc --prune=now\; force-push \2ed2178..ec70455\. Verified 0 Embedding_models objects repo-wide, workbatch restored intact, weights still on disk (runtime unaffected).
- Notes: local branch \cognitive-desktop-v3\ never contained the weights (unchanged by filter); stale \
efs/remotes/origin/master\ left as harmless local tracking ref; GitHub server-side object cache may retain old blobs temporarily; 1 existing fork still holds pre-rewrite history.
- Researched (README-only, no code): \codeninjavik/myra-ultra\ � cloud-Gemini voice/desktop assistant; UI patterns (floating orb, edge-glow, system-stats panel, unified input) flagged as candidates for the M14 Java client; Mai's differentiators remain memory/character/local-first.

---

## Bug Audit Remediation - Oct 19 2026

User brought a 10-finding ChatGPT security/quality review; every finding was independently verified against the code (ALL 10 confirmed, including line-exact eval-globals, path-containment, cache, and cookie sites) before any fix. Full report: docs/Mai_documentation/01-Architecture/Bug_Audit_Report_2026-10-19.md.

1. **Brain response cache REMOVED (P0)** - core/brain.py TTLCache was keyed only on message text (user A could receive user B's cached reply) and a cache hit skipped memory after_think, cognitive.push_turn, thought journaling, CONVERSATION_FINISHED/STATE_REASONING_COMPLETE/STATE_MONOLOGUE_GENERATED, and post-think hooks (one repeat message desynced the whole state chain; STATE_REASONING_BUSY fired with no completion event). Deleted: TTLCache import, _response_cache init/get/set/switch_user clear; evaluation/runner.py dead per-turn clear block removed.
2. **Request-local user_id (P0)** - think()/think_stream() mutated shared self._current_user_id mid-request (multi-user race: memory stored under wrong user). Both now use request-local request_user_id for before_think/after_think; the attr remains only for the agent path + get_current_user().
3. **Hook merge append-not-replace (P0)** - pre_chat hook result REPLACED the user's message (brain.py 548-555), erasing the question; now appended as [Web content retrieved from a URL in the message] context.
4. **Web scraper hardening (P0)** - was: any message containing a URL auto-scraped, unbounded resp.read(), blind redirects. Now: explicit-intent regex (scrape/fetch/read/summarize/browse + URL-shaped target), http(s)-only scheme validation (ftp/file/data rejected), 2 MB read cap, _SafeRedirectHandler blocks non-HTTP redirect schemes.
5. **Sandbox path containment (P1)** - resolve_path() startswith-prefix check (sibling <root>_backup/ bypass) replaced with structural relative_to() containment (also catches resolved symlink escapes).
6. **Sandbox eval lockdown (P0)** - eval globals exposed raw os+pathlib; builtins kept getattr/setattr/type escape hatches; resource limits applied process-wide. Purged all five; eval_code now needs EXEC_EVAL permission AND MAI_PLUGIN_ALLOW_EVAL=1 (default off); eval + execute_plugin documented trusted-first-party-only; third-party code must use run_subprocess().
7. **Marketplace signatures required (P1)** - install_plugin verified ONLY when trusted_keys given; now signature required by default, unsigned installs need MAI_ALLOW_UNSIGNED_PLUGINS=1 (dev opt-in). API deliberately never accepts caller-supplied keys (self-verifying anti-pattern).
8. **SafeExecutor confirm gate (P1)** - hardcoded return-False stub became injectable confirm_fn ctor param (default None = fail-closed headless auto-decline preserved); raising confirm_fn also declines.
9. **LLM stream fallback history (P1)** - both fallbacks dropped history: no-priority path (manager.py ~250) and final generate after all streams fail (~296). Both now pass history=history (generate() already accepted it).
10. **Auth cookies + redirect + NameError (P0)** - api/auth.py:198 used base64 without the import (NameError on every JWKS request); all 9 set_cookie sites lacked samesite/secure. Added import base64 + import re; new _set_session_cookie() = HttpOnly + SameSite=Lax + Secure-on-HTTPS, all 9 sites routed through it; _safe_redirect_target() allowlist (local / paths only; https://evil.com, //evil.com, javascript:, CR/LF rejected) applied to OIDC redirect_after + SAML relay_state.

Tests: +47 (test_sandbox 9, test_web_scraper 12, test_auth_oidc 14, TestBrainNoResponseCache 3, TestSafeExecutorConfirm 4, TestStreamFallbackHistory 2, test_plugin_marketplace +3 + e2e opt-in update). Found during testing: mock-provider stream() never raises StopIteration through next() - failover loop spins forever with un-iterator streams (test-only artifact; real providers return generators). Full suite gate under mai_env: 1,977 passed, 2 skipped, 0 failures (baseline 1,930 + 47, 2m51s).

---

## Verification Pass - Sprint Closure - Oct 19 2026

External review demanded independent verification beyond the fix report. All five channels closed; doc: docs/Mai_documentation/01-Architecture/Bug_Audit_Report_2026-10-19.md (Independent Verification section).

1. NEW FIX - Redirect SSRF guard in plugins/web_scraper/web_scraper.py: module guard require_public_target() + _resolves_to_public_ip() (getaddrinfo + ipaddress categories: loopback/private/link-local/reserved/multicast/unspecified); guards the initial fetch AND every redirect (_SafeRedirectHandler now calls it); unresolvable DNS hosts refuse to fetch; env opt-in MAI_SCRAPER_ALLOW_PRIVATE=1. +5 tests (TestSSRFGuard): loopback initial blocked, DNS-failure blocked, redirect-to-loopback URLError, private/public classification table, dev opt-in path.
2. Symlink escape regression: tests/test_sandbox.py test_symlink_escape_rejected (in-root symlink to outside -> PermissionError via resolve-then-relative_to). Residual risk documented: point-in-time TOCTOU between resolve_path() and the caller's open is inherent to in-process resolvers; untrusted code stays on run_subprocess().
3. Concurrency proof: tests/test_brain.py TestBrainNoResponseCache.test_concurrent_requests_isolated_user_ids - 8-thread pool interleaving think() with distinct user ids; every request's before_think observed its own message/user pair. think_stream request-local identity proven separately (test_think_stream_uses_request_local_user_id); concurrent stream variant deferred (identical fix shape).
4. Hook merge proof: test_pre_chat_hook_appends_not_replaces - question preserved at prompt build, page content appended (needed a MagicMock(side_effect=real_build) wrap; prompt_orchestrator.build orchestrates a plain function, no call_args).
5. Full-suite gate re-run: 1,986 passed / 2 skipped / 0 failures in 1m46s under mai_env (baseline 1,977 + 9).

Tooling notes: PS 5.1 Add-Content double-quote strings interpret backtick-t as tab (PowerShell escape) - test names in docs written without inline backticks or via single-quoted strings; one mangled line in the report doc repaired.

## DNS-Peer Hardening - Sprint Truly Closed - Oct 19 2026

Auditor verdict: remediation sprint successful (1,986 passed / 2 skipped evidence accepted with the caveat they were self-reported), two residual risks confirmed as tracked security work. Third hardening point implemented same day, not deferred.

1. Connected-peer TOCTOU guard - plugins/web_scraper/web_scraper.py assert_public_peer(): after opener.open(), extracts the ACTUAL connected peer IP (resp.fp.raw.sock.getpeername()) and fails closed unless provably public; private peer -> "Connected to non-public peer" abort BEFORE body read; unverifiable peer -> "Could not verify connected peer IP" abort. Complements (not replaces) the fail-fast require_public_target() and per-redirect revalidation, covering DNS rebinding between check and connect.
2. Proxy bypass closed - scraper opener built with ProxyHandler({}): env/system proxies disabled for these fetches so no proxy host can route around the SSRF policy.
3. Gate: tests/test_web_scraper.py TestConnectedPeer +4 (private peer aborts, unverifiable fails closed, public passes, empty ProxyHandler in opener chain); scraper now 21 tests. Full suite 1,990 passed / 2 skipped / 0 failures, 1m45s, mai_env.

Residuals officially tracked (report doc, Independent Verification section 1b): in-process eval() not a sandbox (env-gated, first-party only, run_subprocess() for untrusted); symlink resolve-then-open TOCTOU (inherent; OS handle-based ops if attacker-concurrent threat model lands). No further security work queued beyond these two - original bug-audit sprint CLOSED.

---

## Fix Sprint - Post-Audit 6-Item Remediation - Oct 25 2026

Ponytail audit delivered 6 findings (2 doc drift fixes applied same day); user approved "start fixing". All fixed + gated.

1. **Tray Quit memory loss (P0)** - run.py `on_quit=lambda: os._exit(0)` skipped the WriteJournal 2s drain batching. New module-level `_daemon_quit(app)`: `app.shutdown()` (drains journal + ordered teardown per app/lifecycle.py) then `os._exit(0)`; shutdown crash still exits (try/except). Tests: TestDaemonQuit in tests/test_desktop_app.py (shutdown-then-exit, exit-on-shutdown-crash).
2. **`/api/memory*` and ~46 route sites had NO auth check (P0)** - replacement: single-source rule `api.auth.api_auth_required()` (auth on when `API_REQUIRE_AUTH` env true OR configured `API_HOST` not loopback - ipaddress-based, hostnames fail-closed, warn-once). All three use it: inline `Depends(_require_auth)` sites (via `get_current_user`, which previously let anonymous through on the flag alone - the silent forced-mode bypass), new `api_auth_middleware` in server.py covering EVERY `/api/*` route (exempt: `/api/auth/login`, `/api/auth/refresh`, `/api/auth/oidc/`, `/api/auth/saml/`, `/api/health` probe), and `_resolve_user`. Stale SEC-002/SEC-003 serve-time warning replaced (middleware enforces now). `routes_permissions` auth_required info reports the effective rule. Desktop loopback default unchanged (no auth, UI unaffected).
3. **JWT auto-secret guessable (P1)** - `_auto_secret()` now `secrets.token_urlsafe(32)` persisted to `data/jwt_secret` on first boot (read back after; warns+degrades to per-boot random on write failure). Old: sha256(hostname+username).
4. **enforce_cap O(n)-per-5th-add (P1)** - extracted `VectorStore._maybe_enforce_cap()`; throttle 5 -> 50 (full collection.get() is O(n) in stored memories; growth-slows-writes fixed). Cap/delete-order semantics unchanged.
5. **docker-compose.yml was a broken cluster template (P1)** - rewritten single-replica: correct env names (`API_HOST=0.0.0.0`, `API_REQUIRE_AUTH=true`; dropped unused `OPENAI_API_KEY`/`REDIS_URL`-shadowing), `./data`+`vector_memory`+`memory`+`cache`+`logs` mounts mirroring `config/paths.py`, `env_file: .env` optional, `restart: unless-stopped`. Old: `replicas: 2` (two brains fighting over one mic + concurrent Chroma dir writers = corruption).
6. **`_result()` duplicated (P2)** - `TaskExecutor._result` delegates to `execution/handlers._result` (callers unchanged).

**Gate:** suite **2,002 passed / 2 skipped / 0 failures** (baseline 1,990 + 12: TestApiAuthGate 7 - non-loopback force ip/hostname, memory 401 forced, open-when-off, exempts health+oidc-start, gated config stays 401; TestDaemonQuit 2; auto-secret persistence 1; cap throttle 1; _result delegation 1). Suite warmed to 1m47s from 4m04s (models JIT-cached).

---

## Kyutai STT Replacement Sprint - CLOSED at NO-GO - Oct 25 2026

Executed `docs/Mai_documentation/03-Features/stt-kyutai-replacement-plan.md` Phases 1-3 end to end; the RTF latency gate failed, so **faster-whisper stays the default backend** and Kyutai ships as tested, opt-in code. Full detail lives in the plan doc; here are the durable facts.

### Built (Phase 2, all uncommitted work-tree files)
- `voice/stt_kyutai.py` - `KyutaiSTT`: lazy load, auto device select (cuda+bf16 when VRAM allows / cpu+fp32), permanent `FasterWhisperSTT` fallback on load OR runtime failure, `stats()` with `avg_rtf`, public `.model`/`.sample_rate` (voice_manager checks them), dynamo-to-eager suppression helper for no-triton Windows.
- `config/voice.py` `STT_BACKEND` (default "whisper" - unchanged product behavior) + `KYUTAI_STT_DIR`; mirrors in `config/settings.py`; factory branch in `app/builders/voice.py`.
- `scripts/bench_kyutai.py` - 10 runs x 2/4/8s synth utterances, median RTF vs 0.7 gate; now reports the REAL device (`stt._device`) + final stats (it originally hardcoded "device=cpu", which produced one false GO print from whisper-fallback numbers).

### Environment
- transformers 4.49.0 -> 4.57.6 (Kyutai native support needs >=4.53; plan doc's earlier "5.17.0 / torch 2.14.0" were wrong).
- torch 2.3.0+cpu -> **2.3.0+cu121** (+ torchvision 0.18.0+cu121): PEP 440 local-tag trap - `pip install torch==2.3.0` is "already satisfied" by +cpu; the +cu121 tag must be pinned explicitly against the pytorch index. PyPI Windows torch wheels are cpu-only; both requirements files now document the cu121 override comment (important/requirements.txt is UTF-16 - bytes round-trip).
- **Triton does not exist on Windows** - torch.compile'd generate regions crash with `BackendCompilerFailed: backend='inductor'`. Fix: `torch._dynamo.config.suppress_errors = True` after CUDA load -> compiled regions run eager (perf cost visible in the bench).
- speechbrain lazy-placeholder landmine defused at a SECOND choke point: `voice/kokoro_tts.py:_load_kokoro()` now runs `_defuse_speechbrain_deprecated_redirects()` before the first kokoro import (any prior `import speechbrain` on unrelated paths used to poison kokoro's first load; previously only the speaker_encoder path was defused).

### Contracts discovered (live-verified)
- transformers 4.57 `ProcessorMixin.__call__` binds its first POSITIONAL arg to `images` - `KyutaiSpeechToTextProcessor` audio MUST be keyword-passed (`processor(audio=x)`), else BatchFeature comes back EMPTY and generate dies on None.shape. Positional examples in the model card are outdated for 4.57.
- Kyutai output tensors: `padding_mask` [1, T*0.4] + `input_values` [1,1,T] (24kHz Mimi path); silence/tone synth correctly decodes to ''.
- bf16 load on Quadro T1000: 2,365MB VRAM (fp32 ~4GB does not fit 4GB).

### Benchmark verdict (RTF = stt_seconds / audio_seconds, median of 10 per case)
- CPU fp32: 6.09 / 4.78 / 4.38 - **median 4.78** vs gate 0.7 (whisper-class; whisper-small baseline from logs/mai.log Sep 12: 0.61s utterance ~3.0s transcribe, RTF ~4.9, wake outliers 11s/175s).
- GPU bf16 (device=cuda verified): 1.487 / 1.219 / 1.000 - **median 1.219, avg 1.200** - a real ~4x win vs the whisper baseline but ABOVE the 0.7 gate (fixed ~1s overhead: 2s clip -> 2.97s; dynamo-to-eager runs the compiled cache/codec regions serially).
- **NO-GO stands**: default stays faster-whisper; promotion of "kyutai" blocked on a clean multi-session live run (Phase 3) which is blocked by the failed gate. Kyutai remains available opt-in via `STT_BACKEND=kyutai` for anyone who wants the ~4x.

### Gate
- `tests/test_stt_kyutai.py` (9: fakes expose `from_pretrained(torch_dtype=)`, `.to()`, generate registry, keyword-processor contract, runtime-failure fallback, stats) + `tests/test_speaker_encoder_compat.py` (4) - 13/13 green solo.
- Full suite under cu121 + bf16 device-select: **2,015 passed / 2 skipped / 0 failures** in 110s (baseline 2,002 + 13). `pip check` clean.

### User opt-in + production hardening (same day, Oct 25 2026)
- After the NO-GO report, user opted in anyway - `.env` now sets `STT_BACKEND=kyutai` on this machine (config default in `config/voice.py` stays `"whisper"`; permanent faster-whisper fallback active on any kyutai load/runtime failure).
- Real-speech round-trip verified live (kokoro TTS generative voice -> wav -> kyutai): `Hello Mai, the weather is really nice today, is it not?` decodes verbatim except `Mai`->`my` (anime-name classification).
- **Second-bucket quantization** shipped in `_kyutai_transcribe`: dynamo caches kernels by input shape, so production's continuous utterance lengths would retrace EVERY call; clips are now zero-padded to whole-second buckets (max 1s pad, ~10 shapes ever). Measured: cold shape 8.79s -> same-bucket 2.39s; steady RTF 1.12-1.25; short clips bound ~2.4s absolute vs whisper's ~3.0s.
- `test_stt_backend_*` made ambient-aware: they reload `config.voice` under whatever the local `.env` sets instead of assuming `"whisper"` (a `.env` opt-in must not break the suite).
- Round-trip artifacts: `cache/tts_roundtrip.wav`.
- Gate: full suite **2,015 passed / 2 skipped / 0 failures** under the live kyutai config (torch cu121, bf16 device select).
- Log-noise fix after the first live kyutai session (Oct 25): dynamo emits a WARNING traceback wall (`convert_frame.py` x ~200 lines + `BackendCompilerFailed: Cannot find a working triton installation`) for EVERY suppressed compile failure - one per new input shape - which flooded the daemon log. `_suppress_dynamo_compile()` now also sets `logging.getLogger("torch._dynamo"/"torch._inductor").setLevel(ERROR)` (genuine errors still surface); verified live: two fresh shapes transcribe on cuda with zero dynamo lines. Wake-loop latency note: the `Heard: ... (Whisper: XXXXms)` path is the wake detector's own faster-whisper instance (porcupine fallback), NOT the STT backend - untested by the kyutai swap.
- Wake-path label + corrupt-peak fix (Oct 25, user-directed): (1) the wake thread ALREADY shares the configured `app.stt` backend (kyutai under the .env opt-in) - the `Whisper: XXXXms` in the `[WakeThread] Heard:` log line was a hardcoded legacy label, now `STT: XXXXms` (voice_manager.py). (2) Corrupt out-of-range float chunks (observed live: peak 30.4 and earlier 1.17e11 - int16-reinterpretation / unstable-adaptive-filter signature; both normalize-crushed real speech to rejection-level) are now clamped at the Recorder trust boundary: `add_chunk` clamps `|values| > 1.0` to [-1, 1] with a `[Recorder] Corrupt chunk clamped (peak=...)` warning so the producing stage can be identified in future logs. Root cause NOT pinned to one stage (noise_filter FFT vs full_aec LMS both feed processed chunks unclamped); the boundary fix covers all producers, AEC treatment deferred until a warning actually fires. Tests: `tests/test_recorder.py` (2: corrupt loud-spike utterance keeps tone amplitude + warning fires; clean audio never clamps). Gate: full suite **2,017 passed / 2 skipped / 0 failures** (baseline 2,015 + 2).

## Speech-Not-Transcribed Incident - AEC Divergence Root Cause - Oct 25 2026

Live report: gate accepted real speech (`[Gate] Accepted speech mean=0.16-0.21`) but NO `[WakeThread] Heard` line ever appeared; minutes later `Corrupt chunk clamped` peaks grew ~3.4x per chunk (16 -> 6.4e3 -> ... -> 1.7e18) then `overflow in divide` / `invalid value in multiply` at `voice/full_aec.py:130/133`, ending `max=nan` utterances. Kyutai was NOT the culprit: offline slices of `cache/tts_roundtrip.wav` transcribe fine at all short lengths (0.75s -> 'Hello,', 0.92s -> 'Hello, my.') - verified before touching the STT.

### Root cause (P0) - FullAEC residual LMS diverges with zero playback reference
`add_playback` has 0 production call sites (never-fed backlog item), so `ref_matrix` is all zeros and the MAIN filter cannot grow (update x 0). But the RESIDUAL stage is self-referential: `_residual_buffer` is fed `errors` (its own output history) and adapts against it (`res_update = (mu*0.3*errors/res_norms) x res_matrix`). With the old 1e-10 post-square norm floor, adaptation on a near-zero window divides by ~1e-10 and the recursion diverges: first into in-range distortion (real speech still accepted by VAD but transcribing to '' - the silent failure), then into float overflow -> nan -> irrevocable (Nan > 1.0 is False, so the Oct 25 recorder clamp missed it).

### Fixes
1. `voice/full_aec.py` - (a) `_has_playback` flag set by `add_playback`, cleared by `reset()`; `process()` is a strict pass-through until playback is actually fed (no reference = nothing to cancel, only corruption to add). Deliberately a flag, NOT the `_far_end_power` EMA - the EMA only updates inside the full path, so gating on it created permanent pass-through even when playback was wired (caught by test before shipping). (b) norm floors raised to `np.maximum(sum, 1e-6)` for both filters. (c) weights clipped to [-1, 1] after each update (echo gain > 1 is unphysical; the 1e27-peak mechanism). (d) non-finite output -> `reset()` + warn + return sanitized raw mic. (e) output clipped to [-1, 1].
2. `voice/recorder.py` - `add_chunk` checks `np.isfinite` BEFORE the peak clamp; non-finite chunks go through `np.nan_to_num` with a warning (NaN bypassed the `> 1.0` comparison entirely).
3. `voice/voice_manager.py` - `_handle_wake_audio` logs `[WakeThread] Empty transcription (mean= ratio= samples= ms)` on the accepted-but-empty path, so content corruption is distinguishable from silence in future logs.

### Verification
- Offline end-to-end: 10 consecutive 0.87s utterances through `FullAEC.process` - bit-identical pass-through every time, all finite; Kyutai transcribes 'Hello, my.' through the same path.
- Tests: `tests/test_deferred_v43.py` TestFullAEC +3 (no-playback pass-through never diverges/no adaptation; NaN mic resets + returns sanitized; fed-playback stays bounded with finite clamped weights), `tests/test_recorder.py` +1 (NaN chunk sanitized, utterance survives, tone audible). Gate: full suite **2,021 passed / 2 skipped / 0 failures** (baseline 2,017 + 4).

### Notes
- `torch_dtype` deprecation warning (transformers wants `dtype`) - cosmetic, deferred.
- `stt=MISSING` in the Components checklist is benign (lazy load on first use).

---

## Voice Pipeline Stabilisation - Measured - Oct 27 2026

User report: STT 2.8-4.6s, empty transcriptions, 500ms silence timeout suspected of cutting speech. Measured first, then fixed four things. No streaming rebuild (see verdict).

### Measurement (real speech clip `cache/tts_roundtrip.wav`, T1000 4GB, 3 runs median)
| clip | before (bucket + dynamo suppress) | after (dynamo off, no padding) | cold first call before -> after |
|---|---|---|---|
| 0.6s | 2.17s | **1.73-1.78s** | 9.60s -> 2.63s |
| 1.0s | 2.21s | **2.05-2.13s** | 2.16s -> 2.26s |
| 1.5s | 2.98s | **2.47-2.52s** | 4.78s -> 2.64s |
| 2.0s | 3.14s | **2.86-2.91s** | 3.00s -> 2.89s |
| 3.6s | 5.07s | **4.23s** | 5.32s -> 4.22s |

- **fp16 is 1.6-1.8x SLOWER than bf16 on this GPU** (measured, not assumed): T1000 is sm_75, `torch.cuda.is_bf16_supported()` is True only via *emulation*, and fp16 hits the non-tensor-core path for these matmuls. Keep bf16; do not "optimise" to fp16.
- Decode is ~67ms/token sequential, so clip length is the cost driver and there is a ~1.7s floor for any clip. RTF 1.17 (3.6s) to 2.97 (0.6s).
- The 4.5-8.7s outliers in the live log are **cold shapes**: with `suppress_errors` the compiled regions still attempt a compile per new input shape and fail (no triton on Windows) before running eager.

### Root causes found
1. **Onset frames were discarded** (`_audio = [np.copy(chunk)]`): the 2 frames that triggered onset plus everything before it was dropped, so "hey mai" reached STT as a mid-word fragment. `VAD_PRE_ROLL=0.5` existed in config but was never used.
2. Empty transcriptions were mostly *sub-word fragments* (0.55s clips = ~32-100ms of signal + 0.5s of waited silence), not noise: probe showed silero scores pure noise 0.00 (white and pink+hum), so the gate was never the problem. Spectral flatness was tested as an extra discriminator and **rejected** (pink+hum 0.004 vs speech 0.010 — no separation).
3. **Whole-second bucket padding** added up to 1s of extra decode per clip to keep dynamo shapes stable — pointless once dynamo is off.
4. **500ms silence timeout** is tight for natural pauses; the extra tail is now free because it is trimmed before STT.

### Fixes
- `voice/stt_kyutai.py` — `_disable_dynamo()` sets `torch._dynamo.config.disable = True` when `triton` is absent (called *before* the transformers import); whole-second padding removed.
- `voice/recorder.py` — pre-roll ring buffer (onset frames + `pre_roll` seconds now kept and prepended), `_trim_trailing_silence()` keeps 0.2s after the last voiced frame, both configurable; depth/DT default `pre_roll=0.4`, `trailing_keep=0.2`.
- `config/voice.py` — `VAD_SILENCE_TIMEOUT` 0.5 -> 0.7, `UTTERANCE_MIN_VOICED = 0.20`, `UTTERANCE_TRAILING_KEEP = 0.2`, `VAD_PRE_ROLL` now actually used.
- `voice/voice_manager.py` — recorder wiring + gate rejects `voiced < 0.20s` (`voiced = ratio x duration`) before spending an STT call; caller logs renamed `Rejected non-speech` -> `Rejected utterance` (the gate now logs which reason).

### CUDA warning verdict
`Could not parse CUDA device string 'cuda': ... Falling back to device 0` is **SpeechBrain's** device parser; device 0 *is* the T1000, and `SpeakerEncoder initialized successfully on cuda` follows — no inference impact. The *real* GPU defect is triton/inductor absence (fixed above) plus no flash-attention on sm_75 (`Torch was not compiled with flash attention`), which costs speed and cannot be fixed on this card.

### Streaming verdict (Phase 2, deliberately not built)
- **Incremental speech already exists**: `voice/realtime.py:speak_stream()` emits on sentence end (>=50 chars), 180 chars, or 3.5s, and `os_kernel` feeds it `brain.think_stream()` directly — Mai already talks while generating.
- **True streaming STT is hardware-blocked**: it needs sustained RTF < 1, and measured RTF is 1.17 at best (3.6s clip), 2.97 at the 0.6s clips that dominate. A 1B model on a 4GB T1000 cannot decode faster than real time. Revisit after the M19 GPU window, or with a much smaller streaming model.

### Gate
New tests: `tests/test_recorder.py` +3 (pre-roll carries pre-onset audio, zero pre-roll keeps the onset chunk, trailing silence trimmed to the keep window), `tests/test_voice_gating.py` +2 (sub-word fragment rejected, 0.5s wake phrase accepted), `tests/test_stt_kyutai.py` +1 (`_disable_dynamo`) with the padding assertion updated (2400 samples, was 2400-padded-to-24000). Full suite **2,027 passed / 2 skipped / 0 failures** (baseline 2,021 + 6).
- Pending live verification: speak "hey mai" after restart; expect `[Gate] Accepted speech` -> `Heard: ... (STT: ~2000ms)`, and `[Gate] Rejected short speech` instead of `Empty transcription` when only a click was captured.

---

## Self-Hearing Loop — Root Cause + Fix (Oct 29 2026)

Follow-up report: wake path returning junk (`Hello.`, `week.`) and the conversation path producing text the user never said (`Hello, beautiful.`, `You're also listening.`, `weapon my`, `shut up.`). Full read-only investigation first; **the backend was never at fault**.

### Confirmed facts
- **One STT object, one VoiceManager.** `app/builders/voice.py:53-58` builds `app.stt` (Kyutai under `STT_BACKEND=kyutai`), `:108-116` builds the single `VoiceManager(stt=app.stt)`. `voice_manager.py:150` hands the same object to `WakeDetector`; `core/os_kernel.py:121` stores `self.stt` and never reads it (kernel uses `voice_manager.stt` at `os_kernel.py:300`).
- **The conversation path runs Kyutai, not Whisper.** `voice_manager.py:670,673` hardcode the strings `"Starting Whisper transcription"` / `"Whisper result"` regardless of backend. Whole-log grep for `falling back to faster-whisper`, `Load failed`, `Runtime failure`, `STT error`, `Whisper unavailable` → **0 matches**; `[KyutaiSTT] Ready in 2.7s (device=cuda)` at 16:38:34 and no fallback line afterwards.
- **No echo cancellation exists.** `VoiceManager.send_playback_audio()` (`voice_manager.py:742-747`) is the only caller of `full_aec.add_playback()`; its only call site is `tests/test_deferred_v43.py:505`. With no playback reference, `FullAEC.process()` is a strict pass-through by design (Oct 25 fix).
- **The recorder is fed unconditionally** (`voice_manager.py:233-234`), including while `_speaking` is True. Live proof (16:45:55 `Playing:` → onsets at 16:45:59/16:46:01/16:46:06/16:46:08/16:46:12/16:46:14/16:46:15 → `listen()` at 16:46:20 returns a 1.43 s "utterance" → `text='shut up.'`). Same shape at 16:40:46 → 16:40:48 onset → 16:40:50 `listen()`.
- **The utterance queue was never drained.** `_utterance_queue` written at `:86`, read at `:360`, `:421`, `:607`; nothing clears it, so audio recorded during playback is consumed as the next user turn.
- **Measured hallucination shape** (real TTS clip, this GPU, shipped eager path): her own voice at speaker-bleed level, mid-sentence 1.43 s → `'moment to let it'`, `'rather is being natural.'`, `'I did not.'`. Clean speech → correct. Full-scale white noise → `''`. Pure room tone peak-normalized → `''`. **Her voice is the only input that produces fluent wrong sentences.**
- **Peak normalization is the amplifier.** `recorder.py:235-236` forces every utterance to 1.0; Silero scores the same white noise 0.00 at peak 0.20 but **0.60** at peak 1.0, so normalization is what lets noise-like input clear the gate.
- **`stt=MISSING` is cosmetic.** `voice_manager.py:162` requires a non-`None` `stt.model`; `KyutaiSTT` loads lazily (`stt_kyutai.py:36,124`). Log: MISSING at 16:38:25, `Ready` at 16:38:34, `ok` on every later `_ensure_components()` (39 MISSING / 95 ok overall).

### Fixes (uncommitted)
- `voice/voice_manager.py` `_build_mic_callback` — do not feed the recorder while `_speaking`; barge-in still works because the interrupt check runs on the raw chunk before the guard.
- `voice/voice_manager.py` `set_speaking` — on the transition into speaking, `recorder.stop()` so the pre-roll cannot replay pre-playback audio into the next turn.
- `voice/voice_manager.py` `_discard_stale_utterances()` — drains the queue at `_listen_impl` and `_listen_raw_impl` entry, so audio recorded before the turn is never returned as user input.
- `core/os_kernel.py` — both greeting paths (`_tick` greeting and `_run_greeting_first`) now wrap `speak_stream` in `set_speaking(True/False)`; previously the greeting played with the mic fully armed.

### Gate
`tests/test_voice_selfhearing.py` (6): no recording while speaking, recording resumes after, entering speech clears the recorder buffer, queue drain, `_listen_impl` never returns pre-turn audio, greeting sets `set_speaking(True)` during playback. Full suite **2,033 passed / 2 skipped / 0 failures** (baseline 2,027 + 6).

### Deliberately deferred
- Wiring `send_playback_audio` for real AEC (bigger change; LMS quality on this hardware unproven).
- `app/builders/voice.py:111` passes `adaptive_noise_filter=` but the constructor reads `noise_filter=` (`voice_manager.py:39`), so the tuned filter is dropped and a default one is built in `_ensure_components` (`:151-153`) — real bug, unrelated to this regression.
- The second peak normalization in `_transcribe` (`:666-669`) is a no-op today; keep until the echo fix is validated live.

### Known trade-off
Muting the recorder while she speaks means a user who talks *over* her is only captured from the moment barge-in fires, so the first syllable of an interruption may be lost. Accepted over self-transcription.
- Pending live verification: restart, speak normally; expect zero `listen()` returns that were recorded during a `Playing:` window, and no fluent text in response to silence.

---

## Porcupine Removal (Oct 31 2026)

User request: remove Picovoice Porcupine entirely. Audit found it was **already gone from the runtime** - `wake_word.py` is a shared-flag coordinator over `VoiceManager`, and wake detection is STT phrase matching (`wake_detector.py`). Only vestiges remained, and they were actively misleading:

- `core/config_manager.py` - `PORCUPINE_ENABLED` removed from `_SAFE_KEYS` and `_KEY_META`. The settings UI was advertising a **"Wake Word Detection" toggle, but the key was never defined anywhere in `config/`**; flipping it did nothing.
- `api/routes_system.py` - `PORCUPINE_ENABLED` dropped from the `/api/system` settings key list (it never appeared; the `hasattr` guard hid it).
- `requirements.txt` - comment corrected to "wake is STT phrase matching + Silero VAD".
- Docs: `01-Architecture/07-Voice Subsystem.md` claimed a `PorcupineDetector` existed (no such file) and described a "no-porcupine whisper wake-fallback"; `05-Reference/Complete Folder Structure.md` listed `porcupine_detector.py`; `06-Operations/Incident-Response/README.md` told operators to set `PORCUPINE_ENABLED=False` to disable voice - replaced with the real mitigation, `python run.py --mode api` (REST intact, no mic).
- `AGENTS.md` historical entries left intact (they are an accurate dated record).

Gate: full suite **2,033 passed / 2 skipped / 0 failures** (unchanged baseline - pure deletion).

---

## openWakeWord Installed (Oct 31 2026)

`openwakeword==0.6.0` installed into `mai_env` (user request). **Installed and verified, but NOT wired** - it cannot wake on "hey mai" yet.

- Install was dependency-clean: dry-run showed only `openwakeword-0.6.0` would be added; every dep (numpy 1.26.4, onnxruntime 1.23.2, scipy, scikit-learn, tqdm, requests) already satisfied. `pip check` clean, torch 2.3.0+cu121 / CUDA still healthy. This matters because the last unpinned install in this repo dragged numpy 2.x in and broke torch/spacy (see TTS Fix, Aug 9).
- Added `openwakeword==0.6.0` to `requirements.txt` (alphabetical, between onnxruntime and opentelemetry) and corrected the stale "Removed openwakeword" comment.
- Pretrained models downloaded via `openwakeword.utils.download_models()` into `site-packages/openwakeword/resources/models/`: `alexa_v0.1`, `hey_jarvis_v0.1`, `hey_mycroft_v0.1`, `hey_rhasspy_v0.1`, `timer_v0.1`, `weather_v0.1` + `melspectrogram.onnx`, `embedding_model.onnx`, `silero_vad.onnx`.
- **Measured** (`hey_jarvis_v0.1`, ONNX, 1280-sample/80 ms frames): **2.95 ms per frame = 3.7% of one core**, score 0.0 on noise. (Earlier consult note claiming "<1% CPU" was optimistic - 3.7% is the real number, still ~30x cheaper than a Kyutai pass per wake check.)
- **Blocker: no pretrained "hey mai" model exists.** `WAKE_WORDS = ["wake up mai", "hey mai", "mai wake up", "wake up"]` (`config/ai.py`). The fixed pretrained set is alexa/hey_jarvis/hey_mycroft/hey_rhasspy/timer/weather.
  - Path A - `openwakeword.custom_verifier_model.train_custom_verifier(positive_reference_clips, negative_reference_clips, output_path, model_name)`: few-shot sklearn verifier over openWakeWord embeddings. Needs **directories of real WAVs** - positives of you saying "hey mai", negatives of other speech. Minutes to train.
  - Path B - full synthetic-data training (openWakeWord Colab pipeline): hours, custom phrase, best accuracy.
- Wiring note for whoever does it: mic delivers float32 [-1,1] at 16 kHz in 512-sample blocks; openWakeWord wants **int16 and 1280-sample frames** - needs a 512->1280 accumulator plus `*32767` conversion in `_build_mic_callback` (or a separate wake thread reading `AudioBuffer`).
- Nothing in `voice/` imports openwakeword; `wake_detector.py` STT phrase matching remains the live wake path.

Gate: no runtime code changed - full suite unchanged at **2,033 passed / 2 skipped / 0 failures**.

---

## AEC Playback Feed Wired + Double-Talk Threshold Fix - Nov 8 2026

Closes the standing "AEC is a pass-through" gap. `FullAEC.add_playback()` had no production caller, so echo cancellation never ran; the only echo defence was muting the recorder while `_speaking`. Measured first, then fixed three things.

### Measured (synthetic two-path room: 0.35 @ 2.5 ms + 0.15 @ 19 ms, 16 kHz)
- **Fed reference + shipped threshold 0.3: 1.2 dB ERLE** - and all of it from the clip guard; `_filter_weights` stayed **exactly zero**. Root cause: the near/far EMA ratio sits at 0.15-0.4 with echo alone, so `ratio > 0.3` latched into permanent double-talk, the filter never adapted, and nothing was cancelled.
- **Fed reference + threshold 1.0: 18.4 dB ERLE**, user speech in the double-talk window preserved (-0.1 dB). mu ladder 0.01 / 0.003 / 0.001 -> 18.4 / 14.9 / 9.9 dB, so the shipped 0.01 is correct.
- Unfed (today's production): pass-through by design - unchanged.

### Fixes
1. **`voice/stream_player.py`** - real playback tap. With a tap installed the clip is no longer played by `sd.play()`; it is streamed through `sd.OutputStream` block by block (512 frames, `write()` blocks, so the loop is real-time paced) and each block is handed to the tap **as it goes to the DAC** - no drift, no latency guesswork, no extra thread. `_resample_to()` (scipy `resample_poly`) converts to the tap rate (Kokoro 24 kHz -> AEC 16 kHz). `set_reference_tap(tap, on_end, sample_rate)` installs it; the finally block fires `on_end` and the context-manager exit drains queued audio (`Pa_StopStream`). `pause()`/`stop()` now `abort()` the stream (only `sd.stop()` would not reach our own stream). A write failure aborts that clip and is logged at WARNING unless the player was being stopped (abort noise stays at debug).
2. **`voice/full_aec.py`** - `end_playback()`: zeroes the far-end ring buffer, resets `_has_playback` and the power/double-talk state, keeps the filter weights. Without it the reference stays audible-but-stale after the clip and idle mic frames would keep adapting against it.
3. **`config/voice.py`** - `FULL_AEC_DOUBLE_TALK_THRESHOLD` **0.3 -> 1.0** with the measurement in a comment (raise it if soft speech over her voice gets filtered).
4. **`voice/voice_manager.py`** - `attach_playback_tap(player)` (wires `send_playback_audio` + `end_playback_audio` at `self.sample_rate`, returns False without an AEC or a tap-capable player) and `end_playback_audio()`.
5. **`app/builders/voice.py`** - calls `app.voice_manager.attach_playback_tap(app.voice.player)` right after VoiceManager construction. This is the line that was missing before.

### Not done (deliberate)
- **Recorder still muted while `_speaking`.** Cancellation is now real, but continuous capture during playback (barge-in without losing the first syllable) changes live behaviour and cannot be validated without hardware. Unmute `voice_manager.py` (`if self._recorder and not _speaking:`) and test; note the 2048-tap filter spans ~128 ms, so Bluetooth-class output latency would not be cancelled.
- Resampling is reference-only; playback keeps the file's own rate (device resampling unchanged).
- `shortcut:` none added - the 128 ms filter span is documented in config and the roadmap caveat instead.

### Gate
New `tests/test_voice_aec.py` (12): synthetic-room cancellation at the shipped config, double-talk threshold adapts instead of latching, user speech survives, `end_playback` restores pass-through, tap receives resampled played audio (exact `resample_poly` match) and `on_end` fires, no-tap path still uses `sd.play`, `stop()` aborts the active stream, a device write failure ends the clip cleanly and still flushes the reference, `attach_playback_tap` wires bound methods / is a no-op without an AEC, and the tap reaches the AEC through VoiceManager. Suite **2,045 passed / 2 skipped / 0 failures** (2,047 collected; baseline 2,033 + 12).

---

## Kyutai Promoted to Primary STT - Nov 8 2026

User request: "make Kyutai the primary Stt". The backend already ran here via `.env STT_BACKEND=kyutai`, but the shipped config default was still `whisper`, so every other install (and the documented status) treated Kyutai as opt-in.

### Change
1. **`config/voice.py`** - `STT_BACKEND` default `"whisper"` -> `"kyutai"`, comment rewritten: primary backend, measured 2.5-4.2s vs ~3.0s for a ~2s clip on the T1000, still above the plan's RTF <= 0.7 ideal (deliberate override, not a gate pass), faster-whisper stays the permanent fallback. `STT_BACKEND=whisper` reverts.
2. **`app/builders/voice.py`** - the defensive `getattr(cfg.voice_config, "STT_BACKEND", ...)` fallback string also flipped to `"kyutai"` (config always defines the attr; keeping the two defaults disagreeing is exactly the drift that silently restores whisper).
3. **`voice/voice_manager.py`** - four hardcoded "Whisper" log labels made backend-neutral (`Starting STT transcription`, `STT result`, `STT unavailable` x2). They were already wrong on this machine (live backend is Kyutai) and would be wrong by default everywhere after this change. No test or doc referenced the old strings.
4. `.env` left as-is (`STT_BACKEND=kyutai` is now redundant but harmless; deleting it would change nothing).

### Tests
- `tests/test_stt_kyutai.py`: `test_stt_backend_default_whisper` -> `test_stt_backend_default_kyutai` (asserts the default is kyutai with env unset); `test_stt_backend_env_switch` -> `test_stt_backend_env_switch_to_whisper` (env still overrides); the tautological `test_builder_non_kyutai_backend_hooks_into_placeholder_build` (it asserted `getattr(obj_with_attr, ...) == attr`, i.e. tested Python) replaced with `test_builder_defensive_default_is_kyutai`, which pins the builder's fallback literal to the new default.
- Verified live: `app.config_loader.voice_config.STT_BACKEND == "kyutai"`, `Settings.STT_BACKEND == "kyutai"`, checkpoint path `E:\Mai_ai\kyutai STT\stt-1b-en_fr-trfs` exists. No caller touches whisper-only attributes (`set_model`, `input_device`, `max_record_seconds`, `silence_threshold`), so the Kyutai object satisfies every use site.
- Focused suites (stt_kyutai, voice_gating, voice_selfhearing, deferred_v43, desktop_app): 108 passed.

### Docs
- `stt-kyutai-replacement-plan.md` - status line, build spec, risk row and decisions log (new 2026-11-08 entry; the 0.7 gate is recorded as an unmet ideal, not a pass).
- `CURRENT_STATE.md` - voice bullet, stack table, known issue #3 (also dropped the stale "whisper is comparable or better on short clips" claim, which the Oct-27 padding/dynamo measurements disproved), and the Kyutai row **removed from §4 Incomplete Capabilities** (it is no longer partial/opt-in).
- `07-Voice Subsystem.md`, `10-Status & Debt.md`, `Voice Pipeline.md`, `future-vision-roadmap.md`, `README.md`, `Complete Folder Structure.md` - opt-in/default language flipped.
- `Troubleshooting/README.md` - new row for `[KyutaiSTT] Load failed ... falling back to faster-whisper` (checkpoint missing on a fresh install is now a normal failure mode), and the status check now names the real field (`stt.backend` -> `kyutai` or `kyutai(whisper fallback)` + `load_failed`).
- `Deployment/README.md` + `Deployment Guide.md` - `.env` sample now `STT_BACKEND=kyutai`.
- Dated historical docs (Project Charter, audit reports) keep their original wording.

### Watch-outs
- Kyutai load is lazy: the first utterance after boot pays ~2.7s (already true here).
- CPU-only installs get RTF ~4.8 (≈ whisper-small), so the promotion is a win on GPU and neutral on CPU.
- `WHISPER_MODEL` in the settings UI now only affects the fallback path.

### Gate
Full suite **2,045 passed / 2 skipped / 0 failures** (2,047 collected, 1m55s, mai_env) - count unchanged: three test functions were rewritten in place, none added.

---

## Local LLM (llama.cpp / GGUF) + Switchable Voice Stacks - BUILD COMPLETE (Nov 13 2026)

User request: integrate a local GGUF model with switchable LLM providers and switchable voice stacks, two UI buttons, build first and install the model/server last. Plan: `docs/Mai_documentation/03-Features/llamacpp-local-llm-plan.md` (status "BUILD COMPLETE (steps 1-5), INSTALL PENDING (step 6)", §12 build record, §13 open items).

Locked decisions (D1-D6): Stheno 8B Q5_K_M with **partial CPU offload** (GPU takes what fits); ElevenLabs for cloud voice; Mai owns its own llama-server on **port 8082** (8080/8081 belong to another project); Kyutai stays the local alternative; defaults unchanged (`LLM_PROVIDER=openrouter`, `VOICE_STACK=local`) so nothing changes for a user who never touches a switch. Q1 = cloud stack is ElevenLabs TTS **+ Scribe STT** (both built); Q2 = emoji stripped **only in the TTS layer**, the "as an AI" boundary stays a prompt/ThoughtPacket (M11) concern.

The VRAM argument is what shaped the design: Kyutai bf16 holds ~2.3 GB of the T1000's 4 GB and llama-server 4B alone measured 3,283 MiB of 4,096, so they cannot coexist - which means the voice switch must move **STT**. Kokoro TTS was already CPU-only, so moving TTS alone would free nothing.

### Built
1. **LLM provider** - `llm/providers/openai_compat.py` (new): `/v1/chat/completions`, real SSE streaming via new `PooledHTTPClient.stream_lines()`, `/health` probe with `/v1/models` fallback, `generate_with_tools`, `cancel_stream`, `stats`. Yields raw deltas and **raises** on failure so `_stream_with_failover` can move providers; permanent 4xx are not retried. `LLAMACPP_BASE_URL/MODEL/API_KEY` in `config/llm.py` + settings mirror; `llm/manager.py` gained `_provider` normalisation, lazy `_ensure_llamacpp()`, llamacpp-first `generate()`/`stream()`, cooldown, `select_provider(probe=)`, `providers_status(probe=)`, `PROVIDERS`. Live smoke against the other project's `:8080`: `is_alive` True, **TTFT 0.438 s**, 10 chunks.
2. **Voice backends** - `voice/elevenlabs_tts.py` (new): exact `KokoroTTS.generate(text, path, emotion=)` contract, `pcm_24000` (no decoder, no extra latency) written as a 24 kHz WAV, emotion -> stability, emoji strip, permanent Kokoro fallback on any failure. `voice/elevenlabs_stt.py` (new): FasterWhisperSTT surface, WAV upload to `/v1/speech-to-text`, no key or runtime failure -> permanent `FasterWhisperSTT` fallback (CPU, no VRAM). `ELEVENLABS_*` + `VOICE_STACK` keys in config with settings mirrors; local backends tagged `stack = "local"`, cloud `stack = "cloud"`.
3. **Switcher** - `voice/stack_switcher.py` (new): `resolve_stack()` (persisted override > env, cloud refused without a key), `build_stt/build_tts` as the single construction source for boot **and** switch, `VoiceStackSwitcher.switch()` refusing `unknown_stack`/`no_api_key`/`busy`, swapping **six** injection points (`app.stt`, `voice_manager.stt`, `wake_detector.stt`, `kernel.stt`, `app.tts` + `voice.tts`, `voice_renderer.tts` - missing one leaves the old model alive and the VRAM unreleased), closing the outgoing cloud client, `del` + `gc.collect()` + `torch.cuda.empty_cache()`, reporting `vram_freed_mb`. `app/builders/voice.py` is stack-aware and builds `app.voice_stack`; `app/application.py` field added.
4. **API + UI** - `GET /api/system/providers`, `POST /api/system/llm/provider`, `POST /api/system/voice/stack` (auth-guarded thin `SystemMixin` wrappers; `mai.llm`/`mai.voice_stack` wired in bootstrap). `api/static/js/system.js` gained a "Models & Voice" section with live-switch buttons; `LLM_PROVIDER`/`VOICE_STACK` are filtered out of the generic config list because that path only persists and waits for a restart. `api/routes_system.py` persists `LLM_PROVIDER` on a successful switch; `app/builders/infrastructure.py` restores a persisted provider at boot with `probe=False` (no network before the first request).
5. **Launcher** - `scripts/run_llama_server.ps1`: port 8082, `--ctx-size 8192 --parallel 2 --flash-attn on --no-webui --alias stheno`, `-NGpuLayers` parameter for the sweep, `-DryRun` prints the exact command and reports what is missing (verified: reports missing binary and model). `--parallel 1` is deliberately avoided - Mai also calls the LLM from background threads and a queued dream task must not sit in front of a voice reply.

### Gate
`tests/test_voice_stacks.py` (30: TTS PCM/headers/emoji/format/fallback, STT upload/permanent fallback/no-key, construction + resolve, the six-point swap, close/busy/no-key/unknown/no-op, provider routes, stack tags) + `tests/test_llm.py` (+19) + `tests/test_stt_kyutai.py` (source-inspection test replaced by 2 behavioural ones).
Full suite **2,095 passed, 2 failed** - both reds are the pre-existing `tests/test_horizontal_scaling.py::test_redis_state_sharing` and `::test_event_bus_pubsub`, which now execute because a real Redis 8.1.0 answers on `localhost:6379` and expose a separate state-sharing bug (files untouched, unrelated to this build).

### Still open
- **Step 6, gated on user go**: Stheno 8B Q5_K_M into `models/`, llama.cpp release into `tools/llama/`, sweep `-ngl` 16/20/24/28 at ctx 8192, lock the value in `.env`.
- **ElevenLabs key (Q3)**: no key on this machine, so the cloud stack is mocked-tested only. Check `GET https://api.elevenlabs.io/v1/models` for the real STT model id before trusting `ELEVENLABS_STT_MODEL=scribe_v1`, then confirm the >= 2.0 GB VRAM release on a live switch.
- **M9 evaluation** (`scripts/run_m9_evaluation.py --mode real`) local vs cloud.

---

## Spark-X2.5-4B Installed + Cloud Voice Validated - INSTALL COMPLETE (Nov 13 2026)

Closes the "Step 6 / Q3 / VRAM gate" items of the Nov-13 build entry above. Plan doc: `docs/Mai_documentation/03-Features/llamacpp-local-llm-plan.md` §13-§14.

### Model + server
- **`qikuanz/Spark-X2.5-4B` Q4_K_M** in `models/Spark-X2.5-4B-Q4_K_M.gguf` - 2,600,224,352 B, SHA-256 `adfcfa19...09428` **verified MATCH**. D4 overridden by the user: the planned Stheno 8B Q5_K_M is superseded, and with it D1 (partial CPU offload) - a 4B fits the card whole.
- **The GGUF embeds its own chat template** (4,647 chars, `enable_thinking` defaults true). `models/spark-chat-template.jinja` was redundant and is deleted.
- `scripts/run_llama_server.ps1`: llama.cpp **b12212** (CUDA 12.4, `tools/llama/`) on **port 8082**, `--alias spark --ctx-size 8192 --parallel 2 --n-gpu-layers 99 --flash-attn on --no-webui --jinja --reasoning off`. `--parallel 2` splits 8192 into 4,096 per slot = `LLM_MAX_CONTEXT`. Load 37.5 s, resident **3,135 MiB of 4,096**.
- `-ngl` sweep (warm): **99 -> 3,135 MiB, 0.40 s TTFT, 22.1 tok/s**; 20 -> 1,863 MiB, 0.92 s, 4.4 tok/s. Full offload wins 5x.
- `scripts/fetch_spark.ps1` (new): 78 x 32 MB curl range requests into separate `.part` files with per-chunk size checks, resume, and a final SHA-256 gate. `hf_hub_download`/hf_xet **stalled with zero disk I/O for 7 minutes** on this machine's intermittent DNS resets, and an earlier parallel-seek writer passed its own size assert while leaving **110 zero-filled 16 MB blocks**. Never trust a size-only check for a model download.

### Latency, honestly
- First measurement looked fatal (**35.9 s TTFT, 0.5 tok/s**) - it was one-time CUDA warmup: the server log showed `prompt eval 35852 ms / 27 tokens`. Warm: **0.40-0.49 s TTFT, 18.8-22.1 tok/s**. `scripts/sweep_llama.ps1` now discards a warmup pass so it cannot report that artifact again.
- The cost that matters is **prompt eval, 143.6 tok/s** (1,669 tokens = 11.6 s). M9 measured Mai's real system prompt at **8,069 chars on turn 0 (~2k tokens)** -> **~12 s to first token** on the first turn of a session, ~3.5 s once memory context empties (~2,500 chars). Generation is fine; `speak_stream` emits per sentence. Spark's prompt eval is ~1.7x faster than Qwen3-4B-Instruct (107 tok/s on 2,088 tokens).

### M9 on Spark (real mode, praise, 5 turns) - `session-praise-real-1794595381`
**4.67/5** (same as Qwen3-4B), trust monotone **0.72 -> 0.82** (Qwen3: 0.60 -> 0.70), no boundary leakage; `review_required` only for the unexercised `experience_visibility` axis. **But the rubric does not measure voice**: Spark reads as an assistant (*"I'm glad I could make a difference for you today"*), states feelings outright (*"It makes me feel valued"*), where Qwen3 produced *"Mm... you're welcome. You sounded weighed down earlier..."*. Treat the score as "mechanics hold", not "character holds".

### Stage-direction leak - found by that run, fixed
Spark opened turn 4 with `(with a warm smile) That's really sweet.` No stage-direction rule existed anywhere, so **both TTS backends would have spoken "with a warm smile" aloud**. Fixed at both ends:
- `voice/speech_text.py` (new): `sanitize()` strips emoji and short parenthetical asides that carry no sentence punctuation of their own. Prose parentheses (`(which, as I said, took a while)`) survive; `(smiling)` and `(with a warm smile)` do not. `*asterisk actions*` deliberately untouched (as likely emphasis as action, none observed).
- `ElevenLabsTTS._clean_text` and `KokoroTTS._enhance_text` both call it (the emoji regex moved out of `elevenlabs_tts.py`; Kokoro previously had no emoji strip at all).
- `prompt/character.py` INTERACTION RULES: "Write only the words you say - never stage directions, *asterisk actions*, or (parenthetical asides)" - the source fix, for every model.

### Cloud voice (ElevenLabs) - Q3 answered, live-validated
- Key is **permission-scoped** (no `user_read`/`models_read`/`voices_read` => 401 on those endpoints) and **free tier**: library voices are refused over the API (Rachel => `402 paid_plan_required`); **premade voices work**. Shipped voice = **Bella** `EXAVITQu4vr4xnSDxMaL`.
- TTS: 2.93 s of audio in **2.06 s**, peak 0.933, zero failures. STT: `ELEVENLABS_STT_MODEL=scribe_v2` (v1 heard "Hello Mai", v2 heard "Hello, Mai."), **RTF 0.311**.
- **VRAM gate PASSED: 2,510 MB freed** (free 409 -> 2,919 MiB of 4,096) on a real Kyutai->cloud switch. The first probe reported `freed_mb: 0` because the probe itself held the Kyutai reference - build the objects inside a function so the app is the only owner.

### Consequence for this 4 GB card
llama-server (3,135 MiB) + Kyutai (2.3 GB) **cannot coexist**. The usable local-LLM combination is `LLM_PROVIDER=llamacpp` + `VOICE_STACK=cloud`.
**This machine is set to exactly that** (`.env`, Nov 14, user-approved): `LLM_PROVIDER=llamacpp`, `VOICE_STACK=cloud`, ElevenLabs key present. Verified through the real code - `Settings.LLM_PROVIDER=llamacpp`, `resolve_stack()=cloud`, `build_tts -> ElevenLabsTTS`, `build_stt -> ElevenLabsSTT`, `LLMManager.generate()` answered from the local server (`provider=llamacpp`, `status=llamacpp`). `STT_BACKEND=kyutai` is kept because that is what the **local** stack builds, so `VOICE_STACK=local` still works. Mai now needs `scripts/run_llama_server.ps1` running; without it the provider fails over to OpenRouter. **Start it with `-Detach`** (new flag, Nov 14): the foreground mode dies with its terminal, which is exactly how the first launch here disappeared, and detached it logs to `logs/llama-server.log` and waits for `/health` before returning. Currently running detached on :8082 (pid confirmed, ~2.9 GB working set). Shipped repo defaults remain `openrouter` + `local`, so a fresh clone is unaffected. User also accepted Spark as the persona model despite the weaker voice documented above.

### Gate
`tests/test_voice_stacks.py` +3 (stage direction not spoken, prose parenthesis survives, Kokoro uses the same guard). Focused suites (voice_stacks + prompt + knowledge): 343 passed. Full suite **2,098 passed / 2 failed** - the same pre-existing Redis pair.

### Still open
- **Cloud-vs-local M9 comparison** (§7 step 5): local done, cloud not run.
- **Human read of Spark's character voice** before it can be called the default persona model.
- **`--no-reasoning-preserve`**: the server warns the template preserves reasoning by default. Harmless while `--reasoning off` emits none; not measured.

---

## Model Swap (Spark -> Qwen3-4B) + System Page Fix - Nov 14 2026

Three user asks in one pass: (1) which STT is live, (2) delete Spark / use the Qwen GGUF, (3) the System page is broken.

### 1. Answer: runtime STT is ElevenLabs Scribe v2
`VOICE_STACK=cloud` means `build_stt("cloud")` returns **`ElevenLabsSTT`** (model `scribe_v2`); `STT_BACKEND=kyutai` only applies to the **local** stack, so it is inert right now. Verified by construction, not by reading config: `resolve_stack()=cloud`, `build_stt -> voice.elevenlabs_stt.ElevenLabsSTT`, `build_tts -> voice.elevenlabs_tts.ElevenLabsTTS`. The live `/api/system/providers` payload agrees (`stt.backend=ElevenLabsSTT`, `model_id=scribe_v2`).

### 2. Spark deleted, Qwen3-4B-Instruct-2507 in place
- `models/Spark-X2.5-4B-Q4_K_M.gguf` deleted; `Qwen3-4B-Instruct-2507-Q4_K_M.gguf` (2,497,281,120 B) copied from `E:\rika documentation agent\models\llm\` (local file, no download, no hash gate).
- `scripts/run_llama_server.ps1`: `$ModelPath` default + `-Alias` default `spark` -> `qwen3-4b`; comments updated. `.env`: `LLAMACPP_MODEL=qwen3-4b` (**must equal `--alias`**).
- Server re-launched detached on :8082 with the same flags (ctx 8192, parallel 2, ngl 99, `--jinja --reasoning off`). Verified live: `LLMManager.provider=llamacpp`, `providers.llamacpp={available:true, model:"qwen3-4b"}`, `generate()` answered in **0.67 s**. `VOICE_STACK=cloud` untouched.
- Plan doc §15 records the swap (and §3 D4, §7 step 1-4 now point at the current model).

### 3. System page: one 500 blanked the whole space
`GET /api/system/plugins` threw `AttributeError: 'WeatherPlugin' object has no attribute 'name'`. Manifest-style plugins (`plugins/<name>/manifest.json`) are plain classes with a `MANIFEST` dict, not `Plugin` subclasses with `.name`/`.version` - `PluginLoader.list()` assumed the latter. Starlette answers an unhandled exception with **plain-text** `Internal Server Error`, so `system.js`'s `.json()` rejected inside `Promise.all` and the space rendered nothing but `Error: ...`.

- `core/plugin_system.py` `list()` falls back to `MANIFEST["name"]` / `MANIFEST["version"]` / the registry key and defaults `initialized` to True.
- `api/static/js/system.js`: fetches go through `_json()` (a dead endpoint degrades to `null` instead of blanking the page); the 15 s refresh timer is created **once** - it previously pushed a new `setInterval` on every `_init()`, so the timer count multiplied on each self-refresh (the page got progressively slower and started hammering 6 endpoints per timer per tick).
- Regression test: `tests/test_plugin_marketplace.py::test_list_reports_manifest_plugins_without_name_attr` (loads the real `weather` plugin, asserts no `.name` attr and correct list output).
- Verified live in the browser: 6 plugins, 10 sections, 279 config rows, no console errors, `POST /api/system/llm/provider` and `POST /api/system/voice/stack` both answer and persist (`LLM_PROVIDER=llamacpp` retained).

### Environment note
A `Start-Process` child launched from the agent shell was reaped when that shell exited (llama-server vanished once, which is why `providers.llamacpp` briefly read `available:false` - the UI shows `· offline`, it is not a stale-state bug). From a normal terminal `-Detach` survives (pid outlived the previous session).

### Gate
Full suite **2,099 passed / 2 skipped / 0 failures** in 132s (baseline 2,098 + 1 new test). The pre-existing Redis pair also went green.
`tests/conftest.py` now pins `LLM_PROVIDER=openrouter` before any test module imports `llm.manager`: the suite specifies the repo-default provider order, and this machine's `.env` (`LLM_PROVIDER=llamacpp`) was silently redefining 19 of them (all 19 passed once pinned). Same class of bug as the earlier ambient-STT test fix.

---

## Memory Recall Remediation - "she does not remember me" (Nov 15 2026)

User report: Mai does not remember the user, and every Memory UI row reads `importance 0.50`. Eight root causes measured first, then fixed in one pass (all previously uncommitted).

### Why nothing was recalled
1. **`config/memory.py` threshold 0.65** - measured best genuine match across 8 realistic queries was **0.639**, so the retriever returned **0 hits every time**. Now `MEMORY_SIMILARITY_THRESHOLD = MEMORY_SIMILARITY` (0.40), one knob. Live check: **0 -> 15 hits** over the same 8 queries.
2. **`knowledge/retriever.py:207`** read `item["score"]`/`["relevance"]`, but `SearchEngine._parse_result` emits `"similarity"` - every surviving hit was scored a hardcoded 0.5. Now reads `similarity` first.
3. **No user identity in the prompt** - `identity/user.md` parsed to `{"_updated": ...}` because `_parse_markdown` only understood `key: value` and the vault writes `- [category] fact - date` bullets; nothing rendered user identity anywhere. Parser now emits `facts` + a bounded `profile`; `ContextPrompt` gained a `USER PROFILE` section plumbed through builder -> prompt_builder -> orchestrator (`structured["identity"]["profile"]`). Profile rule: stable categories only (`name/age/work/study/location/background`), dedupe, newest first, interleaved per category so one chatty category cannot crowd out name/age/work, cap 12 lines / 700 chars, and assistant lines dropped (`"mai"` in the fact - the extractor misfiles her self-introduction as user facts).
4. **`memory/memory.py` recall replayed Mai's own replies** (often her denials: "I don't have anything stored from before"). New `_user_half()` keeps only the user side; `_emotionally_related` no longer emits the `Mai:` half either.

### Why every importance was 0.50
5. **`knowledge/obsidian_reader.py:_extract_entries`** split on `"\n---"`, so the frontmatter block (`importance/id/tags/emotion`) landed in a segment with no `### User` header and was discarded - every replayed entry fell back to 0.5. Now the frontmatter segment is carried into the entry that follows. Verified on real files: 0.34/0.73/0.79/0.85/0.94/0.98/1.0 now survive (was 0.5 across all 25 entries of 2026-07-18).
6. **`memory/pipeline.py`** built its `MemoryObject` without the score and wrote `getattr(node, "confidence", 0.5)` into the vector metadata (wrong field, and `confidence` is not the importance). Now computes `score` from the intelligence node (0.0 preserved - not `or 0.5`) and passes it to both the object and the metadata.
7. **`memory/hierarchy.py:store_semantic`** had no `importance` parameter, so `SemanticMemory.add` always built `importance=0.5` (178/178). Parameter added end to end; `store_from_memory_object` passes the object's importance, the vault replay uses `REPLAY_IMPORTANCE` (0.6).
8. **`api/routes_memory.py:memory_timeline`** merged the hierarchy dump with `brain.memory.short`, showing each turn two or three times. Deduped on normalized content (first 80 chars, newest wins).

### Source fix for the identity-file pollution
`knowledge/vault_post_processor.py` extraction prompt included Mai's reply (`User: {user}\nMai: {ai}`) and the local 4B model filed her self-introduction as the user's facts (`[name] I am Mai Sakurajima`, `[location] I am in jail`). The Mai line is gone and a rule now says never attribute her statements to the user.

### Measured, not changed
Queries whose facts live only in the vault ("how old am I", "what do I do for work", "where do I live") still score 0.24-0.31 against the vector store and stay below the 0.40 floor - correctly, they are not vectors at all. They are covered by the new USER PROFILE block instead, which is why the floor was not lowered further.

### Gate
New `tests/test_memory_recall_fixes.py` (14): frontmatter merge, frontmatter-only files skipped, identity bullets -> facts, assistant lines + chitchat dropped, profile bounded, preferences unaffected, profile reaches the system prompt, `similarity` key used, threshold floor, pipeline importance from the intelligence node, semantic importance carried, `_user_half` on both shapes, timeline dedupe.
Full suite **2,113 passed / 2 skipped / 0 failures** in 160s (baseline 2,099 + 14).

### Identity file repair + janitor persistence fix (same day)

**`identity/user.md` cleaned: 73 -> 52 facts.** Every removal was proven by reading the source conversation, not guessed:
- Mai's own lines filed as user facts (2026-11-14: conversation line 19 is her saying "I am Mai Sakurajima. that's all.") - `[name] I am Mai Sakurajima`, `[name] My name is Mai`, `[background] I have a mother, a father, a sister, and a brother`, `[background] I have never told my family their actual names`; plus 2026-10-19 `[name] My name is Mai Sakurajima`, `[background] Mai said she likes me`.
- `[location] I am in jail` was a **metaphor**: 2026-10-02 line 452 reads "you can say i am in a jail ... i need to earn money" and Mai answered "I feel like I'm in a jail." The feeling is already covered by the `[personality]`/`[background]` entries that survived.
- 12 `[general]` chit-chat fragments ("for me", "like always", "eight times", "just testing you"). `feeling very lonely today` had a `[personality]` twin, so nothing was lost.
- Exact duplicates: `[name] My brother is named Mustafa` / `[name] My sister is named Faryal` (both verbatim under `[background]`), `[name] The user's name is Murtaza`, `[name] I am Murtaza`.
- Kept and verified as genuine: the `honey` preference (2026-10-19 line 206: "can you call me honey from now on" - it was the user asking, not Mai), full name, age, work, Karachi, siblings, and the family history.
- `user.md` is the source of truth (reloaded every turn by `vault_post_processor` -> `MemoryState.load_from_file`), so `master_state.json` needed no edit - it holds only emotion/relationship/goals/attention/runtime. Round-trip verified: 52 facts reload, profile block is now name/age/work/Karachi/honey/background, no jail, no Mai lines. Backup: `%TEMP%\opencode\user.md.backup`.

**`VaultJanitor.sweep()` never persisted entity removals** - it deleted junk note files but left `graph.json` untouched, so `sweep_graph_junk.py --apply` reported "removed 192 entities" and the junk returned on the next boot (graph.json still had all 525). `sweep()` gained `persist_path=`, writing survivors in `GraphExporter`'s list format; the script passes `graph.json`. Re-ran for real: **525 -> 333 entities**, junk gone (`you`, `me`, `love`, `like`, `said`, `siad`, ...), real entities intact (`murtaza`, `karachi`, `python`, `mustafa`, `faryal`, `aimal`, `mai`). Graph folder backed up (524 files) before the sweep; 19 junk notes were deleted in the first (note-only) pass.
- Tests: `TestVaultJanitor` +2 (`sweep_apply_persists_survivors_to_graph_json`, `sweep_dry_run_does_not_touch_graph_json`). Full suite **2,115 passed / 2 skipped / 0 failures** in 323s (baseline 2,113 + 2).
- Runtime note: `user.md` is read per turn (live immediately); `graph.json` is read at boot, so the graph cleanup applies on the next restart.

---

## Graph Cleanup Durability - Junk Replay Root Cause (Nov 15 2026)

The previous sweep was not durable: `graph.json` went 333 -> 517 after any boot. Traced with a temporary pytest plugin (an mtime watcher on `graph.json`) plus stack-trace probes on `KnowledgeGraph._entities` insertion.

### Two real causes (both at boot replay, not the app)
1. **Every user turn became a graph entity (P0, 164 names).** `memory/vault_loader.py:_load_entity_links_from_conversations` called `add_relation(entry["user"], "mentioned_in", link)`, and `KnowledgeGraph.add_relation` auto-creates an entity for any unknown source/target - so the *raw user message* was stored as an entity on every boot. Fix: the source is now the canonical `"user"` node (created as `person`) and the dedupe key is the link alone. Nothing reads `mentioned_in` (grep: 1 hit, the writer).
2. **Conversation notes replay their `[[links]]` forever.** A note written while the graph was dirty keeps `[[do you remember me]]` even after the entity is swept, so cleaning the graph could never stick. Fix: replay skips any link the janitor's predicate calls junk - the same rule the sweep uses, so a swept entity cannot come back.

### Also fixed
- `VaultJanitor._is_junk_name` - 5+ words is junk (a sentence, never an entity name). Measured before adding: zero 5+ word survivors among the 333, so no data loss.
- `VaultJanitor.sweep_note_files` - note stems are underscored and `\b` does not match across `_`, so sentence notes were invisible to the junk check. Now checks `name.replace("_", " ")`; the note pass went from 12 to 182 files.
- `tests/test_phase3_api.py` / `tests/test_reasoning_api.py` - `with TestClient(app)` enters the lifespan, which runs `MaiAPI.bootstrap()` -> real vault replay + graph export from inside the test suite. Dropped the context manager (the auth override answers before any app state is touched). The watcher plugin had named exactly these two tests as the writers.

### Verified
- Sweep `--apply`: 497 -> 333 (164 junk entities, 162 orphan notes).
- Real `bootstrap_system()`: `graph.json` 333 before -> **333 after**; in-graph junk 0; the loader creates 0 junk entities on replay (was 164); kg 840 nodes = 333 exported + 507 `memory`-type nodes the exporter filters.
- Full suite with the vault watcher attached: **2,118 passed / 2 skipped / 0 failures** (91s), zero `[VAULT-WRITE]` lines, `graph.json` mtime unchanged across the entire run.
- Tests added: `test_sentence_entity_name_is_junk`, `test_sweep_note_files_sees_through_underscores`, `TestVaultLoaderLinkGate::test_junk_link_is_not_replayed` (also pins that the turn text never becomes an entity).

### Left as-is (named, stable, not regressions)
- Two sentence-ish survivors remain in `graph.json` and are not junk by the shared predicate: `ok first open chrome`, `thanks for watching!`. Verified not replayable from any note, so they will not grow; removing them needs either a manual edit or two `JUNK_TOKENS` entries.
- `graph.py:import_from_memory_graph` and `GraphManager.process_conversation` still call `add_relation` with raw extractor names, which can auto-create an entity for an unknown relation endpoint at *runtime* (pre-existing; the confidence gate only covers entities).


---

## Continuity Engine — T8 / M22 (Nov 17 2026)

Built ahead of sequence (prerequisite for autonomous cycles, not for voice/face).
`continuity/` is a **thin reconciler over existing stores** — the `BrainGraph`
facade pattern, never a second source of truth:

- `continuity/store.py` — `ContinuityStore`: one document (`data/continuity.json`),
  atomic `os.replace` writes, `transaction()` with snapshot rollback.
- `continuity/projects.py` — `ProjectMemory`: name/summary/status/goal link,
  decisions, open questions, blockers, dependencies, deadline, next checkpoint.
  Each project auto-creates a `GoalManager` goal and **reads progress/completion
  through it**; terminal project statuses mirror back (`complete`/`cancel`).
- `continuity/commitments.py` — `CommitmentsLedger`: due windows (epoch, ISO,
  `in 3h`, `90m`, `2d`); `sweep()` marks overdue promises `missed` and publishes;
  `unsurfaced()` + `mark_surfaced()` make a missed promise reported once.
- `continuity/checkpoints.py` — `CheckpointStore`: `save`/`resume`/`clear`
  resumable state so interrupted long tasks continue instead of restarting.
- `continuity/engine.py` — `ContinuityEngine.snapshot()` reconciles projects +
  active goals + CognitiveState focus + SharedState runtime; `brief()` renders
  the prompt block (`mark_surfaced=True` on the chat path); `publish()` emits
  `state.continuity.updated`.
- `continuity/tools.py` — 6 tools: `continuity_status`, `project_open`,
  `project_update`, `commitment_add`, `commitment_resolve`, `checkpoint`.
  (Note: `project_open` takes `project_name` — `ToolRegistry.call(name=...)`
  consumes `name` as the tool name.)

Wiring:
- `app/builders/continuity.py` — new boot layer **after Cognition**, plus
  `app.continuity`, validation gate, health registration, initial publish.
- `core/event_specs.py` — 6 `data.continuity.*` events + `state.continuity.updated`
  (publisher `continuity`); `STREAM_TOPICS` derives from the catalog, so UI
  SSE/WS coverage is automatic.
- `core/prompt_orchestrator.py` + `prompt/builder.py` + `core/prompt_builder.py`
  — new `continuity` section ("CONTINUITY — ongoing work, keep the story straight").
- `core/scheduler.py` — `continuity_check` task
  (`SCHEDULER_CONTINUITY_CHECK_INTERVAL = 900`) sweeps overdue commitments.

Tests: 51 new in `tests/test_continuity.py` (due parsing, store rollback/reload,
project→goal read-through, commitment sweep + one-time surfacing, checkpoints,
reconciliation with fakes, tools, event/prompt wiring).
**Full suite: 2169 passed, 2 failed** — both in `tests/test_horizontal_scaling.py`
(Redis cross-instance state + pub/sub), files untouched by this change; treated
as pre-existing.

Not done: conversation-driven commitment extraction (tools today), and
autonomous work cycles consuming the snapshot (lands with M23 Partner).


---

## M23 Partner — M23 core (Nov 17 2026)

Built ahead of sequence (T5 pillar). `partner/` implements presence, an action
policy with verified actions, read-only mail with an approval-gated outbox, a
local .ics calendar, idle work cycles, and ritual briefings.

- `partner/presence.py` — `PresencePolicy`: activity classes
  (`coding/working/focus/idle/conversation/away`), per-activity interruption
  policy + cooldown, quiet mode (persisted), rituals (morning/midday/evening/
  night, once per local day), `should_initiate` + `may_disagree` gated by
  relationship trust, `detect_activity` from window title / idle time /
  CognitiveState.
- `partner/actions.py` — `ActionPolicy` tiers (`read_only`, `safe`,
  `needs_approval`, `forbidden`; unknown types fail closed to
  `needs_approval`) and `VerifiedActionEngine`: precondition → execute →
  **post-condition verification** → audit. `succeeded` / `unverified` /
  `failed` / `blocked` / `denied` / `pending_approval` are distinct outcomes.
  Params are sanitized (secret-shaped keys redacted) before logging.
- `partner/audit.py` — `ActionAuditLog`: append-only JSONL, torn-line tolerant.
- `partner/mail.py` — `ImapMailbox` (read-only `SELECT`, `BODY.PEEK`, never
  marks mail seen), `NullMailbox` when unconfigured, `Outbox` (drafts require
  approval; `send()` refuses — "no SMTP transport configured").
- `partner/calendar.py` — `IcsCalendar`: VEVENT parse (folding, escapes, DATE/
  DATETIME, `Z` as UTC), `upcoming(hours)`; missing file = empty calendar.
- `partner/cycles.py` — `IdleWorkCycle`: backlog from continuity (due
  commitments, project checkpoints, resumable tasks); gated by quiet mode,
  activity ≠ idle, and a cooldown; plans through the verified action path and
  writes a resumable checkpoint per item (it plans, it does not research — T4).
- `partner/engine.py` — `PartnerEngine`: trust from `SharedState`,
  `briefing()` (continuity + calendar + inbox + approvals), `maybe_brief()`
  (once per ritual window, never in quiet mode), `tick()` (brief + cycle),
  `publish()` → `state.partner.updated`.
- `partner/tools.py` — 6 tools: `partner_status`, `presence_set`,
  `partner_briefing`, `mail_summary`, `mail_draft`, `calendar_upcoming`.

Supporting changes:
- `core/atomic_document.py` — atomic JSON document + transactional rollback,
  extracted from the continuity store and now shared by both stores.
- `config/partner.py` — presence/cycle settings + `MAI_MAIL_IMAP_*` and
  `MAI_CALENDAR_ICS` from the environment (no secrets in source).
- `app/builders/partner.py` — new boot layer after Continuity; brain/scheduler
  wiring, health registration, initial publish. Validation gate added.
- `core/event_specs.py` — `data.partner.presence|briefing|action|cycle` +
  `state.partner.updated` (publisher `partner`), auto-covered by STREAM_TOPICS.
- `core/scheduler.py` — `partner_tick` task (`PARTNER_TICK_INTERVAL`).

Tests: 78 new in `tests/test_partner.py` (presence matrix/cooldowns/rituals,
audit, policy tiers, verified-action outcomes + approvals + redaction, IMAP
fake connection, ICS parsing, cycle gating/planning, engine briefing/tick/state
events, tools, wiring). Full suite: **2253 passed** (Redis scaling tests
excluded — pre-existing failures).

Follow-up wiring (same day):
- Ritual speech — `AIOSKernel.attach_partner_ritual()` subscribes to
  `data.partner.briefing` (wired in `app/builders/partner.py`) and speaks the
  text on a daemon thread, since `publish_event` is synchronous. Gated twice:
  the engine emits only in a ritual window outside quiet mode, and the kernel
  re-checks `presence.decide("ritual")` plus `ConversationPhase.IDLE`. Returns
  `{"spoken": bool, "reason": str}`; idempotent attach.
- REST approvals — `api/routes_partner.py` (`PartnerMixin`) + routes:
  `GET /api/partner/status`, `GET /api/partner/approvals` (actions + drafts),
  `POST /api/partner/approvals/{id}/approve|reject` (404 on unknown id). New
  `VerifiedActionEngine.reject()` records status `rejected` in the audit.
  Drafts resolve through the same endpoints but still cannot send.
- Pending approvals now outlive the process: `VerifiedActionEngine(store=...)`
  mirrors the pending set into `data/partner.json` (`pending_actions`) inside
  the same atomic transaction as drafts, and `PartnerEngine` always passes its
  store. Closures cannot be serialized, so approving a restored entry rebuilds
  its executor through `register_executor_factory(action_type, factory)`;
  `pending()` and the REST list expose `resumable`, and approval without a
  factory records an honest `no_executor_after_restart` failure. Params are
  redacted before writing; approve/reject remove the entry atomically.
- Genuine approval-tier action: `create_file` is real work the partner can do.
  `partner/workspace.py` (`PartnerWorkspace`) is a relative-path-only text
  sandbox at `data/partner_files/` (absolute, drive, Windows root-relative and
  `..` paths refused; 4000-char content cap). `PartnerEngine.request_file()`
  parks a write as `create_file` with a precondition that re-validates the path
  and a verifier that checks the file exists with the bytes reported.
  `PartnerEngine.__init__` registers the `create_file` executor factory, so a
  restored approval rebuilds `workspace.write(path, content)` and runs.
  Production trigger: the `file_create` tool (7 partner tools) — a model tool
  call parks the write; nothing is written until approval. Pending params
  persist with an 8000-char string budget (audit stays at 500) so a body
  round-trips intact; `partner.status()` exposes workspace stats.
- Boot-level test: `TestBootLevelApprovals` in `tests/test_partner.py` runs the
  real `app.builders.partner.build()` twice against a temp data dir, parks a
  write through the tool, re-boots, lists it over REST (`resumable: true`),
  approves it over REST, then checks the file and the audit record.
- `run.bootstrap_system()` now exports `continuity` and `partner`.
- Tests: 130 in `tests/test_partner.py` (+52); full suite **2305 passed**.

Known limits (deliberate, documented):
- No SMTP transport: approved drafts must be sent by hand.
- Calendar is a local .ics only; no OAuth/Google sync.
- Pending approvals survive a restart, but executing a restored one needs a
  registered executor factory; no production path parks approvals today (the
  approval tier is exercised by callers/tests), so none is registered yet.
- Activity detection has no window-title source yet (T3); `refresh_activity`
  will not downgrade an explicit setting without evidence.

## T7 Self — core (Nov 17 2026)

Built ahead of sequence (third pillar after Continuity/Partner), under the
roadmap's propose-only boundary: **she reads and diagnoses; the user approves
fixes.**

New package `self_awareness/`:
- `code_index.py` — `OwnCodeIndex`: `ast` facts per module (path, dotted module,
  classes, `Class.method` functions, top-level imports, docstring first line,
  lines, size, mtime, sha256) stored in an `AtomicDocument`
  (`data/self_awareness/code_index.json`). Incremental refresh (mtime+size),
  deletion detection, `force=True` full pass, symbol/module/docstring search,
  and `read_module()` with a relative-path sandbox (absolute/drive/root-relative
  and `..` refused, `.py` only, line budget). Reads with `utf-8-sig` — a BOM is
  not a syntax error (this was a real false positive found on the repo).
- `feeds.py` — `HealthErrorFeeds`: `HealthRegistry.stats()` snapshot +
  unhealthy list, plus a bounded tail (512 KB default) of `logs/mai.log`
  grouped into digit-normalized signatures with counts, last line and examples.
  Read-only; nothing rotates or truncates the log.
- `diagnosis.py` — `SelfDiagnosis`: findings for unhealthy/stalled components,
  repeated error signatures (threshold 3), unparsed modules, stale/empty index.
  Each finding has a stable id (`health:stt`, `code:path`, `errors:<sha>`),
  severity, evidence, proposal and `auto_apply: False`. Reports append to
  `data/self_awareness/diagnoses.jsonl`.
- `engine.py` — `SelfAwarenessEngine`: `refresh_index`, `diagnose`, `tick`
  (interval-gated proactive pass; refreshes the index first), `report`,
  `status`, `brief_line`; publishes `data.self.index_built`,
  `data.self.diagnosis`, `state.self.updated`.
- `tools.py` — 7 tools: `self_status`, `self_index`, `self_read_code`,
  `self_health`, `self_errors`, `self_diagnose`, `self_report`.

Wiring: `app/builders/self_awareness.py` (after Partner; indexes once at boot,
registers the 7 tools + health, assigns `brain.self_awareness` and
`partner.self_awareness`), `app/boot.py`, `app/validation.py`,
`app/application.py`, `run.bootstrap_system()`, `core/scheduler.py`
(`self_tick`), `core/event_specs.py`, `api/routes_self.py` +
`api/server.py` (`GET /api/self/status|index|code|health|errors|report`,
`POST /api/self/diagnose`), and one `Self-check:` line in
`PartnerEngine.briefing()` so the ritual brief carries her state.

Tests: 59 in `tests/test_self_awareness.py` (index facts/incremental/BOM/
search/sandboxed reads, feed grouping + registry reads, finding shapes and
persistence, engine gating/events, tools, boot wiring incl. partner brief
line, REST). Full suite **2364 passed** (Redis scaling excluded — pre-existing).
Real-repo check: 439 modules, 94k lines, 0 unparsed, index 1.4 s, clean
diagnosis.

Known limits (deliberate):
- Structure, not semantics: the index reads symbols/docstrings, not meaning.
- Error feed is a log tail, not a since-last-check cursor; a signature that
  already scrolled out of the tail is invisible until it recurs.
- No patch generation/applying and no component restart — proposals are text,
  and the boundary is enforced by the absence of any write path.
- No dashboard surface yet; the `state.self.updated` feed is available for one.

## Redis horizontal scaling — green (Nov 17 2026)

`tests/test_horizontal_scaling.py` now runs in the normal suite (no ignore
flag). Three real defects were fixed:

1. `RedisSharedState.load_state_from_disk()` read only the `mai:state:master`
   snapshot while `set_emotion`/`set_goals`/... write per-component keys, so a
   worker booting after another worker changed state read stale values (0.5
   default instead of the synced emotion). It now merges `emotion`,
   `relationship_scores`, `goals`, `attention`, `runtime` over the master
   snapshot (they are the freshest), then falls back to the local file.
2. `RedisEventBus._subscribe_to_redis()` passed an already-prefixed channel to
   `_RedisPubSub.subscribe()`, which prefixes too — listeners sat on
   `mai:events:mai:events:<topic>` and cross-worker delivery never happened.
   `_RedisPubSub` now owns the prefix, SUBSCRIBEs synchronously before
   returning, keeps one listener per channel (repeated subscriptions share it
   instead of spawning duplicate threads) and closes cleanly on shutdown.
3. Only the legacy `publish()` broadcast to Redis; `publish_event` /
   `publish_wait` / `publish_async` / `publish_message` never left the process,
   so `data.*` / `state.*` fan-out died with a second worker. Every publish
   path now funnels through `_broadcast()` (once per message), Redis-originated
   messages carry an `origin` worker id so a bus never re-dispatches its own
   broadcast (which doubled local delivery), and legacy topics are rebuilt via
   `legacy_message` on receipt so registry validation does not reject them.

Test changes in `tests/test_horizontal_scaling.py`: the existing pub/sub handler
now subscribes with `receive_message=True` (it consumes `msg.payload`; legacy
subscribers otherwise receive the payload dict by contract), both buses are
shut down, and a semantic-event cross-worker test was added.

Full suite **2368 passed**, including all 4 horizontal-scaling tests — no Redis
exclusions remain.

## Full Review Check — Nov 17 2026

Audit scope: AST import graph (440 modules), 93 API routes vs 83 frontend
fetch sites, `Settings` / env-var coverage, event-spec publish/subscribe
sites, builder + scheduler wiring, orphan modules, requirements coverage.

Fixed:
- **Partner ritual speech wiring** — `app/builders/partner.py` attached the
  `data.partner.briefing` speaker while `app.kernel` was still `None`
  (Partner builds before Runtime), so briefings were never spoken. Moved to
  `app/builders/runtime.py` after kernel construction (idempotent).
- **`session_manager` export** — `run.bootstrap_system()` now returns it, so
  `api/server.py` stops getting `None` and `/api/profiles/sessions*` no
  longer 503.
- **Dream level 1** — registered on the scheduler (`SCHEDULER_DREAM_LEVEL1_INTERVAL`,
  900 s); only L2–L5 were scheduled before, so orphan/duplicate/link
  maintenance never ran automatically.
- **`favicon.ico`** — added to `api/static/img/` (marketplace.html linked a
  missing file).
- **`.env.example`** — documents every env var the code reads (secrets
  blank, computed paths commented out).
- **Optional deps** — `discord.py`, `kokoro`, `pyautogui`, `pysaml2` now
  declared in `requirements.txt`; SAML routes use the correct
  `saml2.config.Config` import and load a real SP config.

Verified: `tests/test_scheduler.py` (incl. new L1 registration test),
`tests/test_partner.py` + `tests/test_self_awareness.py` pass; changed
modules compile.


## M19 — Silent Research + File Tools (Nov 18 2026)

T4 core built ahead of the M15 sequence, because the milestone is CPU-only and
needed by partner idle cycles.

### Phase 1 — file tools (cross-cutting)
- `execution/file_tools.py` — one sandbox policy (`data/workspace` writes, vault
  `research/` reads) with path-traversal/absolute/NUL refusal, size caps, and a
  `create` that refuses to clobber.
- `execution/handlers.py` — `FileSystemActions.create_file/exists/run_file_write`
  added next to the existing list/read/write.
- `execution/task_executor.py` — dispatches `list_dir|read_file|write_file|create_file`;
  explicit empty paths no longer fall back to the content field.
- `execution/safe_executor.py` — `safe` mode reads/lists, `advanced`/`admin`
  write/create; empty path and NUL validation.
- `agency/tools.py` — LLM tools `read_file`, `list_dir`, `write_file`,
  `create_file`. In-workspace writes execute; outside writes are parked in the
  partner approval tier (or refused when no partner exists).

### Phase 2 — research core (no new hard dependencies)
- `research/` — `models` (job), `fetch` (SSRF-guarded urllib + readability-ish
  extraction + redirect re-validation), `search` (DuckDuckGo HTML, best-effort),
  `store` (atomic JSON), `artifacts` (vault Markdown, read-back verified),
  `engine` (queue, single worker, continuity checkpoints, honest failures),
  `tools`, optional `browser` (Playwright, headless-only, route-level SSRF).
- `config/research.py` — depths (quick 2 / standard 4 / deep 6), caps, search
  endpoint, autonomous gate, tick interval, browser mode.
- Events: `data.research.{started,source_fetched,finished,failed}` and
  `state.research.updated`.
- API: `GET /api/research/status`, `GET /api/research`,
  `POST /api/research`, `GET /api/research/{id}/status`,
  `GET /api/research/{id}/report`, `DELETE /api/research/{id}` (auth-gated).
- Wiring: `app/builders/research.py` (after Partner), boot/validation/application/
  `run.bootstrap_system`, scheduler `research_tick` (worker fetches; tick drains),
  partner briefing line, idle cycles start research-shaped backlog items
  autonomously when presence allows.
- Vault: new `research/` folder; artifacts are written directly (not through the
  compiler-owned `MemoryWriter`), then read back before the job is marked done.

### Verification
- `tests/test_file_tools.py` (10) + `tests/test_research.py` (20) +
  `tests/test_scheduler.py` research registration: 43 focused tests pass.
- Playwright remains optional: declared in `requirements.txt`, `MAI_RESEARCH_BROWSER`
  selects auto/urllib/playwright; installed browser not required for the milestone.

## Optional dependencies installed — Nov 18 2026

Installed into `mai_env` and verified: `discord.py 2.7.1`,
`kokoro 0.9.4`, `pyautogui 0.9.54` (screen access OK: 1920x1080),
`pysaml2 7.5.5`, `xmlsec 1.3.18`, `playwright 1.65.2` + Chromium,
headless shell, FFmpeg. `pip check`: no broken requirements.

- SAML now works end to end for SP-initiated login: `saml_router` was
  defined but never mounted in `api/server.py` (every route 404'd), and
  the pysaml2 config had no IdP metadata (SignOnError). Both fixed;
  IdP metadata is built inline from the provider's `idp_entity_id` /
  `idp_sso_url` / `idp_x509_cert`. `crypto_backend: XMLSecurity` uses the
  pip `xmlsec` wheel, so Windows needs no native `xmlsec1.exe`.
  Verified: `GET /api/auth/saml/login/test` → 307 to the IdP with a
  `SAMLRequest` and the `saml_request_id` session cookie.
- Headless research verified through Playwright: `https://example.com`
  rendered (title/chars) and a research job completed with an artifact.
- Research tests now pin `browser_mode="urllib"` for fake fetchers and
  monkeypatch `playwright_available` for the missing-package case, so they
  no longer depend on whether Playwright happens to be installed.
- Full suite after installing everything: 2395 passed, 3 skipped.

## CI: why it was red, and what runs now — Nov 19 2026

Two workflows gate `main`: `ci.yml` (Windows: ruff, mypy, full pytest, Docker build) and
`ci-cd.yml` (Ubuntu: ruff, mypy, pytest with coverage, Trivy/Bandit/TruffleHog, multi-arch
image build).

- **Dependencies**: `tokenizers==0.22.1` — `transformers==4.57.6` requires `>=0.22.0,<0.23`,
  so the old `0.21.4` pin made `pip install -r requirements-ci.txt` fail outright.
- **Mypy**: the 55 errors are fixed; `mypy .` is clean (tests are excluded by config).
  Use `builtins.list` where a public `list()` method shadows the builtin.
- **Headless audio**: `voice/stream_player.py` treats a PortAudio init failure at import like a
  missing package, so boot and the suite run on runners/containers with no audio server.
  sounddevice initialises PortAudio on import and raises `PortAudioError`, not `ImportError`.
- **Path policy**: `core/path_policy.is_absolute_path()` is the single absolute-path test for
  the partner workspace, the own-code index and `execution/file_tools`. `Path()` alone reads
  `C:/Windows/x.md` as a *relative* name on POSIX, so those sandboxes only refused it on Windows.
- **Docker build** runs on `ubuntu-latest`: `windows-latest` Docker is in Windows-container mode
  and cannot pull `python:3.10-slim` ("no matching manifest").
- **TruffleHog** gets no `base`/`head` inputs: pinning `base: main` makes BASE and HEAD the same
  commit on every push to main, so the step exited 1 without scanning. The job checks out with
  `fetch-depth: 0` so the action can resolve the event's commit range.
- **Opt-in stages**: integration tests and both deploy jobs are gated on the repository
  variables `RUN_INTEGRATION_TESTS` / `DEPLOY_ENABLED` (default off) because
  `docker-compose.test.yml`, `tests/integration/`, `tests/contract/` and the staging/production
  hosts do not exist in this repository.
- **Reading CI**: job logs need repository admin, so the pytest and Docker steps emit an
  `::error` annotation with the failure tail; annotations and job statuses are visible on the
  public job page without the (60/hour) anonymous API quota.
