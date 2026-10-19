# tests/test_greeting_first.py — M5 FSM tests
from unittest.mock import MagicMock, patch

from core.os_kernel import AIOSKernel, KernelMode


def _kernel(greeting_first=None, greeting_delay=0.0, wake_set=False):
    """Build a minimal AIOSKernel with everything patched but the FSM."""
    with patch("core.os_kernel.Attention"), \
         patch("core.os_kernel.Cognition"), \
         patch("core.os_kernel.IdleBehavior"), \
         patch("core.os_kernel.Scheduler"), \
         patch("core.os_kernel.Autonomy"), \
         patch("core.os_kernel.WakeGenerator"), \
         patch("core.os_kernel._get_identity"):
        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.memory = MagicMock()
        brain.executor = MagicMock()
        brain.personality_state = MagicMock()
        brain.dream_engine = None
        voice = MagicMock()
        voice.is_speaking = False
        voice.is_generating = False
        wake = MagicMock()
        stt = MagicMock()
        state = MagicMock()
        state.runtime.conversation_active = False
        relationship_engine = MagicMock()
        kernel = AIOSKernel(
            brain=brain,
            voice=voice,
            wake=wake,
            stt=stt,
            state=state,
            relationship_engine=relationship_engine,
            greeting_first=greeting_first,
            greeting_delay=greeting_delay,
        )
        vm = MagicMock()
        wake_event = MagicMock()
        wake_event.is_set.return_value = wake_set
        vm._wake_event = wake_event
        kernel.voice_manager = vm
        kernel._conversation_phase = MagicMock()
        kernel._identify_speaker_phase = MagicMock(return_value=True)
        kernel._restore_last_known_speaker = MagicMock()
        return kernel


class TestGreetingFirstFSM:

    def test_greeting_fires_once_per_session(self):
        kernel = _kernel(greeting_first=True, greeting_delay=0.0)
        with patch("core.os_kernel.time.sleep"):
            kernel._tick(mode=KernelMode.BACKGROUND)
        assert kernel._session_greeted is True
        assert kernel.wake_generator.generate.called
        assert kernel.voice.speak_stream.called
        first_calls = kernel.voice.speak_stream.call_count

        # conversation ends; second tick must NOT re-greet
        with patch("core.os_kernel.time.sleep"):
            kernel._tick(mode=KernelMode.BACKGROUND)
        assert kernel.voice.speak_stream.call_count == first_calls
        assert kernel._session_greeted is True

    def test_greeting_respects_delay(self):
        kernel = _kernel(greeting_first=True, greeting_delay=999.0)
        with patch("core.os_kernel.time.sleep"):
            kernel._tick(mode=KernelMode.BACKGROUND)
        assert kernel._session_greeted is False
        assert not kernel.wake_generator.generate.called

    def test_greeting_first_fires_without_wake_event(self):
        kernel = _kernel(greeting_first=True, greeting_delay=0.0)
        with patch("core.os_kernel.time.sleep"):
            kernel._tick(mode=KernelMode.BACKGROUND)
        # wake event never set — greeting-first alone drove the trigger
        assert kernel.wake_generator.generate.called
        assert kernel._restore_last_known_speaker.called
        assert kernel._conversation_phase.called

    def test_wake_mode_unchanged_no_event(self):
        kernel = _kernel(greeting_first=False, greeting_delay=0.0, wake_set=False)
        with patch("core.os_kernel.time.sleep"):
            kernel._tick(mode=KernelMode.BACKGROUND)
        assert not kernel.wake_generator.generate.called
        assert not kernel._conversation_phase.called

    def test_wake_mode_unchanged_with_event(self):
        kernel = _kernel(greeting_first=False, greeting_delay=0.0, wake_set=True)
        with patch("core.os_kernel.time.sleep"):
            kernel._tick(mode=KernelMode.BACKGROUND)
        assert kernel.wake_generator.generate.called
        assert kernel._conversation_phase.called

    def test_wake_still_works_after_greeting_first(self):
        kernel = _kernel(greeting_first=True, greeting_delay=0.0)
        with patch("core.os_kernel.time.sleep"):
            kernel._tick(mode=KernelMode.BACKGROUND)
        assert kernel._session_greeted is True
        # wake event now set — must still open a conversation
        kernel.voice_manager._wake_event.is_set.return_value = True
        with patch("core.os_kernel.time.sleep"):
            kernel._tick(mode=KernelMode.BACKGROUND)
        assert kernel._conversation_phase.call_count == 2

    def test_default_flag_from_config(self):
        from config.character import GREETING_FIRST_ENABLED
        kernel = _kernel(greeting_first=None, greeting_delay=0.0)
        assert kernel.greeting_first_enabled is bool(GREETING_FIRST_ENABLED)


class TestGreetingFirstConfig:

    def test_config_exports(self):
        from config.settings import Settings
        assert hasattr(Settings, "GREETING_FIRST_ENABLED")
        assert hasattr(Settings, "GREETING_FIRST_DELAY_SECONDS")
        assert Settings.GREETING_FIRST_ENABLED is True