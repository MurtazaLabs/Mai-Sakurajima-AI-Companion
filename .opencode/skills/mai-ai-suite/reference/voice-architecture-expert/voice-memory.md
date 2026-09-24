# Voice Memory Integration

## Pipeline

```
Voice Interaction
  → Conversation Manager
  → Memory Pipeline (async, non-blocking)
    → Episodic Memory: save conversation as event
    → Entity Extraction: extract people, places, projects, etc.
    → Knowledge Graph: update entities and relationships
    → Relationship Engine: update trust, closeness scores
    → MemoryState: merge all updates
  → Reflection Queue (schedule post-conversation reflection)
  → Dream Queue (schedule idle-time dreaming)
  → Vault Compiler (incremental, on significant updates only)
```

## Event Triggers

| Event | Memory Action |
|-------|---------------|
| User speaks | Start working memory buffer |
| User finishes turn | Extract entities + relationships |
| Mai responds | No memory action |
| Conversation ends | Save as episodic memory, trigger reflection |
| Emotion detected | Tag episodic memory with emotion |
| New entity mentioned | Add to knowledge graph |
| Known entity mentioned | Reinforce relationship edge |

## Async Design

Memory pipeline runs asynchronously after the user's turn. The response pipeline does not wait for memory writes. Memory writes are queued and processed by background workers. The user perceives no latency from memory operations.