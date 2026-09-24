# Metrics Framework

## Metric Taxonomy

### User Experience
| Metric | Definition | Target | Instrumentation |
|--------|-----------|--------|-----------------|
| Response Time (p50) | Median time from send to first token | <500ms | LLM call start/end |
| Response Time (p95) | 95th percentile | <2000ms | LLM call start/end |
| User Retention | Sessions per user per week | >3 | Session tracking |
| Message Depth | Avg turns per session | >8 | Conversation tracker |
| Re-engagement Rate | Return within 7 days | >60% | User activity log |

### Retrieval Quality
| Metric | Definition | Target | Instrumentation |
|--------|-----------|--------|-----------------|
| Recall@5 | Relevant docs in top 5 | >0.85 | Judgment set |
| Precision@5 | Relevant / retrieved | >0.70 | Judgment set |
| Cache Hit Rate | Served from cache | >0.40 | Cache counter |
| Retrieval Latency | Time to return results | <100ms | Timer |
| Diversity Score | Unique sources per query | >2 | Source tracker |

### System Performance
| Metric | Definition | Target | Instrumentation |
|--------|-----------|--------|-----------------|
| Boot Time | App.build() to ready | <5s | Timer |
| Memory Usage | Resident set size | <500MB | psutil |
| LLM Call Success | Non-error responses | >99% | Provider wrapper |
| Embedding Latency | Text → vector | <200ms | Timer |
| Voice Pipeline Latency | Audio in → response out | <3s | End-to-end timer |

### Conversation Quality
| Metric | Definition | Target | Instrumentation |
|--------|-----------|--------|-----------------|
| Engagement Score | User messages / session | >5 | Counter |
| Sentiment Drift | User sentiment change per session | <0.3 | Sentiment model |
| Goal Completion Rate | Active goals closed as done | >70% | Goal manager |
| Memory Recall Rate | Relevant memories retrieved | >0.75 | Memory pipeline |

## Instrumentation Points

```
User Input → (Timer) → Intent Classifier → (Counter) → LLM Call → (Timer, Counter)
                                                              ↓
                                                        Memory Pipeline → (Timer, Metric)
                                                              ↓
                                                        Response → (Timer, Sentiment)
```

## KPI Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│  RESPONSE TIME (p50/p95) │ RETRIEVAL (Recall@5)     │
│  [sparkline]             │ [sparkline]               │
├─────────────────────────┼───────────────────────────┤
│  CACHE HIT RATE         │ LLM SUCCESS RATE          │
│  [gauge 42%]            │ [gauge 99.2%]             │
├─────────────────────────┴───────────────────────────┤
│  ENGAGEMENT TREND (7-day rolling)                   │
│  [line chart]                                        │
└─────────────────────────────────────────────────────┘
```
