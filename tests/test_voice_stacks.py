"""Voice stack switching — ElevenLabs cloud backends and the local↔cloud swap.

Guards the two properties the plan depends on:
- a cloud failure must degrade to the local backend, never to silence;
- switching to cloud must actually release the ~2.3 GB Kyutai held, which means
  every reference to the old STT (app, voice_manager, wake_detector, kernel)
  gets replaced in one place.
"""
import types
from unittest.mock import MagicMock

import numpy as np
import soundfile as sf

import voice.elevenlabs_stt as stt_mod

# ---------------------------------------------------------------------------
#  ElevenLabs TTS
# ---------------------------------------------------------------------------

def _pcm(values):
    return np.asarray(values, dtype="<i2").tobytes()


class TestElevenLabsTTS:

    def _make(self, **kw):
        from voice.elevenlabs_tts import ElevenLabsTTS
        tts = ElevenLabsTTS(api_key="test-key", **kw)
        tts._http = MagicMock()
        return tts

    def test_generate_writes_pcm_as_wav(self, tmp_path):
        tts = self._make()
        tts._http.post.return_value = MagicMock(
            status_code=200, content=_pcm([0, 16384, -16384, 16384])
        )
        out = tmp_path / "a.wav"
        tts.generate("Hello there.", str(out), emotion="happy")

        data, sr = sf.read(str(out))
        assert sr == 24000
        assert len(data) == 4
        assert abs(float(data[1]) - 0.5) < 0.01
        assert tts.stats()["calls"] == 1

    def test_request_targets_voice_and_pcm_format(self, tmp_path):
        tts = self._make(voice_id="vx", model_id="eleven_flash_v2_5")
        tts._http.post.return_value = MagicMock(status_code=200, content=_pcm([0, 0]))
        tts.generate("hi", str(tmp_path / "a.wav"))

        args, kwargs = tts._http.post.call_args
        assert args[0].endswith("/v1/text-to-speech/vx")
        assert kwargs["params"]["output_format"] == "pcm_24000"
        assert kwargs["headers"]["xi-api-key"] == "test-key"
        assert kwargs["json"]["model_id"] == "eleven_flash_v2_5"

    def test_emoji_are_stripped_from_spoken_text(self, tmp_path):
        tts = self._make()
        tts._http.post.return_value = MagicMock(status_code=200, content=_pcm([0, 0]))
        tts.generate("Hi 😊 there 🎉", str(tmp_path / "a.wav"))
        assert tts._http.post.call_args.kwargs["json"]["text"] == "Hi there"

    def test_stage_direction_is_not_spoken(self, tmp_path):
        """Spark-X2.5 opened a real turn with this; TTS read it aloud."""
        tts = self._make()
        tts._http.post.return_value = MagicMock(status_code=200, content=_pcm([0, 0]))
        tts.generate("(with a warm smile) That's really sweet.", str(tmp_path / "a.wav"))
        assert tts._http.post.call_args.kwargs["json"]["text"] == "That's really sweet."

    def test_ordinary_prose_parenthesis_survives(self):
        from voice.speech_text import sanitize
        text = "It worked (which, as I said, took a while)."
        assert sanitize(text) == text
        assert sanitize("(smiling) Hi.") == "Hi."
        # Punctuation inside the group means it is speech, not a stage note.
        assert sanitize("Wait (huh?) what.") == "Wait (huh?) what."

    def test_kokoro_enhance_text_uses_the_same_guard(self):
        # No self access in _enhance_text, so skip building the real model.
        from voice.kokoro_tts import KokoroTTS
        assert KokoroTTS._enhance_text(None, "(smiling) Hi.") == "Hi."

    def test_unsupported_format_falls_back_to_pcm_24000(self):
        tts = self._make(output_format="mp3_44100_128")
        assert tts.output_format == "pcm_24000"
        assert tts.sample_rate == 24000

    def test_api_error_degrades_to_kokoro(self, tmp_path, monkeypatch):
        tts = self._make()
        tts._http.post.return_value = MagicMock(status_code=401, text="bad key")
        kokoro = MagicMock()
        monkeypatch.setattr(tts, "_kokoro", lambda: kokoro)

        tts.generate("Hello.", str(tmp_path / "a.wav"))

        kokoro.generate.assert_called_once()
        assert tts.stats()["failures"] == 1

    def test_empty_text_is_a_noop(self, tmp_path):
        tts = self._make()
        tts.generate("   ", str(tmp_path / "a.wav"))
        tts._http.post.assert_not_called()

    def test_is_available_requires_key(self):
        from voice.elevenlabs_tts import ElevenLabsTTS
        assert ElevenLabsTTS(api_key="").is_available() is False
        assert ElevenLabsTTS(api_key="k").is_available() is True


