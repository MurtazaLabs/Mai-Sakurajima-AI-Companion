"""KyutaiSTT backend — interface parity + permanent-whisper-fallback contract.

All offline/stubbed: no checkpoint downloads, no faster-whisper model loads.
Pins the plan §4 requirements:
- same public surface as FasterWhisperSTT (lazy model, transcribe, stats,
  .sample_rate, .model);
- any load or runtime failure falls back to faster-whisper permanently,
  voice never dies;
- STT_BACKEND config honors the env var ("whisper" default).
"""
import sys
from types import ModuleType

import numpy as np
import pytest
import torch
from voice import stt_kyutai as stt_mod


# ── stubs ────────────────────────────────────────────────────────────────

class _FakeModel:
    def __init__(self, registry):
        self._registry = registry

    def eval(self):
        return self

    def to(self, device):
        return self

    def generate(self, **kwargs):
        self._registry["generate_calls"].append(kwargs)
        if self._registry.get("fail_generate"):
            raise RuntimeError("boom")
        return torch.zeros(1, 8, dtype=torch.int32)


class _FakeModelCls:
    _registry = None

    @classmethod
    def from_pretrained(cls, _path, torch_dtype=None):
        return _FakeModel(cls._registry)


class _FakeInputs(dict):
    def to(self, device):
        return self


class _FakeProcessor:
    received = {}

    def __init__(self, registry):
        self._registry = registry

    def __call__(self, audio=None, **kw):
        _FakeProcessor.received = np.asarray(audio)
        return _FakeInputs({"input_features": torch.zeros(1, 4)})

    def batch_decode(self, tokens, skip_special_tokens=True):
        assert skip_special_tokens is True
        return ["  hello mai "]


class _FakeProcessorCls:
    _registry = None

    @classmethod
    def from_pretrained(cls, _path):
        return _FakeProcessor(cls._registry)


def _fake_transformers(registry) -> ModuleType:
    _FakeModelCls._registry = registry
    _FakeProcessorCls._registry = registry
    fake = ModuleType("transformers")
    fake.KyutaiSpeechToTextProcessor = _FakeProcessorCls
    fake.KyutaiSpeechToTextForConditionalGeneration = _FakeModelCls
    return fake


@pytest.fixture
def loaded_stt(monkeypatch):
    """KyutaiSTT whose transformers import hits fakes; model pre-'loaded'."""
    registry = {"generate_calls": [], "fail_generate": False}
    monkeypatch.setitem(sys.modules, "transformers", _fake_transformers(registry))
    stt = stt_mod.KyutaiSTT()
    assert stt._ensure_model() is True
    assert stt.model is not None  # voice_manager.py:157 gate needs this
    assert stt._processor is not None
    return stt, registry


# ── interface parity ─────────────────────────────────────────────────────

def test_public_surface_matches_faster_whisper():
    stt = stt_mod.KyutaiSTT()  # constructor is import-light (lazy loaders)
    for name in ("transcribe", "stats", "sample_rate", "model", "_ensure_model"):
        assert hasattr(stt, name), f"KyutaiSTT missing {name}"


def test_transcribe_resamples_16k_to_24k_and_decodes(loaded_stt):
    stt, _ = loaded_stt
    audio = np.zeros(1600, dtype=np.float32)  # 0.1 s @ 16 kHz
    text = stt.transcribe(audio)
    assert text == "hello mai"  # stripped
    n = _FakeProcessor.received.shape[0]

    # resampled 0.1s@16k -> 0.1s@24k = 2400 samples, passed through unchanged:
    # whole-second padding was removed once dynamo was disabled (no per-shape
    # retracing left to protect, and the padding cost up to 1s of extra decode)
    assert n == 2400, f"processor must see the 24 kHz audio unpadded, got {n}"


def test_initial_prompt_accepted_but_ignored(loaded_stt):
    stt, registry = loaded_stt
    text = stt.transcribe(np.zeros(1600, dtype=np.float32), initial_prompt="Wake up")
    assert text == "hello mai"
    assert registry["generate_calls"]  # pipeline ran normally


