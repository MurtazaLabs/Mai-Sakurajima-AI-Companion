# Context Management

## Ranking

```python
class ContextRanker:
    def rank(self, sources: list[ContextSource], budget: int) -> list[ContextSource]:
        # Score each source by relevance, timeliness, and information density
        # Sort by score descending
        # Greedily select until budget is full
        # If overflow, compress lowest-ranked source instead of dropping
```

## Compression Strategies

| Strategy | Compression | Quality | Use Case |
|----------|-------------|---------|----------|
| Truncation | High | Low | Old conversation turns |
| Summarization | High | Medium | Historical context |
| Keyword extraction | Very high | Low | Background facts |
| Semantic chunking | Medium | High | Knowledge retrieval |
| Priority drop | Configurable | Maintains top | Token budget overflow |

## Token Budget Allocation

```python
BUDGET = {
    "system_prompt": 500,
    "conversation_history": 2000,
    "retrieved_memories": 1500,
    "world_model": 500,
    "active_goals": 300,
    "tool_results": 1000,
    "reasoning_scratchpad": 500,
}
TOTAL = sum(BUDGET.values())  # ~6300 tokens
```

## Dynamic Assembly

The prompt is assembled from ranked context sources in priority order. If the total exceeds the model's context window, lower-priority sources are compressed or dropped. The assembler logs what was included and what was dropped for debugging.