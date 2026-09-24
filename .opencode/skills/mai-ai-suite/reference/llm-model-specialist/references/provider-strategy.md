# Provider Strategy

## Provider Selection Matrix

| Provider | Strengths | Weaknesses | Best For | Notes |
|----------|-----------|-----------|----------|-------|
| OpenAI GPT-4o | High quality, broad capability, good latency | Expensive, rate limits | Primary conversation | Best default |
| Anthropic Claude 3.5 | Long context, safety, nuanced reasoning | Slower, lower availability | Complex reasoning | Fallback for intricate tasks |
| OpenRouter | Multi-provider access, automatic fallback | Variable latency, third-party | Cost optimization | Primary for cost-sensitive routes |
| Ollama (local) | Zero cost, offline capable, privacy | Lower quality, hardware dependent | Dev/testing, private data | Use for sensitive contexts |
| Groq | Extremely fast inference | Limited model selection | Real-time/low-latency | Voice pipeline, simple tasks |

## Fallback Chain Design

```
Primary:      GPT-4o
  │ timeout/error
  ▼
Fallback 1:   Claude 3.5 Sonnet
  │ timeout/error
  ▼
Fallback 2:   OpenRouter (best available)
  │ timeout/error
  ▼
Fallback 3:   Ollama (local, degraded quality)
```

### Per-Task Routing

| Task | Primary | Fallback | Notes |
|------|---------|----------|-------|
| Chat | GPT-4o | Claude → OpenRouter | Quality priority |
| Simple Q&A | Groq | GPT-4o-mini | Speed priority |
| Memory retrieval | GPT-4o-mini | Ollama | Cost priority |
| Complex reasoning | Claude 3.5 | GPT-4o | Quality priority |
| Private / offline | Ollama | None | Privacy priority |

## Cost Modeling

```python
# Per-call cost estimation
COST_PER_1K_TOKENS = {
    "gpt-4o":       {"input": 0.005,  "output": 0.015},
    "gpt-4o-mini":  {"input": 0.00015, "output": 0.0006},
    "claude-3.5":    {"input": 0.003,  "output": 0.015},
    "groq-llama-70b": {"input": 0.00059, "output": 0.00079},
    "ollama":        {"input": 0,      "output": 0},
}
```

## Provider Health Monitoring

- Provider-level circuit breaker: 5 consecutive errors → 60s cooldown
- Latency SLO: p95 < 5s per provider (measured per hour)
- Cost budget: per-provider daily cap (configurable)
- Fallback activation logged with reason for auditing
