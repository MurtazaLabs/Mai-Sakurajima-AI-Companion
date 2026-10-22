"""Tests for VAD failure latching (R-5)."""

from unittest.mock import patch

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def _reset_vad_state():
    from voice.vad import VAD
    old_model, old_failed = VAD._shared_model, VAD._shared_load_failed
    VAD._shared_model, VAD._shared_load_failed = None, False
    yield
    VAD._shared_model, VAD._shared_load_failed = old_model, old_failed


def _chunk():
    return np.zeros(512, dtype=np.float32)


class TestVADFailureLatch:

    def test_load_failure_latches_no_retry(self):
        """After a failed load, subsequent is_speech calls must not
        re-attempt the download (R-5)."""
        from voice.vad import VAD
        vad = VAD()
        with patch("torch.jit.load", side_effect=RuntimeError("boom")):
            assert vad.is_speech(_chunk()) is False
        assert vad._load_failed is True
        with patch("torch.jit.load", side_effect=AssertionError("must not reload")):
            assert vad.is_speech(_chunk()) is False

    def test_speech_prob_returns_zero_after_failure(self):
        from voice.vad import VAD
        vad = VAD()
        with patch("torch.jit.load", side_effect=RuntimeError("boom")):
            assert vad.speech_prob(_chunk()) == 0.0

    def test_shared_failure_flag_blocks_other_instances(self):
        """A failed load in one instance blocks downloads in all others."""
        from voice.vad import VAD
        vad1 = VAD()
        with patch("torch.jit.load", side_effect=RuntimeError("boom")):
            vad1.is_speech(_chunk())
        assert VAD._shared_load_failed is True
        vad2 = VAD()
        with patch("torch.jit.load", side_effect=AssertionError("must not reload")):
            assert vad2.is_speech(_chunk()) is False

    def test_load_never_reloads_after_shared_success(self):
        """Once a shared model exists, the quick path is used and neither
        failure latches nor the slow load path run."""
        from voice.vad import VAD
        fake_model = type("FakeModel", (), {"eval": lambda self: None})()
        VAD._shared_model = fake_model
        vad = VAD()
        with patch("torch.jit.load", side_effect=AssertionError("must not load")):
            vad._load_model()
        assert vad._model is fake_model

    def test_reset_allows_new_attempt_after_cooling(self):
        from voice.vad import VAD
        vad = VAD()
        with patch("torch.jit.load", side_effect=RuntimeError("boom")):
            vad.is_speech(_chunk())
        assert vad._load_failed is True
        VAD._shared_load_failed = False
        vad._load_failed = False
        vad._model = None
        fake_model = type("FakeModel", (), {"eval": lambda self: None})()
        with patch("torch.jit.load", return_value=fake_model):
            vad._load_model()
        assert vad._model is fake_model
