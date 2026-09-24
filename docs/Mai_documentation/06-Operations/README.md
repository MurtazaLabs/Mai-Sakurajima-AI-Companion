# 06 — Operations

> Production operations, monitoring, deployment, and incident response for Mai AI.

---

## Quick Navigation

| Area | Description | Status |
|------|-------------|--------|
| [[Monitoring-Alerting]] | Prometheus/Grafana, alert rules, health endpoints | 🟡 Planned |
| [[Backup-Disaster-Recovery]] | Backup/restore procedures, DR testing | 🟡 Planned |
| [[Deployment]] | Docker, native daemon installer, rollback | 🟢 Partial |
| [[Troubleshooting]] | Common issues, debugging guides, performance | 🟢 Partial |
| [[Maintenance]] | Log rotation, vault janitor, model updates | 🟢 Partial |
| [[Incident-Response]] | Runbooks, escalation, post-mortems | 🔴 Not Started |

---

## Quick Links

- **Health Check**: `GET /api/health` — liveness probe
- **Status**: `GET /api/status` — readiness, emotion, goals, world model
- **Metrics**: `GET /api/inspector/events` — live event stream
- **Logs**: `logs/` — structured JSON, cognitive audit, orchestrator transitions

---

## Operational Principles

1. **Observability First** — Every subsystem emits health metrics via `HealthRegistry`
2. **Graceful Degradation** — STT/TTS/embeddings/LLM unavailability degrades stepwise
3. **Single Writer** — Vault: `StateDumper` owns compiled folders; `MemoryWriter` owns raw
4. **Fail-Safe Telemetry** — Subsystem failure never crashes runtime
4. **Rollback Ready** — Stop daemon, restore `data/`, `OBSIDIAN_VAULT/`, `logs/`, restart

---

## Related Documentation

- [[01-Architecture/10-Status & Debt]] — Subsystem maturity, technical debt register
- [[04-Development/Deployment Guide]] — Docker, daemon installer, hardening checklist
- [[01-Architecture/02-Application Boot & Lifecycle]] — 8-phase boot, validation, shutdown
- [[01-Architecture/09-Events & Data Flow]] — Event fabric, 67 specs, 4 data paths

---

*Last updated: 2026-09-03*