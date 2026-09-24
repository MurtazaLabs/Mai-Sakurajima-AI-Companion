# Backup & Disaster Recovery

> Backup strategies, restore procedures, and disaster recovery for Mai AI.

---

## What to Back Up

| Data | Location | Type | Frequency | Priority |
|------|----------|------|-----------|----------|
| Vector DB | `data/vector_db/chroma.sqlite3` | SQLite | Daily | Critical |
| Knowledge Graph | `data/graph/graph.json` | JSON | Daily | Critical |
| Profiles | `data/profiles/profiles.db` | SQLite | Daily | Critical |
| Obsidian Vault | `OBSIDIAN_VAULT/` | Markdown | Hourly (inc) | Critical |
| Embedding Cache | `data/cache/` | Binary | Weekly | High |
| Logs | `logs/` | JSON | Daily (rotate) | Medium |
| Config | `config/` + `.env` | Python/env | On change | Critical |

---

## Backup Procedures

### Automated (Recommended)

**Cron Example:**
```bash
# Daily 3 AM: Full backup
0 3 * * * /path/to/backup.sh >> /var/log/mai_backup.log 2>&1
```

**Backup Script (`backup.sh`):**
```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/backups/mai_$(date +%F_%H-%M-%S)"
MAI_DIR="/path/to/Mai_ai"
VAULT_DIR="/path/to/MaiMemory"

mkdir -p "$BACKUP_DIR"

# Vector DB
cp "$MAI_DIR/data/vector_db/chroma.sqlite3" "$BACKUP_DIR/"

# Knowledge Graph
cp "$MAI_DIR/data/graph/graph.json" "$BACKUP_DIR/"

# Profiles
cp "$MAI_DIR/data/profiles/profiles.db" "$BACKUP_DIR/"

# Config
cp -r "$MAI_DIR/config" "$BACKUP_DIR/"
cp "$MAI_DIR/.env" "$BACKUP_DIR/" 2>/dev/null || true

# Vault (incremental via rsync)
rsync -a --delete "$VAULT_DIR/" "$BACKUP_DIR/vault/"

# Compress
tar -czf "${BACKUP_DIR}.tar.gz" -C "$(dirname "$BACKUP_DIR")" "$(basename "$BACKUP_DIR")"
rm -rf "$BACKUP_DIR"

# Retention: keep 30 days
find /backups -name "mai_*.tar.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_DIR}.tar.gz"
```

### Manual Backup
```bash
# Quick full backup
tar -czf mai_backup_$(date +%F_%H-%M).tar.gz \
  data/vector_db/chroma.sqlite3 \
  data/graph/graph.json \
  data/profiles/profiles.db \
  config/ \
  .env \
  MaiMemory/
```

---

## Restore Procedures

### Full Restore (Disaster Recovery)

```bash
# 1. Stop services
docker compose down
# or kill run.py process

# 2. Extract backup
tar -xzf mai_backup_2026-09-03_03-00-00.tar.gz

# 3. Restore files
cp -r backup/data/* data/
cp -r backup/config/* config/
cp backup/.env .env 2>/dev/null || true

# 4. Restore vault (rsync for incremental safety)
rsync -a --delete backup/MaiMemory/ MaiMemory/

# 4. Restart
docker compose up -d
# or python run.py --mode daemon
```

### Partial Restore

**Vector DB only:**
```bash
cp backups/vector_db_2026-09-01.sqlite3 data/vector_db/chroma.sqlite3
```

**Vault only:**
```bash
rsync -a --delete backup/MaiMemory/ MaiMemory/
```

**Config only:**
```bash
cp backups/config/* config/
cp backups/.env .env
```

---

## Disaster Recovery Scenarios

### Scenario 1: Disk Failure (Complete Data Loss)

**RTO:** 2-4 hours | **RPO:** 24 hours (daily backup)

1. Provision new server/VM
2. Install Docker / Python env
3. Clone repo
4. Run full restore procedure
4. Verify: `/api/health`, `/api/voice/status`, `/api/status`
5. Test conversation

---

### Scenario 2: Vault Corruption (Graph/Markdown Inconsistent)

**RTO:** 30 min | **RPO:** 1 hour (hourly vault sync)

