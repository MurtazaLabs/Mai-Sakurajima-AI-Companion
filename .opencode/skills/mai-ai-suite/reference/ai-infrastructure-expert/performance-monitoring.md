# Performance Monitoring

## Metrics Collected

```
per_model:
  - load_time_ms: int
  - inference_time_ms: histogram
  - tokens_per_second: float
  - memory_usage_mb: {gpu: int, ram: int}
  - queue_wait_ms: histogram
  - error_count: int
  - total_inferences: int
  - uptime_seconds: int

system:
  - gpu_utilization: percent
  - gpu_temperature: celsius
  - gpu_memory_used: int
  - gpu_memory_total: int
  - cpu_utilization: percent
  - ram_used: int
  - ram_total: int
  - thread_count: int
  - active_models: int
  - queue_depth: int
  - disk_cache_size: int
```

## Health States

| State | Meaning | Recovery |
|-------|---------|----------|
| HEALTHY | All metrics within thresholds | — |
| DEGRADED | One or more metrics above warning threshold | Self-monitoring |
| CRITICAL | Metrics above critical threshold, or model failing | Auto-recovery |
| UNKNOWN | No recent health report | Check component |

## Reporting

```python
class HealthMonitor:
    def __init__(self, tick_interval=1.0):
        self.models = {}
        self.tick_interval = tick_interval
        
    async def run(self):
        while True:
            for model_id, model in self.models.items():
                status = await model.health_check()
                self.report(model_id, status)
            await asyncio.sleep(self.tick_interval)
    
    def report(self, model_id, status):
        if status == ModelStatus.CRITICAL:
            logger.warning(f"Model {model_id} is CRITICAL: {status.detail}")
            # Trigger auto-recovery
        self.history[model_id].append({
            "timestamp": time.time(),
            "status": status,
        })
```

## Profiling

- Use `cProfile` for CPU hotspots
- Use `torch.cuda.profiler` for GPU bottlenecks
- Use `py-spy` for live thread analysis
- Profile duration: 30s-5min depending on context
- Profile output: flamegraph HTML or structured JSON

## Alert Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| GPU VRAM usage | > 85% | > 95% |
| RAM usage | > 75% | > 90% |
| Inference latency > 2x baseline | > 5% of requests | > 20% of requests |
| Error rate | > 1% | > 5% |
| Queue depth > 10 | > 30s | > 60s |