# Memory Pipeline Reference

> Complete reference for the memory storage and retrieval pipeline — `memory/pipeline.py`, `memory/manager.py`, `memory/intelligence.py`, `memory/vector_store.py`, `memory/embedding_service.py`, `memory/experience.py`.

---

## Overview

The memory pipeline is the **unified entry point** for all memory storage. It replaced the legacy dual-path (journal + sync) with a single `MemoryPipeline.store()` that handles both paths internally.

**Architecture:** [[01-Architecture/04-Memory Subsystem]]

---

## Store Path (Write)

```
turn text → FastExtractor → MemoryPipeline.store()
  → MemoryIntelligence.process() (extract + score + tag + emotion)
  → WriteJournal batch | VectorStore.add (embed + persist)
  → KnowledgeGraph/BrainGraph entities
  → MemoryWriter vault (raw record + reinforcement counters)
  → publish state.memory.updated
```

### Key Classes

| Class | File | Role |
|-------|------|------|
| `MemoryPipeline` | `pipeline.py` | unified store pipeline |
| `MemoryIntelligence` | `intelligence.py` | processing/consolidation |
| `FastExtractor` | `extractor.py` | memory extraction from text |
| `WriteJournal` | `core/write_journal.py` | async batched writes |
| `VectorStore` | `vector_store.py` | vector + metadata store (RLock on all 9 methods) |
| `EmbeddingService` | `embedding_service.py` | embeddings + cache (RLock) |
| `MemoryWriter` | `knowledge/memory_writer.py` | vault raw records |

### FastExtractor (`memory/extractor.py`)

Extracts structured `MemoryObject` from raw text:
- Entities (people, places, projects, etc.)
- Topics / keywords
- Emotion tags (via `EmotionAnalyzer`)
- Importance score (0–1)
- Memory type classification

### MemoryIntelligence (`memory/intelligence.py`)

Post-extraction processing:
- Deduplication (semantic similarity)
- Importance scoring (multi-factor)
- Tagging (topic, emotion, entity)
- Consolidation triggers

### WriteJournal (`core/write_journal.py`)

Async batched write path for hot-path performance:
- Buffers writes in memory
- Flushes on timer (default 5s) or batch size (default 100)
- Flushes on shutdown
- Prevents blocking the conversation turn

### VectorStore (`memory/vector_store.py`)

**Thread-safe** (RLock on all 9 public methods):
- `add(objects)` — embed + persist
- `search(query, k, filter)` — vector search with metadata filter
- `delete_by_metadata(filter)` — multi-key delete via `$and`
- `enforce_cap()` — age/count capping
- `SchemaMigrator` — handles schema evolution

### EmbeddingService (`memory/embedding_service.py`)

- Caches embeddings (RLock on `_cache`)
- **Known issue:** lacks model fingerprinting — cache not invalidated on model change (roadmap Item 4)
- Supports multiple models (configurable)

### Text Chunker (`knowledge/chunker.py`)

Unified chunking with **semantic boundaries**, **token-level overlap**, and **rich metadata**.

#### Semantic Chunking (3a)
- Uses embedding cosine similarity between adjacent sentences as boundary signal
- Configurable threshold (default 0.3) — gap > threshold = new chunk
- Falls back to character split when embeddings unavailable (`embedding_service.is_available` check)
- Pre-computes boundary map for efficiency with deduplication

#### Overlap Unification (3b)
- Single `OVERLAP_TOKENS = 64` constant across all chunking paths
- Both `_carry_over()` and `_split_by_tokens()` use token-level overlap (~4 chars/token)
- Removed dual word-level / character-level overlap implementations

#### Chunk Metadata (3c)
Enhanced `Chunk` class with:
- `section_heading` — detected from short non-punctuated paragraphs (requires blank-line separation)
- `position` — character offset in document
- `embedding_hash` — MD5 of chunk text for cache invalidation (16-char prefix)
- `from_dict()` / `to_dict()` for serialization
- All chunk creation sites updated to populate metadata

#### Chunking Flow
```
text → paragraphs → semantic boundary map → chunks with metadata
                ↓
     sentence-level semantic boundary check
                ↓
     token-level chunking with OVERLAP_TOKENS
                ↓
     Chunk(text, index, source, metadata, section_heading, position, embedding_hash)
```

