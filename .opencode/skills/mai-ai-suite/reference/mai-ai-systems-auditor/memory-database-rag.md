# Memory, Database, Vector Database & RAG Auditors

---

## MEMORY SYSTEM AUDITOR {#memory}

### Short-Term Memory (Context Handling)

**Review**
- How is conversation history maintained within a session?
- What's the context window budget, and how is it allocated (system prompt + personality +
  retrieved memories + conversation history + current message)?
- How is history trimmed when it grows too large? (drop oldest / summarize / sliding window)

**Detection Checklist**
- [ ] **Unbounded Growth**: Conversation history list that only appends, never trims — will
      eventually exceed context window or cause memory bloat
- [ ] **No Summarization Strategy**: When history is trimmed, is information just dropped, or
      summarized first? Dropping loses context abruptly.
- [ ] **Context Window Miscalculation**: Token budget doesn't account for system prompt +
      personality + retrieved memories — could silently truncate the user's actual message

### Long-Term Memory (Vector/Persistent Storage)

**Review**
- Storage design: what gets stored (raw conversation? summaries? facts?)
- Retrieval: how are relevant memories selected for a given query?
- Ranking: similarity score only, or also recency/importance weighting?
- Relevance: are retrieved memories actually relevant, or is retrieval too broad/narrow?
- Aging: do old/stale memories get pruned, archived, or do they accumulate forever?

**Detection Checklist**
- [ ] **Duplicate Memories**: Same fact stored multiple times (e.g., "user likes anime" stored
      from 5 different conversations with no deduplication)
- [ ] **Retrieval Failures**: Retrieval returns nothing relevant, or returns everything
      (similarity threshold too loose/strict)
- [ ] **Memory Pollution**: Irrelevant or low-value information stored (e.g., every single
      message, including "ok" and "thanks") drowning out important memories
- [ ] **Conflicting Memories**: Contradictory facts stored without resolution (e.g., "user
      works at Company A" and later "user works at Company B" both retrievable with no
      indication which is current)
- [ ] **Context Fragmentation**: A single logical memory split across multiple chunks that get
      retrieved separately, losing coherence
- [ ] **No Memory Aging/Pruning**: Vector store grows forever — degrades retrieval quality and
      performance over time
- [ ] **Embedding Model Mismatch**: Memories embedded with one model, queries embedded with
      another — silently degrades retrieval quality

### Memory Health Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MEMORY HEALTH REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Short-Term Memory:
  Context strategy:    [sliding window / summarization / none]
  Token budget:        [how allocated]
  Unbounded growth risk: [yes/no — location]

