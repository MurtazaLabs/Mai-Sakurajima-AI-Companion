# Profiling Results — Jul 23 2026

## Boot Sequence Profile

**Measured:** `ApplicationBuilder().build()` (all 8 layers)

| Metric | Value |
|--------|-------|
| Total wall time | 16.14s (with imports) |
| Build time (imports excluded) | 6.96s |
| Python files imported | 3,364 |
| Function calls | 7,218,076 |

### Top 5 Bottlenecks (cumulative time)

| Rank | Component | Time | % of Total | Notes |
|------|-----------|------|------------|-------|
| 1 | **HuggingFace Hub model downloads** | 4.70s | 29% | 25 HTTP requests to download sentence-transformers models; network-bound |
| 2 | **PyTorch import** | 2.54s | 16% | `torch.__init__` — unavoidable, cached after first import |
| 3 | **Python import machinery** | 9.60s | 59% | `importlib._find_and_load` — 3,364 files imported; dominates first boot |
| 4 | **faster-whisper model init** | 0.96s | 6% | `encode()` + `__init__` — Whisper model loading |
| 5 | **sounddevice init** | 0.32s | 2% | Audio hardware initialization |

### Key Insight

**59% of boot time is Python import overhead.** This is unavoidable for the first `python run.py` call. On subsequent runs in the same process, imports are cached.

Network model downloads (29%) are cached to `~/.cache/huggingface/` after first boot → drops to ~0s on subsequent boots.

---

## Chat Hot Path Profile

**Measured:** 5 `brain.think()` calls with different prompts

| Metric | Value |
|--------|-------|
| Total time (5 calls) | 42.28s |
| Average per call | 8.46s |
| Fastest | 3.77s |
| Slowest | 13.16s |

### Top 5 Bottlenecks (cumulative time)

| Rank | Component | Time | % of Total | Notes |
|------|-----------|------|------------|-------|
| 1 | **LLM API network I/O** | 44.4s | 76% | SSL socket read — waiting for OpenRouter API response |
| 2 | **Brain.think() / tool loop** | 42.3s | 72% | Dispatch overhead (negligible vs network) |
| 3 | **OpenRouter provider** | 36.7s | 63% | HTTP POST + wait for streaming response |
| 4 | **Response body parsing** | 22.9s | 39% | Chunked transfer encoding read |
| 5 | **Import overhead** | 10.0s | 17% | Same as boot — first-run only |

### Key Insight

**76% of chat latency is waiting for the remote LLM API.** The local code path (Brain.think → tool loop → prompt assembly → context management) adds <100ms overhead. The dominant cost is the LLM provider's response time.

---

## Actionable Optimizations

### High Impact

| Item | Est. Gain | Effort | Description |
|------|-----------|--------|-------------|
| **Streaming TTFB optimization** | Perception improvement | 1 day | Show first tokens as they arrive instead of waiting for full response |
| **Persistent HTTP connections** | ~1s per call | 0.5 day | Reuse httpx.AsyncClient connection pool instead of new connections |
| **Lazy-import heavy models** | -6s from boot | 1 day | Move faster-whisper, sounddevice, TTS imports out of boot → first-use |

### Medium Impact

| Item | Est. Gain | Effort | Description |
|------|-----------|--------|-------------|
| **LLM provider fallback tuning** | Variable | 0.5 day | Route to faster provider for simple queries, slower for complex |
| **Conversation history pruning** | -1s on long sessions | 1 day | Reduce context window rebuild cost |
| **Response caching for repeated queries** | -8s per cache hit | 1 day | Short TTL cache for identical messages |

### Low Impact

| Item | Est. Gain | Effort | Description |
|------|-----------|--------|-------------|
| **Reduce import count** | -2s from boot | 3 days | Tree-shake unused imports across 197 files |
| **Lazy torch import** | -2.5s from boot | 1 day | Only import if local embedding/whisper needed |
| **Model download timeout reduction** | -4s on no-network boot | 0.5 day | Reduce HuggingFace retry from 5→2 attempts |