1. Stop writes: Disable scheduler, pause voice
2. Backup corrupted vault: `cp -r MaiMemory/ MaiMemory.corrupted/`
3. Restore from latest hourly backup: `rsync -a --delete backup/vault/ MaiMemory/`
4. Run vault janitor: `python scripts/sweep_graph_junk.py --apply`
5. Run vault compiler: `python -c "from app.builder import ApplicationBuilder; app=ApplicationBuilder().build(); app.vault_compiler.compile_schema(); app.vault_compiler.compile_graph(app.graph_manager); app.vault_compiler.compile_index()"`
6. Verify: `/api/status`, check vault files

---

### Scenario 3: Vector DB Corruption

**RTO:** 1 hour | **RPO:** 24 hours

1. Stop services
2. Restore `chroma.sqlite3` from backup
3. Verify: `python -c "import chromadb; c=chromadb.PersistentClient(path='data/vector_db'); print(c.list_collections())"`
4. If embeddings incompatible: Clear cache `rm -rf data/cache/*`, restart (re-embeds on demand)

---

### Scenario 4: Config/Credentials Lost

**RTO:** 15 min | **RPO:** 0 (git tracked)

1. Restore `config/` from git: `git checkout HEAD -- config/`
2. Restore `.env` from secure backup or re-enter credentials
3. Restart services

---

### Scenario 5: Ransomware / Malicious Encryption

**RTO:** 4+ hours | **RPO:** Depends on backup isolation

**Prerequisites:** Offline/immutable backups (separate network/credentials)

1. Isolate infected system
2. Provision clean environment
3. Restore from known-good offline backup
4. Rotate all credentials (API keys, JWT secrets, DB passwords)
5. Audit access logs for entry point

---

## Backup Verification

### Monthly Verification Checklist

- [ ] Restore vector DB to test env, verify collections
- [ ] Restore vault, open 5 random notes, verify content
- [ ] Restore profiles DB, query user data
- [ ] Full end-to-end: Restore → Start → `/api/health` → Send test message

### Automated Verification (Planned)

```python
# verify_backup.py
def verify_backup(backup_path):
    # 1. Extract
    # 2. Validate JSON/DB integrity
    # 3. Spot-check 10 random vault notes
    # 4. Verify vector DB collections count
    # 5. Return PASS/FAIL
```

---

## Offsite / Immutable Backup Strategy

### 3-2-1 Rule
- **3** copies of data
- **2** different media (local disk + cloud)
- **1** offsite/immutable

### Implementation

| Copy | Location | Method | Immutable |
|------|----------|--------|-----------|
| Primary | Local NVMe | Daily tar.gz | No |
| Secondary | NAS / Second disk | Rsync hourly | No |
| Tertiary | Backblaze B2 / S3 | `rclone sync` daily | **Yes** (Object Lock) |
| Quaternary | GitHub (config only) | Git push on change | Yes |

### Cloud Sync Setup (B2 Example)

```bash
# Install rclone
curl https://rclone.org/install.sh | bash

# Configure
rclone config  # Name: b2_remote, Type: b2, KeyID, AppKey

# Sync vault daily
rclone sync /path/to/MaiMemory b2_remote:mai-backup/vault --progress

# Sync DBs daily
rclone copy /path/to/Mai_ai/data/vector_db/chroma.sqlite3 b2_remote:mai-backup/db/
rclone copy /path/to/Mai_ai/data/profiles/profiles.db b2_remote:mai-backup/db/
```

---

## Recovery Time Objectives (RTO) / Recovery Point Objectives (RPO)

| System | RTO | RPO | Backup Frequency |
|--------|-----|-----|------------------|
| API Server | 15 min | 0 | N/A (stateless) |
| Voice Pipeline | 30 min | 0 | N/A (stateless) |
| Vector DB | 1 hour | 24 hr | Daily |
| Knowledge Graph | 30 min | 1 hr | Hourly (vault sync) |
| Profiles | 15 min | 24 hr | Daily |
| Obsidian Vault | 30 min | 1 hr | Hourly (rsync) |
| Config | 5 min | 0 | Git |

---

## Testing Schedule

| Test | Frequency | Owner |
|------|-----------|-------|
| Full DR drill | Quarterly | Platform |
| Partial restore (vault) | Monthly | Platform |
| Backup integrity check | Weekly | Platform |
| Config restore | Monthly | Platform |

---

*Last updated: 2026-09-03*