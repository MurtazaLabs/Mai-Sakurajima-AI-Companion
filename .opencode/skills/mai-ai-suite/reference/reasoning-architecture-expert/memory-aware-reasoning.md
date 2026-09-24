# Memory-Aware Reasoning

## Retrieval Strategy

At each reasoning step, determine relevance of:
1. **Current conversation** — recent turns (windowed)
2. **Recent conversations** — last N sessions (summarized)
3. **Long-term memories** — entities, facts, relationships (vector search)
4. **User preferences** — known likes, dislikes, communication style
5. **Relationship state** — trust level, intimacy, history length
6. **Active goals** — current and pending objectives
7. **World model** — known entities, beliefs, predictions

## Relevance Scoring

```python
def score_relevance(memory: MemoryObject, query: str, context: ReasoningContext) -> float:
    semantic = cosine_similarity(memory.embedding, query_embedding)
    temporal = recency_score(memory.timestamp, context.current_time)
    relational = relationship_score(memory, context.world_model)
    return 0.5 * semantic + 0.3 * temporal + 0.2 * relational
```

## Memory Fusion

When multiple memories are relevant, fuse them into a coherent context:
1. Deduplicate overlapping information
2. Resolve contradictions (prefer higher confidence / more recent)
3. Fill gaps with world model inferences (labeled as such)
4. Present as unified narrative to the reasoning stage

## Working Memory

Working memory holds the current reasoning context: the last 3 conversation turns, the active plan step, retrieved memories for the current step, and pending tool results. Working memory is reset per reasoning cycle.