Long-Term Memory:
  Storage:             [what's stored — raw/summary/facts]
  Retrieval method:    [similarity / similarity+recency / similarity+importance]
  Relevance threshold: [value if known, or "not configured"]
  Aging/pruning:       [yes/no]

[MEM-001]
Issue:       [Duplicate / Retrieval Failure / Pollution / Conflict / Fragmentation / No Aging]
Location:    [module/function]
Evidence:    [specific code/pattern]
Impact:      [what degrades — relevance, performance, coherence]
Fix:         [specific recommendation]
Confidence:  🟢/🟡/🔴

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## DATABASE AUDITOR {#database}

### What to Review

**Schema Design**
- Are tables/collections normalized appropriately (not over- or under-normalized)?
- Do field types match the data (dates as datetime, not strings; IDs as proper types)?

**Relationships**
- Are foreign keys/references defined and enforced?
- Are relationships (1:1, 1:N, N:N) modeled correctly for the domain?

**Constraints**
- NOT NULL where required, UNIQUE where appropriate, CHECK constraints for valid ranges?

**Indexes**
- Are columns used in WHERE/JOIN/ORDER BY indexed?
- Are there indexes that are never used (overhead with no benefit)?

**Migrations**
- Is there a migration system (Alembic, Django migrations)?
- Are migrations reversible? Tested?

**Query Design**
- Any N+1 patterns (query in a loop)?
- Any `SELECT *` where only specific columns needed?
- Any queries without pagination on potentially large result sets?

### Detection Checklist

- [ ] **Missing Indexes**: Frequently filtered/joined columns without indexes
- [ ] **Redundant Fields**: Same data stored in multiple tables without clear sync strategy
- [ ] **Slow Query Patterns**: `SELECT *`, missing WHERE clauses, unindexed JOINs
- [ ] **N+1 Patterns**: Loop containing a DB call
- [ ] **Schema Weaknesses**: Missing constraints allowing invalid data (negative quantities,
      empty required fields, invalid enum values stored as free strings)
- [ ] **No Migration System**: Schema changes made by hand, no version history
- [ ] **Connection Management**: No pooling, or connections not properly closed (leak risk)

### Database Health Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DATABASE HEALTH REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Database Type:     [SQLite/Postgres/MySQL/etc]
Schema Overview:   [tables/collections and purposes]
Migration System:  [present/absent — tool used]

[DB-001]
Issue:       [Missing Index / Redundant Field / Slow Query / N+1 / Schema Weakness]
Location:    [table/query/file]
Evidence:    [specific schema or query]
Impact:      [performance/correctness impact]
Fix:         [specific recommendation]
Confidence:  🟢/🟡/🔴

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## VECTOR DATABASE AUDITOR {#vectordb}

### What to Review

**Embeddings**
- Which embedding model is used? Is it appropriate for the content (general text vs. code vs.
  conversational)?
- Is the same model used for both indexing and querying?

**Chunking Strategy**
- How is content split into chunks before embedding?
- Chunk size: too small loses context, too large dilutes relevance
- Is there overlap between chunks to preserve continuity?

**Retrieval Quality**
- What's the similarity metric (cosine, L2, dot product) and is it appropriate for the
  embedding model?
- What's `n_results` / top-k, and is it tuned or left at a default?
- Is there a similarity score threshold, or are all top-k results used regardless of relevance?

**Similarity Search**
- Is metadata filtering used to scope searches (e.g., search only this user's memories)?
- Are searches scoped appropriately, or searching the entire collection every time?

**Context Recall**
- When a memory is retrieved, is enough surrounding context included to make it useful, or is
  it an isolated fragment?

### Detection Checklist

- [ ] **Duplicate Embeddings**: Same content embedded and stored multiple times
- [ ] **Poor Chunking**: Chunks too small (losing meaning) or too large (diluting relevance),
      or chunking at arbitrary character counts instead of semantic boundaries
- [ ] **Retrieval Failures**: No similarity threshold — low-relevance results always returned;
      or threshold too strict — relevant results filtered out
- [ ] **Context Loss**: Retrieved chunks lack surrounding context (e.g., a chunk says "yes, I
      agree" with no indication what it's agreeing to)
- [ ] **No Metadata Filtering**: Every query searches the entire collection, even when scoped
      to a specific user/session/topic would be more accurate and faster
- [ ] **Embedding Model Drift**: If the embedding model has been changed, old embeddings may be
      incompatible with new queries (different vector space)

### Vector Database Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 VECTOR DATABASE REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Vector Store:       [ChromaDB/Pinecone/etc]
Embedding Model:    [name]
Chunking Strategy:  [size, overlap, method]
Similarity Metric:  [cosine/L2/dot]
Top-K:              [value]
Similarity Threshold: [value or "none configured"]
Metadata Filtering: [used/not used]

[VDB-001]
Issue:       [Duplicate / Poor Chunking / Retrieval Failure / Context Loss / No Filtering / Drift]
Location:    [module/function]
Evidence:    [specific code/config]
Impact:      [retrieval quality impact]
Fix:         [specific recommendation]
Confidence:  🟢/🟡/🔴

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## RAG SYSTEM AUDITOR {#rag}

### What to Review

**Data Ingestion**
- How does content get into the vector store? (manual, automated, real-time, batch)
- Is there validation/cleaning of content before embedding?

**Chunking** — see Vector Database Auditor above (closely coupled)

**Retrieval** — see Vector Database Auditor above (closely coupled)

**Re-ranking**
- Is there a re-ranking step after initial retrieval, or is top-k by similarity used directly?
- For small top-k (e.g., 3-5), re-ranking may be unnecessary; for larger candidate sets, its
  absence can hurt precision.

**Context Injection**
- How are retrieved chunks formatted and inserted into the prompt?
- Are sources/citations preserved, or is retrieved content blended in without attribution?
- Is there a limit on how much retrieved content can be injected (token budget)?

**Response Quality**
- Does the system have a way to detect when retrieval found nothing useful, and respond
  accordingly (vs. hallucinating an answer)?
- Is there a fallback when RAG context is empty or low-confidence?

### Detection Checklist

- [ ] **Hallucination Risk**: No instruction or mechanism for the LLM to say "I don't have
      information about that" when retrieval returns nothing relevant
- [ ] **Missing Context**: Retrieved chunks injected without enough surrounding information
      (see Vector DB auditor)
- [ ] **Poor Retrieval Precision**: No threshold/re-ranking, so low-relevance chunks dilute the
      prompt with noise
- [ ] **Inefficient Pipeline**: Retrieval happens even for queries that clearly don't need it
      (e.g., "hello" triggers a vector search)
- [ ] **No Ingestion Validation**: Garbage/empty content can be embedded and pollute the store
- [ ] **Context Budget Not Enforced**: Retrieved content + conversation history + system prompt
      could exceed context window with no truncation strategy

### RAG Health Report Template

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RAG HEALTH REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Ingestion:          [how content enters the store, validation present?]
Retrieval Trigger:  [always / conditional — describe condition]
Re-ranking:         [present/absent]
Context Injection:  [format, attribution, token budget]
No-Context Fallback: [present/absent — what happens when retrieval is empty]

[RAG-001]
Issue:       [Hallucination Risk / Missing Context / Poor Precision / Inefficient / No Validation]
Location:    [module/function]
Evidence:    [specific code/prompt]
Impact:      [response quality impact]
Fix:         [specific recommendation]
Confidence:  🟢/🟡/🔴

Confidence: 🟢/🟡/🔴/⚪
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```