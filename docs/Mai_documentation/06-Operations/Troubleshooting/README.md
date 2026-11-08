# Troubleshooting

> Common issues, debugging guides, and solutions for Mai AI.

---

## Quick Diagnostics

| Symptom | Likely Cause | Check |
|---------|--------------|-------|
| `stt=MISSING` in logs | No STT backend loaded yet (lazy) — or the backend failed to load | `/api/voice/status`; check `STT_BACKEND` |
| `VAD model checksum mismatch` | Silero model updated at source | Delete `~/.cache/silero_vad/silero_vad.jit` and restart |
| `stt=MISSING` → `stt=ok` on first use | Lazy loading (expected) | First transcription triggers load |
| `Speaker unknown` every time | SpeechBrain embeddings failing | Check `voice/speaker/speaker_encoder.py` torch compat |
| `401 Unauthorized` OpenRouter | `OPENROUTER_API_KEY` not set | Set env var or `.env` file |
| `Circuit OPEN — failing fast` | Too many LLM failures | Wait 30s or check API key |
| `Rejected utterance` in logs | Whole-utterance VAD gate refused the clip | Normal for noise; if real speech, tune `UTTERANCE_VAD_MIN_MEAN`/`_RATIO` |
| Fluent text for silence / her own voice transcribed | Self-hearing regression | Check the recorder is muted while `_speaking` (see Voice Pipeline)

---

## Voice Pipeline Issues

### No Transcription (Mic Active)

**Symptoms:** Mic shows activity, but no text appears

**Checklist:**
1. Check `STT_BACKEND` — `whisper` (default) or `kyutai` (opt-in); `/api/voice/status` shows the live backend and whether a fallback happened
2. Check `stt` status in `/api/voice/status` — should show `ok` after first use
3. Check microphone device: `python -c "import sounddevice as sd; print(sd.query_devices())"`
4. Check VAD: `python -c "from voice.vad import VAD; v=VAD(); v._load_model(); print(v._model is not None)"`
5. If the log says `Rejected utterance`, the gate refused the clip (noise or < 0.2 s voiced); if `Empty transcription` after an accepted gate, the audio is corrupted — look for `Corrupt chunk clamped` / `non-finite` warnings upstream (AEC/noise filter)

### VAD Fails to Load

**Error:** `VAD model checksum mismatch`

**Fix:**
```bash
# Delete corrupted model
rm ~/.cache/silero_vad/silero_vad.jit
# Restart Mai — it will re-download with correct checksum
```

### Speaker ID Always "Unknown"

**Checklist:**
1. Check `voice/speaker/speaker_encoder.py` — torch compat shim for `custom_fwd`/`custom_bwd`
2. Verify `models/speaker/` has `embedding_model.ckpt`, `hyperparams.yaml`, etc.
3. Check `SpeakerEncoder` loads on CPU: `Using device: cpu`

### Interruption Not Working

**Symptoms:** Speaking continues despite user talking

**Checklist:**
1. Check `voice/interrupt.py` — `_interrupt_energy_threshold` (default 0.015)
2. Verify `InterruptManager` receives mic RMS in callback
3. Check `voice_manager.set_speaking(True, interrupt_manager)` called

---

## LLM / API Issues

### OpenRouter 401 Unauthorized

**Fix:**
```bash
# Set API key
export OPENROUTER_API_KEY="sk-or-xxxx..."
# Or create .env file
echo "OPENROUTER_API_KEY=sk-or-xxxx..." > .env
```

### Circuit Breaker Open

**Log:** `Circuit OPEN — failing fast for 30s after 8 failures`

**Behavior:** Automatic 30s cooldown after 8 consecutive failures. Wait or restart.

### Ollama Failover Not Working

**Checklist:**
1. `ollama serve` running? (not installed on this machine as of Nov 2026 — the live path is OpenRouter cloud)
2. `curl http://localhost:11434/api/tags` returns 200?
3. Model pulled: `ollama pull qwen2.5:3b-instruct-q4_k_m` (must match `LLM_MODEL`)
4. Preference set: `LLM_PROVIDER=ollama` when you want local-first ordering

---

## Memory / Vault Issues

### Vault Sync Fails

**Symptoms:** Graph/vault not updating

**Checklist:**
1. Check `OBSIDIAN_VAULT` path in `config/paths.py`
2. Verify write permissions on vault directory
3. Check `knowledge/obsidian_writer.py` logs

### Memory Not Persisting

**Checklist:**
1. `VectorStore` using ChromaDB at `vector_memory/chroma.sqlite3` (`VECTOR_DB_DIR` in `config/paths.py`); `data/vector_db/` is a legacy leftover from before the rename
2. `WriteJournal` flushes every 5s or 100 entries
3. Shutdown flushes on `app.shutdown()`
4. SQLite state DB is `memory/mai.db`

---

## Performance Issues

### High Latency

| Component | Check |
|-----------|-------|
| LLM | Provider latency (OpenRouter vs Ollama), context size |
| STT | Model size (tiny vs base), CPU vs GPU |
| TTS | Kokoro model, streaming chunk size |
| Memory | Vector store size, embedding cache hits |
| Voice | VAD threshold, frame size |

### High Memory Usage

| Cause | Fix |
|-------|-----|
| Embedding cache unbounded | Set `EMBEDDING_CACHE_MAX_SIZE` |
| Vector store growing | Run consolidation, check `enforce_cap()` |
| Ollama model loaded | Use smaller model or CPU offload |

---

## Debug Endpoints

| Endpoint | Use |
|----------|-----|
| `GET /api/health` | Liveness — all core subsystems |
| `GET /api/status` | Readiness — emotion, goals, world model |
| `GET /api/voice/status` | Voice pipeline component status |
| `GET /api/inspector/events` | Live event stream |
| `GET /api/inspector/traces` | Cognitive traces |
| `GET /api/memory/stats` | Memory pipeline stats |

---

## Log Locations

| Log Type | Location |
|----------|----------|
| Application | `logs/` (structured JSON) |
| Cognitive audit | `logs/cognitive_audit/` |
| Orchestrator transitions | `logs/orchestrator/transitions.jsonl` |
| Cognitive audit / Tracer (PII-redacted) | `logs/cognitive_audit/*.json` |
| Voice metrics | `logs/` (via `VoiceMetrics`) |

---

## Escalation

If issue persists:
1. Check `logs/` for structured error
2. Enable `DEBUG_MODE=true` in config
3. Check `stderr` for Python tracebacks
4. Open GitHub issue with logs + config

---

*Last updated: 2026-11-08 — voice diagnostics updated for the Kyutai/`STT_BACKEND` path, the whole-utterance gate, and the self-hearing fix.*