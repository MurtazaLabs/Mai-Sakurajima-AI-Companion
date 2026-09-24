# 07 — Voice Subsystem

> Digest of `SUBSYSTEM_DOCUMENTATION/voice.md`. Full: [[SUBSYSTEM_DOCUMENTATION/voice]], [[DATA_FLOW]] §6.

---

## Package Stats

`voice/` — 34 files, 4,346 lines.

## Mission

Full-duplex voice: wake word → listen → transcribe → understand → respond → speak, with interruption handling, speaker identity, noise suppression, and emotional coloring.

## Pipeline

```
WakeWord / hotkey → Mic capture (16k) → VAD → STT → IntentCore
    → Brain.think → KokoroTTS (emotion=) → StreamPlayer
    → InterruptManager (barge-in: mic RMS > threshold breaks speak_stream)
```

## Components

### Input / Front-End

- `WakeWordDetector` + `PorcupineDetector` (Picovoice); `VAD` (Silero, SHA-256-checksummed model download, load-failure latch).
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

- `listen()` 124-line method (P2); `_valid_audio()` extension-only check (P2); dead `noise_filter` param (P2); AEC has no live feed call sites (P2).

---

## Wiki Links

**Previous:** [[06-Agency Reasoning LLM & Execution]]  
**Next:** [[08-API Native & Surface]] — API, native, observability, prompt, plugins  
**Related:** [[01-Architecture/09-Events & Data Flow]] — voice event topics • [[02-Subsystems/Voice Pipeline]] — voice detail • [[03-Features/Native OS Bridge Architecture]] — tray/hotkey integration