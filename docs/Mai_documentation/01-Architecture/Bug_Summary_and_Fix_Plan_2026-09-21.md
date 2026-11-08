# Bug Summary & Fix Plan — Mai AI v2.0.0
*Generated from Full Ecosystem Audit (2026-09-21)*

> **Historical record — kept as-is.** The bugs and counts below describe the
> codebase on 2026-09-21 and are **not** current. Companion documents it links
> (`Full_Ecosystem_Audit_2026-09-21`, `Technical Debt Heatmap`,
> `Security Review 2026-09`, `Brain Architecture`, `Database Migration Plan`)
> were consolidated away during vault cleanup; only this page survives.
> For present-day status see [[00-Overview/CURRENT_STATE]] and
> [[01-Architecture/10-Status & Debt]].

---

## 🔴 CRITICAL BLOCKERS (Fix This Week)

| # | Bug | Location | Fix |
|---|-----|----------|-----|
| 1 | **Prompt injection in `think_stream()`** — missing `_delimit_user_input()` | `core/brain.py:887` | Add `user_input = self._delimit_user_input(user_input)` before `prompt_orchestrator.build()` |
| 2 | **Deadlock: Emotion._sync() lock ordering** | `core/emotion.py:380` vs `core/brain.py:489` | Standardize: always acquire `SharedState.lock` FIRST, then `Emotion.lock` |
| 3 | **SQLite failure = total crash** (no in-memory fallback) | `core/state/shared_state.py` | Add in-memory fallback dict for SharedState/ProfileStore; sync when DB recovers |
| 4 | **Shell command injection** via `run_command` in `execute_action` | `agency/tools.py:135`, `execution/handlers.py` | Remove `run_command` from `_EXECUTE_ALLOWED_TYPES` OR strict command allowlist |
| 5 | **No similarity threshold** in retriever → noise in context | `knowledge/retriever.py`, `memory/vector_store.py` | Add `MEMORY_SIMILARITY_THRESHOLD` config; pass to `vector_store.search()` |

---

## 🟠 HIGH PRIORITY (Fix This Sprint)

| # | Bug | Location | Fix |
|---|-----|----------|-----|
| 6 | `think_stream()` bypasses full prompt context | `core/brain.py:887` | Match `think()` signature: pass `memory_data`, `identity_data`, `monologue=True` |
| 7 | `execute_action` misleading error message | `agency/tools.py:135` | Fix error message to match actual regex; use per-action-type allowlist |
| 8 | ChromaDB EphemeralClient — full re-embed on boot | `memory/vector_store.py:55` | Switch to `PersistentClient` + incremental vault sync |
| 9 | ThreadPoolExecutor created per `retrieve()` call | `knowledge/retriever.py:152` | Reuse single executor instance; or make embedding async |
| 10 | Bare `except:` / `except Exception: pass` swallow errors | Multiple files | Replace with specific exceptions + logging |
| 11 | No startup config validation — fail fast | `run.py`, `app/config_loader.py` | Add `validate_config()` in `bootstrap_system()` |
| 12 | `think_stream()` tool call limit not enforced | `core/brain.py:847` | Add counter in stream wrapper; break at `MAX_TOOL_CALLS_PER_TURN` |

---

## 🟡 MEDIUM PRIORITY (30 Days)

