"""Phase 0 — noise gating: whole-utterance VAD gate before STT.

Rejects fan/hiss-only recordings before they reach Whisper at both queue
consumers (_handle_wake_audio, _transcribe). The gate must fail open when
the VAD is unavailable so voice never bricks.
"""
from unittest.mock import MagicMock

import numpy as np
import pytest

from voice.vad import VAD
from voice.voice_event import VoiceEvent
from voice.voice_manager import VoiceManager


class FixedVad(VAD):
    """VAD stub returning a constant speech probability.

    speech_prob() is overridden, so the real Silero model is never loaded
    and shared class state can never clobber the stub.
    """

    def __init__(self, prob, threshold=0.5):
        super().__init__(threshold=threshold, sample_rate=16000)
        self._prob = prob
        self.calls = 0
        self._model = object()  # sentinel: non-None so utterance_score proceeds

    def speech_prob(self, chunk):
        self.calls += 1
        return self._prob


class PatternVad(FixedVad):
    """Cycles a fixed list of probabilities across frames."""

    def __init__(self, probs, threshold=0.5):
        super().__init__(probs[0], threshold=threshold)
        self._probs = list(probs)

    def speech_prob(self, chunk):
        p = self._probs[self.calls % len(self._probs)]
        self.calls += 1
        return p


class NoModelVad(VAD):
    """Real VAD behavior but never loads a model — score must be None."""

    def _load_model(self):
        return


class BrokenVad:
    """Scoring raises — gate must fail open."""

    def utterance_score(self, audio, max_frames=256):
        raise RuntimeError("boom")


class RecordingSTT:
    def __init__(self, text="hello mai"):
        self.calls = 0
        self.text = text

    def transcribe(self, audio, **kwargs):
        self.calls += 1
        return self.text


class FakeWakeDetector:
    def detect_in_text(self, text):
        return "mai" in text.lower()


def noise_audio(seconds=1.0, seed=0):
    rng = np.random.default_rng(seed)
    return (rng.standard_normal(int(16000 * seconds)) * 0.1).astype(np.float32)


def make_vm(**kwargs):
    kwargs.setdefault("sample_rate", 16000)
    kwargs.setdefault("stt", None)
    return VoiceManager(**kwargs)


class TestUtteranceScore:
    def test_high_prob_returns_pass_values(self):
        vad = FixedVad(0.9)
        score = vad.utterance_score(noise_audio(2.0))
        assert score is not None
        mean, ratio = score
        assert mean == pytest.approx(0.9)
        assert ratio == 1.0

    def test_low_prob_returns_fail_values(self):
        vad = FixedVad(0.1)
        score = vad.utterance_score(noise_audio(2.0))
        assert score is not None
        mean, ratio = score
        assert mean == pytest.approx(0.1)
        assert ratio == 0.0

    def test_no_model_returns_none(self):
        vad = NoModelVad(threshold=0.5)
        assert vad.utterance_score(noise_audio(2.0)) is None

    def test_too_short_returns_none(self):
        vad = FixedVad(0.9)
        assert vad.utterance_score(np.zeros(100, dtype=np.float32)) is None

    def test_scoring_capped_at_max_frames(self):
        vad = FixedVad(0.9)
        score = vad.utterance_score(np.zeros(16000 * 30, dtype=np.float32), max_frames=64)
        assert score is not None
        assert vad.calls <= 64

    def test_ratio_counts_frames_above_threshold(self):
        # ~3 of 4 frames above 0.5 -> ratio ~0.75
        vad = PatternVad([0.9, 0.9, 0.1, 0.9])
        mean, ratio = vad.utterance_score(np.zeros(16000, dtype=np.float32))
        assert ratio == pytest.approx(0.75, abs=0.1)
        assert mean > 0.3


class TestGateUtterance:
    def test_passes_when_speech(self):
        vm = make_vm(vad=FixedVad(0.9))
        ok, mean, ratio = vm._gate_utterance(noise_audio())
        assert ok is True
        assert mean == pytest.approx(0.9)
        assert ratio == 1.0

    def test_rejects_when_noise(self):
        vm = make_vm(vad=FixedVad(0.1))
        ok, mean, ratio = vm._gate_utterance(noise_audio())
        assert ok is False
        assert mean < 0.30
        assert ratio == 0.0

    def test_rejects_when_ratio_below_threshold(self):
        # mean 0.32 clears MIN_MEAN but ratio 0.0 fails MIN_RATIO
        vm = make_vm(vad=FixedVad(0.32))
        ok, _, _ = vm._gate_utterance(noise_audio())
        assert ok is False

    def test_fails_open_when_scoring_raises(self):
        vm = make_vm(vad=BrokenVad())
        ok, mean, ratio = vm._gate_utterance(noise_audio())
        assert ok is True

    def test_fails_open_when_model_missing(self):
        vm = make_vm(vad=NoModelVad())
        ok, _, _ = vm._gate_utterance(noise_audio())
        assert ok is True

    def test_fails_open_when_vad_none(self):
        vm = make_vm(vad=NoModelVad())  # skips the real VAD preload
        vm._vad = None
        ok, _, _ = vm._gate_utterance(noise_audio())
        assert ok is True


