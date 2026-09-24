# Context Window Management

## Context Budgeting

### Total Window Allocation (128K example)
| Subsystem | Allocation | Purpose |
|-----------|-----------|---------|
| Conversation history | 32K | Recent turns |
| Memory retrieval | 16K | Relevant memory objects |
| System prompt | 8K | Personality, instructions |
| Knowledge context | 8K | Retrieved documents |
| Agent state | 4K | Current goals, tools |
| Reasoning scratchpad | 4K | Thought journal |
| Reserve | 56K | Headroom for long conversations |

## Compression Strategies

### 1. Summarization
- Every N turns, summarize old conversation into compressed form
- Store summary in memory, load on next session
- Configurable threshold (default: every 10 turns)

### 2. Truncation Order (most aggressive first)
```
1. Reasoning scratchpad (stale thoughts)
2. Agent state (completed goals archived)
3. Conversation history (oldest turns)
4. Knowledge context (lowest relevance score)
5. Memory retrieval (lowest score memories)
```

### 3. Selective Retention
- Always retain: system prompt, personality instructions, active goals
- Prioritize: user's last message, recent 3 turns, highest-relevance memory
- Deprioritize: tool call outputs, system messages, retry attempts

## Truncation Policies

| Policy | Trigger | Action |
|--------|---------|--------|
| Soft truncation | Usage > 70% | Compress oldest 20% of conversation |
| Medium truncation | Usage > 85% | Remove reasoning scratchpad + archive goals |
| Hard truncation | Usage > 95% | Keep only last 5 turns + system prompt |
| Emergency | Context limit error | Strip to system prompt + last message only |

## Allocation Per Model

| Model | Max Context | Effective Limit (90%) | Recommended Per-Task Max |
|-------|-----------|----------------------|------------------------|
| GPT-4o | 128K | 115K | 96K |
| Claude 3.5 Sonnet | 200K | 180K | 150K |
| GPT-4o-mini | 128K | 115K | 64K |
| Groq Llama 70B | 8K | 7K | 6K |
| Ollama (local) | Varies | 80% of model limit | 4K |

## Context Window Monitoring

```python
@dataclass
class ContextMetrics:
    total_tokens: int
    max_tokens: int
    utilization_ratio: float
    subsystem_breakdown: dict[str, int]
    compression_applied: bool
    truncation_level: str  # none | soft | medium | hard | emergency
```
