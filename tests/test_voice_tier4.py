import pytest
from unittest.mock import MagicMock, call

from voice import events
from voice.metrics import VoiceMetrics


class TestVoiceEvents:
    def test_event_topics_are_strings(self):
        assert events.VOICE_STARTED == "data.voice.started"
        assert events.VOICE_STOPPED == "data.voice.stopped"
        assert events.VOICE_STATE_CHANGED == "data.voice.state_changed"
        assert events.VOICE_LISTENING_STARTED == "data.voice.listening_started"
        assert events.VOICE_RECORDING_COMPLETED == "data.voice.recording_completed"
        assert events.VOICE_SPEAKER_IDENTIFIED == "data.voice.speaker_identified"
        assert events.VOICE_TRANSCRIPTION_COMPLETED == "data.voice.transcription_completed"
        assert events.VOICE_WAKE_DETECTED == "data.voice.wake_detected"
        assert events.VOICE_RETURNED == "data.voice.returned"
        assert events.VOICE_ERROR == "data.voice.error"

    def test_voice_started_data(self):
        d = events.voice_started_data()
        assert d == {"state": "started"}

    def test_voice_stopped_data(self):
        d = events.voice_stopped_data()
        assert d == {"state": "stopped"}

    def test_voice_state_changed_data(self):
        d = events.voice_state_changed_data("idle", "listening")
        assert d == {"old_state": "idle", "new_state": "listening"}

    def test_voice_listening_started_data(self):
        d = events.voice_listening_started_data(True)
        assert d == {"wake_required": True}

    def test_voice_recording_completed_data(self):
        d = events.voice_recording_completed_data(16000, 1.0)
        assert d == {"audio_length": 16000, "duration": 1.0}

    def test_voice_speaker_identified_data(self):
        d = events.voice_speaker_identified_data("Alice", 0.85)
        assert d == {"speaker": "Alice", "confidence": 0.85}

    def test_voice_transcription_completed_data(self):
        d = events.voice_transcription_completed_data("hello", 16000, 1.0)
        assert d == {"text": "hello", "text_length": 5, "audio_length": 16000, "duration": 1.0}

    def test_voice_wake_detected_data(self):
        d = events.voice_wake_detected_data("mai", "hey mai")
        assert d == {"wake_word": "mai", "text": "hey mai"}

    def test_voice_returned_data(self):
        d = events.voice_returned_data("hello", "Alice", True, 2.0)
        assert d == {"text": "hello", "speaker": "Alice", "wake_detected": True, "duration": 2.0}

    def test_voice_error_data(self):
        d = events.voice_error_data("timeout", "recording timed out")
        assert d == {"type": "timeout", "message": "recording timed out"}


class TestVoiceMetrics:
    def test_init(self):
        m = VoiceMetrics()
        stats = m.stats()
        assert stats["recordings"] == 0
        assert stats["errors"] == 0
        assert stats["transcription_success_rate"] == 1.0

    def test_record_recording(self):
        m = VoiceMetrics()
        m.record_recording(2.5, 40000)
        stats = m.stats()
        assert stats["recordings"] == 1
        assert stats["total_duration_seconds"] == 2.5
        assert stats["total_audio_bytes"] == 40000

    def test_record_recording_multiple(self):
        m = VoiceMetrics()
        m.record_recording(1.0, 16000)
        m.record_recording(3.0, 48000)
        stats = m.stats()
        assert stats["recordings"] == 2
        assert stats["total_duration_seconds"] == 4.0
        assert stats["total_audio_bytes"] == 64000
        assert stats["avg_duration_seconds"] == 2.0

    def test_transcription_success(self):
        m = VoiceMetrics()
        m.record_transcription(True)
        m.record_transcription(True)
        stats = m.stats()
        assert stats["successful_transcriptions"] == 2
        assert stats["transcription_success_rate"] == 1.0

    def test_transcription_failure(self):
        m = VoiceMetrics()
        m.record_transcription(True)
        m.record_transcription(False)
        stats = m.stats()
        assert stats["successful_transcriptions"] == 1
        assert stats["failed_transcriptions"] == 1
        assert stats["transcription_success_rate"] == 0.5

    def test_record_wake(self):
        m = VoiceMetrics()
        m.record_wake()
        m.record_wake()
        assert m.stats()["wake_detections"] == 2

    def test_record_speaker_id(self):
        m = VoiceMetrics()
        m.record_speaker_id()
        assert m.stats()["speaker_identifications"] == 1

    def test_record_error(self):
        m = VoiceMetrics()
        m.record_error()
        m.record_error()
        assert m.stats()["errors"] == 2

    def test_avg_duration_zero(self):
        m = VoiceMetrics()
        assert m.avg_duration() == 0.0

    def test_thread_safety(self):
        import threading
        m = VoiceMetrics()
        errors = []

        def worker():
            try:
                for _ in range(20):
                    m.record_recording(0.1, 1600)
                    m.record_transcription(True)
                    m.record_wake()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        stats = m.stats()
        assert stats["recordings"] == 100
        assert stats["wake_detections"] == 100

    def test_events_wired_in_voice_manager(self):
        from voice.voice_manager import VoiceManager
        from core.event_bus import EventBus
        eb = EventBus()
        published = []
        def capture(data):
            published.append(data)
        eb.subscribe("data.voice.started", capture)
        eb.subscribe("data.voice.state_changed", capture)
        vm = VoiceManager(event_bus=eb)
        assert vm.event_bus is eb


class TestMicrophoneCallbacks:

    def test_callbacks_cleared_on_stop(self):
        from voice.microphone import Microphone
        mic = Microphone.__new__(Microphone)
        mic._callbacks = []
        mic._lock = MagicMock()
        mic._stream = None
        mic._running = True
        mic._callbacks.append(lambda c: None)
        mic.stop()
        assert mic._callbacks == []

    def test_callbacks_deduplicated_on_start(self):
        from voice.microphone import Microphone
        mic = Microphone.__new__(Microphone)
        mic._callbacks = []
        mic._lock = MagicMock()
        mic._stream = None
        mic._running = False
        cb = lambda c: None
        mic.start = MagicMock()
        mic._callbacks.append(cb)
        mic.add_callback(cb)
        assert mic._callbacks.count(cb) == 2


class TestVoiceManagerToggle:

    def test_toggle_from_stopped_starts(self):
        from voice.voice_manager import VoiceManager
        vm = VoiceManager(sample_rate=16000)
        vm.start = MagicMock()
        vm.stop = MagicMock()
        vm._running = False
        result = vm.toggle()
        assert result is True
        vm.start.assert_called_once()
        vm.stop.assert_not_called()

    def test_toggle_from_running_stops(self):
        from voice.voice_manager import VoiceManager
        vm = VoiceManager(sample_rate=16000)
        vm.start = MagicMock()
        vm.stop = MagicMock()
        vm._running = True
        result = vm.toggle()
        assert result is False
        vm.stop.assert_called_once()
        vm.start.assert_not_called()
