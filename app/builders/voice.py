import logging

import app.config_loader as cfg
from app.metadata import tag_service
from core.state.per_person_relationship import PerPersonRelationshipManager
from voice.kokoro_tts import KokoroTTS
from voice.realtime import RealtimeVoice
from voice.speaker import SpeakerManager
from voice.stt import FasterWhisperSTT
from voice.wake_word import WakeWord

logger = logging.getLogger("Mai")


def build(app):
    logger.info("    Building TTS...")
    try:
        app.tts = KokoroTTS()
        tag_service(app, "tts", "KokoroTTS", "Voice")
        logger.info("    ✓ KokoroTTS")
    except Exception as e:
        logger.warning("    TTS failed to load: %s", e)
        app.tts = None

    logger.info("    Building RealtimeVoice...")
    app.voice = RealtimeVoice(tts_engine=app.tts)
    if app.tts is None:
        logger.warning("    ⚠ RealtimeVoice: NO TTS ENGINE — voice output will be text-only")
    tag_service(app, "voice", "RealtimeVoice", "Voice")
    logger.info("    ✓ RealtimeVoice")

    # M4 · Voice renderer seam — character speech pipeline (SpeechStylePlanner
    # → ProsodyPlanner → VoiceRenderer) layered on top of the same TTS.
    logger.info("    Building SpeechStylePlanner...")
    from voice.prosody import ProsodyPlanner
    from voice.renderer import create_renderer
    from voice.speech_style import SpeechStylePlanner
    app.speech_style_planner = SpeechStylePlanner()
    tag_service(app, "speech_style_planner", "SpeechStylePlanner", "Voice")
    logger.info("    ✓ SpeechStylePlanner")
    app.prosody_planner = ProsodyPlanner()
    tag_service(app, "prosody_planner", "ProsodyPlanner", "Voice")
    logger.info("    ✓ ProsodyPlanner")
    try:
        app.voice_renderer = create_renderer(cfg.voice_config.VOICE_RENDERER, tts=app.tts)
        tag_service(app, "voice_renderer", "VoiceRenderer", "Voice", active=True)
        logger.info("    ✓ VoiceRenderer (%s)",
                    app.voice_renderer.name if app.voice_renderer else "none")
    except Exception as e:
        logger.warning("    VoiceRenderer failed to build: %s", e)
        app.voice_renderer = None

    if getattr(cfg.voice_config, "STT_BACKEND", "whisper") == "kyutai":
        from voice.stt_kyutai import KyutaiSTT
        app.stt = KyutaiSTT()
        logger.info("    ✓ STT: Kyutai (streams, falls back to faster-whisper on any failure)")
    else:
        app.stt = FasterWhisperSTT()

    try:
        if cfg.voice_config.ADAPTIVE_NOISE_ENABLED:
            from voice.adaptive_noise_filter import AdaptiveNoiseFilter
            app.adaptive_noise = AdaptiveNoiseFilter(
                sample_rate=app.stt.sample_rate,
                low_cut=cfg.voice_config.NOISE_LOW_CUT, high_cut=cfg.voice_config.NOISE_HIGH_CUT,
                noise_floor_percentile=cfg.voice_config.NOISE_FLOOR_PERCENTILE,
                reduction_db=cfg.voice_config.NOISE_REDUCTION_DB,
                adaptation_interval=cfg.voice_config.ADAPTIVE_NOISE_INTERVAL,
                adaptation_decay=cfg.voice_config.ADAPTIVE_NOISE_DECAY,
                min_profile_frames=cfg.voice_config.ADAPTIVE_NOISE_MIN_FRAMES,
            )
            tag_service(app, "adaptive_noise", "AdaptiveNoiseFilter", "Voice")
            logger.info("    ✓ AdaptiveNoiseFilter")
        from voice.full_aec import FullAEC
        app.full_aec = FullAEC(
            sample_rate=app.stt.sample_rate,
            filter_length=cfg.voice_config.FULL_AEC_FILTER_LENGTH,
            adaptation_rate=cfg.voice_config.FULL_AEC_ADAPTATION_RATE,
            max_echo_delay=cfg.voice_config.FULL_AEC_MAX_DELAY,
            double_talk_threshold=cfg.voice_config.FULL_AEC_DOUBLE_TALK_THRESHOLD,
            residual_tail_length=cfg.voice_config.FULL_AEC_RESIDUAL_TAIL,
            hangover_frames=cfg.voice_config.FULL_AEC_HANGOVER,
        )
        tag_service(app, "full_aec", "FullAEC", "Voice")
        logger.info("    ✓ FullAEC")
        from voice.emotion_detector import VoiceEmotionDetector
        app.emotion_detector = VoiceEmotionDetector(
            sample_rate=app.stt.sample_rate, frame_ms=cfg.voice_config.EMOTION_DETECTOR_FRAME_MS,
            history_seconds=cfg.voice_config.EMOTION_DETECTOR_HISTORY_SECONDS,
        )
        tag_service(app, "emotion_detector", "VoiceEmotionDetector", "Voice")
        logger.info("    ✓ VoiceEmotionDetector")
        from voice.diarization import DiarizationEngine
        app.diarization = DiarizationEngine(
            sample_rate=app.stt.sample_rate,
            min_segment_samples=int(app.stt.sample_rate * cfg.voice_config.DIARIZATION_MIN_SEGMENT_MS / 1000),
            max_segment_samples=int(app.stt.sample_rate * cfg.voice_config.DIARIZATION_MAX_SEGMENT_MS / 1000),
            similarity_threshold=cfg.voice_config.DIARIZATION_SIMILARITY_THRESHOLD,
        )
        tag_service(app, "diarization", "DiarizationEngine", "Voice")
        logger.info("    ✓ DiarizationEngine")
    except Exception as e:
        logger.warning("    Deferred voice components: %s", e)

    logger.info("    Building VoiceManager...")
    try:
        from voice.voice_manager import VoiceManager
        app.voice_manager = VoiceManager(
            sample_rate=app.stt.sample_rate, vad_threshold=0.5,
            silence_timeout=cfg.voice_config.VAD_SILENCE_TIMEOUT, min_recording=0.5, max_recording=30.0,
            stt=app.stt, adaptive_noise_filter=getattr(app, 'adaptive_noise', None),
            full_aec=getattr(app, 'full_aec', None),
            emotion_detector=getattr(app, 'emotion_detector', None),
            diarization_engine=getattr(app, 'diarization', None),
            event_bus=app.event_bus,
        )
        tag_service(app, "voice_manager", "VoiceManager", "Voice", active=True)
        app.health_registry.register("voice_manager", component=app.voice_manager)
        app.health_registry.heartbeat("voice_manager")
        # AEC far-end reference: without this the echo canceller never sees
        # what Mai is playing and stays a pass-through.
        if getattr(app, "voice", None) is not None:
            app.voice_manager.attach_playback_tap(app.voice.player)
        logger.info("    ✓ VoiceManager")
    except Exception as e:
        logger.warning("    Voice manager failed to load: %s", e)
        app.voice_manager = None

    logger.info("    Building WakeWord...")
    app.wake = WakeWord(voice_manager=app.voice_manager)
    tag_service(app, "wake", "WakeWord", "Voice", active=True)
    logger.info("    ✓ WakeWord")

    logger.info("    Building SpeakerManager...")
    try:
        app.speaker_manager = SpeakerManager(profiles_dir=str(cfg.ROOT_DIR / cfg.SPEAKER_PROFILES_DIR))
        tag_service(app, "speaker_manager", "SpeakerManager", "Voice")
        app.health_registry.register("speaker_manager", component=app.speaker_manager)
        app.health_registry.heartbeat("speaker_manager")
        logger.info("    ✓ SpeakerManager")
    except Exception as e:
        logger.warning("    Speaker manager failed to load: %s", e)
        app.speaker_manager = None

    logger.info("    Building PerPersonRelationshipManager...")
    try:
        app.per_person_relationship = PerPersonRelationshipManager(
            storage_dir=str(cfg.ROOT_DIR / "core" / "state" / "relationships"),
        )
        tag_service(app, "per_person_relationship", "PerPersonRelationshipManager", "Voice")
        app.health_registry.register("per_person_relationship", component=app.per_person_relationship)
        app.health_registry.heartbeat("per_person_relationship")
        logger.info("    ✓ PerPersonRelationshipManager")
    except Exception as e:
        logger.warning("    Per-person relationship manager failed: %s", e)
        app.per_person_relationship = None

    assert app.voice is not None
    assert app.stt is not None
