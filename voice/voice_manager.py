import logging
import queue
import threading
import time

import numpy as np

_DEFAULT_PRIORITY = 2

from config.voice import (
    UTTERANCE_MIN_VOICED,
    UTTERANCE_TRAILING_KEEP,
    UTTERANCE_VAD_MAX_FRAMES,
    UTTERANCE_VAD_MIN_MEAN,
    UTTERANCE_VAD_MIN_RATIO,
    VAD_PRE_ROLL,
)
from voice.audio_buffer import AudioBuffer
from voice.microphone import Microphone
from voice.stt import TranscriptionUnavailable
from voice.voice_config import VoiceConfig
from voice.voice_state import VoiceState

logger = logging.getLogger(__name__)


class VoiceManager:
    def __init__(self, config: VoiceConfig | None = None, **kwargs):
        cfg = config or VoiceConfig()

        # Accept overrides via kwargs for backward compatibility
        self.sample_rate = kwargs.get("sample_rate", cfg.sample_rate)
        self.blocksize = kwargs.get("blocksize", cfg.blocksize)
        self.vad_threshold = kwargs.get("vad_threshold", cfg.vad_threshold)
        self.silence_timeout = kwargs.get("silence_timeout", cfg.silence_timeout)
        self.min_recording = kwargs.get("min_recording", cfg.min_recording)
        self.max_recording = kwargs.get("max_recording", cfg.max_recording)
        self.stt = kwargs.get("stt")
        self.speaker_manager = kwargs.get("speaker_manager")
        self.wake_detector = kwargs.get("wake_detector")
        self.speaker_identifier = kwargs.get("speaker_identifier")
        self.noise_filter = kwargs.get("noise_filter")
        self.utterance_segmenter = kwargs.get("utterance_segmenter")
        self.event_bus = kwargs.get("event_bus")
        # NOTE: P2-13 — adaptive_noise_filter removed; use noise_filter instead
        self.full_aec = kwargs.get("full_aec")
        self.emotion_detector = kwargs.get("emotion_detector")
        self.diarization_engine = kwargs.get("diarization_engine")
        self._microphone: Microphone | None = kwargs.get("microphone")
        self._audio_buffer: AudioBuffer | None = kwargs.get("audio_buffer")
        self._vad = kwargs.get("vad")
        self._recorder = kwargs.get("recorder")
        self._lock = threading.RLock()
        self._running = False
        self._state = VoiceState.OFF
        self._speaking = False
        # Eagerly init VAD so health check passes even before start()
        if self._vad is None:
            try:
                from voice.vad import VAD
                self._vad = VAD(threshold=self.vad_threshold, sample_rate=self.sample_rate)
                self._vad._load_model()
                logger.info("[VoiceManager] VAD model pre-loaded")
            except Exception as e:
                logger.warning("[VoiceManager] VAD pre-load failed: %s", e)
        self._interrupt_manager = None
        self._interrupt_energy_threshold = kwargs.get("interrupt_energy_threshold", cfg.interrupt_energy_threshold)
        metrics = kwargs.get("metrics")
        if metrics is not None:
            self._metrics = metrics
        else:
            from voice.metrics import VoiceMetrics
            self._metrics = VoiceMetrics()

        # Wake detection — background thread state
        self._wake_thread = None
        self._wake_stop = threading.Event()
        self._wake_event = threading.Event()
        # Shared utterance queue — recorder pushes, wake thread / listen() consume
        self._utterance_queue = queue.Queue(maxsize=100)

    def _on_utterance(self, audio):
        """Called from recorder (audio callback thread) when an utterance completes.
        Pushes to the queue for consumption by wake thread or listen()."""
        try:
            self._utterance_queue.put_nowait(audio)
        except queue.Full:
            logger.warning("[VoiceManager] Utterance queue full — discarding")

    def set_speaking(self, speaking, interrupt_manager=None):
        with self._lock:
            was_speaking = self._speaking
            self._speaking = speaking
        if interrupt_manager:
            self._interrupt_manager = interrupt_manager
        if speaking and not was_speaking and self._recorder is not None:
            # Drop anything the mic caught before playback began, so her own
            # voice never reaches the next user turn (live log 2026-10-27).
            self._recorder.stop()

    def is_speaking(self):
        with self._lock:
            return self._speaking

    @property
    def state(self):
        with self._lock:
            return self._state

    @property
    def wake_event(self):
        return self._wake_event

    def _set_state(self, new_state):
        with self._lock:
            old = self._state
            self._state = VoiceState(new_state) if isinstance(new_state, str) else new_state
        logger.debug("[VoiceManager] State: %s", self._state)
        if self.event_bus and old != self._state:
            from voice.events import VOICE_STATE_CHANGED, publish_voice, voice_state_changed_data
            publish_voice(self.event_bus, VOICE_STATE_CHANGED, voice_state_changed_data(old, new_state))

    def _ensure_components(self):
        from voice.recorder import Recorder
        from voice.vad import VAD
        if self._vad is None:
            self._vad = VAD(threshold=self.vad_threshold, sample_rate=self.sample_rate)
            self._vad._load_model()
        if self._audio_buffer is None:
            self._audio_buffer = AudioBuffer(max_seconds=3.0, sample_rate=self.sample_rate)
        if self._recorder is None:
            self._recorder = Recorder(
                sample_rate=self.sample_rate,
                silence_timeout=self.silence_timeout,
                min_recording=self.min_recording,
                max_recording=self.max_recording,
                vad=self._vad,
                pre_roll=VAD_PRE_ROLL,
                trailing_keep=UTTERANCE_TRAILING_KEEP,
            )
            self._recorder.set_callback(self._on_utterance)
        if self._microphone is None:
            self._microphone = Microphone(
                sample_rate=self.sample_rate,
                blocksize=self.blocksize,
            )
        if self.speaker_identifier is None and self.speaker_manager:
            from voice.speaker_identifier import SpeakerIdentifier
            self.speaker_identifier = SpeakerIdentifier(
                speaker_manager=self.speaker_manager,
                sample_rate=self.sample_rate,
            )
        if self.wake_detector is None:
            from voice.wake_detector import WakeDetector
            self.wake_detector = WakeDetector(stt=self.stt)
        if self.noise_filter is None:
            from voice.adaptive_noise_filter import AdaptiveNoiseFilter
            self.noise_filter = AdaptiveNoiseFilter(sample_rate=self.sample_rate)
        if self.utterance_segmenter is None:
            from voice.utterance_segmenter import UtteranceSegmenter
            self.utterance_segmenter = UtteranceSegmenter(sample_rate=self.sample_rate)
        if self.emotion_detector is None:
            from voice.emotion_detector import VoiceEmotionDetector
            self.emotion_detector = VoiceEmotionDetector(sample_rate=self.sample_rate)

        # Component health report
        stt_ok = self.stt is not None and hasattr(self.stt, 'model') and self.stt.model is not None
        vad_ok = self._vad is not None
        mic_ok = self._microphone is not None
        logger.info(
            "[VoiceManager] Components: stt=%s vad=%s mic=%s recorder=%s noise=%s aec=%s emotion=%s diar=%s",
            "ok" if stt_ok else "MISSING",
            "ok" if vad_ok else "MISSING",
            "ok" if mic_ok else "MISSING",
            "ok" if self._recorder is not None else "MISSING",
            "ok" if self.noise_filter else "none",
            "ok" if self.full_aec else "none",
            "ok" if self.emotion_detector else "none",
            "ok" if self.diarization_engine else "none",
        )

    # ──────────────────────────────────────────────
    # Mic callback — runs in sounddevice audio thread
    # ──────────────────────────────────────────────
    def _build_mic_callback(self):
        def mic_callback(chunk):
            # Interrupt check — always runs, must be fast
            # Read _speaking and _interrupt_manager under lock, then do interrupt check,
            # then re-verify and clear _speaking under lock to avoid race with main thread.
            with self._lock:
                _speaking = self._speaking
                _interrupt_manager = self._interrupt_manager
            if _speaking and _interrupt_manager:
                try:
                    rms = np.sqrt(np.mean(np.square(chunk.astype(np.float32)))) if chunk.size > 0 else 0.0
                    if rms > self._interrupt_energy_threshold:
                        _interrupt_manager.trigger(reason="mic_energy", source="voice_manager", priority=_DEFAULT_PRIORITY)
                        with self._lock:
                            # Re-verify _speaking is still True before clearing (main thread may have changed it)
                            if self._speaking:
                                self._speaking = False
                except Exception as e:
                    logger.warning("[VoiceManager] Interrupt check error: %s", e)
            processed = chunk

            # Heavy processing (VAD, FFT, AEC, features) only during active recording.
            # During idle the callback must stay <32ms to avoid starving sounddevice.
            is_recording = self._recorder is not None and self._recorder.state == "recording"
            if is_recording:
                noise_source = self.noise_filter
                if noise_source:
                    if hasattr(noise_source, 'add_chunk'):
                        try:
                            noise_source.add_chunk(chunk)
                        except Exception as e:
                            logger.warning("[VoiceManager] Noise add_chunk error: %s", e)
                    try:
                        processed = noise_source.filter(processed)
                    except Exception as e:
                        logger.warning("[VoiceManager] Noise filter error: %s", e)

                if self.full_aec:
                    try:
                        processed = self.full_aec.process(processed)
                    except Exception as e:
                        logger.warning("[VoiceManager] AEC error: %s", e)

                if self.emotion_detector:
                    try:
                        self.emotion_detector.add_audio(processed)
                    except Exception as e:
                        logger.warning("[VoiceManager] Emotion add_audio error: %s", e)

            if self._audio_buffer is None:
                logger.warning("[VoiceManager] audio_buffer is None in callback")
                return
            self._audio_buffer.add(processed)
            # Never record while Mai is talking: there is no echo cancellation
            # (send_playback_audio is never called), so her own TTS reaches the
            # mic and would be transcribed as the user's words.
            if self._recorder and not _speaking:
                self._recorder.add_chunk(processed)
        return mic_callback

    # ──────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────
    def start(self):
        """Start the microphone InputStream and keep it open until stop().
        VoiceManager runs permanently — wake detection and conversation
        both use the same audio stream."""
        self._ensure_components()
        with self._lock:
            if self._running:
                logger.debug("[VoiceManager] Already running — skipping start")
                return
            self._running = True

        assert self._microphone is not None
        self._microphone.start(callback=self._build_mic_callback())
        self._set_state(VoiceState.LISTENING_FOR_WAKE)
        self._start_wake_detection()
        if self.event_bus:
            from voice.events import VOICE_STARTED, publish_voice, voice_started_data
            publish_voice(self.event_bus, VOICE_STARTED, voice_started_data())
        logger.info("[VoiceManager] Started — mic permanently open, wake detection active")

    def stop(self):
        """Stop the microphone InputStream and wake detection thread."""
        self._stop_wake_detection()
        with self._lock:
            self._running = False
            if self._microphone:
                self._microphone.stop()
            if self._recorder:
                self._recorder.stop()
        self._set_state(VoiceState.OFF)
        if self.event_bus:
            from voice.events import (
                STATE_VOICE_IDLE,
                VOICE_STOPPED,
                publish_voice,
                publish_voice_state,
                voice_state_idle_data,
                voice_stopped_data,
            )
            publish_voice(self.event_bus, VOICE_STOPPED, voice_stopped_data())
            publish_voice_state(self.event_bus, STATE_VOICE_IDLE, voice_state_idle_data())
        logger.info("[VoiceManager] Stopped")

    def toggle(self):
        """Toggle voice on/off. Returns the resulting running state."""
        with self._lock:
            was_running = self._running
        if was_running:
            self.stop()
            return False
        self.start()
        return True

    # ──────────────────────────────────────────────
    # Wake detection — background thread
    # ──────────────────────────────────────────────
    def _start_wake_detection(self):
        self._wake_event.clear()
        self._wake_stop.clear()
        if self._wake_thread and self._wake_thread.is_alive():
            logger.debug("[VoiceManager] Wake thread already running")
            return
        self._wake_thread = threading.Thread(target=self._wake_loop, daemon=True, name="wake-detection")
        self._wake_thread.start()
        logger.debug("[VoiceManager] Wake detection thread started")

    def _stop_wake_detection(self):
        # Stop the recorder so any in-progress recording is aborted
        if self._recorder:
            self._recorder.stop()
        self._wake_stop.set()
        if self._wake_thread:
            self._wake_thread.join(timeout=5.0)
            if self._wake_thread.is_alive():
                logger.warning("[VoiceManager] Wake thread did not exit in 5s")
            self._wake_thread = None

    def _gate_utterance(self, audio):
        """Whole-utterance VAD gate — (ok, mean_prob, speech_ratio).

        Fails open when VAD is unavailable or errors so voice stays usable;
        only rejects when VAD positively scored the audio as non-speech.
        """
        vad = self._vad
        if vad is None:
            return True, 0.0, 0.0
        try:
            score = vad.utterance_score(audio, max_frames=UTTERANCE_VAD_MAX_FRAMES)
        except Exception as e:
            logger.warning("[VoiceManager] Utterance VAD scoring failed (failing open): %s", e)
            return True, 0.0, 0.0
        if score is None:
            logger.warning("[VoiceManager] VAD unavailable — utterance gate skipped")
            return True, 0.0, 0.0
        mean, ratio = score
        voiced = ratio * len(audio) / self.sample_rate
        ok = (mean >= UTTERANCE_VAD_MIN_MEAN
              and ratio >= UTTERANCE_VAD_MIN_RATIO
              and voiced >= UTTERANCE_MIN_VOICED)
        if ok:
            logger.info("[Gate] Accepted speech (mean=%.2f ratio=%.2f samples=%d)",
                        mean, ratio, len(audio))
        elif voiced < UTTERANCE_MIN_VOICED:
            logger.info("[Gate] Rejected short speech (voiced=%.2fs < %.2fs, "
                        "mean=%.2f ratio=%.2f samples=%d)",
                        voiced, UTTERANCE_MIN_VOICED, mean, ratio, len(audio))
        return ok, mean, ratio

    def _wake_loop(self):
        """Background loop: consume utterances from the recorder's queue.

        The recorder runs continuously (VAD-gated). Completed utterances
        are pushed to the shared queue. This thread blocks on queue.get()
        instead of polling or restarting the recorder every second."""
        while not self._wake_stop.is_set():
            if self.state != VoiceState.LISTENING_FOR_WAKE:
                self._wake_stop.wait(0.5)
                continue

            try:
                audio = self._utterance_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            self._handle_wake_audio(audio)

    def _handle_wake_audio(self, audio) -> bool:
        """Gate + transcribe + wake-word check for one queued utterance.

        Returns True only when the wake word was found.
        """
        ok, mean, ratio = self._gate_utterance(audio)
        if not ok:
            logger.info("[WakeThread] Rejected utterance (mean=%.2f ratio=%.2f samples=%d)",
                        mean, ratio, len(audio))
            return False

        # Transcribe with latency tracking
        t0 = time.perf_counter()
        try:
            norm = audio.astype(np.float32)
            mx = np.max(np.abs(norm))
            if mx > 0:
                norm = norm / mx
            assert self.stt is not None
            text = self.stt.transcribe(norm, initial_prompt="Wake up, hey, hello, computer, mai")
        except TranscriptionUnavailable as e:
            logger.error("[WakeThread] Whisper unavailable: %s", e)
            return False
        except Exception as e:
            logger.warning("[WakeThread] Transcribe error: %s", e)
            return False
        latency = (time.perf_counter() - t0) * 1000

        if not text:
            # Accepted speech transcribing to nothing must be visible — it is
            # the signature of in-range content corruption, not silence.
            logger.info("[WakeThread] Empty transcription (mean=%.2f ratio=%.2f samples=%d, %.0fms)",
                        mean, ratio, len(audio), latency)
            return False

        logger.info("[WakeThread] Heard: %s (STT: %.0fms, samples=%d)", text, latency, len(audio))

        # Check for wake word
        if self.wake_detector and self.wake_detector.detect_in_text(text):
            logger.info("[WakeThread] Wake word detected in: %s", text)
            self._wake_event.set()
            if self.event_bus:
                from voice.events import VOICE_WAKE_FOUND, publish_voice, voice_wake_found_data
                publish_voice(self.event_bus, VOICE_WAKE_FOUND, voice_wake_found_data(text, len(audio)))
            self._set_state(VoiceState.WAKE_DETECTED)
            while not self._wake_stop.is_set() and self.state == VoiceState.WAKE_DETECTED:
                self._wake_stop.wait(0.5)
            return True
        return False

    # ──────────────────────────────────────────────
    # Conversation listen
    # ──────────────────────────────────────────────
    def _get_utterance(self, timeout):
        try:
            audio = self._utterance_queue.get(timeout=timeout)
        except queue.Empty:
            audio = None
        if audio is None:
            logger.info("[VoiceManager] No utterance received within timeout")
            self._set_state(VoiceState.IDLE)
            self._start_wake_detection()
        return audio

    def _process_audio(self, audio):
        self._set_state(VoiceState.PROCESSING)
        if self.event_bus:
            from voice.events import (
                VOICE_RECORDING_COMPLETED,
                publish_voice,
                voice_recording_completed_data,
            )
            publish_voice(self.event_bus, VOICE_RECORDING_COMPLETED, voice_recording_completed_data(len(audio), len(audio) / self.sample_rate))

        segments = [audio]
        if self.utterance_segmenter:
            try:
                segmented = self.utterance_segmenter.segment(audio)
                if segmented:
                    segments = segmented
            except Exception as e:
                logger.warning("[VoiceManager] Utterance segmentation error: %s", e)

        emotion = None
        if self.emotion_detector:
            try:
                emotion_label, emotion_conf, emotion_feats = self.emotion_detector.detect(audio)
                emotion = {"label": emotion_label, "confidence": emotion_conf, "features": emotion_feats}
            except Exception as e:
                logger.warning("[VoiceManager] Emotion detection error: %s", e)

        speaker_segments = None
        if self.diarization_engine:
            try:
                speaker_segments = self.diarization_engine.segment(audio)
            except Exception as e:
                logger.warning("[VoiceManager] Diarization error: %s", e)

        events = []
        if speaker_segments:
            # Diarization returns only the speech regions it detected —
            # everything else was silently dropped before STT, so short
            # utterances reached Whisper as ~0.2s fragments (empty
            # transcripts, live log 2026-10-09). Transcribe the FULL clip
            # and use diarization only to label the dominant speaker.
            dominant = max(
                speaker_segments,
                key=lambda s: (s.end_sample - s.start_sample)
                * max(getattr(s, "confidence", 0.0) or 0.0, 0.01),
            )
            logger.info(
                "[VoiceManager] Diarization: %d region(s), full-clip transcription (speaker=%s conf=%.2f)",
                len(speaker_segments), dominant.speaker_id, dominant.confidence,
            )
            events.append(
                self._transcribe(audio, dominant.speaker_id, dominant.confidence, emotion)
            )
        else:
            for seg in segments:
                speaker, speaker_conf = self._identify_speaker(seg)
                event = self._transcribe(seg, speaker, speaker_conf, emotion)
                events.append(event)

        return segments, emotion, speaker_segments, events

    def _finalize_listen(self, combined, emotion, wake_required):
        if combined:
            self._metrics.record_recording(combined.duration, combined.audio_length)
            if combined.text:
                self._metrics.record_transcription(True)
            else:
                self._metrics.record_transcription(False)
            if combined.wake_detected:
                self._metrics.record_wake()
            if combined.speaker:
                self._metrics.record_speaker_id()

        if wake_required and combined and not combined.wake_detected:
            self._set_state(VoiceState.IDLE)
            self._start_wake_detection()
            return None

        if combined and self.event_bus:
            from voice.events import (
                STATE_VOICE_IDLE,
                VOICE_RETURNED,
                publish_voice,
                publish_voice_state,
                voice_returned_data,
                voice_state_idle_data,
            )
            extra = {}
            if emotion:
                extra["emotion"] = emotion
            publish_voice(self.event_bus, VOICE_RETURNED, voice_returned_data(
                combined.text, combined.speaker, combined.wake_detected, combined.duration, extra
            ))
            publish_voice_state(self.event_bus, STATE_VOICE_IDLE, voice_state_idle_data())

        delay = self._response_timing_delay(emotion)
        if delay > 0:
            time.sleep(delay)
        self._set_state(VoiceState.RETURN)
        logger.info("[VoiceManager] listen() returning: text='%s', speaker='%s', wake=%s",
                    combined.text if combined else "N/A",
                    combined.speaker if combined else "N/A",
                    combined.wake_detected if combined else "N/A")
        return combined

    def listen(self, wake_required=True, timeout=None):
        from core.mai_message import ensure_correlation
        with ensure_correlation("voice"):
            return self._listen_impl(wake_required=wake_required, timeout=timeout)

    def _discard_stale_utterances(self):
        """Drop utterances recorded before this turn started.

        The recorder is always running, so audio captured during playback (or
        between turns) can sit in the queue. Consuming it would answer Mai's
        own voice or a previous turn's tail (live log 2026-10-27).
        """
        while True:
            try:
                self._utterance_queue.get_nowait()
            except queue.Empty:
                return

    def _listen_impl(self, wake_required=True, timeout=None):
        logger.info("[VoiceManager] listen() entered (wake_required=%s)", wake_required)
        self._ensure_components()

        self._stop_wake_detection()
        self._discard_stale_utterances()

        self._set_state(VoiceState.LISTENING)
        if self.event_bus:
            from voice.events import (
                STATE_VOICE_LISTENING,
                VOICE_LISTENING_STARTED,
                publish_voice,
                publish_voice_state,
                voice_listening_started_data,
                voice_state_listening_data,
            )
            publish_voice(self.event_bus, VOICE_LISTENING_STARTED, voice_listening_started_data(wake_required))
            publish_voice_state(self.event_bus, STATE_VOICE_LISTENING, voice_state_listening_data(wake_required))

        audio = self._get_utterance(timeout)
        if audio is None:
            return None

        try:
            logger.info("[VoiceManager] Utterance received: duration=%.2fs samples=%d max=%.4f",
                        len(audio) / self.sample_rate, len(audio),
                        float(np.max(np.abs(audio))) if len(audio) > 0 else 0.0)

            self._set_state(VoiceState.PROCESSING)
            _, emotion, _, events = self._process_audio(audio)
            combined = self._merge_events(events)

            result = self._finalize_listen(combined, emotion, wake_required)
            return result

        except TranscriptionUnavailable:
            logger.warning("[VoiceManager] Whisper unavailable — aborting listen")
            self._set_state(VoiceState.IDLE)
            self._start_wake_detection()
            raise
        except Exception as e:
            logger.error("[VoiceManager] listen error: %s", e)
            self._metrics.record_error()
            if self.event_bus:
                from voice.events import VOICE_ERROR, publish_voice, voice_error_data
                publish_voice(self.event_bus, VOICE_ERROR, voice_error_data("listen_error", e))
            self._set_state(VoiceState.IDLE)
            self._start_wake_detection()
            return None

    def _response_timing_delay(self, emotion=None):
        if not emotion:
            return 0.0
        label = emotion.get("label", "neutral") if isinstance(emotion, dict) else "neutral"
        delays = {"neutral": 0.3, "happy": 0.1, "sad": 0.8, "angry": 0.2, "stressed": 0.7, "energetic": 0.1}
        return delays.get(label, 0.3)

    def listen_raw(self, timeout=None, wake_required=True):
        from core.mai_message import ensure_correlation
        with ensure_correlation("voice"):
            return self._listen_raw_impl(timeout=timeout, wake_required=wake_required)

    def _listen_raw_impl(self, timeout=None, wake_required=True):
        self._ensure_components()
        self._stop_wake_detection()
        self._discard_stale_utterances()
        try:
            try:
                audio = self._utterance_queue.get(timeout=timeout)
            except queue.Empty:
                return None
            emotion = None
            if self.emotion_detector:
                try:
                    emotion_label, emotion_conf, _ = self.emotion_detector.detect(audio)
                    emotion = {"label": emotion_label, "confidence": emotion_conf}
                except Exception as e:
                    logger.warning("[VoiceManager] listen_raw emotion error: %s", e)
            return {"audio": audio, "emotion": emotion}
        except Exception as e:
            logger.error("[VoiceManager] listen_raw error: %s", e)
            self._metrics.record_error()
            if self.event_bus:
                from voice.events import VOICE_ERROR, publish_voice, voice_error_data
                publish_voice(self.event_bus, VOICE_ERROR, voice_error_data("listen_raw_error", e))
            return None
        finally:
            self._start_wake_detection()

    def _identify_speaker(self, audio):
        if self.speaker_identifier:
            try:
                name, conf = self.speaker_identifier.identify(audio)
                if self.event_bus:
                    from voice.events import (
                        VOICE_SPEAKER_IDENTIFIED,
                        publish_voice,
                        voice_speaker_identified_data,
                    )
                    publish_voice(self.event_bus, VOICE_SPEAKER_IDENTIFIED, voice_speaker_identified_data(name, conf))
                return name, conf
            except Exception as e:
                logger.warning("[VoiceManager] Speaker ID error: %s", e)
        return "", 0.0

    def _transcribe(self, audio, speaker="", speaker_conf=0.0, emotion=None):
        from voice.voice_event import VoiceEvent
        text = ""
        wake_detected = False

        ok, mean, ratio = self._gate_utterance(audio)
        if not ok:
            logger.info("[VoiceManager] Rejected utterance (mean=%.2f ratio=%.2f samples=%d)",
                        mean, ratio, len(audio))
            return VoiceEvent(
                text="",
                speaker=speaker,
                speaker_confidence=speaker_conf,
                audio_length=len(audio),
                duration=len(audio) / self.sample_rate,
                timestamp=time.time(),
                wake_detected=False,
                emotion=emotion,
            )

        if self.stt:
            try:
                norm_audio = audio.astype(np.float32)
                max_val = np.max(np.abs(norm_audio))
                if max_val > 0:
                    norm_audio = norm_audio / max_val
                logger.info("[VoiceManager] Starting Whisper transcription (audio=%d samples, max=%.4f)",
                            len(norm_audio), max_val)
                text = self.stt.transcribe(norm_audio)
                logger.info("[VoiceManager] Whisper result: text=%s", repr(text) if text else "(empty)")
            except TranscriptionUnavailable:
                raise
            except Exception as e:
                logger.error("[VoiceManager] STT error: %s", e)

        if self.wake_detector and text:
            wake_detected = self.wake_detector.detect_in_text(text)

        duration = len(audio) / self.sample_rate

        if self.event_bus:
            from voice.events import (
                STATE_VOICE_SPEAKING,
                STATE_VOICE_WAKE,
                VOICE_TRANSCRIPTION_COMPLETED,
                VOICE_WAKE_DETECTED,
                publish_voice,
                publish_voice_state,
                voice_state_speaking_data,
                voice_state_wake_data,
                voice_transcription_completed_data,
                voice_wake_detected_data,
            )
            publish_voice(self.event_bus, VOICE_TRANSCRIPTION_COMPLETED, voice_transcription_completed_data(text, len(audio), duration))
            publish_voice_state(self.event_bus, STATE_VOICE_SPEAKING, voice_state_speaking_data(text, speaker))
            if wake_detected and text:
                publish_voice(self.event_bus, VOICE_WAKE_DETECTED, voice_wake_detected_data("mai", text))
                publish_voice_state(self.event_bus, STATE_VOICE_WAKE, voice_state_wake_data("mai", text))

        return VoiceEvent(
            text=text,
            speaker=speaker,
            speaker_confidence=speaker_conf,
            audio_length=len(audio),
            duration=duration,
            timestamp=time.time(),
            wake_detected=wake_detected,
            emotion=emotion,
        )

    def _merge_events(self, events):
        if not events:
            return None
        if len(events) == 1:
            return events[0]
        from voice.voice_event import VoiceEvent
        texts = [e.text for e in events if e.text]
        best_speaker = max(
            ((e.speaker, e.speaker_confidence) for e in events if e.speaker),
            key=lambda x: x[1],
            default=("", 0.0),
        )
        best_emotion = max(
            (e.emotion for e in events if e.emotion and e.emotion.get("confidence", 0) > 0.3),
            key=lambda e: e.get("confidence", 0),
            default=None,
        )
        return VoiceEvent(
            text=" ".join(filter(None, texts)),
            speaker=best_speaker[0],
            speaker_confidence=best_speaker[1],
            audio_length=sum(e.audio_length for e in events),
            duration=sum(e.duration for e in events),
            timestamp=events[0].timestamp,
            wake_detected=any(e.wake_detected for e in events),
            emotion=best_emotion,
        )

    def send_playback_audio(self, audio):
        if self.full_aec:
            try:
                self.full_aec.add_playback(audio)
            except Exception as e:
                logger.warning("[VoiceManager] send_playback_audio error: %s", e)

    def end_playback_audio(self):
        if self.full_aec:
            try:
                self.full_aec.end_playback()
            except Exception as e:
                logger.warning("[VoiceManager] end_playback_audio error: %s", e)

    def attach_playback_tap(self, player):
        """Feed the real playback stream into the AEC as its far-end reference.

        Without this the AEC has nothing to cancel and stays a pass-through.
        """
        if not self.full_aec or player is None:
            return False
        if not hasattr(player, "set_reference_tap"):
            logger.warning("[VoiceManager] player has no reference tap — AEC unfed")
            return False
        player.set_reference_tap(
            self.send_playback_audio,
            on_end=self.end_playback_audio,
            sample_rate=self.sample_rate,
        )
        return True
