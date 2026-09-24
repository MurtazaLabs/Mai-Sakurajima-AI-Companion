# Mai_ai/voice/kokoro_tts.py
import logging
import re
import threading

import numpy as np
import soundfile as sf

from app.config_loader import (
    KOKORO_VOICE,
    KOKORO_LANG_CODE,
    VOICE_SAMPLE_RATE,
)

logger = logging.getLogger("Mai.TTS")

# 🧠 lazy import — kokoro loads slow
KPipeline: type = None  # type: ignore[assignment]


def _load_kokoro():
    global KPipeline
    if KPipeline is None:
        from kokoro import KPipeline as _KPipeline
        KPipeline = _KPipeline


class KokoroTTS:

    # 🧠 shared singleton pipeline
    _shared_pipeline = None

    _model_lock = threading.Lock()

    def __init__(
        self,
        language="en",
        base_speed=0.92,
        voice=None,
    ):
        self.language  = language
        self.base_speed = base_speed

        # voice from settings if not passed
        self.voice = voice or KOKORO_VOICE

        self.last_emotion = "neutral"

        self.sample_rate = VOICE_SAMPLE_RATE

        # 🧠 load pipeline once globally
        with self._model_lock:

            if KokoroTTS._shared_pipeline is None:

                logger.info("Loading Kokoro...")

                _load_kokoro()

                KokoroTTS._shared_pipeline = KPipeline(
                    lang_code=KOKORO_LANG_CODE,
                    repo_id='hexgrad/Kokoro-82M',
                )

                logger.info("Kokoro ready")

        with KokoroTTS._model_lock:
            self.pipeline = KokoroTTS._shared_pipeline

    # 🗣️ MAIN GENERATION
    def generate(
        self,
        text,
        output_path,
        emotion="neutral"
    ):

        if not text:
            return

        self.last_emotion = emotion

        enhanced = self._enhance_text(text, emotion)

        speed = self._emotion_speed(emotion)

        try:

            audio_chunks = []

            for _, _, audio in self.pipeline(
                enhanced,
                voice=self.voice,
                speed=speed,
            ):
                if audio is not None:
                    audio_chunks.append(audio)

            if audio_chunks:

                full_audio = np.concatenate(
                    audio_chunks
                )

                sf.write(
                    output_path,
                    full_audio,
                    self.sample_rate
                )

        except Exception as e:
            logger.error("[TTS ERROR] %s", e)

    # 🎭 ENHANCE SPEECH RHYTHM
    def _enhance_text(self, text, emotion="neutral"):

        text = text.strip()

        text = re.sub(r"\s+", " ", text)

        text = text.replace("...", "… ")

        text = re.sub(r",\s*", ", ", text)

        text = re.sub(r"\.\s*", ". ", text)

        if emotion == "soft":
            text = text.replace(".", "... ")

        elif emotion == "annoyed":
            text = text.replace("...", ".")

        elif emotion == "teasing":
            text = text.replace("?", "? …")

        if len(text) > 40:
            text = text.replace(" and ", "… and ")

        return text.strip()

    # ⚡ EMOTION → SPEED
    def _emotion_speed(self, emotion):

        speeds = {
            "soft":    0.88,
            "neutral": 0.92,
            "teasing": 0.90,
            "annoyed": 0.98,
            "sad":     0.85,
            "calm":    0.90,
        }

        return speeds.get(emotion, self.base_speed)

    # 📊 DEBUG INFO
    def stats(self):
        return {
            "engine":       "kokoro",
            "voice":        self.voice,
            "language":     self.language,
            "last_emotion": self.last_emotion,
            "base_speed":   self.base_speed,
        }