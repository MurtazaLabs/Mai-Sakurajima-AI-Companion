# Performance & Observability

## Latency Targets

| Stage | Target | Measurement |
|-------|--------|-------------|
| Audio capture → VAD | <10ms | Time from mic to VAD input |
| VAD detection | <50ms | Time from speech onset to SPEECH_START |
| First STT token | <300ms | Time from SPEECH_START to first partial text |
| Full utterance | < utterance length | Real-time factor < 1.0 |
| First LLM token | <500ms | Time from full text to first token |
| First TTS audio | <300ms | Time from first LLM token to first audio chunk |
| End-to-end response | 1-2s | Time from speech end to full response played |

## Metrics Per Module

```python
@dataclass
class ModuleMetrics:
    module_name: str
    latency_p50: float
    latency_p95: float
    latency_p99: float
    error_count: int
    total_calls: int
    last_error: str | None
    uptime: float
```

## Health Check Endpoints

Each module exposes:
- `health()` → HEALTHY, DEGRADED, CRITICAL, UNKNOWN
- `metrics()` → ModuleMetrics
- `histogram()` → latency distribution

## Error Recovery Matrix

| Failure | Detection | Recovery | Time |
|---------|-----------|----------|------|
| Mic disconnected | Audio stream error | Reload device, notify user | <1s |
| STT model crash | Process exit | Restart model, fallback to Vosk | <5s |
| TTS engine fail | Generation timeout | Fallback to Piper, return text | <2s |
| VAD failure | No speech events | Fallback to silence timeout (3s) | Immediate |
| GPU OOM | CUDA OOM | Fallback to CPU int8 | <1s |
| Audio device change | System event | Auto-reconnect | <500ms |

## System Monitor Integration

All metrics exposed via HealthRegistry (observability subsystem). Available in Mai's System Monitor dashboard. Historical data stored for trend analysis.