class TestTranscribeGate:
    def test_noise_rejected_without_stt_call(self):
        stt = RecordingSTT(text="should not run")
        vm = make_vm(stt=stt, vad=FixedVad(0.1))
        event = vm._transcribe(
            noise_audio(),
            speaker="test",
            speaker_conf=0.5,
            emotion={"label": "happy", "confidence": 0.7},
        )
        assert isinstance(event, VoiceEvent)
        assert event.text == ""
        assert event.wake_detected is False
        assert stt.calls == 0
        assert event.emotion["label"] == "happy"
        assert event.speaker == "test"
        assert event.duration == pytest.approx(1.0)

    def test_speech_passes_to_stt(self):
        stt = RecordingSTT(text="the sky is blue")
        vm = make_vm(stt=stt, vad=FixedVad(0.9))
        event = vm._transcribe(noise_audio())
        assert event.text == "the sky is blue"
        assert stt.calls == 1


class TestWakeAudioGate:
    def test_noise_never_reaches_stt(self):
        stt = RecordingSTT(text="should not run")
        vm = make_vm(stt=stt, vad=FixedVad(0.1), wake_detector=FakeWakeDetector())
        found = vm._handle_wake_audio(noise_audio())
        assert found is False
        assert stt.calls == 0

    def test_speech_transcribed_and_wake_detected(self):
        stt = RecordingSTT(text="hey mai")
        vm = make_vm(stt=stt, vad=FixedVad(0.9), wake_detector=FakeWakeDetector())
        vm._wake_stop.set()  # prevents the WAKE_DETECTED wait loop from blocking
        found = vm._handle_wake_audio(noise_audio())
        assert found is True
        assert stt.calls == 1

    def test_speech_without_wake_word_transcribes_only(self):
        stt = RecordingSTT(text="hello there")
        vm = make_vm(stt=stt, vad=FixedVad(0.9), wake_detector=FakeWakeDetector())
        found = vm._handle_wake_audio(noise_audio())
        assert found is False
        assert stt.calls == 1


class TestKernelListenGate:
    """os_kernel._listen_with_voice_manager(return_audio=True) must apply the
    same gate before its direct stt.transcribe() call."""

    def _kernel(self, gate_result, transcribe_text=""):
        from core.os_kernel import AIOSKernel

        vm = MagicMock()
        vm._gate_utterance.return_value = gate_result
        vm.stt.transcribe.return_value = transcribe_text
        vm.listen_raw.return_value = {"audio": noise_audio(), "emotion": None}
        kernel = AIOSKernel(
            brain=MagicMock(),
            voice=MagicMock(),
            wake=MagicMock(),
            stt=MagicMock(),
            state=MagicMock(),
            relationship_engine=MagicMock(),
            voice_manager=vm,
        )
        return kernel, vm

    def test_noise_rejected_before_transcribe(self):
        kernel, vm = self._kernel(gate_result=(False, 0.05, 0.0))
        text, audio = kernel._listen_with_voice_manager(return_audio=True)
        assert text == ""
        assert audio is None
        vm.stt.transcribe.assert_not_called()

    def test_speech_passes_gate(self):
        kernel, vm = self._kernel(gate_result=(True, 0.8, 0.9), transcribe_text="hello there")
        text, audio = kernel._listen_with_voice_manager(return_audio=True)
        assert text == "hello there"
        assert audio is not None
        vm.stt.transcribe.assert_called_once()


class TestDiarizationFullClip:
    """Diarization regions must not clip audio before STT — regions the
    detector missed were silently dropped, so a 1.34s utterance reached
    Whisper as a 0.22s fragment and came back empty (live log 2026-10-09).
    The full clip is transcribed; diarization only labels the speaker."""

    @staticmethod
    def _region(start, end, speaker, conf):
        from types import SimpleNamespace
        return SimpleNamespace(start_sample=start, end_sample=end,
                                speaker_id=speaker, confidence=conf)

    def _run(self, regions, audio_len=16000):
        vm = make_vm()
        vm.utterance_segmenter = None
        vm.emotion_detector = None
        vm.diarization_engine = type("FakeDiar", (), {
            "segment": lambda self, audio: regions,
        })()
        captured = {}

        def fake_transcribe(audio, speaker="", speaker_conf=0.0, emotion=None):
            captured["samples"] = len(audio)
            captured["speaker"] = speaker
            return VoiceEvent(text="", speaker=speaker, audio_length=len(audio))

        vm._transcribe = fake_transcribe
        audio = noise_audio(audio_len / 16000.0)
        _, _, speaker_segments, events = vm._process_audio(audio)
        return captured, events, speaker_segments

    def test_full_clip_transcribed_not_region_slice(self):
        captured, events, _ = self._run(
            [self._region(0, 3584, "alice", 0.9)], audio_len=16000
        )
        assert captured["samples"] == 16000  # full clip, not the 3584 region
        assert captured["speaker"] == "alice"
        assert len(events) == 1

    def test_dominant_region_wins_for_speaker_label(self):
        captured, _, _ = self._run([
            self._region(0, 3200, "bob", 0.5),
            self._region(3200, 16000, "alice", 0.9),
        ])
        assert captured["samples"] == 16000
        assert captured["speaker"] == "alice"

    def test_empty_regions_fall_back_to_segmenter_path(self):
        vm = make_vm()
        vm.utterance_segmenter = None
        vm.emotion_detector = None
        vm.diarization_engine = type("FakeDiar", (), {
            "segment": lambda self, audio: [],
        })()
        captured = {}

        def fake_transcribe(audio, speaker="", speaker_conf=0.0, emotion=None):
            captured["samples"] = len(audio)
            return VoiceEvent(text="", speaker=speaker, audio_length=len(audio))

        vm._transcribe = fake_transcribe
        vm._identify_speaker = lambda seg: ("", 0.0)
        audio = noise_audio(1.0)
        _, _, _, events = vm._process_audio(audio)
        assert captured["samples"] == len(audio)  # segmenter-less fallback: whole clip
        assert len(events) == 1
