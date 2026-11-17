"""ElevenLabs Scribe STT — cloud transcription behind the FasterWhisperSTT surface.

Contract (same as ``KyutaiSTT``, voice must never die from a cloud outage):
- ``transcribe(audio) -> str``, ``stats()``, ``.sample_rate``, ``.model``;
- ``TranscriptionUnavailable`` only when *no* backend is usable;
- any API failure (or a missing key) falls back permanently to
  ``FasterWhisperSTT``, which runs on CPU and holds no VRAM.

Why this class matters for the local LLM: the local stack's Kyutai model holds
~2.3 GB of the T1000's 4 GB. Moving STT to the cloud is what frees the VRAM an
8B GGUF needs (plan §4); TTS was already CPU-only.
"""
import io
import logging
import threading
import time

import httpx
import numpy as np
import soundfile as sf
from numpy.typing import NDArray

from app.config_loader import Settings
from voice.stt import FasterWhisperSTT

logger = logging.getLogger(__name__)

_API_BASE = "https://api.elevenlabs.io"


class ElevenLabsSTT:

    stack = "cloud"

    def __init__(self, api_key=None, model_id=None, sample_rate=None, timeout=None,
                 base_url=None):
        self.api_key = api_key if api_key is not None else Settings.ELEVENLABS_API_KEY
        self.model_id = model_id or Settings.ELEVENLABS_STT_MODEL
        self.sample_rate = sample_rate or Settings.VOICE_SAMPLE_RATE
        self.base_url = (base_url or _API_BASE).rstrip("/")
        self.timeout = timeout or Settings.ELEVENLABS_TIMEOUT

        # voice_manager's component check reads `.model is not None`; the cloud
        # backend has nothing to load, so the id doubles as the ready marker.
        self.model = f"elevenlabs:{self.model_id}" if self.api_key else None

        self._lock = threading.RLock()
        self._http = httpx.Client(timeout=self.timeout)
        self._fallback = None
        self._ok = bool(self.api_key)

        self._calls = 0
        self._speech_seconds = 0.0
        self._stt_seconds = 0.0

    # ==================================================
    # 🎙️ TRANSCRIBE
    # ==================================================

    def transcribe(self, audio: NDArray[np.float32], language: str = "en",
                   initial_prompt: str | None = None) -> str:
        if not self._ensure_backend():
            return self._fallback.transcribe(
                audio, language=language, initial_prompt=initial_prompt
            )
        if initial_prompt:
            logger.debug("[ElevenLabsSTT] initial_prompt unsupported by scribe — ignored")
        try:
            return self._cloud_transcribe(audio, language)
        except Exception as e:
            self._enter_permanent_fallback(f"Runtime failure: {e}")
            return self._fallback.transcribe(
                audio, language=language, initial_prompt=initial_prompt
            )

    def _ensure_backend(self) -> bool:
        """True = cloud usable; False = permanent whisper fallback."""
        with self._lock:
            if self._ok:
                return True
            if self._fallback is not None:
                return False
            self.model = None
            logger.warning(
                "[ElevenLabsSTT] No ELEVENLABS_API_KEY — falling back to faster-whisper"
            )
            self._fallback = FasterWhisperSTT()
            return False

    def _enter_permanent_fallback(self, reason: str) -> None:
        with self._lock:
            if self._fallback is None:
                logger.error(
                    "[ElevenLabsSTT] %s — falling back to faster-whisper permanently", reason
                )
                self._ok = False
                self.model = None
                self._fallback = FasterWhisperSTT()

    def _cloud_transcribe(self, audio: NDArray[np.float32], language: str) -> str:
        x = np.asarray(audio, dtype=np.float32)
        buf = io.BytesIO()
        sf.write(buf, x, self.sample_rate, format="WAV", subtype="PCM_16")

        t0 = time.perf_counter()
        resp = self._http.post(
            f"{self.base_url}/v1/speech-to-text",
            headers={"xi-api-key": self.api_key},
            data={"model_id": self.model_id, "language_code": language or "en"},
            files={"file": ("utterance.wav", buf.getvalue(), "audio/wav")},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        text = (resp.json().get("text") or "").strip()

        dt = time.perf_counter() - t0
        with self._lock:
            self._calls += 1
            self._speech_seconds += len(x) / float(self.sample_rate)
            self._stt_seconds += dt
        logger.info("[ElevenLabsSTT] %.2fs for %.2fs audio", dt,
                    len(x) / float(self.sample_rate))
        return text

    # ==================================================
    # 📊 STATS
    # ==================================================

    def stats(self) -> dict:
        with self._lock:
            fallback = self._fallback
        if fallback is not None:
            out = fallback.stats()
            out["backend"] = "elevenlabs(whisper fallback)"
            out["fallback"] = True
            return out
        speech = self._speech_seconds
        rtf = (self._stt_seconds / speech) if speech > 0 else 0.0
        return {
            "backend": "elevenlabs",
            "model_id": self.model_id,
            "sample_rate": self.sample_rate,
            "model_loaded": self._ok,
            "calls": self._calls,
            "speech_seconds": round(speech, 2),
            "stt_seconds": round(self._stt_seconds, 2),
            "avg_rtf": round(rtf, 3),
        }

    def close(self):
        try:
            self._http.close()
        except Exception as e:
            logger.debug("[ElevenLabsSTT] close: %s", e)
