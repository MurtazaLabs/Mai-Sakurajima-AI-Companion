# core/os_kernel.py
"""
Mai AI Operating System Kernel — Main conversation loop with deterministic FSM.

Two modes:
- FOREGROUND: Blocking main loop (CLI, `run.py`)
- BACKGROUND: Timer-driven tick (daemon, `run_daemon.py`)

Phases: IDLE → WAKE_DETECTED → GREETING/IDENTIFYING_SPEAKER → CONVERSATION →
PROCESSING_RESPONSE → CLEANUP → IDLE
"""
import time
import logging
import threading
import numpy as np

from core.state.models import ConversationPhase, KernelMode
from core.mai_message import ensure_correlation
from app.config_loader import Settings
from voice.stt import TranscriptionUnavailable
from core.wake_generator import WakeGenerator
from core.attention import Attention
from core.cognition import Cognition
from core.idle_behavior import IdleBehavior
from core.scheduler import Scheduler
from core.autonomy.engine import Autonomy

logger = logging.getLogger("Mai.OSKernel")


def _get_identity():
    """Lazy import to avoid circular dependency."""
    try:
        from core.identity.identity_core import get_identity_summary
        return get_identity_summary()
    except Exception:
        return {}


class AIOSKernel:
    def __init__(
        self,
        brain,
        voice,
        wake=None,           # legacy compat
        stt=None,            # legacy compat
        emotion=None,
        state=None,
        event_bus=None,
        scheduler=None,
        personality_state=None,
        memory=None,
        relationship_engine=None,
        wake_generator=None,
        speaker_manager=None,
        voice_manager=None,
        greeting_first_enabled=False,
        greeting_first_delay_seconds=2.0,
        greeting_first=None,  # legacy alias
        greeting_delay=None,  # legacy alias
        per_person_relationship=None,  # legacy compat
    ):
        # Handle legacy parameters
        if wake is not None:
            import warnings
            warnings.warn("'wake' parameter is deprecated, use 'wake_generator'", DeprecationWarning, stacklevel=2)
            if wake_generator is None:
                wake_generator = wake
        if stt is not None:
            import warnings
            warnings.warn("'stt' parameter is deprecated", DeprecationWarning, stacklevel=2)
        # Track if greeting_first was explicitly provided
        greeting_first_provided = greeting_first is not None
        
        if greeting_first is not None:
            import warnings
            warnings.warn("'greeting_first' parameter is deprecated, use 'greeting_first_enabled'", DeprecationWarning, stacklevel=2)
            if not greeting_first_enabled:
                greeting_first_enabled = greeting_first
        if greeting_delay is not None:
            import warnings
            warnings.warn("'greeting_delay' parameter is deprecated, use 'greeting_first_delay_seconds'", DeprecationWarning, stacklevel=2)
            if greeting_first_delay_seconds == 2.0:
                greeting_first_delay_seconds = greeting_delay

        # Default from config if not explicitly provided
        if not greeting_first_provided:
            from app.config_loader import Settings
            greeting_first_enabled = bool(getattr(Settings, "GREETING_FIRST_ENABLED", False))

        if state is None:
            raise ValueError("AIOSKernel requires a valid SharedState instance — got None.")
        if relationship_engine is None:
            raise ValueError("AIOSKernel requires a valid RelationshipEngineV2 instance — got None.")

        # Create scheduler if not provided (backwards compat with tests)
        if scheduler is None:
            from core.os_kernel import Scheduler
            scheduler = Scheduler(self)

        self.brain = brain
        self.voice = voice
        self.voice_manager = voice_manager
        self.emotion = emotion
        self.state = state
        self.event_bus = event_bus
        self.scheduler = scheduler
        self.personality_state = personality_state
        self.memory = memory
        self.relationship_engine = relationship_engine
        self.wake_generator = wake_generator
        self.speaker_manager = speaker_manager
        self.per_person_relationship = per_person_relationship

        # Legacy compat
        self.wake = wake
        self.stt = stt

        self._phase = ConversationPhase.IDLE
        self._running = True
        self._bg_running = False
        self._bg_interval = 0.5
        self._bg_thread = None
        self._voice_was_speaking = False

        self.conversation_lock = threading.Lock()

        self.greeting_first_enabled = greeting_first_enabled
        self.greeting_first_delay_seconds = greeting_first_delay_seconds
        self._session_greeted = False

    @property
    def running(self):
        return self._running

    @property
    def phase(self):
        return self._phase

    def _set_phase(self, phase: ConversationPhase):
        old = self._phase
        if old == phase:
            return
        self._phase = phase
        logger.info("STATE: %s → %s", old.value if hasattr(old, 'value') else old, phase.value)

    def _update_time_context(self):
        """Update time_of_day in state.runtime based on current hour."""
        import time
        hour = time.localtime().tm_hour
        if 5 <= hour < 12:
            tod = "morning"
        elif 12 <= hour < 17:
            tod = "day"
        elif 17 <= hour < 21:
            tod = "evening"
        else:
            tod = "night"
        with self.state.lock:
            self.state.runtime.time_of_day = tod

    def _process_autonomy(self, auto):
        """Process autonomy intent and return appropriate phrase."""
        intent = auto.get("intent")
        phrases = {
            "seek_attention": "You've been quiet for a while.",
            "gentle_checkin": "You seem a little distant today.",
            "soft_presence": "...I'm still here.",
            "playful_tease": "You really do like disappearing randomly, hm?",
        }
        return phrases.get(intent)

    def _record_identification_audio(
        self, duration: float = 3.0, sample_rate: int = 16000
    ) -> np.ndarray | None:
        """Actively capture the next speech segment for speaker identification.

        Uses VoiceManager.listen_raw() which reuses the permanent InputStream
        and its VAD gating — no secondary sd.rec() stream needed.
        Falls back to sd.rec() if VoiceManager is unavailable."""
        try:
            if self.voice_manager:
                logger.info("[Kernel] Capturing identification audio via listen_raw...")
                result = self.voice_manager.listen_raw(timeout=duration + 1.0)
                if result and result.get("audio") is not None:
                    audio = result["audio"]
                    if len(audio) > 0:
                        max_val = np.max(np.abs(audio))
                        if max_val > 0:
                            audio = audio / max_val
                        logger.info("[Kernel] Identification audio captured: %d samples, max=%.4f", len(audio), max_val)
                        return audio
                    logger.debug("[Kernel] listen_raw returned None — falling back to sd.rec()")

            import sounddevice as sd
            logger.info("[Kernel] Recording for speaker identification (via sd.rec)...")
            audio = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
            )
            sd.wait()
            audio = audio.flatten()
            max_val = np.max(np.abs(audio))
            if max_val > 0:
                audio = audio / max_val
            logger.info("[Kernel] Identification recording complete")
            return audio

        except Exception as exc:
            logger.debug("[Kernel] Identification recording failed: %s", exc)
            return None

    def _restore_last_known_speaker(self):
        """Restore the last known speaker from SharedState without prompting.

        This enables natural continuity across sessions - Mai remembers who you are
        and continues the conversation naturally. Only triggers active identification
        if the voice doesn't match (handled in background)."""
        with self.state.lock:
            last_name = self.state.runtime.current_speaker_name or ""
            last_id = self.state.runtime.current_speaker_id or ""
            last_conf = self.state.runtime.speaker_confidence or 0.0

        if last_name:
            logger.info("[Kernel] Restored last known speaker: %s (conf=%.2f)", last_name, last_conf)
            # Speaker is already set in SharedState from previous session
            # No greeting needed - just continue naturally
        else:
            logger.info("[Kernel] No previous speaker known — will identify if needed")
            # First time user - identification will happen naturally if they speak

    def _maybe_identify_speaker_background(self, audio: np.ndarray):
        """Background speaker identification - only prompts if confidence is low
        AND different from last known speaker. Non-blocking."""
        if not self.speaker_manager or not self.speaker_manager.ready:
            return

        # Get last known speaker
        with self.state.lock:
            last_name = self.state.runtime.current_speaker_name or ""
            last_id = self.state.runtime.current_speaker_id or ""

        try:
            profile, confidence = self.speaker_manager.identify_raw(audio, sample_rate=16000)

            if profile and confidence >= 0.7:
                # High confidence match
                if profile.name != last_name:
                    # Different person detected with high confidence
                    with self.state.lock:
                        self.state.runtime.current_speaker_name = profile.name
                        self.state.runtime.current_speaker_id = profile.id
                        self.state.runtime.speaker_confidence = confidence
                        self.state.runtime.known_user = True
                    logger.info("[Kernel] Background ID: Speaker changed to %s (%.2f)", profile.name, confidence)
                    # Could optionally announce: "Oh, you're {name}!"
                else:
                    # Same person, update confidence
                    with self.state.lock:
                        self.state.runtime.speaker_confidence = confidence
            elif profile and confidence >= 0.3:
                # Low confidence - only prompt if different from last known
                if profile.name != last_name:
                    # Different voice detected but uncertain - could prompt later
                    logger.info("[Kernel] Background ID: Uncertain speaker %s (%.2f) - different from %s",
                               profile.name, confidence, last_name)
                    # Don't block conversation - could queue a gentle check
            # Below 0.3 - unknown, but don't prompt unless explicitly asked

        except Exception as e:
            logger.debug("[Kernel] Background speaker ID error: %s", e)

    def _listen_with_voice_manager(self, wake_required=False, return_audio=False):
        if self.voice_manager:
            try:
                if return_audio:
                    # Use listen_raw to get audio for background speaker ID
                    result = self.voice_manager.listen_raw(wake_required=wake_required)
                    if result:
                        text = result.get("text", "") if isinstance(result, dict) else ""
                        # listen_raw returns {"audio": audio, "emotion": emotion}
                        # We need to transcribe the audio
                        audio = result.get("audio")
                        if audio is not None and len(audio) > 0:
                            # Transcribe
                            norm_audio = audio.astype(np.float32)
                            max_val = np.max(np.abs(norm_audio))
                            if max_val > 0:
                                norm_audio = norm_audio / max_val
                            text = self.voice_manager.stt.transcribe(norm_audio) if self.voice_manager.stt else ""
                            return text, audio
                        return "", None
                    return "", None
                else:
                    event = self.voice_manager.listen(wake_required=wake_required)
                    return event.text if event else ""
            except TranscriptionUnavailable as e:
                logger.error("[Kernel] %s", e)
                raise
        logger.error("[Kernel] No VoiceManager available — cannot capture audio")
        return ("", None) if return_audio else ""

    def _speak_and_wait(self, text):
        self.voice.speak_stream(iter([text]))
        self.voice.wait_until_done()

    def _identify_speaker_phase(self):
        if not self.speaker_manager or not self.speaker_manager.ready:
            logger.info("[Kernel] Speaker manager not available — anonymous mode")
            return True

        self._set_phase(ConversationPhase.IDENTIFYING_SPEAKER)
        logger.info("[Kernel] Identifying speaker...")
        ident_audio = self._record_identification_audio()
        if ident_audio is None:
            logger.info("[Kernel] No identification audio — proceeding anonymously")
            return True

        profile, confidence = self.speaker_manager.identify_raw(
            ident_audio, sample_rate=16000
        )

        if profile and confidence >= 0.7:
            with self.state.lock:
                self.state.runtime.current_speaker_name = profile.name
                self.state.runtime.current_speaker_id = profile.id
                self.state.runtime.speaker_confidence = confidence
                self.state.runtime.known_user = True
            logger.info("[Kernel] Speaker identified: %s (%.2f)", profile.name, confidence)
            self._speak_and_wait(f"Welcome back, {profile.name}.")
            time.sleep(1.0)
            return True

        try:
            if profile and confidence >= 0.3:
                self._set_phase(ConversationPhase.CONFIRMING_SPEAKER)
                logger.info("[Kernel] Speaker unknown: %s (%.2f) — confirming", profile.name, confidence)
                self._speak_and_wait(f"Is that {profile.name}?")

                reply = self._listen_with_voice_manager(wake_required=False)
                if reply and any(w in reply.lower()
                                 for w in ["yes", "yeah", "yep", "correct", "right", "it is", "that's me"]):
                    with self.state.lock:
                        self.state.runtime.current_speaker_name = profile.name
                        self.state.runtime.current_speaker_id = profile.id
                        self.state.runtime.speaker_confidence = confidence
                        self.state.runtime.known_user = True
                    logger.info("[Kernel] Speaker confirmed: %s", profile.name)
                else:
                    logger.info("[Kernel] Speaker confirmation denied — proceeding as unknown")
                return True

            # Unknown speaker (< 0.3)
            self._set_phase(ConversationPhase.ASKING_NAME)
            logger.info("[Kernel] Speaker unknown")
            self._speak_and_wait("I don't think we've met before. May I know your name?")

            reply = self._listen_with_voice_manager(wake_required=False)
            if reply and len(reply.strip()) > 1:
                name = reply.strip().title()
                logger.info("[Kernel] User said name: %s", name)

                self._set_phase(ConversationPhase.REGISTERING_SPEAKER)
                logger.info("[Kernel] Registering speaker: %s ...", name)

                new_profile = self.speaker_manager.register_raw(
                    name, ident_audio, sample_rate=16000
                )
                if new_profile:
                    with self.state.lock:
                        self.state.runtime.current_speaker_name = new_profile.name
                        self.state.runtime.current_speaker_id = new_profile.id
                        self.state.runtime.speaker_confidence = 1.0
                        self.state.runtime.known_user = True
                    logger.info("[Kernel] Registration complete: %s", name)
                else:
                    logger.warning("[Kernel] Registration failed for: %s", name)
            else:
                logger.info("[Kernel] No name received — proceeding anonymously")

            return True
        except TranscriptionUnavailable as e:
            logger.error("[Kernel] %s — proceeding anonymously", e)
            return True

    def _conversation_phase(self):
        self._set_phase(ConversationPhase.CONVERSATION)

        while self.running:
            logger.info("[Kernel] Waiting for user input...")
            try:
                user, audio = self._listen_with_voice_manager(wake_required=False, return_audio=True)
            except TranscriptionUnavailable as e:
                logger.error("[Kernel] %s", e)
                return

            if not user:
                logger.info("[Kernel] No speech detected — ending conversation")
                return

            # Background speaker identification (non-blocking)
            if audio is not None and len(audio) > 0:
                self._maybe_identify_speaker_background(audio)

            user = user.strip()
            if not user:
                continue

            logger.info("[Kernel] User said: %s", user)

            with self.state.lock:
                self.state.runtime.last_user_message = user
                self.state.runtime.last_interaction_time = time.time()

            # Emotion update
            relationship = (
                self.brain.memory
                .get_structured()
                .get("relationship", {})
            )
            if not isinstance(relationship, dict):
                relationship = {}
            try:
                self.emotion.update(user, relationship=relationship)
            except Exception as e:
                logger.error("[Emotion Error] %s", e)

            self.voice.stop()

            self._set_phase(ConversationPhase.PROCESSING_RESPONSE)
            logger.info("[Kernel] Thinking...")
            try:
                stream = self.brain.think_stream(user)
            except Exception as e:
                logger.error("[Kernel Brain Error] %s", e)
                self._speak_and_wait("Something went wrong.")
                time.sleep(1.0)
                continue

            logger.info("[Kernel] Speaking response...")
            collected_chunks = []

            def collecting_stream(s):
                for chunk in s:
                    if not chunk:
                        continue
                    cleaned = str(chunk).strip()
                    if not cleaned:
                        continue
                    collected_chunks.append(cleaned)
                    yield cleaned

            try:
                if self.voice_manager:
                    self.voice_manager.set_speaking(True, self.voice.interrupt)
                self.voice.speak_stream(collecting_stream(stream))
            except Exception as e:
                logger.error("[Kernel Speak Error] %s", e)
            finally:
                if self.voice_manager:
                    self.voice_manager.set_speaking(False)

            full_response = "".join(collected_chunks)
            logger.info("[Kernel] Response complete: %s", full_response[:80])

            # Store conversation in memory
            try:
                speaker_name = self.state.runtime.current_speaker_name or "User"
                self.brain.memory.store(user, full_response, speaker=speaker_name)
            except Exception as e:
                logger.error("[Memory Store Error] %s", e)

            # Publish conversation finished event
            if self.event_bus:
                from core.event_specs import CONVERSATION_FINISHED
                from core.mai_message import publish_event
                publish_event(self.event_bus, CONVERSATION_FINISHED, {
                    "user_input": user,
                    "response": full_response,
                    "speaker": speaker_name,
                }, source="kernel")

    def _tick(self, mode: KernelMode = KernelMode.FOREGROUND):
        """Single FSM tick — called repeatedly in background mode, once in foreground."""

        # Greeting-first mode: proactive greeting on first tick after boot delay
        if self.greeting_first_enabled and not self._session_greeted:
            import time
            if not hasattr(self, '_boot_time'):
                self._boot_time = time.time()
            delay = getattr(self, 'greeting_first_delay_seconds', 2.0)
            if time.time() - self._boot_time >= delay:
                self._session_greeted = True
                logger.info("[Kernel] Greeting-first mode: initiating proactive greeting")
                self._run_greeting_first()
                return

        if self._phase == ConversationPhase.IDLE:
            import time
            if self.voice_manager and getattr(self.voice_manager, '_wake_event', None) and self.voice_manager._wake_event.is_set():
                self.voice_manager._wake_event.clear()
                self._voice_was_speaking = False

                with self.state.lock:
                    self.state.runtime.user_active = True
                    self.state.runtime.conversation_active = True
                    self.state.runtime.known_user = False
                    self.state.runtime.current_speaker_name = ""
                    self.state.runtime.current_speaker_id = ""
                    self.state.runtime.speaker_confidence = 0.0

                if not self._voice_was_speaking:
                    self.voice.stop()
                else:
                    self.voice.stop()
                logger.info("[Kernel] Wake triggered")

                self._set_phase(ConversationPhase.WAKE_DETECTED)

                # Greeting
                self._set_phase(ConversationPhase.GREETING)
                wake_text = self.wake_generator.generate(context={
                    "identity": _get_identity(),
                    "personality_state": self.brain.personality_state,
                    "emotion": self.emotion.get() if hasattr(self.emotion, "get") else {},
                    "cognitive_state": self.brain.cognitive.get() if hasattr(self.brain, "cognitive") else {},
                    "time_of_day": self.brain._time_of_day() if hasattr(self.brain, "_time_of_day") else "day",
                })
                self.voice.speak_stream(iter([wake_text]))
                self.voice.wait_until_done()
                time.sleep(1.5)

                # Restore last known speaker from previous session (no blocking identification)
                self._restore_last_known_speaker()

                # Conversation
                self._conversation_phase()

            # In background mode, also check for hotkey/trigger
            elif mode == KernelMode.BACKGROUND:
                # Could add hotkey check here
                pass

    def _run_greeting_first(self):
        """Proactive greeting on boot (greeting-first mode)."""
        logger.info("[Kernel] Running greeting-first greeting")
        wake_text = self.wake_generator.generate(context={
            "identity": _get_identity(),
            "personality_state": self.brain.personality_state,
            "emotion": self.emotion.get() if hasattr(self.emotion, "get") else {},
            "cognitive_state": self.brain.cognitive.get() if hasattr(self.brain, "cognitive") else {},
            "time_of_day": self.brain._time_of_day() if hasattr(self.brain, "_time_of_day") else "day",
        })
        self.voice.speak_stream(iter([wake_text]))
        self.voice.wait_until_done()
        time.sleep(1.5)
        self._restore_last_known_speaker()
        self._conversation_phase()

    # ==================================================
    # 🚀 MAIN LOOP — Deterministic FSM (event-driven wake)
    # ==================================================
    def run(self):
        if self.greeting_first_enabled:
            logger.info("Greeting-first mode — Mai greets you on launch")
        else:
            logger.info("Say 'wake up Mai'")
        with self.state.lock:
            self.state.runtime.conversation_active = False
        self._set_phase(ConversationPhase.IDLE)
        self.scheduler.start()

        while self.running:
            self._tick(mode=KernelMode.FOREGROUND)

    # ==================================================
    # 🔄 BACKGROUND MODE — timer-driven operation
    # ==================================================

    def background_start(self, tick_interval=0.5):
        """Start the kernel in background (non-blocking) mode.

        The FSM runs on a timer tick rather than blocking the main thread.
        Call ``background_stop()`` to stop.
        """
        self._bg_running = True
        self._bg_interval = tick_interval

        def _bg_loop():
            logger.info("[Kernel] Background mode started")
            while self._bg_running and self.running:
                self._tick(mode=KernelMode.BACKGROUND)
                time.sleep(tick_interval)
            logger.info("[Kernel] Background mode stopped")

        self._bg_thread = threading.Thread(
            target=_bg_loop, daemon=True, name="kernel-bg"
        )
        self._bg_thread.start()

    def background_stop(self):
        """Stop background mode."""
        self._bg_running = False
        logger.info("[Kernel] Background stop requested")

    def shutdown(self):
        """Graceful shutdown."""
        logger.info("[Kernel] Shutdown initiated")
        self._running = False
        self._bg_running = False
        try:
            if self.voice_manager:
                self.voice_manager.stop()
        except Exception as e:
            logger.error("[Kernel] voice_manager stop failed: %s", e)
        try:
            self.voice.stop()
        except Exception as e:
            logger.error("[Kernel] voice stop failed: %s", e)
        try:
            if self.scheduler:
                self.scheduler.stop()
        except Exception as e:
            logger.error("[Kernel] scheduler stop failed: %s", e)
        try:
            if self.event_bus:
                self.event_bus.stop()
        except Exception as e:
            logger.error("[Kernel] event_bus stop failed: %s", e)
        try:
            if self.state:
                self.state.save_state_to_disk()
        except Exception as e:
            logger.error("[Kernel] state save failed: %s", e)
        try:
            if self.brain and self.brain.personality_state:
                self.brain.personality_state.save()
        except Exception as e:
            logger.error("[Kernel] personality_state save failed: %s", e)
        logger.info("[Kernel] Shutdown complete")