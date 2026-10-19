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

# VAD settings
VAD_THRESHOLD = 0.5 
VAD_SILENCE_TIMEOUT = 0.5
VAD_MIN_RECORDING = 0.5
VAD_MAX_RECORDING = 30.0
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
FULL_AEC_DOUBLE_TALK_THRESHOLD = 0.3
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
