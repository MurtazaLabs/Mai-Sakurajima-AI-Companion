# Speech Synthesis

## Preferred (Local)

| Engine | Quality | Latency | Emotion | Voice Cloning | Size |
|--------|---------|---------|---------|---------------|------|
| Kokoro | Very good | <100ms | Yes | No | ~100MB |
| Piper | Good | <50ms | No | No | ~10MB |
| XTTS | Excellent | <500ms | Yes | Yes | ~1GB |
| Coqui | Good | <200ms | Limited | Yes | ~500MB |

## Configuration

```python
@dataclass
class TTSConfig:
    engine: str = "kokoro"  # default
    voice: str = "default"
    speed: float = 1.0
    emotion: str = "neutral"  # neutral, happy, sad, excited, calm
    streaming: bool = True
    device: str = "cpu"  # cpu, cuda
    fallback: str = "piper"
```

## Streaming Playback

- Audio chunks generated incrementally
- First chunk sent to playback as soon as available (<300ms)
- Subsequent chunks queued and played sequentially
- On interrupt: flush buffer, stop generation, start listening

## Playback Controls

```python
class AudioPlayback:
    async def play(self, stream: AsyncIterator[np.ndarray]): ...
    async def pause(self): ...
    async def resume(self): ...
    async def stop(self): ...
    async def interrupt(self): ...  # stop + flush + reset
    async def set_volume(self, level: float): ...
    async def crossfade(self, duration_ms: int = 50): ...
```