| # | Bug | Location | Fix |
|---|-----|----------|-----|
| 13 | SQLite → PostgreSQL migration + Alembic | `core/state/shared_state.py` | Add migrations, connection pool, read replicas |
| 14 | Query cache in AdvancedRetriever | `knowledge/retriever.py` | Per-turn TTL cache for embeddings + search results |
| 15 | Semantic chunking in TextChunker | `knowledge/chunker.py` | Embedding similarity boundaries instead of char count |
| 16 | Cross-encoder re-ranking | `knowledge/retriever.py` | Optional ms-marco-MiniLM re-rank for top-20 |
| 17 | Intent classifier to skip phatic retrieval | `core/brain_memory.py:86` | Keyword/tiny-LLM classifier for "hello", "thanks" |
| 18 | Semantic dedup in VectorStore | `memory/vector_store.py:177` | Search similarity > 0.9 before add; reinforce instead |
| 19 | Supersession metadata for conflicting memories | `memory/vector_store.py`, `knowledge/belief_engine.py` | Add `supersedes` field; mark deprecated on conflict |
| 20 | Tool result injection unmarked as untrusted | `core/brain.py:357` | Wrap in `[UNTRUSTED_TOOL]...[/UNTRUSTED_TOOL]` |
| 21 | API key leakage in exception logs | `llm/manager.py:127` | Redact `sk-[a-zA-Z0-9]{32,}` before logging |
| 22 | Multi-user isolation at storage layer | `memory/vector_store.py:181` | Add `user_id` to metadata; enforce at write time |

---

## 🟢 LONG-TERM (90 Days)

| # | Initiative | Description |
|---|------------|-------------|
| 23 | **Brain Decomposition** | Extract PromptCoordinator, ToolCoordinator, AgentCoordinator, MemoryCoordinator → BrainFacade <300 lines |
| 24 | **Horizontal Scaling** | Redis for SharedState/EventBus; stateless Brain workers; PostgreSQL read replicas |
| 24 | Multi-tenancy | User-scoped retrieval at storage layer; ProfileStore isolation; per-user vault namespaces |
| 24 | Enterprise Auth | OIDC/SAML, JWT rotation, audit logging, RBAC |
| 24 | Observability Stack | Prometheus metrics, Grafana dashboards, OpenTelemetry tracing |
| 24 | CI/CD Hardening | Blue-green deploy, health verify, automated rollback, chaos engineering |
| 24 | Model Lifecycle | Versioning, fingerprinting, gradual rollout, automated rollback |

---

## Phase Plan

### Phase 1: Security & Reliability Sprint (Week 1-2)
**Goal**: Zero critical blockers; system survives DB/LLM failures
- [x] Fix 1-5 (Critical Blockers)
- [x] Fix 6-12 (High Priority)
- [x] Add integration tests for each fix

### Phase 2: Database & Data Quality Sprint (Week 3-4)
**Goal**: Production-grade data layer; no silent corruption
- [x] Fix 13-14 (Database + Retrieval)
- [x] Fix 15-16 (Chunking + Re-ranking)
- [x] Fix 17-19 (Memory Quality)
- [x] Add migration system (Alembic) + connection pool

### Phase 3: Brain Decomposition & Scalability (Week 5-7)
**Goal**: Maintainable architecture; horizontal scaling ready
- [x] Fix 23 (Brain Decomposition)
- [x] Fix 24 (Horizontal Scaling)
- [x] Extract coordinators from Brain
- [x] Redis for SharedState/EventBus

### Phase 4: Enterprise Hardening (Week 8-10)
**Goal**: Enterprise-ready; observable; auditable
- [x] Fix 24-28 (Enterprise features)
- [x] Observability stack (Prometheus/Grafana/OpenTelemetry)
- [x] CI/CD hardening (blue-green, chaos)
- [x] Load testing + chaos engineering

---

## Tracking

| Phase | Status | Target Date |
|-------|--------|-------------|
| Phase 1 | 🔴 Not Started | 2026-09-28 |
| Phase 2 | 🔴 Not Started | 2026-10-05 |
| Phase 3 | 🔴 Not Started | 2026-10-19 |
| Phase 4 | 🔴 Not Started | 2026-11-02 |

---

## Related Docs
- [[Full_Ecosystem_Audit_2026-09-21]]
- [[Technical Debt Heatmap]]
- [[Security Review 2026-09]]
- [[Database Migration Plan]]
- [[Brain Architecture]]

---
*Generated by Mai AI Systems Auditor*