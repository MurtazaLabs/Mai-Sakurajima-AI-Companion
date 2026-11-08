# 04 — Memory Subsystem

> Source doc `SUBSYSTEM_DOCUMENTATION/memory.md` was merged and deleted; this page is the surviving reference. Capability status: [[00-Overview/CURRENT_STATE]].

---

## Package Stats

`memory/` — 28 files, 7,378 lines.

## Mission

Persist, rank, retrieve, and consolidate user + world memories across sessions — the long-term companion memory. Also hosts the **experience layer** (M6): emotionally charged turns become `EmotionExperience` records that the dreaming cycle reflects on.

## Storage Backends

| Store | Purpose | Owner |
|-------|---------|-------|
| SQLite (`memory/mai.db`) | durable state DB | `core/state/database.py` |
| ChromaDB (`vector_memory/`) | vector index (optional) | `VectorStore` |
| JSON memory objects | fallback / export | `VectorStore` |
| Embedding cache | in-process LRU keyed by model fingerprint | `EmbeddingService` |
| Vault raw records | human-readable archive | `MemoryWriter` ([[05-Knowledge Graph & Vault]]) |

## Store Path

```
turn text → FastExtractor → MemoryPipeline.store (single unified entry)
  → MemoryIntelligence.process() (extract + score + tag + emotion)
  → WriteJournal batch | VectorStore.add (embed + persist)
  → KnowledgeGraph/BrainGraph entities
  → MemoryWriter vault (raw record + reinforcement counters)
  → publish state.memory.updated
```

## Retrieve Path

`MemoryCoordinator` ([[03-Core Brain Kernel & State]]) → `AdvancedRetriever.retrieve()` ([[05-Knowledge Graph & Vault]]) — **4 sources in parallel** via ThreadPoolExecutor: vector search (MMR diversify, multi-factor ranking), belief engine, knowledge-graph traversal, attention-weighted recency. Guards: `<3` word queries skip heavy retrieval; `memory_type` filter enforced to `VectorStore.search()`; early-exit cancels remaining futures.

## Lifecycle

- `MemoryLifecycle` — new → consolidated → archived → forgotten.
- `ConsolidationEngine` — duplicate merge + decay; `decay.consolidate(store_fn=...)` persists orphaned `MemoryObject` nodes.
- `hierarchy.py` — cognitive-science hierarchy (sensory/episodic/autobiographical/etc.).

## Key Classes

| Class | File | Role |
|-------|------|------|
| `MemoryObject` | `schema.py` | canonical schema |
| `MemoryPipeline` | `pipeline.py` | unified store pipeline (journal + sync paths) |
| `MemoryManager` | `manager.py` | facade |
| `MemoryIntelligence` | `intelligence.py` | processing/consolidation |
| `VectorStore` | `vector_store.py` | vector + metadata store (RLock on all 9 methods; `SchemaMigrator`) |
| `EmbeddingService` | `embedding_service.py` | embedding + cache (RLock) |
| `FastExtractor` | `extractor.py` | memory extraction |
| `ConsolidationEngine` | `consolidation.py` | merge/decay |
| `MemoryLifecycle` | `lifecycle.py` | lifecycle machine |
| `MemoryHierarchy` | `hierarchy.py` | cognitive hierarchy |
| `EmotionExperience` | `experience.py` | experience record (event, meaning, emotion, lessons, growth, significance) |
| `ExperienceStore` | `experience.py` | JSONL append-only, RLock, md5 replay dedup, `mark_reflected()` |

## Experience Layer (M6/M8)

- Charged turns (emotion intensity ≥ 0.6) recorded at `_store_impl()` — one JSONL append.
- `MemoryObject.emotion_experience` field carries the link (additive, backward compatible).
- Replay dedup by md5 event fingerprint — identical text recorded once (`stats()["deduped"]`).
- Consumers: dreaming `experience_reflection` task (fills meaning/lessons/growth), `MemoryCoordinator.experience_context()` (Dice-relevance gate ≥ 0.10, M12 — injects reflected experiences into the prompt only when relevant).

## Events

- Publishes `state.memory.updated` after stores.
- Memory updates broadcast via EventBus to stream_manager / ws_bridge / notifier.

## Thread Safety

- `VectorStore`: RLock on all 9 public methods.
- `EmbeddingService._cache`: RLock.
- Legacy `Memory` uses RLock (verified Oct 2026).
- ⚠️ `memory/` imports from `knowledge/` — known layer breach (debt D-2; narrowed to 3 lazy in-method imports across 2 files).

## Known Issues (Register Refs)

- `MemoryObject.lock` dead field; unused `embeddings` field; `MemoryNode` duplicates `MemoryObject` fields; `_text_overlap` duplicated (vector_store + consolidation).
- Embedding cache lacks model fingerprinting — roadmap Item 4.

---

## Wiki Links

**Previous:** [[03-Core Brain Kernel & State]]  
**Next:** [[05-Knowledge Graph & Vault]] — knowledge graph, beliefs, vault  
**Related:** [[01-Architecture/09-Events & Data Flow]] — memory store/retrieve data paths • [[02-Subsystems/Memory Pipeline]] — detailed pipeline docs • [[03-Features/Native OS Bridge Architecture]] — daemon integration