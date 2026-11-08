# Voice Pipeline Reference

> Complete reference for the full-duplex voice pipeline — `voice/voice_manager.py`, `voice/vad.py`, `voice/stt.py`, `voice/stt_kyutai.py`, `voice/kokoro_tts.py`, `voice/stream_player.py`, `voice/interrupt.py`, `voice/speaker/`, `voice/emotion_detector.py`, `voice/full_aec.py`.
> Capability status: [[00-Overview/CURRENT_STATE]].

---

## Overview

Full-duplex voice: wake word → listen → transcribe → understand → respond → speak, with interruption handling, speaker identity, noise suppression, and emotional coloring.

**Architecture:** [[01-Architecture/07-Voice Subsystem]]

---

## Pipeline Flow

```
WakeWord / hotkey → Mic capture (16k) → Recorder
    → whole-utterance VAD gate (Phase 0, Oct 2026) → STT (full clip) → IntentCore
    → Brain.think / think_stream → KokoroTTS (emotion=) → StreamPlayer
    → InterruptManager (barge-in: mic RMS > threshold breaks speak_stream)
```

**Whole-utterance VAD gate (Phase 0, Oct 2026):** before *any* `stt.transcribe()`, the clip is scored by `VAD.utterance_score()` (Silero mean over ≤256 frames). Reject when `mean < 0.15` or `speech_ratio < 0.10` (`UTTERANCE_VAD_*` in `config/voice.py`, live-calibrated). Fail-open if VAD unavailable. Enforced in `VoiceManager._handle_wake_audio()` + `_transcribe()` and on the kernel's `return_audio` conversation path — this killed Whisper's hallucinated transcriptions of fan/hiss noise. Diarization (when active) only labels the dominant speaker on the **full clip** — regions are never sliced before STT.

---

## Components

### Wake Word Detection

| Component | File | Details |
|-----------|------|---------|
| `WakeWordDetector` | `wake_detector.py` | generic interface |
| `WakeWord` | `wake_word.py` | keyword definitions |

### Voice Activity Detection (VAD)

| Component | File | Details |
|-----------|------|---------|
| `VAD` | `vad.py` | Silero VAD; SHA-256-checksummed model download; **load-failure latch** (never retries download per chunk) |

### Audio Capture

| Component | File | Details |
|-----------|------|---------|
| `Microphone` | `microphone.py` | 16kHz capture; `stop()` clears callbacks (no accumulation) |
| `AudioBuffer` | `audio_buffer.py` | ring buffer for streaming |
| `Recorder` | `recorder.py` | utterance recording |
| `UtteranceSegmenter` | `utterance_segmenter.py` | segments continuous audio |

### Noise Suppression & Echo Cancellation

| Component | File | Details |
|-----------|------|---------|
| `AdaptiveNoiseFilter` | `adaptive_noise_filter.py` | adaptive spectral subtraction |
| `FullAEC` | `full_aec.py` | vectorized acoustic echo cancellation — **fed from the real playback stream** (`StreamPlayer` → `VoiceManager.attach_playback_tap()`, reference cleared by `end_playback()` at clip end); 18 dB measured on a synthetic room |
| `NoiseFilter` | `noise_filter.py` | legacy static filter (deprecated) |

**Echo mitigation in production:** the AEC now receives the true playback reference, but the recorder is still not fed while `VoiceManager._speaking` is true; the recorder buffer is cleared when speech starts, and `_discard_stale_utterances()` drains the queue at listen entry. Trade-off: the first syllable of an interruption may be lost. Unmuting (continuous capture) is the next step and needs live validation; also note the 2048-tap filter spans ~128 ms, so device latency beyond that (Bluetooth) would not be cancelled.

### Speech-to-Text (STT)

| Component | File | Details |
|-----------|------|---------|
| `FasterWhisperSTT` | `stt.py` | Faster-Whisper; RLock; lazy load; typed; TranscriptionUnavailable exception |
| `KyutaiSTT` | `stt_kyutai.py` | optional Kyutai 1B backend (`STT_BACKEND=kyutai`); lazy load; auto device (cuda/bf16 or cpu/fp32); **permanent whisper fallback** on load or runtime failure; dynamo disabled when Triton is absent |

### Text-to-Speech (TTS)

| Component | File | Details |
|-----------|------|---------|
| `KokoroTTS` | `kokoro_tts.py` | `generate(emotion=)` — text enhancement via `influence("word_choice")`; streams audio chunks |
| `StreamPlayer` | `stream_player.py` | playback with interruption support |

### Interruption Handling

| Component | File | Details |
|-----------|------|---------|
| `InterruptManager` | `interrupt.py` | private `_lock`; guarded `is_interrupted()`; mic RMS > 0.015 threshold during TTS triggers barge-in |

### Speaker Identity

