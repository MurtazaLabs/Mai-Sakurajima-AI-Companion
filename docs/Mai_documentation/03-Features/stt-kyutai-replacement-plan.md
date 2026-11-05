# STT Replacement Plan — faster-whisper → Kyutai 1B

Status: **NO-GO on the 0.7 gate, but user opted in anyway (2026-10-25): `.env` sets `STT_BACKEND=kyutai` — ~2x vs the whisper baseline in steady state (~4x for longer turns); faster-whisper remains the permanent fallback; product default (config) stays "whisper"**
Date: 2026-10-09 (updated 2026-10-25)
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

## 3. Current state (re-verified 2026-10-25)

- **Model weights (dsm format): COMPLETE** (Phase 0, Oct 9).
  Location: `E:\Mai_ai\kyutai STT\delayed-streams-modeling\stt-1b-en_fr\`
  (dsm layout, clonable source — NOT loadable by transformers directly).
- **Transformers -trfs checkpoint (Phase 1 route): downloading.**
  Location: `E:\Mai_ai\kyutai STT\stt-1b-en_fr-trfs\` (config, tokenizer,
  preprocessor + single model.safetensors ~1.9GB; verified via `HfApi` +
  `preprocessor_config.json` stating `sampling_rate: 24000`).
- **transformers 4.57.6** (upgraded from 4.49.0 in-env on 2026-10-25 —
  Kyutai native support needs >= 4.53; `KyutaiSpeechToTextProcessor` import
  verified). `pip check` clean; faster_whisper/speechbrain/kokoro imports OK.
- **torch 2.3.0+cpu, `cuda: False`** — the doc's earlier "torch 2.14.0 /
  transformers 5.17.0" note was wrong; these are the real versions.
- **Env fix shipped with the upgrade:** transformers >= 4.53 imports
  torchvision inside the Albert chain; a first-time torchvision import runs
  `torch.library.impl_abstract`, whose inspect sys.modules walk trips
  speechbrain 1.x's lazy deprecated-alias placeholders (`import k2` → missing)
  and kills the unrelated kokoro import. Defused in
  `voice/speaker/speaker_encoder.py` (`_defuse_speechbrain_deprecated_redirects`,
  called after every speechbrain import) + pinned by
  `tests/test_speaker_encoder_compat.py` (4 tests) and
  `tests/test_stt_kyutai.py` (9 tests).
- Integration points (the swap surface):
  - `voice/stt.py` — `FasterWhisperSTT`: lazy `_ensure_model()`,
    `transcribe(audio: NDArray[float32], language="en", initial_prompt) -> str`,
    `set_model()`, `stats()`, raises `TranscriptionUnavailable` on load
    failure. Input: 16 kHz float32 mono (full utterance clip).
  - `app/builders/voice.py` — single construction site; now selects the
    backend by `cfg.voice_config.STT_BACKEND` ("whisper" default).
  - `config/voice.py` — `STT_BACKEND` (env-switchable) + `KYUTAI_STT_DIR`,
    re-exported via `config/settings.py`.
  - Callers: `voice/voice_manager.py` `_transcribe()` (after the Phase 0
    `UTTERANCE_VAD_*` whole-utterance gate; diarization labels speakers on the
    full clip — does not slice), `voice/wake_detector.py`, and
    `core/os_kernel.py` conversation path.</think><tool_call>edit<arg_key>newString</arg_key><arg_value>## 4. Architecture (shipped — 2026-10-25)

```
VoiceManager / kernel
        │  transcribe(clip) -> str
        ▼
    app.stt  (factory selects by STT_BACKEND)
        ├── KyutaiSTT        (voice/stt_kyutai.py — transformers -trfs path)
        └── FasterWhisperSTT (default backend + permanent fallback)
