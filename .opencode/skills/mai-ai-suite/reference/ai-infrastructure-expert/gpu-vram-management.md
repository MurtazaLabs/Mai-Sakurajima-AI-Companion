# GPU / VRAM Management

## VRAM Budget

Track VRAM per model and total:
```
total_vram = torch.cuda.get_device_properties(0).total_memory
reserved = sum(model.vram_estimate for model in loaded_models)
safety_margin = 0.1 * total_vram  # 10% headroom
available = total_vram - reserved - safety_margin
```

Never exceed budget. If a model load would exceed total_vram - safety_margin, reject or unload another model.

## Model VRAM Estimates (typical)

| Model Type | INT4 | INT8 | FP16 | FP32 |
|-----------|------|------|------|------|
| 1B LLM | ~0.6 GB | ~1 GB | ~2 GB | ~4 GB |
| 3B LLM | ~1.8 GB | ~3 GB | ~6 GB | ~12 GB |
| 7B LLM | ~4 GB | ~7 GB | ~14 GB | ~28 GB |
| 13B LLM | ~7 GB | ~13 GB | ~26 GB | ~52 GB |
| 70B LLM | ~35 GB | ~70 GB | ~140 GB | ~280 GB |
| Whisper small | — | — | ~1 GB | ~2 GB |
| Whisper large | — | — | ~3 GB | ~6 GB |
| Embedding (384) | — | — | ~0.5 GB | ~1 GB |
| Embedding (768) | — | — | ~1 GB | ~2 GB |

## GPU Scheduling

Single GPU:
- Time-slice between priority tasks
- Allow preemption: higher priority suspends lower priority inference
- Support concurrent CUDA streams for independent models

Multi-GPU:
- Assign models to specific GPUs via model affinity config
- Support tensor parallelism for large models across GPUs
- Each GPU has independent budget tracking

## Offloading Strategy

```
VRAM Available       Strategy
────────────────────────────────────────────
> model size        Full GPU (fastest)
> 50% model size    Partial offload (some layers on CPU)
> 25% model size    Minimal offload (key layers only)
< 25% model size    CPU only (fallback)
```

## Dynamic Quantization

If VRAM pressure detected:
1. Try INT8 on loaded models (no reload needed if pre-quantized)
2. If still pressured, switch to INT4 (requires reload)
3. If still pressured, offload to CPU
4. Log the quantization switch with performance impact

## CUDA Stream Management

Use separate CUDA streams for:
- High-priority inference (voice, real-time)
- Batch/background inference
- Model loading (async)
- Cache operations