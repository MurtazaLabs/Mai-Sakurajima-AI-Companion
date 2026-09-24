# Streaming Infrastructure

## Async Generator Pattern

```python
async def stream_inference(model_id, prompt, config):
    model = await model_lifecycle.get(model_id)
    async for token in model.generate_async(prompt, config):
        yield token
        # Token is immediately sent to consumer
        # Consumer can cancel via cancellation token
```

## Supported Streams

| Stream Type | Granularity | Consumer | Backpressure |
|-------------|-------------|----------|--------------|
| LLM tokens | Single token | UI, TTS | TTS speed |
| Speech chunks | 10-30ms audio | Speaker | Playback buffer |
| Reasoning steps | Structured JSON | UI, Log | UI render |
| Tool calls | Function call | Executor | Call latency |
| Memory retrieval | Relevance score | Reasoner | Retrieval time |
| Knowledge search | Chunk text | Reasoner | Search time |

## Pipeline

```
User Input
  → STT (streaming) → LLM (streaming) → TTS (streaming) → Output

All three stages run concurrently once the pipeline is primed:
STT produces text tokens → LLM consumes text tokens and produces response tokens → TTS consumes response tokens and produces audio.
```

## Cancellation

- Each stream has a `CancellationToken`
- Upstream components check `token.is_cancelled()` between each yield
- On cancel, stream raises `CancelledError` which propagates through pipeline
- Downstream components receive `on_cancelled` callback

## Backpressure

- If consumer is slower than producer, buffer grows to `max_buffer_size`
- When buffer is full, producer pauses (backpressure)
- Producer resumes when consumer drains buffer below `low_water_mark`
- If producer is slower than consumer, consumer waits (no extra latency)

## Latency Budget

| Stage | Budget | Notes |
|-------|--------|-------|
| First token | < 500ms | Critical for perceived responsiveness |
| Inter-token | < 50ms | Smooth text output |
| Audio chunk | < 30ms | Real-time speech |
| Tool call | < 200ms | Tool detection, not execution |