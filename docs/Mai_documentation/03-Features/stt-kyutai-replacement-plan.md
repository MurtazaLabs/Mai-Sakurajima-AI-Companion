# STT Replacement Plan — faster-whisper → Kyutai 1B

Status: **Phase 0 complete, Phase 1 pending go/no-go**
Date: 2026-10-09
Owner: Syed Murtaza / Mai AI Suite

---

## 1. Motivation

Current STT is `faster-whisper` (`small`, CPU int8) batch transcription of whole
utterances (`voice/stt.py`). Problems observed in live runs:

- **Latency**: transcription starts only after the utterance ends; Whisper's
  full-clip pass adds hundreds of ms to every voice turn on top of LLM+TTS.
- **Hallucination on noise**: before the Phase 0 VAD gate, fan/hiss-only audio
  was normalized to full scale and Whisper produced hallucinated text
  (`Heard: "it's awesome."`). A streaming model with a semantic VAD has a
  fundamentally better failure mode.

Kyutai STT (`kyutai/stt-1b-en_fr`) is a decoder-only streaming speech-to-text
model: 0.5s audio delay, incremental tokens, built-in semantic VAD. It can
produce text while the user is still speaking.

## 2. Model choice

| Model | Size | Delay | Languages | Verdict |
|---|---|---|---|---|
| `kyutai/stt-1b-en_fr` (~1B) | ~2.3GB total | 0.5s | EN + FR | **Selected** |
| `kyutai/stt-2.6b-en` (~2.6B) | ~5GB+ | 2.5s | EN | Rejected — 2.5s delay defeats the purpose; weights exceed the T1000's 4GB VRAM budget; download never completed |

Hardware context: Quadro T1000 (4GB VRAM), 12 CPUs, 16GB RAM. The 1B fits in
VRAM with headroom (nothing else is on the GPU today — TTS is Kokoro/CPU, LLM
is cloud).

## 3. Current state (verified 2026-10-09)

- **Model download: COMPLETE** (Phase 0 done).
  Location: `E:\Mai_ai\kyutai STT\delayed-streams-modeling\stt-1b-en_fr\`
  - `model.safetensors` — 1886.8 MB
  - `mimi-pytorch-e351c8d8@125.safetensors` — 366.8 MB (Mimi neural codec)
  - `tokenizer_en_fr_audio_8000.model`, `config.json`, README (model card)
  - No incomplete Git-LFS objects.
  - Format: Kyutai's native `delayed-streams-modeling` (dsm) layout, cloned
    from HuggingFace.
- **transformers 5.17.0 installed** — satisfies the ≥4.53 requirement for the
  native transformers checkpoint `kyutai/stt-1b-en_fr-trfs`.
- **torch 2.14.0+cpu, `cuda: False`** — GPU currently unused; this is the only
  real environment blocker.
- Integration points (the swap surface):
  - `voice/stt.py` — `FasterWhisperSTT`: lazy `_ensure_model()`,
    `transcribe(audio: NDArray[float32], language="en", initial_prompt) -> str`,
    `set_model()`, `stats()`, raises `TranscriptionUnavailable` on load
    failure. Input: 16 kHz float32 mono (full utterance clip).
  - `app/builders/voice.py:53` — single construction site
    (`app.stt = FasterWhisperSTT()`), injected into `VoiceManager`.
  - `config/voice.py:1` — `WHISPER_MODEL = "small"`.
  - Callers: `voice/voice_manager.py` `_transcribe()` (after the Phase 0
    `UTTERANCE_VAD_*` whole-utterance gate; diarization labels speakers on the
    full clip — does not slice) and `core/os_kernel.py` conversation path.

## 4. Architecture (target)

```
VoiceManager / kernel
        │  transcribe(clip) -> str
        ▼
   STTBackend (same interface as FasterWhisperSTT)
        ├── KyutaiSTT        (new — transformers -trfs path)
        └── FasterWhisperSTT (kept as default + fallback)
