# Integration Patterns

## Third-Party Auth Flows

### OAuth 2.0 (External Service Access)
```
1. Redirect user to provider auth URL
2. Provider redirects to callback with code
3. Exchange code for access_token + refresh_token
4. Store tokens securely (encrypted at rest)
5. Use access_token for API calls
6. Refresh when token expires
```

### API Key (Direct Service Access)
```
Header: X-API-Key: <key>
- Store key in environment variable or secrets manager
- Never log the key
- Rotate keys on suspicion of compromise
```

## Data Mapping

```
External Format → Internal Format → External Format
     [Mapper]         [Core]          [Mapper]

Mapper responsibilities:
- Field name translation (snake_case ↔ camelCase)
- Type coercion (string dates → datetime objects)
- Null handling (default values, omissions)
- Validation against schema
```

## Retry Logic

```python
RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay": 1.0,       # seconds
    "max_delay": 30.0,
    "backoff_factor": 2.0,   # exponential: 1, 2, 4, 8...
    "retryable_statuses": {408, 429, 500, 502, 503, 504},
    "jitter": True            # ±25% random jitter
}
```

## Error Handling

| External Error | System Action | User-facing Response |
|---------------|--------------|---------------------|
| Timeout | Retry 3x, then fallback | "Service temporarily unavailable" |
| 429 Rate Limited | Exponential backoff | "Please wait a moment" |
| 401 Unauthorized | Refresh token, retry | "Authentication expired" |
| 500 Server Error | Retry 3x, then degrade gracefully | "This feature is offline" |
| Network error | Retry 3x with jitter | "Connection failed, please retry" |

## Webhook Architecture

### Design
```
[External Service] ──POST──→ [Mai Webhook Endpoint]
                                  │
                                  ▼
                            [Webhook Router]
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              [Handler A]   [Handler B]   [Handler C]
                    │             │             │
                    └─────────────┼─────────────┘
                                  ▼
                            [Event Bus]
```

### Webhook Contract
```json
{
  "webhook_id": "wh_abc123",
  "event_type": "memory.created",
  "timestamp": "2026-07-24T12:00:00Z",
  "data": { ... },
  "signature": "sha256=..."
}
```

### Verification
- Verify HMAC signature on every webhook
- Reject unsigned or invalid webhooks immediately
- Respond 200 quickly, process asynchronously
- Idempotency key to prevent duplicate processing
