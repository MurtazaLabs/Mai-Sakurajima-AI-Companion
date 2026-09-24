# Analytics Queries

## Retrieval Analytics

### Query Pattern: Recall Rate Over Time
```sql
SELECT
  DATE(timestamp) AS day,
  COUNT(*) AS total_queries,
  SUM(CASE WHEN recall@5 >= 0.85 THEN 1 ELSE 0 END) AS good_recall,
  AVG(recall@5) AS avg_recall
FROM retrieval_metrics
WHERE timestamp >= NOW() - INTERVAL 30 DAY
GROUP BY DATE(timestamp)
ORDER BY day;
```

### Query Pattern: Cache Effectiveness
```sql
SELECT
  cache_hit,
  COUNT(*) AS query_count,
  AVG(latency_ms) AS avg_latency
FROM retrieval_metrics
GROUP BY cache_hit;
```

### Query Pattern: Lowest Performing Sources
```sql
SELECT
  source_doc_id,
  COUNT(*) AS retrieval_count,
  AVG(recall@5) AS avg_recall,
  AVG(precision@5) AS avg_precision
FROM retrieval_metrics
GROUP BY source_doc_id
HAVING retrieval_count >= 5
ORDER BY avg_recall ASC
LIMIT 20;
```

## Conversation Analytics

### Query Pattern: Session Depth Distribution
```sql
SELECT
  session_id,
  COUNT(*) AS turn_count,
  AVG(response_time_ms) AS avg_response_time,
  MAX(sentiment_score) - MIN(sentiment_score) AS sentiment_range
FROM conversation_logs
WHERE session_start >= NOW() - INTERVAL 7 DAY
GROUP BY session_id
ORDER BY turn_count DESC;
```

### Query Pattern: Engagement Trends
```sql
SELECT
  DATE(timestamp) AS day,
  COUNT(DISTINCT user_id) AS active_users,
  COUNT(*) AS total_messages,
  COUNT(*) / COUNT(DISTINCT user_id) AS messages_per_user
FROM conversation_logs
WHERE timestamp >= NOW() - INTERVAL 30 DAY
GROUP BY DATE(timestamp)
ORDER BY day;
```

### Query Pattern: Topic Popularity
```sql
SELECT
  topic,
  COUNT(*) AS mention_count,
  AVG(user_sentiment) AS avg_sentiment
FROM conversation_logs
CROSS APPLY OPENJSON(detected_topics)
WHERE timestamp >= NOW() - INTERVAL 14 DAY
GROUP BY topic
ORDER BY mention_count DESC;
```

## Performance Analytics

### Query Pattern: Endpoint Latency Percentiles
```sql
SELECT
  endpoint,
  COUNT(*) AS call_count,
  AVG(latency_ms) AS avg_latency,
  PERCENTILE_CONT(0.50) AS p50,
  PERCENTILE_CONT(0.95) AS p95,
  PERCENTILE_CONT(0.99) AS p99
FROM endpoint_logs
WHERE timestamp >= NOW() - INTERVAL 24 HOUR
GROUP BY endpoint;
```

### Query Pattern: LLM Provider Reliability
```sql
SELECT
  provider,
  model,
  COUNT(*) AS total_calls,
  SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successes,
  SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) AS errors,
  AVG(latency_ms) AS avg_latency,
  AVG(token_count) AS avg_tokens
FROM llm_call_log
WHERE timestamp >= NOW() - INTERVAL 7 DAY
GROUP BY provider, model;
```

### Query Pattern: Bottleneck Detection
```sql
SELECT
  operation,
  COUNT(*) AS occurrences,
  AVG(duration_ms) AS avg_duration,
  SUM(duration_ms) AS total_duration
FROM trace_events
WHERE timestamp >= NOW() - INTERVAL 1 HOUR
  AND duration_ms > 100
GROUP BY operation
ORDER BY total_duration DESC;
```

## Log Schema Reference

```python
@dataclass
class RetrievalMetric:
    query: str
    recall_at_5: float
    precision_at_5: float
    latency_ms: float
    cache_hit: bool
    source_count: int
    timestamp: datetime

@dataclass
class EndpointLog:
    endpoint: str
    method: str
    status_code: int
    latency_ms: float
    user_id: Optional[str]
    timestamp: datetime

@dataclass
class LLMCallLog:
    provider: str
    model: str
    status: str  # success | error | timeout
    latency_ms: float
    token_count: int
    cost: float
    error_type: Optional[str]
    timestamp: datetime
```