| Component | File | Details |
|-----------|------|---------|
| `SpeakerIdentifier` | `speaker_identifier.py` | orchestrates speaker pipeline |
| `SpeakerManager` | `speaker/speaker_manager.py` | profile management |
| `SpeakerEncoder` | `speaker/speaker_encoder.py` | SpeechBrain embeddings; **torch 2.3 compat shim** for `custom_fwd`/`custom_bwd` |
| `SpeakerDatabase` | `speaker/speaker_database.py` | embedding storage |
| `SpeakerProfile` | `speaker/speaker_profile.py` | per-speaker data |

### Emotion & Diarization

| Component | File | Details |
|-----------|------|---------|
| `VoiceEmotionDetector` | `emotion_detector.py` | emotion from prosody + text |
| `DiarizationEngine` | `diarization.py` | VAD-based region detection + dominant-speaker labelling (no pyannote) |

---

## VoiceManager State Machine

`VoiceState` enum: `IDLE` → `LISTENING` → `PROCESSING` → `SPEAKING` (via events)

| Method | Behavior |
|--------|----------|
| `toggle()` | flip start/stop listening |
| `listen()` | thin wrapper (5 lines) over `_listen_impl()` |
| `speak(text, emotion)` | TTS → StreamPlayer with interrupt monitoring |
| `stop()` | immediate stop, clears state |
| `set_speaking(bool)` | marks playback (mutes recorder, clears its buffer) |

**Constructor:** `VoiceConfig` (single param) + `**kwargs` backward compat.

---

## Events (Publisher-Only)

| Topic | Payload |
|-------|---------|
| `state.voice.idle` | `{}` |
| `state.voice.listening` | `{speaker_id?}` |
| `state.voice.speaking` | `{text_preview, emotion}` |
| `state.voice.wake` | `{keyword}` |

**Consumers:** `api/stream_manager.py`, `api/ws_bridge.py`, `native/notifier.py`, `core/os_kernel.py`

**Single source of truth:** `voice/events.py` re-exports from `core/event_specs.py`

---

## Emotion Integration

1. **Response timing:** emotion-based pre-speech delay (0.1s happy → 0.8s sad)
2. **TTS enhancement:** emotion label passed to `KokoroTTS.generate(emotion=)` → `influence("word_choice")`
3. **Interrupt tolerance:** emotion influences `InterruptManager` threshold
3. **Snapshots:** emotion labels stored as BrainGraph nodes

---

## Resolved Issues (Previously "Known Issues")

- ✅ `listen()` refactored — now 5-line wrapper over a 51-line `_listen_impl()` (P2 fixed)
- ✅ `_valid_audio()` enhanced with header validation (P2 fixed)
- ✅ Dead `noise_filter` param in `VoiceManager` removed (P2 fixed)
- ✅ Self-hearing loop fixed (Oct 2026) — recorder muted while speaking, queue drained, greeting playback marked as speaking
- ✅ FullAEC divergence fixed — pass-through until playback is fed, norm floors raised, weights clipped, NaN reset
- ✅ AEC playback feed wired (Nov 2026) — `StreamPlayer` taps the real DAC stream into `FullAEC`; double-talk threshold corrected 0.3 → 1.0 (at 0.3 the detector latched permanently and the filter never adapted)
- ✅ `stt=MISSING` → `stt=ok` = lazy load on first use
- ✅ `eval()` in sandbox replaced with `exec()` for safety
- ✅ Type hints added to `stt.py` and `recorder.py`

## Open Issues

- ❌ AEC is wired but not exploited — the reference is real, yet the recorder stays muted during playback, so cancellation is not used. Unmute `voice_manager.py` and validate live (needs echo cancellation better than the mute guard on the actual mic/speaker path) (see [[00-Overview/CURRENT_STATE]] §4)
- ❌ Wake word costs a full STT pass; openWakeWord is installed but unwired (no "hey mai" model)
- ❌ Kyutai RTF (1.17–2.97) is above the 0.7 promotion gate — opt-in only
- ❌ True streaming STT is blocked by hardware (RTF < 1 required)

---

## Thread Safety

- `STT`: RLock
- `SpeakerEncoder`: RLock
- `InterruptManager`: private `_lock` (RLock)
- `VoiceManager._speaking`: lock-guarded
- Audio callbacks post to queues; heavy work on background workers
- `StreamPlayer`: queue-based, thread-safe

---

## Wiki Links

**Architecture:** [[01-Architecture/07-Voice Subsystem]] • [[01-Architecture/09-Events & Data Flow]] — voice events  
**Related:** [[01-Architecture/03-Core Brain Kernel & State]] — kernel integration • [[03-Features/Native OS Bridge Architecture]] — tray/hotkey voice toggle • [[02-Subsystems/Event System]] — event topics