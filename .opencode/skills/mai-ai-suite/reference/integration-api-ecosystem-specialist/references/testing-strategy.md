# Testing Strategy

## Test Pyramid for APIs

```
         ╱ e2e ╲
        ╱ integration ╲
       ╱  contract  ╲
      ╱   unit tests   ╲
```

## Contract Tests

### What to Test
- Request validation (missing fields, wrong types, out of range)
- Response format (status codes, body structure, headers)
- Error format consistency
- Pagination contract (limit, cursor, has_more)
- Rate limit headers

### Tools
- `pytest` + `httpx` for HTTP-level contract tests
- OpenAPI/Swagger schema validation via `openapi-core`
- Example: mock server returns fixture, verify client handles it

```python
def test_get_memory_returns_correct_structure(client):
    response = client.get("/api/v1/memory?q=test")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "pagination" in data
    assert "next_cursor" in data["pagination"]
```

## Integration Tests

### What to Test
- API → memory pipeline end-to-end
- API → LLM provider integration (with mock provider)
- API → knowledge base integration
- Plugin loading and hook execution
- Webhook reception and event bus delivery

### Approach
- Use real subsystems where feasible (in-memory vector store, test LLM)
- Mock external services (OpenWeatherMap, Google Calendar)
- Test failure modes (timeouts, rate limits, auth expiry)

```python
async def test_chat_endpoint_integration(async_client, mock_brain):
    response = await async_client.post("/api/v1/chat", json={
        "message": "Hello Mai",
        "user_id": "test-user"
    })
    assert response.status_code == 200
    assert "response" in response.json()["data"]
    mock_brain.chat.assert_called_once()
```

## End-to-End Tests

### What to Test
- Full user flow: chat → memory retrieval → response
- Voice pipeline: audio in → STT → LLM → TTS → audio out
- Knowledge ingestion: file → chunking → embedding → searchable
- Boot sequence: startup → health check → ready

### Approach
- Use dedicated test environment with real services
- Minimal test suite (covers critical paths only)
- Run nightly or pre-deployment

```python
@pytest.mark.e2e
def test_full_chat_flow(live_client):
    # Send message
    r1 = live_client.post("/api/v1/chat", json={"message": "Remember my birthday is Dec 25"})
    assert r1.status_code == 200

    # Memory should be retrievable
    r2 = live_client.get("/api/v1/memory?q=birthday")
    assert r2.status_code == 200
    assert "Dec 25" in r2.text
```

## Mock Strategies

| External Dependency | Mock Strategy |
|--------------------|---------------|
| LLM provider | Fixed response mock with configurable delay |
| Vector store | In-memory ChromaDB instance |
| File system | TemporaryDirectory |
| External API (weather, calendar) | responses library or httpx mock |
| Audio device | Null audio stream |
| System clock | freezegun or time_machine |