```

- New `KyutaiSTT` class in `voice/stt.py` (or `voice/stt_kyutai.py`) with the
  **exact same public interface**: lazy model load, `transcribe()`,
  `TranscriptionUnavailable` contract, `stats()`.
- Config switch: `STT_BACKEND` in `config/voice.py` — `"whisper"` (default)
  | `"kyutai"`. Factory selection in `app/builders/voice.py`.
- Hard fallback: if `KyutaiSTT._ensure_model()` fails at boot or raises at
  runtime, log and fall back to `FasterWhisperSTT` — voice must never die
  because of an experimental backend.

## 5. Phases

### Phase 0 — Model acquisition — DONE
Downloaded `kyutai/stt-1b-en_fr` (dsm format), verified complete (§3).

### Phase 1 — Environment + benchmark — PENDING GO/NO-GO
1. Install CUDA torch build (replace `torch 2.14.0+cpu` with a `+cu12x` wheel;
   driver 580.92 supports current CUDA). CPU-only remains an acceptable
   outcome of the benchmark.
2. Decide checkpoint route:
   - **Preferred**: native transformers `kyutai/stt-1b-en_fr-trfs`
     (`AutoModel`/`AutoProcessor`, transformers 5.x) — may require a separate
     ~2–3GB download since the dsm weight layout may not load directly;
   - **Fallback**: load the already-downloaded local dsm clone via the
     `delayed-streams-modeling` package.
3. **Benchmark gate: RTF ≤ 0.7** on this machine (representative 2–8s
   utterances, batch-of-one, model resident). Measure CPU-only first; install
   CUDA torch only if CPU fails the gate.
   - Script: one-off `scripts/bench_kyutai.py` (wall-clock transcribe time ÷
     audio duration, median of ≥10 runs).
4. Output: recorded RTF numbers (CPU and, if needed, GPU) + GO/NO-GO.

### Phase 2 — Integration
1. Implement `KyutaiSTT` behind the shared interface (§4).
2. `STT_BACKEND` config + factory in `app/builders/voice.py`.
3. Unit tests: interface parity with `FasterWhisperSTT`, fallback-on-failure,
   config switch honored. Gate: full suite green, no behavior change with
   default `STT_BACKEND="whisper"`.

### Phase 3 — Live validation
1. Daemon restart, `STT_BACKEND=kyutai`.
2. Real conversation test: wake → gate → transcribe → reply; compare turn
   latency vs the faster-whisper baseline (log timestamps exist for both).
3. Memory/VRAM check alongside Kokoro TTS under load.
4. Promotion: switch default to `"kyutai"` only after a clean multi-session
   live run; faster-whisper stays as the permanent fallback backend.

### Phase 4 — Deferred (not in scope now)
- True streaming transcription feeding partial hypotheses into the
  interrupt/endpointing loop (Kyutai emits text mid-utterance; the current
  pipeline is whole-utterance).
- Possible synergy/replacement of the Phase 0 whole-utterance VAD gate with
  Kyutai's semantic VAD — only after Phase 3 evidence.
- FR language usage / language auto-detect.

## 6. Risks

| Risk | Mitigation |
|---|---|
| CPU-only RTF > 0.7 | Gate catches it; CUDA torch install is the fix (VRAM is free) |
| dsm weights not loadable by transformers 5.x | Re-download `-trfs` checkpoint; local dsm clone + dsm package as offline fallback |
| transformers 5.17 API drift vs 4.53-era docs | Integration written against installed version; unit tests pin the load path |
| VRAM pressure with TTS later moved to GPU | 1B model leaves ~1.5GB headroom; 2.6B stays rejected |
| Voice regression | `STT_BACKEND` default stays `whisper`; hard runtime fallback (§4) |

## 7. Decisions log

- 2026-10-09: 1B EN/FR selected over 2.6B EN (delay + VRAM).
- 2026-10-09: Plan documented; Phase 0 confirmed complete by file inspection.
- Pending: user go/no-go for Phase 1 (CUDA torch + RTF benchmark).