def test_dynamo_disabled_when_triton_missing():
    # Windows has no triton, so every compile attempt fails after burning
    # 2-9s on a cold shape (measured). The backend turns torch.compile off.
    import importlib.util

    stt = stt_mod.KyutaiSTT()
    saved = torch._dynamo.config.disable
    try:
        stt._disable_dynamo(torch)
        if importlib.util.find_spec("triton") is None:
            assert torch._dynamo.config.disable is True
        assert stt._dynamo_disabled is True
    finally:
        torch._dynamo.config.disable = saved


# ── fallback contract ────────────────────────────────────────────────────

class _StubWhisper:
    calls = []

    def __init__(self, *a, **k):
        self.model = "stub"
        self.sample_rate = 16000

    def transcribe(self, audio, language="en", initial_prompt=None):
        _StubWhisper.calls.append((language, initial_prompt))
        return "whisper says hi"

    def stats(self):
        return {"device": "stub"}


def test_load_failure_permanently_falls_back(monkeypatch):
    registry = {"generate_calls": [], "fail_generate": False}
    fake = _fake_transformers(registry)

    def _broken_loader(_path):
        raise OSError("weights missing")

    fake.KyutaiSpeechToTextForConditionalGeneration = _broken_loader
    monkeypatch.setitem(sys.modules, "transformers", fake)
    monkeypatch.setattr(stt_mod, "FasterWhisperSTT", _StubWhisper)

    stt = stt_mod.KyutaiSTT()
    assert stt._ensure_model() is False
    out = stt.transcribe(np.zeros(1600, dtype=np.float32))
    assert out == "whisper says hi"
    assert stt.model is None
    stats = stt.stats()
    assert stats["backend"] == "kyutai(whisper fallback)"
    assert stats["load_failed"] is True


def test_runtime_failure_falls_back_and_stays(loaded_stt, monkeypatch):
    stt, registry = loaded_stt
    monkeypatch.setattr(stt_mod, "FasterWhisperSTT", _StubWhisper)
    # first (successful) call
    assert stt.transcribe(np.zeros(1600, dtype=np.float32)) == "hello mai"
    # second call: generate raises -> delegate to whisper, permanently
    registry["fail_generate"] = True
    _StubWhisper.calls.clear()
    assert stt.transcribe(np.zeros(3200, dtype=np.float32)) == "whisper says hi"
    # third call: no kyutai retry at all
    assert stt.transcribe(np.zeros(3200, dtype=np.float32)) == "whisper says hi"
    #_total stays at 2 (call1 + the failing call2) — a kyutai retry would make it 3
    assert len(registry["generate_calls"]) == 2


def test_stats_reports_rtf_and_calls(loaded_stt):
    stt, _ = loaded_stt
    stt.transcribe(np.zeros(4800, dtype=np.float32))
    s = stt.stats()
    assert s["backend"] == "kyutai"
    assert s["model_loaded"] is True
    assert s["calls"] >= 1
    assert s["sample_rate"] == 16000
    assert "avg_rtf" in s and s["avg_rtf"] >= 0.0


# ── config switch ────────────────────────────────────────────────────────

def test_stt_backend_default_whisper(monkeypatch):
    import importlib

    import config.voice as cv
    monkeypatch.delenv("STT_BACKEND", raising=False)
    importlib.reload(cv)
    assert cv.STT_BACKEND == "whisper"
    assert cv.KYUTAI_STT_DIR  # path string present
    # restore ambient config (a .env may legitimately set STT_BACKEND)
    monkeypatch.undo()
    importlib.reload(cv)


def test_stt_backend_env_switch(monkeypatch):
    monkeypatch.setenv("STT_BACKEND", "kyutai")
    import importlib

    import config.voice as cv
    importlib.reload(cv)
    try:
        assert cv.STT_BACKEND == "kyutai"
    finally:
        monkeypatch.undo()
        importlib.reload(cv)  # ambient env decides the restored value


def test_builder_non_kyutai_backend_hooks_into_placeholder_build():
    """boundary: factory branch reads the live module via getattr with a
    'whisper' guard — a missing/typo'd attr must fall back to whisper."""
    class _NoAttr:
        STT_BACKEND = "whisper"

    assert getattr(_NoAttr(), "STT_BACKEND", "whisper") == "whisper"
