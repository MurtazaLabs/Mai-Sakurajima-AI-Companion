# 05 — Knowledge, Graph & Vault

> Source docs `SUBSYSTEM_DOCUMENTATION/knowledge.md` / `FILE_REFERENCE.md` were merged and deleted; this page is the surviving reference. Capability status: [[00-Overview/CURRENT_STATE]].

---

## Package Stats

`knowledge/` — 29 files, 5,853 lines.

## Mission

Maintain the durable world-knowledge layer: entity graph, document knowledge base, beliefs, and the **Obsidian vault** (human-readable character memory).

## Graph Architecture (Three Layers — Known Debt)

| Layer | File | Role |
|-------|------|------|
| 1 | `graph.py` — `KnowledgeGraph` | atomic in-memory entity/relation store; `query()` O(relations×depth) |
| 2 | `brain_graph.py` — `BrainGraph` | facade over 7+ typed node types (person, place, project, technology, event, skill, media, organization, relationship, interest, character); bridges all stores |
| 3 | `cognitive_graph.py` — `CognitiveGraph` | cognitive dimension; `import_beliefs()` |

⚠️ Three-layer overlap — collapse to 2 layers proposed (debt D-3).

### Junk Detection

- `GraphManager` refuses `unknown` entities with confidence < 0.25 (fallback extractor tier).
- `VaultJanitor` sweeps junk entities + orphan notes (dry-run default; `scripts/sweep_graph_junk.py --apply` commits).

## Belief Engine

- `belief_engine.py` — beliefs with confidence, source, updates.
- ✅ **Single source of truth (D-1 resolved Aug 12 2026):** `BeliefEngine._beliefs` is the only belief store; `BrainGraph` belief operations delegate to it (a wired `BeliefEngine` is required, legacy graph fallbacks removed). `CognitiveGraph.import_beliefs()` reads from it.

## Retrieval — `AdvancedRetriever`

Cascade + **parallel** (4 sources concurrent): vector search (MMR), beliefs, KG traversal, attention-weighted recency. Early-exit cancels remaining futures.

## Vault Writing — Single-Writer Principle

| Writer | Owns | Notes |
|--------|------|-------|
| `StateDumper` / `VaultCompiler` | compiled folders: identity, preferences, relationship, knowledge, projects, people, places, dreams, statistics | structured facts; `first_met` from vault, real turn counts |
| `MemoryWriter` | raw growth folders: conversation, archive, important | per-turn records; cross-day dedup; reinforcement counters |

- Raw writes targeting compiler-owned folders are **redirected** to `conversation/` (dual-writer clobber fix, Aug 2026).
- Wiki links emitted only when the target note exists (`_link_target_exists`).
- Cross-day dedup via `_dedup_hit_anywhere()`; duplicates bump `reinforcement_count` in place.
- `obsidian_writer.py` is the orchestrating facade (GraphExporter, StateDumper, MemoryWriter).

## Knowledge Base (Documents)

| Component | File | Role |
|-----------|------|------|
| `TextChunker` | `chunker.py` | character/word chunking |
| `DocumentStore` | `document_store.py` | chunk metadata |
| `Indexer` | `indexer.py` | embedding + index (RLock on counter) |
| `KnowledgeBaseBuilder` | `builder.py` | build KB from files/directories |
| `DirectoryWatcher` | `watcher.py` | background auto-indexing (60s interval) |

## Vault Integrity Tooling

`vault_schema.py` (schema), `vault_migrator.py` (migrations), `vault_post_processor.py`, `vault_janitor.py` (junk sweep), `link_integrity.py` (wiki-link checks), `vault_logger.py`.

## Events

- Publishes `state.knowledge.updated` after graph/doc updates.

## Known Issues

- Three-layer graph abstraction (D-3); `memory/` imports `knowledge/` (D-2 — 3 lazy imports, 2 files). ~~Triple belief storage~~ resolved Aug 12 2026 (BrainGraph delegates to BeliefEngine).

---

## Wiki Links

**Previous:** [[04-Memory Subsystem]]  
**Next:** [[06-Agency Reasoning LLM & Execution]] — agency, reasoning, LLM, execution  
**Related:** [[01-Architecture/09-Events & Data Flow]] — knowledge ingest data path • [[02-Subsystems/Vault Compilation]] — vault detail • [[03-Features/Native OS Bridge Architecture]] — daemon integration