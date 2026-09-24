# Monitoring & Alerting

> Observability stack for Mai AI production deployment.

---

## Stack Overview

| Component          | Purpose                       | Status         |
| ------------------ | ----------------------------- | -------------- |
| **Prometheus**     | Metrics collection & storage  | 🟡 Planned     |
| **Grafana**        | Dashboards & visualization    | 🟡 Planned     |
| **Alertmanager**   | Alert routing & deduplication | 🟡 Planned     |
| **Loki**           | Log aggregation               | 🔴 Not Started |
| **HealthRegistry** | In-process health metrics     | 🟢 Active      |

---

## Existing Health Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `GET /api/health` | Liveness probe | `{"status": "ok"}` if all core subsystems healthy |
| `GET /api/status` | Readiness probe | Emotion, goals, world model stats |
| `GET /api/inspector/events` | Live event stream | Event Inspector feed |
| `GET /api/inspector/traces` | Tracer | Recent traces |

---

## HealthRegistry (In-Process)

**File**: `observability/health.py`

```python
health_registry.register("component_name", component=obj)
health_registry.heartbeat("component_name")
health_registry.stats()  # {"component_name": {"status": "ok|warn|error|stalled", ...}}
```

**Statuses**: `ok`, `warn`, `error`, `stalled`

**Stall Detection**: Component must heartbeat ≥2 times before stall check triggers (prevents false positives at boot)

---

## Key Metrics to Monitor

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| `health_registry.stats()` | HealthRegistry | Any `error` or `stalled` |
| `event_bus.stats()` | EventBus | Publish latency > 1s |
| `scheduler.stats()` | Scheduler | Task failure rate > 10% |
| `voice_manager.metrics` | VoiceManager | VAD/STT/TTS latency > 5s |
| `memory_pipeline.stats()` | MemoryPipeline | Store/retrieve latency > 2s |

---

## Alert Rules (Planned)

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| `MaiHealthCritical` | Any component `error` | Critical | Page on-call |
| `MaiHealthStalled` | Component `stalled` > 2min | Warning | Investigate |
| `MaiEventBusLatency` | Publish latency > 1s | Warning | Check load |
| `MaiVoiceLatency` | STT/TTS > 5s | Warning | Check GPU/CPU |
| `MaiMemoryLatency` | Store/retrieve > 2s | Warning | Check vector DB |

---

## Grafana Dashboards (Planned)

1. **System Overview** — HealthRegistry status grid, EventBus throughput, Scheduler task success
2. **Voice Pipeline** — VAD/STT/TTS latency, interruption rate, speaker ID accuracy
3. **Memory Pipeline** — Store/retrieve latency, consolidation runs, vault sync status
4. **LLM Providers** — OpenRouter/Ollama latency, failover count, token usage
5. **Scheduler** — Task success/failure, background tick duration, dream engine runs

---

## Integration Points

- **EventBus** → `EventInspector` → `/api/inspector/events` (real-time)
- **HealthRegistry** → Prometheus exporter (planned)
- **Structured Logs** → Loki (planned) — `logs/` JSON format
- **Tracer** → `data/traces/` — PII-redacted cognitive traces

---

## Next Steps

- [ ] Deploy Prometheus + Grafana stack (Docker Compose)
- [ ] Add Prometheus exporter to HealthRegistry
- [ ] Define alert rules in Alertmanager
- [ ] Build Grafana dashboards
- [ ] Configure Loki for log aggregation
- [ ] Set up notification channels (Discord, email, PagerDuty)

---

*Last updated: 2026-09-03*