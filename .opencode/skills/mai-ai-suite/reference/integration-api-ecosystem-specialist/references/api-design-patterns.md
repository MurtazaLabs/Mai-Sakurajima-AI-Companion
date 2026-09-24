# API Design Patterns

## REST Design Principles

### URL Structure
```
/api/{version}/{resource}
/api/{version}/{resource}/{id}
/api/{version}/{resource}/{id}/{subresource}
```

### HTTP Methods
| Method | Action | Idempotent | Safe |
|--------|--------|------------|------|
| GET | Retrieve | Yes | Yes |
| POST | Create | No | No |
| PUT | Full update | Yes | No |
| PATCH | Partial update | No | No |
| DELETE | Remove | Yes | No |

### Request/Response Format
```json
// Success response
{
  "status": "ok",
  "data": { ... },
  "meta": {
    "request_id": "abc-123",
    "timestamp": "2026-07-24T12:00:00Z"
  }
}

// Error response
{
  "status": "error",
  "error": {
    "code": "INVALID_INPUT",
    "message": "field 'query' must be at least 1 character",
    "details": { "field": "query", "constraint": "min_length" }
  },
  "meta": { "request_id": "abc-123" }
}
```

## Versioning

- **Strategy**: URL path versioning (`/api/v1/...`, `/api/v2/...`)
- **Deprecation**: Sunset header + min 90 day overlap period
- **Migration guide**: Required for every breaking change
- **Backward compatibility**: Add fields, don't remove or rename

## Error Formats

| HTTP Code | Error Code | When |
|-----------|-----------|------|
| 400 | INVALID_INPUT | Validation failure |
| 401 | UNAUTHORIZED | Missing or invalid auth |
| 403 | FORBIDDEN | Authenticated but not allowed |
| 404 | NOT_FOUND | Resource doesn't exist |
| 409 | CONFLICT | Idempotency key replay |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server error (no details exposed) |
| 503 | UNAVAILABLE | Temporary (retry after X) |

## Pagination

```
GET /api/v1/memory?cursor=abc123&limit=50

Response:
{
  "data": [...],
  "pagination": {
    "next_cursor": "def456",
    "limit": 50,
    "has_more": true
  }
}
```

## Rate Limiting

```
Response Headers:
  X-RateLimit-Limit: 60
  X-RateLimit-Remaining: 42
  X-RateLimit-Reset: 1627075200
  Retry-After: 30
```
