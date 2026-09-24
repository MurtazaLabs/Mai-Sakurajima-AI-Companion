# Speech Recognition

## Recommended Configuration

| Hardware | Engine | Precision | Model | Notes |
|----------|--------|-----------|-------|-------|
| CPU | Faster Whisper | int8 | large-v3 | Best accuracy on CPU |
| CPU (low power) | Faster Whisper | int8 | small | Lower CPU usage |
| GPU (6GB+) | Faster Whisper | float16 | large-v3 | Fastest local option |
| GPU (12GB+) | Whisper.cpp | fp16 | large-v3 | Lower memory than FT Whisper |
| Apple Silicon | faster-whisper | int8 | large-v3 | MLX alternative |

## Streaming

```python
class StreamingSTT:
    def __init__(self, model="large-v3", compute="int8"):
        self.model = faster_whisper.WhisperModel(model, compute_type=compute)
        self.buffer = AudioBuffer(max_duration=30.0)
    
    async def transcribe_stream(self, chunk: np.ndarray):
        self.buffer.add(chunk)
        if self.buffer.should_partial():
            segments, _ = self.model.transcribe(self.buffer.get(), 
                beam_size=1, vad_filter=True)
            for seg in segments:
                if seg.no_speech_prob < 0.6:
                    yield seg.text  # partial result
```

## Caching

- Model loaded once at startup (or on first voice use)
- Held in memory for entire session
- Unloaded only on memory pressure
- Reload time: ~2-5s (model size dependent)

## Fallback Chain

```
Faster Whisper large-v3 → Faster Whisper small → Vosk (tiny) → Text input mode
```