# ---------------------------------------------------------------------------
#  ElevenLabs STT
# ---------------------------------------------------------------------------

class _StubWhisper:
    stack = "local"

    def __init__(self, *a, **kw):
        self.calls = 0

    def transcribe(self, audio, language="en", initial_prompt=None):
        self.calls += 1
        return "whisper said this"

    def stats(self):
        return {"device": "cpu", "sample_rate": 16000}


class TestElevenLabsSTT:

    def _make(self, api_key="test-key", monkeypatch=None):
        if monkeypatch is not None:
            monkeypatch.setattr(stt_mod, "FasterWhisperSTT", _StubWhisper)
        return stt_mod.ElevenLabsSTT(api_key=api_key)

    def test_no_key_uses_whisper_and_reports_missing(self, monkeypatch):
        stt = self._make(api_key="", monkeypatch=monkeypatch)
        audio = np.zeros(1600, dtype=np.float32)
        assert stt.transcribe(audio) == "whisper said this"
        assert stt.model is None
        assert stt.stats()["backend"] == "elevenlabs(whisper fallback)"

    def test_transcribe_posts_wav_and_returns_text(self, monkeypatch):
        stt = self._make(monkeypatch=monkeypatch)
        stt._http = MagicMock()
        stt._http.post.return_value = MagicMock(
            status_code=200, json=lambda: {"text": "  hello mai  "}
        )
        audio = np.zeros(1600, dtype=np.float32)
        assert stt.transcribe(audio) == "hello mai"

        args, kwargs = stt._http.post.call_args
        assert args[0].endswith("/v1/speech-to-text")
        assert kwargs["data"]["model_id"] == stt.model_id
        assert kwargs["files"]["file"][0].endswith(".wav")
        assert stt.model is not None  # voice_manager's readiness check
        assert stt.stats()["backend"] == "elevenlabs"

    def test_http_error_falls_back_permanently(self, monkeypatch):
        stt = self._make(monkeypatch=monkeypatch)
        stt._http = MagicMock()
        stt._http.post.return_value = MagicMock(status_code=422, text="unknown model_id")
        audio = np.zeros(1600, dtype=np.float32)

        assert stt.transcribe(audio) == "whisper said this"
        assert stt.stats()["backend"] == "elevenlabs(whisper fallback)"
        # permanent: the next call goes straight to whisper, no second request
        stt._http.post.reset_mock()
        assert stt.transcribe(audio) == "whisper said this"
        stt._http.post.assert_not_called()

    def test_sample_rate_defaults_to_voice_rate(self, monkeypatch):
        from app.config_loader import Settings
        stt = self._make(monkeypatch=monkeypatch)
        assert stt.sample_rate == Settings.VOICE_SAMPLE_RATE


# ---------------------------------------------------------------------------
#  Stack construction + resolve
# ---------------------------------------------------------------------------

