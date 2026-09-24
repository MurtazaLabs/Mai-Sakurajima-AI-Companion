# Decision Making

## Adaptive Depth

```python
def determine_depth(question: str, context: ReasoningContext) -> ReasoningDepth:
    complexity = estimate_complexity(question)
    user_patience = estimate_user_patience(context)
    available_time = estimate_available_time(context)
    
    if complexity == "simple" and user_patience == "low":
        return ReasoningDepth.FAST
    elif complexity == "complex" or user_patience == "high":
        return ReasoningDepth.DEEP
    else:
        return ReasoningDepth.BALANCED
```

## Depth Levels

| Level | Planning | Reflection | Tools | Latency |
|-------|----------|------------|-------|---------|
| FAST | None | Inline only | Direct answer only | < 500ms |
| BALANCED | Single step | Inline | 1-2 tool calls | < 3s |
| DEEP | Multi-step | Inline + periodic | Full tool access | < 10s |
| THOROUGH | Full decomposition | Full reflection | All tools | < 30s |

## Decision Factors

| Factor | FAST | BALANCED | DEEP | THOROUGH |
|--------|------|----------|------|----------|
| Question complexity | Low | Medium | High | Very high |
| User patience | Low | Medium | High | Very high |
| Confidence requirement | Medium | High | Very high | Maximum |
| Available tokens | Low | Medium | High | Full window |
| History with user | Any | Any | Established | Long-term |

## Balancing Trade-offs

Each decision is a trade-off. Default to BALANCED. Escalate to DEEP when:
- User asks "think about this carefully"
- Question involves multiple entities with complex relationships
- Planning involves 3+ steps
- Reflection from previous similar question suggested deeper reasoning

Default to FAST when:
- Simple greeting or acknowledgment
- User is in a hurry (short messages, rapid back-and-forth)
- Battery is low
- System is under load