# Error Recovery

## Error Types and Recovery

| Error | Detection | Recovery | Priority |
|-------|-----------|----------|----------|
| OOM (GPU) | torch.cuda.OutOfMemoryError | Unload cached models, retry. If still OOM, fall back to CPU with smaller model. | P0 |
| OOM (RAM) | MemoryError | Unload idle models, clear L2 cache, retry. If still OOM, reject request with graceful message. | P0 |
| GPU unavailable | cuda.Error, driver mismatch | Fall back to CPU, log error, alert health monitor. | P0 |
| Corrupt model | Checksum mismatch, load failure | Delete corrupt files, attempt re-download, use fallback model. | P0 |
| Missing model | FileNotFoundError | Check registry, attempt download, use fallback. | P1 |
| Driver errors | RuntimeError from CUDA/ROCm | Reload driver context, retry inference. If persistent, switch runtime. | P1 |
| Runtime crash | Process exit, segfault | Restart model process, reload state from health monitor snapshot. | P1 |
| Timeout | Exceeds max_inference_time | Cancel inference, return partial result or fallback response. | P1 |
| Deadlock | Threads stuck > watchdog_timeout | Force unlock, log stack trace, restart model. | P2 |
| Dependency failure | ImportError, version mismatch | Log dependency chain, suggest fix, use fallback. | P2 |

## Fallback Chain Pattern

```python
FALLBACK_CHAINS = {
    "stt": ["faster-whisper-large", "faster-whisper-small", "whisper-cpp-tiny", "text_input"],
    "llm": ["llama-3.1-8b", "phi-3-mini", "default_response"],
    "tts": ["kokoro", "piper", "espeak"],
    "embedding": ["bge-large", "bge-small", "minilm"],
}
```

Each fallback step degrades gracefully in quality but never fails completely.

## Auto-Recovery Logic

1. Catch the error
2. Log full context (model, input, traceback, resource stats)
3. Try recovery action (unload, fallback, retry)
4. If recovery succeeds: return result, log recovery action
5. If recovery fails: escalate to next fallback, alert health monitor
6. If all fallbacks exhausted: return graceful error message, log for analysis

## Graceful Degradation

| Capability | Full | Degraded | Minimal |
|------------|------|----------|---------|
| Speech input | GPU STT large | CPU STT small | Text-only input |
| Voice output | Neural TTS | Piper TTS | Beep indicator |
| LLM response | 70B model | 3B model | Template response |
| Memory recall | Full vector search | Keyword search | Last-turn context |