"""Self-hearing loop (live log 2026-10-27): Mai's own TTS reached the mic and
was transcribed as the user's words ("shut up.", "soft bar.", "Hello, beautiful.").

`send_playback_audio` has no production caller, so echo cancellation never
runs. The recorder must therefore stop taking audio while she speaks, and
`listen()` must drop anything recorded before the turn started.
"""
from unittest.mock import MagicMock

import numpy as np

from voice.voice_manager import VoiceManager


class _StubVad:
    """Non-None `.model` plus a constant speech score — no silero load."""

    _model = object()

    def is_speech(self, chunk):
        return True

    def utterance_score(self, audio, max_frames=None):
        return 0.9, 1.0


def _vm(**kwargs):
    kwargs.setdefault("sample_rate", 16000)
    kwargs.setdefault("vad", _StubVad())
    vm = VoiceManager(**kwargs)
    vm._recorder = MagicMock()
    vm._recorder.state = "listening"
    vm._audio_buffer = MagicMock()
    return vm


class TestMicCallbackMutedWhileSpeaking:
    def test_no_recording_while_she_speaks(self):
        vm = _vm()
        cb = vm._build_mic_callback()
        vm.set_speaking(True)
        vm._recorder.reset_mock()
        cb(np.zeros(512, dtype=np.float32))
        vm._recorder.add_chunk.assert_not_called()

    def test_recording_resumes_when_she_stops(self):
        vm = _vm()
        cb = vm._build_mic_callback()
        vm.set_speaking(True)
        cb(np.zeros(512, dtype=np.float32))
        vm._recorder.reset_mock()
        vm.set_speaking(False)
        cb(np.zeros(512, dtype=np.float32))
        vm._recorder.add_chunk.assert_called_once()

    def test_starting_to_speak_clears_stale_recorder_buffer(self):
        # Audio captured before playback would otherwise sit in the pre-roll
        # and be prepended to the next user utterance.
        vm = _vm()
        vm.set_speaking(True)
        vm._recorder.stop.assert_called_once()
        vm.set_speaking(True)  # already speaking: no repeated reset
        assert vm._recorder.stop.call_count == 1


class TestStaleUtteranceDrain:
    def test_discard_stale_utterances_empties_queue(self):
        vm = _vm()
        vm._utterance_queue.put_nowait(np.zeros(1600, dtype=np.float32))
        vm._utterance_queue.put_nowait(np.zeros(1600, dtype=np.float32))
        vm._discard_stale_utterances()
        assert vm._utterance_queue.empty()

    def test_listen_never_returns_audio_recorded_before_the_turn(self, monkeypatch):
        vm = _vm()
        monkeypatch.setattr(vm, "_ensure_components", lambda: None)
        monkeypatch.setattr(vm, "_stop_wake_detection", lambda: None)
        monkeypatch.setattr(vm, "_start_wake_detection", lambda: None)
        vm._utterance_queue.put_nowait(np.zeros(1600, dtype=np.float32))
        assert vm._listen_impl(wake_required=False, timeout=0.01) is None
        assert vm._utterance_queue.empty()


def test_greeting_mutes_mic_while_speaking(monkeypatch):
    from core.os_kernel import AIOSKernel

    vm = MagicMock()
    voice = MagicMock()
    observed = {}

    def _speak(_stream):
        observed["speaking"] = vm.set_speaking.call_args_list[-1][0][0]

    voice.speak_stream.side_effect = _speak

    kernel = AIOSKernel(
        brain=MagicMock(), voice=voice, emotion=MagicMock(), state=MagicMock(),
        relationship_engine=MagicMock(), voice_manager=vm,
        wake_generator=MagicMock(),
    )
    monkeypatch.setattr(kernel, "_restore_last_known_speaker", MagicMock())
    monkeypatch.setattr(kernel, "_conversation_phase", MagicMock())
    monkeypatch.setattr("core.os_kernel.time.sleep", lambda _s: None)

    kernel._run_greeting_first()

    assert observed["speaking"] is True, "greeting played with the mic armed"
    assert vm.set_speaking.call_args_list[-1][0][0] is False