class TestStackConstruction:

    def test_local_stack_builds_kyutai_and_kokoro(self, monkeypatch):
        import voice.kokoro_tts as kt
        from voice.stack_switcher import build_stt, build_tts
        from voice.stt_kyutai import KyutaiSTT

        sentinel = object()
        monkeypatch.setattr(kt, "KokoroTTS", lambda: sentinel)
        assert isinstance(build_stt("local"), KyutaiSTT)
        assert build_tts("local") is sentinel

    def test_cloud_stack_builds_elevenlabs(self):
        from voice.elevenlabs_stt import ElevenLabsSTT
        from voice.elevenlabs_tts import ElevenLabsTTS
        from voice.stack_switcher import build_stt, build_tts

        assert isinstance(build_stt("cloud"), ElevenLabsSTT)
        assert isinstance(build_tts("cloud"), ElevenLabsTTS)

    def test_local_stack_honours_whisper_backend(self, monkeypatch):
        from app.config_loader import Settings
        from voice.stack_switcher import build_stt
        from voice.stt import FasterWhisperSTT

        monkeypatch.setattr(Settings, "STT_BACKEND", "whisper")
        assert isinstance(build_stt("local"), FasterWhisperSTT)

    def test_resolve_stack_reads_persisted_override(self, monkeypatch):
        from app.config_loader import Settings
        from voice.stack_switcher import resolve_stack

        cm = MagicMock()
        cm.get.return_value = "cloud"
        monkeypatch.setattr(Settings, "ELEVENLABS_API_KEY", "k")
        assert resolve_stack(cm) == "cloud"

    def test_resolve_stack_without_key_stays_local(self, monkeypatch):
        from app.config_loader import Settings
        from voice.stack_switcher import resolve_stack

        cm = MagicMock()
        cm.get.return_value = "cloud"
        monkeypatch.setattr(Settings, "ELEVENLABS_API_KEY", "")
        assert resolve_stack(cm) == "local"

    def test_resolve_stack_unknown_value_stays_local(self):
        from voice.stack_switcher import resolve_stack
        cm = MagicMock()
        cm.get.return_value = "banana"
        assert resolve_stack(cm) == "local"


# ---------------------------------------------------------------------------
#  The switch itself
# ---------------------------------------------------------------------------

class _Wake:
    def __init__(self, stt):
        self.stt = stt


class _VM:
    def __init__(self, stt):
        self.stt = stt
        self.wake_detector = _Wake(stt)
        self.speaking = False

    def is_speaking(self):
        return self.speaking


class _FakeStt:
    def __init__(self, stack):
        self.stack = stack
        self.closed = False

    def stats(self):
        return {"backend": self.stack}


class _FakeTts:
    def __init__(self, stack):
        self.stack = stack
        self.closed = False

    def close(self):
        self.closed = True

    def stats(self):
        return {"engine": self.stack}


class _App:
    def __init__(self, stack="local"):
        self.stt = _FakeStt(stack)
        self.tts = _FakeTts(stack)
        self.voice_manager = _VM(self.stt)
        self.voice = types.SimpleNamespace(tts=self.tts, is_speaking=False)
        self.voice_renderer = types.SimpleNamespace(tts=self.tts)
        self.kernel = types.SimpleNamespace(stt=self.stt)
        self.config_manager = MagicMock()


def _switcher(app, monkeypatch, cloud_ok=True):
    import voice.stack_switcher as sw
    from app.config_loader import Settings

    monkeypatch.setattr(Settings, "ELEVENLABS_API_KEY", "k" if cloud_ok else "")
    monkeypatch.setattr(sw, "build_stt", lambda stack: _FakeStt(stack))
    monkeypatch.setattr(sw, "build_tts", lambda stack: _FakeTts(stack))
    # Hardware-free: the real query imports torch and needs a GPU.
    monkeypatch.setattr(sw, "_vram_free_mb", lambda: None)
    return sw.VoiceStackSwitcher(app)


