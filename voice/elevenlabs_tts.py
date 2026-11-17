"""ElevenLabs TTS — cloud voice behind the same ``generate(text, path, emotion=)``
contract ``KokoroTTS`` exposes.

Both call sites inspect that signature (``voice/realtime.py`` and
``voice/renderer.py``), so nothing downstream changes: swap the engine object and
playback, the AEC reference tap and the prosody renderer keep working.

Raw PCM (``pcm_24000``) is requested rather than MP3 — MP3 would need a decoder
and add latency. The clip is written as a 24 kHz WAV; ``StreamPlayer`` reads the
rate from the file and resamples the AEC reference to 16 kHz.

Cost is per character (plan §9 R3): Flash v2.5 is the cheap real-time tier.
Any API failure falls back to Kokoro permanently — the voice must degrade, never
go silent.
"""
import logging
import threading
import time

import httpx
import numpy as np
import soundfile as sf

from app.config_loader import Settings
from voice.speech_text import sanitize

logger = logging.getLogger("Mai.ElevenLabsTTS")

_API_BASE = "https://api.elevenlabs.io"

# Emotion → stability. Low stability = more expressive delivery.
_STABILITY = {
    "soft": 0.65,
    "calm": 0.65,
    "sad": 0.6,
    "neutral": 0.5,
    "happy": 0.35,
    "teasing": 0.35,
    "annoyed": 0.35,
}

# PCM formats carry their rate in the name; writing the wrong rate plays the
# clip at the wrong speed, so unsupported formats fall back instead.
_PCM_RATES = {
    "pcm_16000": 16000,
    "pcm_22050": 22050,
    "pcm_24000": 24000,
    "pcm_44100": 44100,
}


class ElevenLabsTTS:

    stack = "cloud"
    name = "elevenlabs"

    def __init__(
        self,
        api_key=None,
        voice_id=None,
        model_id=None,
        output_format=None,
        timeout=None,
        base_url=None,
    ):
        self.api_key = api_key if api_key is not None else Settings.ELEVENLABS_API_KEY
        self.voice_id = voice_id or Settings.ELEVENLABS_VOICE_ID
        self.model_id = model_id or Settings.ELEVENLABS_TTS_MODEL
        self.base_url = (base_url or _API_BASE).rstrip("/")
        self.timeout = timeout or Settings.ELEVENLABS_TIMEOUT

        fmt = (output_format or Settings.ELEVENLABS_OUTPUT_FORMAT).strip().lower()
        if fmt not in _PCM_RATES:
            logger.warning(
                "[ElevenLabsTTS] Unsupported output_format %r — using pcm_24000", fmt
            )
            fmt = "pcm_24000"
        self.output_format = fmt
        self.sample_rate = _PCM_RATES[fmt]

        self.last_emotion = "neutral"

        self._lock = threading.RLock()
        self._http = httpx.Client(timeout=self.timeout)
        self._fallback = None

        self._calls = 0
        self._chars = 0
        self._failures = 0
        self._last_latency = 0.0

    # ==================================================
    # 🗣️ MAIN GENERATION (KokoroTTS contract)
    # ==================================================

    def generate(self, text, output_path, emotion="neutral"):
        if not text:
            return

        self.last_emotion = emotion
        clean = self._clean_text(text)
        if not clean:
            return

        started = time.perf_counter()
        try:
            audio = self._fetch(clean, emotion)
            if audio.size == 0:
                raise RuntimeError("empty audio response")
            sf.write(output_path, audio, self.sample_rate)
            with self._lock:
                self._calls += 1
                self._chars += len(clean)
                self._last_latency = round(time.perf_counter() - started, 2)
            logger.info(
                "[ElevenLabsTTS] %s in %.2fs (%d chars, %s)",
                len(audio) / self.sample_rate,
                time.perf_counter() - started,
                len(clean),
                self.model_id,
            )
        except Exception as e:
            with self._lock:
                self._failures += 1
            logger.error(
                "[ElevenLabsTTS] %s — falling back to Kokoro for this and later clips", e
            )
            self._kokoro().generate(text, output_path, emotion=emotion)

    def _fetch(self, text, emotion):
        resp = self._http.post(
            f"{self.base_url}/v1/text-to-speech/{self.voice_id}",
            headers={"xi-api-key": self.api_key, "Accept": "audio/pcm"},
            params={"output_format": self.output_format},
            json={
                "text": text,
                "model_id": self.model_id,
                "voice_settings": {"stability": _STABILITY.get(emotion, 0.5)},
            },
        )
        if resp.status_code != 200:
            # The body names the culprit (bad voice id, unknown model id, quota).
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:300]}")
        # pcm_* is little-endian signed 16-bit mono.
        return np.frombuffer(resp.content, dtype="<i2").astype(np.float32) / 32768.0

    def _clean_text(self, text):
        return sanitize(text)

    def _kokoro(self):
        with self._lock:
            if self._fallback is None:
                from voice.kokoro_tts import KokoroTTS
                self._fallback = KokoroTTS()
            return self._fallback

    # ==================================================
    # 📊 STATUS
    # ==================================================

    def is_available(self):
        return bool(self.api_key)

    def stats(self):
        with self._lock:
            return {
                "engine": "elevenlabs",
                "voice_id": self.voice_id,
                "model": self.model_id,
                "output_format": self.output_format,
                "sample_rate": self.sample_rate,
                "last_emotion": self.last_emotion,
                "calls": self._calls,
                "chars": self._chars,
                "failures": self._failures,
                "last_latency_seconds": self._last_latency,
                "fallback": self._fallback is not None,
                "available": bool(self.api_key),
            }

    def close(self):
        try:
            self._http.close()
        except Exception as e:
            logger.debug("[ElevenLabsTTS] close: %s", e)
