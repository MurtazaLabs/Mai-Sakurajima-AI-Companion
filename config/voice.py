import os
from pathlib import Path

from config.paths import ROOT_DIR

WHISPER_MODEL = "small"
VOICE_SAMPLE_RATE = 16000
SILENCE_THRESHOLD = 0.01
SILENCE_DURATION = 1.2
MAX_RECORDING_SECONDS = 60
KOKORO_VOICE = "af_heart"
KOKORO_LANG_CODE = "a"
USE_CUSTOM_VOICE = True
VOICE_COOLDOWN = 2.0
WAKE_COOLDOWN = 2.0

# STT backend selection — "whisper" (default) | "kyutai".
# Kyutai (kyutai/stt-1b-en_fr-trfs, streaming, semantic VAD) is gated on the
# Phase 1 RTF benchmark (docs/Mai_documentation/03-Features/stt-kyutai-replacement-plan.md),
# RTF <= 0.7 on this machine; faster-whisper stays the fallback backend.
STT_BACKEND = os.environ.get("STT_BACKEND", "whisper").strip().lower()
KYUTAI_STT_DIR = str(Path(
    os.environ.get("KYUTAI_STT_DIR", str(ROOT_DIR / "kyutai STT" / "stt-1b-en_fr-trfs"))))

# VAD settings
VAD_THRESHOLD = 0.5 
# 0.7s (was 0.5): 500ms cut natural mid-sentence pauses short. The extra tail is
# trimmed before STT (UTTERANCE_TRAILING_KEEP), so this costs no decode time.
VAD_SILENCE_TIMEOUT = 0.7
VAD_MIN_RECORDING = 0.5
VAD_MAX_RECORDING = 30.0
# Pre-roll: audio kept from before the VAD onset so the first syllable survives.
VAD_PRE_ROLL = 0.5
VAD_FRAME_SIZE = 512

# Whole-utterance VAD gate — rejects noise-only recordings (fan/hiss) before
# they reach STT. mean = average speech probability across the utterance,
# ratio = fraction of frames above VAD_THRESHOLD. Reject when mean < MIN_MEAN
# or ratio < MIN_RATIO. Both are tuned via the fan-noise rejection test.
# Whole-utterance VAD gate thresholds — calibrated from live log 2026-10-09:
# fan/noise bursts scored mean<=0.10, ratio<=0.04; real speech attempts scored
# mean 0.23-0.26, ratio 0.19-0.22 (conversation noise always had ratio 0.00).
# Bias toward accepting: a false accept costs one whisper call (no wake-word
# match = harmless), a false reject makes Mai look dead to the user.
UTTERANCE_VAD_MIN_MEAN = 0.15
UTTERANCE_VAD_MIN_RATIO = 0.10
UTTERANCE_VAD_MAX_FRAMES = 256

# Minimum VAD-voiced time (ratio x duration) before STT is worth calling.
# Kills sub-word fragments (measured: a 0.58s click scores ratio 0.06 -> 0.03s
# voiced) that cost a full 2-3s transcription and return ""; real speech clears
# it easily ("hey mai" ~0.45s at ratio 0.6 -> 0.27s voiced).
UTTERANCE_MIN_VOICED = 0.20

# Trailing silence kept after the last voiced frame (the rest of the
# silence_timeout window is trimmed, so longer patience is free).
UTTERANCE_TRAILING_KEEP = 0.2

# Noise filter settings
NOISE_LOW_CUT = 80.0
NOISE_HIGH_CUT = 7600.0
NOISE_FLOOR_PERCENTILE = 10
NOISE_REDUCTION_DB = 6.0

# Echo canceller settings
ECHO_FILTER_LENGTH = 1024
ECHO_ADAPTATION_RATE = 0.01
ECHO_MAX_DELAY = 0.3

# Utterance segmenter settings
UTTERANCE_SILENCE_THRESHOLD = 0.01
UTTERANCE_MIN_SILENCE = 0.6
UTTERANCE_MIN_DURATION = 0.3
UTTERANCE_MAX_DURATION = 30.0

# Adaptive noise filter settings
ADAPTIVE_NOISE_ENABLED = True
ADAPTIVE_NOISE_INTERVAL = 2.0
ADAPTIVE_NOISE_DECAY = 0.85
ADAPTIVE_NOISE_MIN_FRAMES = 10

# Full AEC settings
FULL_AEC_FILTER_LENGTH = 2048
FULL_AEC_ADAPTATION_RATE = 0.01
FULL_AEC_MAX_DELAY = 0.5
# near/far power ratio that counts as double talk. Measured with a 0.35/0.15
# two-path echo: the ratio sits around 0.15-0.4 with echo alone, so the old 0.3
# latched into permanent double-talk and the filter never adapted (1.2 dB, all
# from clipping). At 1.0 the same room cancels 18 dB with the user's speech
# untouched. Raise it if soft speech over her voice gets filtered.
FULL_AEC_DOUBLE_TALK_THRESHOLD = 1.0
FULL_AEC_RESIDUAL_TAIL = 256
FULL_AEC_HANGOVER = 20

# Voice emotion detector settings
EMOTION_DETECTOR_FRAME_MS = 30
EMOTION_DETECTOR_HISTORY_SECONDS = 2.0

# Diarization settings
DIARIZATION_MIN_SEGMENT_MS = 200
DIARIZATION_MAX_SEGMENT_MS = 3000
DIARIZATION_SIMILARITY_THRESHOLD = 0.65

# Microphone device — single source of truth across the entire app.
# Set to an integer device index to pin a specific mic, or None for auto-detect.
# Auto-detect logic in Microphone.start() selects the first input-capable device.
MICROPHONE_DEVICE = None

# M4 · Voice renderer seam — which renderer impl backs the character speech
# pipeline ("kokoro" = default; "stub" = dry-run / recording).
VOICE_RENDERER = "kokoro"
