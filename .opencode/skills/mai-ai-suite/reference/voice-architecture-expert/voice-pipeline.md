# Voice Pipeline

## Event Flow

```
Audio Capture ──[chunk]──→ VAD ──[speech_start/speech_end]──→ STT
  │                              │                              │
  │                              │ (interrupt detected)         │
  │                              └──→ TTS: stop                 │
  │                                   LLM: cancel               │
  │                                   ConvMgr: reset            │
  │                                                            │
  │                   ┌────────────────────────────────────────┘
  │                   │ [partial_text / full_text]
  │                   ↓
  │              Conversation Manager
  │                   │
  │                   ├──→ Memory Retrieval
  │                   ├──→ Knowledge Retrieval
  │                   ├──→ Reasoning / LLM ──[tokens]──→ TTS ──[audio]──→ Playback
  │                   └──→ Memory Storage (async)
  │                              │
  │                              ├──→ Reflection Queue
  │                              └──→ Dream Queue
```

## Module Interface

```python
class VoiceModule(ABC):
    @property
    def name(self) -> str: ...
    async def start(self): ...
    async def stop(self): ...
    async def health(self) -> HealthStatus: ...
    def metrics(self) -> dict[str, float]: ...

class AudioSource(VoiceModule):
    def on_chunk(self) -> AsyncIterator[np.ndarray]: ...

class VADProcessor(VoiceModule):
    async def process(self, chunk: np.ndarray) -> VADEvent: ...

class STTEngine(VoiceModule):
    async def transcribe(self, audio: AsyncIterator[np.ndarray]) -> AsyncIterator[str]: ...
```

## Module Registry

All modules register with the voice pipeline manager. Modules can be enabled/disabled/replaced at runtime. The pipeline manager handles module lifecycle, health checks, and error recovery.