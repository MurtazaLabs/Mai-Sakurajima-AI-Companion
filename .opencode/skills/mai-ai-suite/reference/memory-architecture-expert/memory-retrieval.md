# Memory Retrieval

## Priority Cascade

```
1. Working Memory          (current session, in-memory, ~0ms)
2. Active Conversation     (recent turns, in-memory, ~0ms)
3. Relationship Memory     (per-person, pre-indexed, <5ms)
4. Knowledge Graph         (entity lookup, indexed, <10ms)
5. Semantic Search         (vector + keyword hybrid, <50ms)
6. Vault                   (full-text search, <100ms)
7. Archived Memory         (old/sleeping, cold storage, <500ms)
```

Stop at the first level that provides sufficient context.

Never retrieve all levels unless explicitly needed.

## Dynamic Context Construction

```python
def construct_context(query, context_state):
    context = {}
    
    # Always include working memory
    context["working"] = context_state.working_memory
    
    # Always include active conversation
    context["active"] = context_state.conversation[-3:]  # last 3 turns
    
    # Retrieve relationship memory if person mentioned
    if persons := extract_persons(query):
        context["relationships"] = [
            context_state.relationships[p] for p in persons if p in context_state.relationships
        ]
    
    # Semantic search only if query has substantive content
    if len(query.split()) > 3:
        context["semantic"] = semantic_search(query, top_k=5)
    
    return context
```

## Budget

- Target: < 100ms for 90% of retrievals
- Max: < 500ms for any single retrieval
- Cache: LRU cache for repeated queries within session