#### Configuration
- `chunk_size` (default 512 chars, ~128 tokens)
- `overlap` (default `OVERLAP_TOKENS=64`, ~256 chars)
- `semantic_threshold` (default 0.3 cosine similarity)
- `embedding_service` (optional, for semantic boundaries)

#### Integration
- `DocumentStore` stores `chunk_count`, `total_tokens` per document
- `Chunk.to_dict()` / `Chunk.from_dict()` for persistence
- Embedding hash enables cache invalidation on model change (roadmap Item 4)

---

## Retrieve Path (Read)

`MemoryCoordinator` ([[01-Architecture/03-Core Brain Kernel & State]]) → `AdvancedRetriever.retrieve()` ([[01-Architecture/05-Knowledge Graph & Vault]]) — **4 sources in parallel** via ThreadPoolExecutor:

1. **Vector search** — MMR diversification, multi-factor ranking
2. **Belief engine** — relevant beliefs by topic
3. **Knowledge graph** — entity traversal from query entities
4. **Attention-weighted recency** — recent + salient memories

**Guards:**
- `<3` word queries skip heavy retrieval (fast path)
- `memory_type` filter enforced to `VectorStore.search()`
- Early-exit cancels remaining futures

---

## Experience Layer (M6/M8)

### EmotionExperience (`memory/experience.py`)

```python
@dataclass
class EmotionExperience:
    event: str              # raw turn text
    meaning: str            # what it meant (filled at reflection)
    emotion: str            # emotion name
    relationship_impact: float
    reflection: str         # LLM reflection (filled at dream L5)
    lessons: str            # extracted lessons (filled at dream L5)
    growth: str             # personal growth (filled at dream L5)
    significance: float     # 0–1
    timestamp: float
```

### ExperienceStore (`memory/experience.py`)

- JSONL append-only (RLock)
- `record(experience)` — md5 replay dedup (identical text recorded once)
- `mark_reflected(id)` — fills meaning/lessons/growth
- `stats()` — includes `deduped` counter

### Integration Points

1. **Store:** Charged turns (emotion intensity ≥ 0.6) recorded at `_store_impl()` — one JSONL append.
2. **MemoryObject:** `emotion_experience` field carries link (additive, backward compatible).
3. **Dreaming:** Level-5 task `experience_reflection` — LLM reflection over significant unreflected experiences; knowledge entry per revisit.
4. **Retrieval:** `MemoryCoordinator.experience_context()` — Dice-relevance gate ≥ 0.10 (M12), injects reflected experiences into prompt only when relevant.

---

## Lifecycle & Consolidation

### MemoryLifecycle (`memory/lifecycle.py`)

State machine: new → consolidated → archived → forgotten.

### ConsolidationEngine (`memory/consolidation.py`)

- Duplicate merge (semantic similarity > threshold)
- Decay: importance reduction over time
- `decay.consolidate(store_fn=...)` — persists orphaned `MemoryObject` nodes

### MemoryHierarchy (`memory/hierarchy.py`)

Cognitive-science hierarchy:
- Sensory → Working → Episodic → Semantic → Autobiographical → Procedural

---

## Thread Safety

| Component | Lock |
|-----------|------|
| `VectorStore` | RLock on all 9 public methods |
| `EmbeddingService._cache` | RLock |
| `ExperienceStore` | RLock |
| Legacy `Memory` | RLock (verified Oct 2026) |

⚠️ **Known layer breach:** `memory/` imports from `knowledge/` (debt D-2)

---

## Known Issues

- `MemoryObject.lock` dead field (unused)
- `MemoryObject.embeddings` field unused
- `MemoryNode` duplicates `MemoryObject` fields
- Embedding cache lacks model fingerprinting (roadmap Item 4)

---

## Wiki Links

**Architecture:** [[01-Architecture/04-Memory Subsystem]] • [[01-Architecture/09-Events & Data Flow]] — store/retrieve data paths  
**Related:** [[01-Architecture/05-Knowledge Graph & Vault]] — vault writing • [[01-Architecture/06-Agency Reasoning LLM & Execution]] — dreaming experience reflection • [[02-Subsystems/Vault Compilation]] — MemoryWriter detail