```

- **Implemented** as `voice/stt_kyutai.py`: lazy `from_pretrained` load,
  `transcribe()` (16 kHz in → 24 kHz Mimi path → generate → decode),
  `stats()` incl. `avg_rtf`, public `.model`/`.sample_rate` for callers, and
  **permanent** faster-whisper fallback on any load or runtime failure.
- `STT_BACKEND` config select in `app/builders/voice.py` — default stays
  `"whisper"`; nothing changes without the env var.
- Hard fallback (§ plan): Kyutai load failure at first use, or a runtime
  failure mid-call, downgrades the backend permanently to faster-whisper
  (tested: `tests/test_stt_kyutai.py`).

## 5. Phases

### Phase 0 — Model acquisition — DONE
Downloaded `kyutai/stt-1b-en_fr` (dsm format), verified complete (§3).

### Phase 1 — Environment + benchmark — COMPLETE: NO-GO (2026-10-25)
1. CPU bench: RTF 6.09 / 4.78 / 4.38, **median 4.78** vs gate 0.7 — whisper-class.
2. GPU contingency (torch 2.3.0+cu121 + torchvision 0.18.0+cu121, Quadro
   T1000, bf16 2.3GB VRAM, dynamo→eager — no triton on Windows):
   **median RTF 1.219, avg 1.200 (device=cuda verified)** — ~4x faster than
   the whisper baseline (~4.9) but **fails the 0.7 gate** (a ~1s fixed
   overhead + eager-run compiled regions). **User decision (same day):
   opted in anyway via `.env` `STT_BACKEND=kyutai`** — config default stays
   "whisper"; kyutai is machine-level opt-in with permanent whisper fallback.
   Steady-state evidence: RTF 1.12-1.25 on warm shapes (long turns ~4x vs
   the 4.9 whisper baseline; short clips bound ~2.4s absolute vs whisper's
   ~3.0s). Real-speech round-trip verbatim (kokoro TTS -> wav -> kyutai).
   Loader bugs found + fixed by the first (invalid) bench attempt:
   - `ProcessorMixin.__call__` binds positional args to `images` in
     transformers 4.57 — audio MUST be keyword-passed (`processor(audio=x)`);
     the model card's positional example is outdated for 4.57.x.
   - bench script's device report was hardcoded "cpu" — now prints
     `stt._device` + final stats (the earlier "GO 0.566 / 0.598" prints were
     invalid whisper-fallback artifacts, not kyutai numbers).

### Phase 2 — Integration — SHIPPED (2026-10-25, gated by tests)
1. Implement `KyutaiSTT` behind the shared interface (§4).
2. `STT_BACKEND` config + factory in `app/builders/voice.py`.
3. Unit tests: interface parity with `FasterWhisperSTT`, fallback-on-failure,
   config switch honored. Gate: full suite green (2,015 passed / 2 skipped
   under torch cu121), no behavior change with default `STT_BACKEND="whisper"`.

### Phase 3 — Live validation — USER-ENABLED (2026-10-25); watch the logs
1. Bench GO required first (Phase 1 numbers below).
2. Boot: `set STT_BACKEND=kyutai` then `python run_daemon.py` (window) or
   `python run.py --mode daemon --no-window`; expect
   `[KyutaiSTT] Loading checkpoint ... Ready in Xs` on first voice turn.
3. Real conversation test: wake → gate (`[Gate] Accepted speech`) →
   kyutai transcribe → reply; log timestamps give per-turn STT latency to
   compare against the faster-whisper baseline **measured from `logs/mai.log`
   (Sep 12 runs, whisper `small`, cpu int8)**: 0.61s utterance → ~3.0s
   transcription (RTF ≈ 4.9); wake-loop outliers 11s/175s. So the 0.7 gate
   implies an expected ≥7x per-turn latency win.
4. Regression checks: wake word path (`WakeThread`), `STT_BACKEND=whisper`
   boot still identical, speaker embedding still labels the user.
5. Memory/VRAM: monitor process RSS/VRAM beside Kokoro TTS under load
   (kyutai fp32 ~2.7-3.5GB RAM on CPU; VRAM stays free unless CUDA torch is
   installed after a failed CPU gate).
6. Promotion: switch default to `"kyutai"` ONLY after a clean multi-session
   live run (edit `config/voice.py` default). faster-whisper stays as the
   permanent fallback.

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
- 2026-10-25: User go-ahead ("start building it") for Phases 1+2. transformers
  upgraded to 4.57.6; -trfs checkpoint route chosen (dsm clone not
  transformers-loadable); KyutaiSTT + STT_BACKEND + permanent whisper fallback
  shipped behind the unchanged default; RTF benchmark pending the weight
  download (first attempt stalled → restarted; hub `snapshot_download`
  stalled twice → completed via resumable curl, sha256 verified).
- 2026-10-25: **Bench verdict NO-GO** — CPU median RTF 4.78, GPU (torch
  2.3.0+cu121 bf16, eager under no-triton Windows) median 1.219; both above
  the 0.7 gate. Default backend stays faster-whisper; kyutai is shipped code,
  opt-in only. `processor(audio=x)` keyword contract fixed (positional binds
  to `images` in transformers 4.57); bench device report made honest
  (hardcoded "cpu" invalidated an earlier false GO); environment pins
  documented: PyPI Windows torch wheels are cpu-only — cu121 comes from the
  pytorch extra index (both requirements files note the override).
- 2026-10-25: **User opted in** (".env → STT_BACKEND=kyutai") after seeing the
  ~4x claim. Real-speech round-trip verified live (kokoro TTS → wav → kyutai):
  `Hello Mai, the weather is really nice today, is it not?` heard verbatim
  except `Mai`→`my`. Two follow-ups shipped:
  - **second-bucket quantization** in `_kyutai_transcribe` — dynamo caches by
    input shape, and continuous utterance lengths would retrace every call in
    production; clips are now zero-padded to whole-second buckets (measured:
    cold shape 8.79s → same-bucket 2.39s; steady RTF 1.12-1.25 on repeat
    shapes; short-clip absolute steps to ~2.4s).
  - `test_stt_backend_*` made ambient-aware — they reloaded config under
    whatever the .env sets instead of hardcoding "whisper".
