# Incident Response

> Runbooks and procedures for handling production incidents.

---

## Incident Severity Levels

| Level | Definition | Response Time | Examples |
|-------|------------|---------------|----------|
| **SEV-1** | Core functionality down, data loss risk | < 15 min | API down, voice pipeline dead, data corruption |
| **SEV-2** | Major feature degraded, workaround exists | < 1 hour | STT/TTS down, LLM failover stuck, memory slow |
| **SEV-3** | Minor issue, workaround available | < 4 hours | Voice quality degraded, slow transcription |
| **SEV-4** | Cosmetic/non-blocking | Next release | UI glitch, minor log noise |

---

## Response Process

```
1. DETECT    → Alert fires / user reports / health check fails
2. TRIAGE    → Determine severity, assign owner
3. MITIGATE  → Apply workaround / failover / rollback
4. RESOLVE   → Root cause fix, deploy
5. REVIEW    → Post-mortem within 48h (SEV-1/2)
```

---

## Communication Channels

| Channel | Purpose |
|---------|---------|
| **Primary** | Discord #mai-incidents (or configured webhook) |
| **Secondary** | Email / PagerDuty (if configured) |
| **Status Page** | GitHub Issues / internal dashboard |

---

## Runbooks

### SEV-1: API Down / Kernel Crashed

**Detection:** `/api/health` returns non-200 or times out

**Immediate Actions:**
1. Check process: `ps aux | grep -E "run\.py|uvicorn"`
2. Check logs: `tail -f logs/*.log | grep -i error`
3. Check system resources: `htop`, `df -h`, `nvidia-smi`

**Mitigation:**
- If kernel dead: `python run.py --mode cli` (restart CLI)
- If API only: Restart uvicorn / container
- If OOM: Check memory, restart with smaller model

**Rollback:** Restore `data/`, `OBSIDIAN_VAULT/`, `config/settings.py` from backup

---

### SEV-1: Voice Pipeline Dead

**Detection:** `stt=MISSING`, `vad=MISSING`, or `tts=FAILED` in `/api/voice/status`

**Immediate Actions:**
1. Check STT: `python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu')"`
2. Check VAD: Delete `~/.cache/silero_vad/silero_vad.jit`, restart
3. Check TTS: Kokoro model loads (`Kokoro ready` in logs)

**Mitigation:**
- Fallback to text-only mode (API chat still works)
- Disable voice in config: `PORCUPINE_ENABLED=False`

---

### SEV-2: OpenRouter Failover Loop

**Detection:** `Circuit OPEN — failing fast for 30s after 8 failures`

**Immediate Actions:**
1. Verify `OPENROUTER_API_KEY` valid
2. Check OpenRouter status page
3. Check network: `curl -I https://openrouter.ai/api/v1/chat/completions`

**Mitigation:**
- Wait 30s for circuit breaker reset
- Force Ollama: `LLM_DEFAULT_PROVIDER=ollama`
- If Ollama down: fallback text responses

---

### SEV-2: Memory/Vault Corruption

**Detection:** Vault sync errors, vector DB errors, inconsistent state

**Immediate Actions:**
1. Stop writes: Disable scheduler, pause voice
2. Backup current state: `cp -r data/ data.bak/`, `cp -r OBSIDIAN_VAULT/ OBSIDIAN_VAULT.bak/`
3. Run vault janitor: `python scripts/sweep_graph_junk.py --apply`
3. Rebuild vector index if needed

---

### SEV-3: Degraded Voice Quality

**Symptoms:** Transcription inaccurate, TTS robotic, interruptions excessive

**Investigation:**
1. Check VAD threshold (`VAD_THRESHOLD` in config)
2. Check mic gain / device selection
3. Check TTS model (Kokoro voice)
4. Check STT model size (tiny vs base)

---

## Post-Mortem Template

**Incident:** [Title] — [SEV-X] — [Date]

### Timeline
| Time (UTC) | Event |
|------------|-------|
| HH:MM | Detection |
| HH:MM | Triage started |
| HH:MM | Mitigation applied |
| HH:MM | Resolution deployed |
| HH:MM | All clear |

### Root Cause
[5 Whys analysis]

### Impact
- Users affected: [count/type]
- Duration: [X minutes/hours]
- Data loss: [yes/no — details]

### Action Items
| Action | Owner | Due | Status |
|--------|-------|-----|--------|
| [Fix] | [Person] | [Date] | [TODO/DONE] |
| [Monitoring] | [Person] | [Date] | [TODO/DONE] |
| [Doc update] | [Person] | [Date] | [TODO/DONE] |

### Lessons Learned
- What worked well?
- What didn't?
- What should we automate?

---

## Escalation Matrix

| Severity | Primary | Secondary | External |
|----------|---------|-----------|----------|
| SEV-1 | Primary on-call | Secondary on-call | Vendor support (OpenRouter, Ollama) |
| SEV-2 | Primary on-call | — | — |
| SEV-3 | Next business day | — | — |

---

## Post-Incident Checklist

- [ ] Incident documented in GitHub Issues
- [ ] Post-mortem scheduled within 48h (SEV-1/2)
- [ ] Action items assigned with due dates
- [ ] Monitoring/alerting updated to detect earlier
- [ ] Documentation updated (runbooks, troubleshooting)
- [ ] Team debrief completed

---

*Last updated: 2026-09-03*