class TestVoiceStackSwitcher:

    def test_switch_replaces_every_injection_point(self, monkeypatch):
        app = _App("local")
        switcher = _switcher(app, monkeypatch)

        result = switcher.switch("cloud")

        assert result["stack"] == "cloud"
        assert app.stt.stack == "cloud"
        assert app.voice_manager.stt is app.stt
        assert app.voice_manager.wake_detector.stt is app.stt
        assert app.kernel.stt is app.stt
        assert app.voice.tts is app.tts
        assert app.voice_renderer.tts is app.tts
        app.config_manager.set.assert_called_once_with("VOICE_STACK", "cloud")

    def test_switch_closes_the_old_cloud_tts(self, monkeypatch):
        app = _App("cloud")
        old_tts = app.tts
        switcher = _switcher(app, monkeypatch)

        switcher.switch("local")

        assert old_tts.closed is True

    def test_refuses_while_speaking(self, monkeypatch):
        app = _App("local")
        app.voice_manager.speaking = True
        switcher = _switcher(app, monkeypatch)

        result = switcher.switch("cloud")

        assert result["error"] == "busy"
        assert app.stt.stack == "local"

    def test_refuses_cloud_without_key(self, monkeypatch):
        app = _App("local")
        switcher = _switcher(app, monkeypatch, cloud_ok=False)

        result = switcher.switch("cloud")

        assert result["error"] == "no_api_key"
        assert app.stt.stack == "local"

    def test_unknown_stack_rejected(self, monkeypatch):
        switcher = _switcher(_App("local"), monkeypatch)
        assert switcher.switch("banana")["error"] == "unknown_stack"

    def test_switching_to_current_stack_is_a_noop(self, monkeypatch):
        app = _App("local")
        switcher = _switcher(app, monkeypatch)

        result = switcher.switch("local")

        assert result.get("unchanged") is True
        app.config_manager.set.assert_not_called()


# ---------------------------------------------------------------------------
#  API routes
# ---------------------------------------------------------------------------

class TestProviderRoutes:

    def _api(self):
        from api.routes_system import SystemMixin

        class Api(SystemMixin):
            pass

        api = Api()
        api.llm = MagicMock()
        api.llm.providers_status.return_value = {"selected": "openrouter", "providers": {}}
        api.llm.select_provider.return_value = {"selected": "llamacpp", "providers": {}}
        api.voice_stack = MagicMock()
        api.voice_stack.status.return_value = {"stack": "local"}
        api.voice_stack.switch.return_value = {"stack": "cloud"}
        api.config_manager = MagicMock()
        return api

    def test_providers_reports_both_halves(self):
        api = self._api()
        out = api.system_providers()
        assert out["llm"]["selected"] == "openrouter"
        assert out["voice"]["stack"] == "local"

    def test_llm_switch_persists_the_choice(self):
        api = self._api()
        out = api.system_llm_provider("llamacpp")
        assert out["selected"] == "llamacpp"
        api.config_manager.set.assert_called_once_with("LLM_PROVIDER", "llamacpp")

    def test_llm_switch_does_not_persist_on_error(self):
        api = self._api()
        api.llm.select_provider.return_value = {"error": "unknown_provider"}
        api.system_llm_provider("banana")
        api.config_manager.set.assert_not_called()

    def test_voice_switch_delegates(self):
        api = self._api()
        assert api.system_voice_stack("cloud")["stack"] == "cloud"

    def test_missing_components_report_unavailable(self):
        from api.routes_system import SystemMixin

        class Api(SystemMixin):
            pass

        api = Api()
        assert api.system_providers()["llm"]["error"] == "llm_unavailable"
        assert api.system_llm_provider("openrouter")["error"] == "llm_unavailable"
        assert api.system_voice_stack("cloud")["error"] == "voice_stack_unavailable"


def test_kokoro_and_kyutai_are_tagged_local():
    from voice.kokoro_tts import KokoroTTS
    from voice.stt import FasterWhisperSTT
    from voice.stt_kyutai import KyutaiSTT

    assert KokoroTTS.stack == "local"
    assert KyutaiSTT.stack == "local"
    assert FasterWhisperSTT.stack == "local"


def test_elevenlabs_backends_are_tagged_cloud():
    from voice.elevenlabs_stt import ElevenLabsSTT
    from voice.elevenlabs_tts import ElevenLabsTTS

    assert ElevenLabsSTT.stack == "cloud"
    assert ElevenLabsTTS.stack == "cloud"
