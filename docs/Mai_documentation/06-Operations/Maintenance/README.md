# Maintenance

> Routine maintenance tasks, schedules, and procedures for Mai AI.

---

## Recurring Tasks

### Daily
- [ ] Check `/api/health` — all core subsystems `ok`
- [ ] Review `logs/` for ERROR/CRITICAL entries
- [ ] Verify vault sync completed (check `logs/` for GraphExporter)
- [ ] Monitor disk space: `df -h` (ensure > 10% free)

### Weekly
- [ ] Run vault janitor: `python scripts/sweep_graph_junk.py --apply`
- [ ] Check embedding cache size: `du -sh data/cache/`
- [ ] Review consolidation runs: `logs/` for `ConsolidationEngine`
- [ ] Check LLM provider costs (OpenRouter dashboard)
- [ ] Rotate logs if not automated

### Monthly
- [ ] Update dependencies: `pip list --outdated`
- [ ] Update Silero VAD model (delete `~/.cache/silero_vad/`, restart)
- [ ] Update Whisper model if new version
- [ ] Update Kokoro TTS model
- [ ] Review and prune old logs: `find logs/ -mtime +30 -delete`
- [ ] Test backup restore procedure
- [ ] Update system packages: `apt update && apt upgrade` (if Linux)

### Quarterly
- [ ] Full disaster recovery drill
- [ ] Review and update runbooks
- [ ] Penetration test / security scan
- [ ] Capacity planning (disk, RAM, GPU)
- [ ] Review and update dependencies (security audit)

---

## Automated Maintenance

### WriteJournal
- **File**: `core/write_journal.py`
- **Behavior**: Buffers writes, flushes every 5s or 100 entries
- **Shutdown**: Flushes on `app.shutdown()`

### ConsolidationEngine
- **File**: `memory/consolidation.py`
- **Triggers**: Periodic via scheduler, or manual
- **Actions**: Duplicate merge, decay, orphan persistence

### Vault Compiler
- **File**: `knowledge/vault_compiler.py`
- **Schedule**: Daily via scheduler + on shutdown
- **Outputs**: Compiled folders (identity, preferences, relationships, etc.)

### Vault Janitor
- **File**: `knowledge/vault_janitor.py`
- **Manual**: `python scripts/sweep_graph_junk.py --apply`
- **Actions**: Removes junk entities (confidence < 0.25), orphan notes

### Log Rotation
- **Location**: `logs/`
- **Format**: Structured JSON
- **Rotation**: Manual or via external logrotate

---

## Model Updates

### STT (Whisper)
```bash
# Check current model
ls -la ~/.cache/faster_whisper/

# Update to new version
pip install --upgrade faster-whisper
# Model downloads on first use
```

### TTS (Kokoro)
```bash
# Update model
pip install --upgrade kokoro-onnx
# Model auto-downloads on first use
```

### VAD (Silero)
```bash
# Force re-download (model updated upstream)
rm ~/.cache/silero_vad/silero_vad.jit
# Restart Mai — auto-downloads with new checksum
```

### Embedding Model
```bash
# Current: all-MiniLM-L6-v2 (sentence-transformers)
# Update:
pip install --upgrade sentence-transformers
# Clear cache to force re-embed
rm -rf data/cache/*
```

---

## Log Management

### Log Locations
| Type | Location |
|------|----------|
| Application | `logs/*.log` (JSON) |
| Cognitive Audit | `logs/cognitive_audit/` |
| Orchestrator | `logs/orchestrator/transitions.jsonl` |
| Tracer | `data/traces/` (PII-redacted) |

### Log Rotation (Manual)
```bash
# Compress old logs
find logs/ -name "*.log" -mtime +7 -exec gzip {} \;

# Delete very old
find logs/ -name "*.gz" -mtime +90 -delete
```

### Log Analysis
```bash
# Find errors in last hour
grep '"level": "ERROR"' logs/$(date +%Y-%m-%d).log

# Count errors by component
grep '"level": "ERROR"' logs/*.log | jq -r '.component' | sort | uniq -c | sort -rn

# Voice pipeline errors
grep '"component": "voice"' logs/*.log | grep '"level": "ERROR"'
```

---

## Database Maintenance

### Vector Store (ChromaDB)
```bash
# Check size
du -sh data/vector_db/

# Compact (if supported)
# Note: ChromaDB doesn't auto-compact; monitor size

# Backup
cp data/vector_db/chroma.sqlite3 backups/vector_db_$(date +%F).sqlite3
```

### Profiles (SQLite)
```bash
# Backup
cp data/profiles/profiles.db backups/profiles_$(date +%F).db

# Vacuum (reclaim space)
sqlite3 data/profiles/profiles.db "VACUUM;"
```

### Knowledge Graph
```bash
# Backup
cp data/graph/graph.json backups/graph_$(date +%F).json

# Validate
python -c "import json; json.load(open('data/graph/graph.json')); print('Valid JSON')"
```

---

## Cleanup Commands

```bash
# Clean Python cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete

# Clean pytest cache
rm -rf .pytest_cache/

# Clean temp audio
rm -rf temp/*

# Clean embedding cache (force rebuild)
rm -rf data/cache/*

# Clean Silero VAD cache (force re-download)
rm -rf ~/.cache/silero_vad/
```

---

## Health Checks

### Quick Health Check
```bash
# API health
curl -s http://localhost:8000/api/health | jq

# Voice status
curl -s http://localhost:8000/api/voice/status | jq

# Memory stats
curl -s http://localhost:8000/api/memory/stats | jq

# Event bus stats
curl -s http://localhost:8000/api/inspector/events | head -5
```

---

## Automation (Cron Examples)

```bash
# Daily at 3 AM: Vault janitor
0 3 * * * cd /path/to/Mai_ai && python scripts/sweep_graph_junk.py --apply >> logs/janitor.log 2>&1

# Daily at 4 AM: Backup vector DB
0 4 * * * cp /path/to/Mai_ai/data/vector_db/chroma.sqlite3 /backups/vector_db_$(date +\%F).sqlite3

# Weekly Sunday 2 AM: Log compression
0 2 * * 0 find /path/to/Mai_ai/logs -name "*.log" -mtime +7 -exec gzip {} \;

# Monthly 1st 3 AM: Dependency check
0 3 1 * * cd /path/to/Mai_ai && pip list --outdated --format=freeze > outdated_$(date +\%F).txt
```

---

*Last updated: 2026-09-03*