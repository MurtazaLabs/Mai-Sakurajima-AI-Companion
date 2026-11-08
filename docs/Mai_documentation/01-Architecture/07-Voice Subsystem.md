# 07 — Voice Subsystem

> Source docs `SUBSYSTEM_DOCUMENTATION/voice.md` / `DATA_FLOW.md` were merged and deleted; this page is the surviving reference. Capability status: [[00-Overview/CURRENT_STATE]].

---

## Package Stats

`voice/` — 33 files, 4,665 lines.

## Mission

Full-duplex voice: wake word → listen → transcribe → understand → respond → speak, with interruption handling, speaker identity, noise suppression, and emotional coloring.

## Pipeline

```
WakeWord / hotkey → Mic capture (16k) → Recorder
    → whole-utterance VAD gate (Phase 0, Oct 2026: VAD.utterance_score — mean ≥ 0.15, ratio ≥ 0.10; fail-open; noise-only clips rejected before Whisper)
    → STT (full clip — diarization labels the dominant speaker, never slices)
    → IntentCore
    → Brain.think / think_stream (stream-guarded) → KokoroTTS (emotion=) → StreamPlayer
    → InterruptManager (barge-in: mic RMS > threshold breaks speak_stream)
```

## Components

### Input / Front-End

- `WakeDetector` (STT phrase matching, phonetic-close tolerance). **openWakeWord 0.6.0 is installed but not wired** — no pretrained "hey mai" model exists (needs a custom verifier or synthetic training).
- `VAD` (Silero, SHA-256-checksummed model download, load-failure latch). Whole-utterance gate before every `transcribe()`: mean ≥ 0.15, speech ratio ≥ 0.10, voiced ≥ 0.20 s; fail-open when the model is unavailable.
- `Microphone` (stop() clears callbacks — no accumulation), `AudioBuffer`, `Recorder` (pre-roll ring buffer, trailing-silence trim to 0.2 s, non-finite/over-range chunk sanitization), `UtteranceSegmenter`.
- `AdaptiveNoiseFilter`, `FullAEC` (vectorized, but **strict pass-through — no playback feed is wired**; `send_playback_audio()` has no production caller).

### Speech-to-Text / Text-to-Speech

- `STT` — `FasterWhisperSTT` (default, RLock) and `KyutaiSTT` (opt-in via `STT_BACKEND=kyutai`, permanent whisper fallback on any load/runtime failure, dynamo disabled on Windows because Triton is absent). Measured Kyutai RTF 1.17–2.97 on the 4 GB T1000 — above the 0.7 promotion gate.
- `KokoroTTS` — `generate(emotion=)` text enhancement; `StreamPlayer` playback; sentence-level streaming fed by `brain.think_stream()`.

### Identity & Analysis

- `SpeakerIdentifier` + `speaker/` (Manager/Encoder/DB/Profile; encoder RLock; torch.amp compatibility shim so SpeechBrain works on torch 2.3).
- `VoiceEmotionDetector`, `DiarizationEngine` — diarization labels the dominant speaker but transcription always uses the **full clip**.
- `InterruptManager` — private lock, guarded `is_interrupted()`; barge-in on mic RMS threshold during playback.

## VoiceManager State Machine

`VoiceState`: IDLE → LISTENING → PROCESSING → SPEAKING (via events); `toggle()`; `VoiceConfig` constructor (1 param); `_speaking` flag lock-guarded; `listen()` is a 5-line wrapper over `_listen_impl()` (51 lines).

**Self-hearing protection (Oct 2026):** the recorder is not fed while `_speaking`, entering speech clears the recorder buffer, and `_discard_stale_utterances()` drains the queue at listen entry — audio captured during her own playback is never returned as a user turn.

## Events (Publisher-Only)

- `state.voice.idle` / `speaking` / `listening` / `wake` → UI projection.
- Consumers: `api/stream_manager.py`, `api/ws_bridge.py`, `native/notifier.py`, `core/os_kernel.py`.
- `voice/events.py` re-exports topics from `core/event_specs.py` (single source of truth).

## Known Issues

Former P2s resolved (listen() split, `_valid_audio` header check, dead `noise_filter` param, RLock everywhere). Open items:

- **AEC is not live.** `FullAEC` works but has no playback reference (`send_playback_audio()` is called only from tests), so it is a pass-through by design. Echo is mitigated by muting the recorder while `_speaking` — accepted trade-off: the first syllable of an interruption can be lost.
- **Wake word is an STT pass.** Every wake attempt costs a transcription (~1.7 s floor on this GPU). openWakeWord would cut that but has no "hey mai" model.
- **Kyutai is opt-in.** Above the RTF ≤ 0.7 gate; whisper remains the config default.
- **True streaming STT is hardware-blocked** — needs sustained RTF < 1; measured 1.17 at best on the T1000.

---

## Wiki Links

**Previous:** [[06-Agency Reasoning LLM & Execution]]  
**Next:** [[08-API Native & Surface]] — API, native, observability, prompt, plugins  
**Related:** [[01-Architecture/09-Events & Data Flow]] — voice event topics • [[02-Subsystems/Voice Pipeline]] — voice detail • [[03-Features/Native OS Bridge Architecture]] — tray/hotkey integration