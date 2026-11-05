# 06 — Agency, Reasoning, LLM & Execution

> Digest of `SUBSYSTEM_DOCUMENTATION/core.md` (Agency/Reasoning/LLM/Execution section). Full: [[CLASS_REFERENCE]] §6.

---

## Agency — Autonomous Capability Layer

Packages: `agency/` 12 files, 2,499 lines.

### Tools (`agency/tools.py` + `registry.py`)

- 12+ built-in tools (search, calculate, open_url, run_command, …).
- `ToolRegistry.dispatch()` — RLock-guarded.
- `_safe_execute()` character whitelist (blocks shell metacharacters; URL chars supported).

### Agent (`agency/agent.py`)

- Multi-step tool loop with `_plan_next()`.
- Analysis tasks get **one synthesis pass** via the `reason` tool before `complete`.
- **Honest failure** — run ends `success=False` when every step failed (no false success).
- `registry.call` wrapped in try/except; step tracking for observability.

### Goals (`agency/goals.py`)

- `GoalManager`: create, progress, subtasks, auto-advance, completion reflection.
- Over `_max_active` → lowest-priority goal paused (min→max fix).
- Goals stored in BrainGraph; `check_goals(beliefs)`.

### Dreaming & Evolution

- `DreamEngine` — background dream cycles (TOCTOU fixed); `DreamTasks`, `DreamReport`. Level-5 task `experience_reflection` (M6) — LLM reflection over significant unreflected experiences; knowledge entry per revisit; `DreamReport.experiences_reflected` metric.
- `PersonalityEvolution` — long-term drift. `ProceduralMemory` — procedural skills.
- `PreferenceEvolution` (`preference_evolution.py`) — evidence windows, N≥3 threshold, weekly cadence, direction flip via effective-list (canon + overlay), decision trail, `revert()`, `overlay_map()`, publishes `PREFERENCE_EVOLVED`.
- `WorldModel` — 11 entity categories, bridges to BrainGraph.

## Reasoning (5 files, 900 lines)

| Component | File | Role |
|-----------|------|------|
| `ReasoningEngine` | `engine.py` | orchestrates reasoning passes |
| `ThoughtJournal` | `journal.py` | append-only JSONL thought log (O(1) per store) |
| `ReflectionEngine` | `reflection.py` | cadence-gated daily/weekly/monthly reflections (`due()`; `force=True` bypasses) |
| `LearningEngine` | `learning.py` | behavior adjustment from outcomes |
| `ThoughtPacket` | `thought_packet.py` | structured thought envelope; leak-strip guard (M11) |

## LLM (4 files, 1,262 lines)

| Component | File | Role |
|-----------|------|------|
| `LLMManager` | `manager.py` | provider preference via `LLM_PROVIDER` (`openrouter` default, `ollama` = local-first ordering); probe TTL 15s, decision snapshotted under lock with network I/O outside; mid-stream failover restarts on next provider **with history**; final generate fallback passes history too |
| `OpenRouterProvider` | `providers/openrouter.py` | bounded retry budget (45s default); permanent HTTP status codes (400/401/403/404/422) break the per-model attempt loop immediately; default model `openrouter/free` with sanitized failover list (drop None/empty/dup) |
| `OllamaProvider` | `providers/ollama.py` | local inference; top-level `think: false` in every chat payload (single choke point, all 4 paths) |

Config: `LLM_PROVIDER` (env, Oct 9), `OPENROUTER_DEFAULT_MODEL` (default `openrouter/free`).

## Execution (3 files, 850 lines)

| Component | File | Role |
|-----------|------|------|
| `SafeExecutor` | `safe_executor.py` | validates actions; legacy `url`/`command` key fallback |
| `System/Command/Desktop/Clipboard/FileSystem Actions` | `handlers.py` | sandboxed primitives |
| `TaskExecutor` | `task_executor.py` | task runner |

Security posture:
- App whitelist (20+ apps) in `SystemActions.open_app()`.
- Keystroke filter blocks destructive hotkeys (Alt+F4 / Ctrl+W).
- FS + clipboard sandbox `[ROOT_DIR, OBSIDIAN_VAULT]` **active everywhere** (not daemon-only).

## Known Issues

Providers duck-typed (no ABC); `_result()` duplicated across 3 handler classes. ~~`generate_with_tools()` dead passthrough~~ — resolved claim was stale: it is **live** (`core/brain.py`, `core/brain_routing.py` route the envelope path through it).

---

## Wiki Links

**Previous:** [[05-Knowledge Graph & Vault]]  
**Next:** [[07-Voice Subsystem]] — the voice pipeline  
**Related:** [[01-Architecture/09-Events & Data Flow]] — agent/goal/dream events • [[02-Subsystems/Tool System]] — tools detail • [[03-Features/Discord Integration Plan]] — Discord bot uses tools