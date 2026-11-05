# 07 — Voice Subsystem

> Digest of `SUBSYSTEM_DOCUMENTATION/voice.md`. Full: [[SUBSYSTEM_DOCUMENTATION/voice]], [[DATA_FLOW]] §6.

---

## Package Stats

`voice/` — 32 files, 3,526 lines.

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

- `WakeDetector` (STT phrase matching, phonetic-close tolerance); `VAD` (Silero, SHA-256-checksummed model download, load-failure latch).
- `Microphone` (stop() clears callbacks — no accumulation), `AudioBuffer`, `Recorder`, `UtteranceSegmenter`.
- `AdaptiveNoiseFilter`, `FullAEC` (vectorized acoustic echo cancellation).

### Speech-to-Text / Text-to-Speech

- `STT` — whisper / faster-whisper / openai; RLock.
- `KokoroTTS` — `generate(emotion=)` text enhancement; `StreamPlayer` playback.

### Identity & Analysis

- `SpeakerIdentifier` + `speaker/` (Manager/Encoder/DB/Profile; encoder RLock).
- `VoiceEmotionDetector`, `DiarizationEngine` (who spoke when).
- `InterruptManager` — private lock, guarded `is_interrupted()`.

## VoiceManager State Machine

`VoiceState`: IDLE → LISTENING → PROCESSING → SPEAKING (via events); `toggle()`; `VoiceConfig` constructor (1 param); `_speaking` flag lock-guarded; `listen()` ~124-line hot path (P2 refactor).

## Events (Publisher-Only)

- `state.voice.idle` / `speaking` / `listening` / `wake` → UI projection.
- Consumers: `api/stream_manager.py`, `api/ws_bridge.py`, `native/notifier.py`, `core/os_kernel.py`.
- `voice/events.py` re-exports topics from `core/event_specs.py` (single source of truth).

## Known Issues

Former P2s all resolved (see [[02-Subsystems/Voice Pipeline]] — listen() refactored, `_valid_audio` header check, dead `noise_filter` param removed, AEC wired with live feed via `add_playback`). Current watch item: the STT-based wake path transcribes ambient noise - diagnostics only (Phase 0 gate suppresses it as a conversation-turn source). A dedicated wake-word engine is the planned fix.

---

## Wiki Links

**Previous:** [[06-Agency Reasoning LLM & Execution]]  
**Next:** [[08-API Native & Surface]] — API, native, observability, prompt, plugins  
**Related:** [[01-Architecture/09-Events & Data Flow]] — voice event topics • [[02-Subsystems/Voice Pipeline]] — voice detail • [[03-Features/Native OS Bridge Architecture]] — tray/hotkey integration