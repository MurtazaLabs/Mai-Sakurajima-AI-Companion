# Model Selection

## Selection Strategy

```python
def select_model(task, hardware, context):
    if task.requires_reasoning and hardware.vram_gb >= 8:
        return "deepseek-r1:7b-q4"  # reasoning model
    if task.is_simple_query and hardware.battery_mode:
        return "phi-3-mini:q4"  # fast, low power
    if task.is_conversation:
        return "llama-3.2-3b:q4"  # balanced
    if hardware.platform == "apple-silicon":
        return "qwen-2.5-7b-mlx"  # MLX optimized
    # Fallback
    return "phi-3-mini:q4"
```

## Selection Factors

| Factor | Weight | Source |
|--------|--------|--------|
| Hardware capability | 30% | DeviceDetector |
| Current load | 20% | ResourceScheduler.stats() |
| Task complexity | 25% | Task classifier |
| Latency requirement | 15% | Pipeline config |
| Quality requirement | 10% | User preference |

## Model Tiers

| Tier | Description | Examples | Latency | Quality |
|------|-------------|----------|---------|---------|
| Tiny | < 3B params | Phi-3-mini, TinyLlama | < 100ms | Basic |
| Small | 3-7B params | Llama-3.2-3B, Qwen-2.5-7B | < 500ms | Good |
| Medium | 7-13B params | Llama-3.1-8B, Mistral-7B | < 2s | Very good |
| Large | 13-70B params | Llama-3-70B, Qwen-2.5-72B | < 10s | Excellent |
| XLarge | > 70B params | DeepSeek-V3, Llama-405B | > 10s | State-of-art |

## Fallback Chains

```
Primary → Fallback 1 → Fallback 2 → Error

Example STT:
Faster-Whisper large → Faster-Whisper small → Whisper.cpp tiny → "I didn't catch that"

Example LLM:
llama-3.1-8b → phi-3-mini → "Let me think about that differently..."
```

## Hardware-Aware Routing

| Hardware | Recommended Runtime | Recommended Precision |
|----------|-------------------|----------------------|
| NVIDIA RTX 4090 | CUDA / TensorRT | FP16 / INT8 |
| NVIDIA RTX 3060 | CUDA | INT8 / INT4 |
| AMD RX 7900 | ROCm / ONNX | FP16 |
| Apple M1-M3 | MLX / CoreML | FP16 / INT4 |
| Intel Arc | OpenVINO | INT8 |
| CPU-only | GGUF / ONNX | INT4 |
| Integrated GPU | OpenVINO / DirectML | INT4 |