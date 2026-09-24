# Error Recovery

## Error Taxonomy

| Error Type | Example | Recovery Strategy |
|-----------|---------|-------------------|
| Missing context | No relevant memories found | Answer with uncertainty, ask clarifying question |
| Conflicting memories | Two contradictory facts | Flag both, note contradiction, ask user |
| Tool failure | Execution timeout | Fallback to direct answer, retry once with timeout |
| Model uncertainty | Low confidence output | Express uncertainty, offer alternatives |
| Planning failure | Subtask cannot be completed | Replan affected branch, notify user of scope change |
| External failure | No internet for web search | Note offline mode, use cached knowledge |
| Overload | Too many concurrent tasks | Queue tasks, inform user of wait time |

## Recovery Flow

```
Error detected
  → Log full context
  → Classify error type
  → Execute recovery strategy
  → If recovery succeeds → continue with adjusted output
  → If recovery fails → escalate to next strategy
  → If all strategies exhausted → graceful fallback with user notification
```

## Graceful Degradation

```
Full reasoning → Fast reasoning (skip deep reflection)
  → Direct response (skip planning, tool use)
  → Template response (acknowledge, promise follow-up)
  → Error message with recovery instructions
```

## Uncertainty Estimation

```python
def estimate_uncertainty(output, context) -> float:
    factors = [
        retrieval_quality(context),  # How good were the retrieved memories?
        confidence_scores(output),   # Model's own confidence tokens
        contradiction_count(output, context),  # Conflicting info?
        knowledge_coverage(output, context),  # Missing info?
    ]
    return weighted_average(factors)
```