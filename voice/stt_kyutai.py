"""Kyutai STT backend — streaming speech-to-text behind the FasterWhisperSTT interface.

Wraps ``transformers``' native Kyutai support (``KyutaiSpeechToTextProcessor`` /
``KyutaiSpeechToTextForConditionalGeneration``, checkpoint ``kyutai/stt-1b-en_fr-trfs``).
The pipeline feeds 16 kHz float32 mono utterances; Mimi (the Kyutai audio codec)
runs at 24 kHz, so this backend resamples internally.

Contract (plan §4, voice must never die from an experimental backend):
- same public surface as ``FasterWhisperSTT``: lazy ``_ensure_model()``,
  ``transcribe(audio) -> str``, ``stats()``, ``.sample_rate``, ``.model``;
- raises ``TranscriptionUnavailable`` when no backend is usable;
- any Kyutai load or runtime failure falls back permanently to
  ``FasterWhisperSTT``.
"""
import importlib.util
import logging
import threading
import time

import numpy as np
from numpy.typing import NDArray

from app.config_loader import Settings
from voice.stt import FasterWhisperSTT

logger = logging.getLogger(__name__)


class KyutaiSTT:

    def __init__(self, model_path: str | None = None, sample_rate: int | None = None):
        self.sample_rate = sample_rate or Settings.VOICE_SAMPLE_RATE
        self._model_path = model_path or Settings.KYUTAI_STT_DIR

        self._lock = threading.RLock()
        self.model = None        # transformers model once loaded (public: voice_manager checks it)
        self._processor = None
        self._device = "cpu"     # updated by _ensure_model when CUDA is present
        self._load_ok = False
        self._dynamo_disabled = False
        self._fallback: FasterWhisperSTT | None = None
        self._load_seconds = 0.0
        self._calls = 0
        self._speech_seconds = 0.0
        self._stt_seconds = 0.0

    # ==================================================
    # 🔒 MODEL LIFECYCLE
    # ==================================================

    def _ensure_model(self) -> bool:
        """True when the Kyutai checkpoint is loaded; False = permanent whisper
        fallback mode (fallback instance is built here or below)."""
        with self._lock:
            if self._load_ok:
                return True
            if self._fallback is not None:
                return False
            t0 = time.perf_counter()
            try:
                import torch
                # Must run before transformers imports: it decides at import
                # time whether its compiled generation path is usable.
                self._disable_dynamo(torch)
                from transformers import (
                    KyutaiSpeechToTextForConditionalGeneration,
                    KyutaiSpeechToTextProcessor,
                )
                # CUDA when available: the fp32 CPU checkpoint is RTF~4.8 on
                # this machine (Phase 1 NO-GO), and fp32 1B (~4GB) does not fit
                # the T1000's 4GB VRAM — bf16 (~1.3GB) does.
                use_cuda = torch.cuda.is_available()
                self._device = "cuda" if use_cuda else "cpu"
                dtype = torch.bfloat16 if use_cuda else torch.float32
                logger.info("[KyutaiSTT] Loading checkpoint from %s (device=%s, dtype=%s) ...",
                            self._model_path, self._device, str(dtype))
                self._processor = KyutaiSpeechToTextProcessor.from_pretrained(self._model_path)
                self.model = KyutaiSpeechToTextForConditionalGeneration.from_pretrained(
                    self._model_path, torch_dtype=dtype)
                self.model.eval().to(self._device)
                self._load_seconds = time.perf_counter() - t0
                self._load_ok = True
                logger.info("[KyutaiSTT] Ready in %.1fs (device=%s)", self._load_seconds, self._device)
                return True
            except Exception as e:
                logger.error("[KyutaiSTT] Load failed: %s — falling back to faster-whisper", e)
                self._fallback = FasterWhisperSTT()
                return False

    def _disable_dynamo(self, torch) -> None:
        """Turn torch.compile off entirely when triton is unavailable (Windows).

        With ``suppress_errors`` the compiled regions still *attempt* a compile
        on every new input shape before falling back to eager — measured on this
        machine: 9.6s on a cold shape vs 1.7s with dynamo disabled, and the old
        whole-second padding (needed to keep shapes stable) added up to 1s of
        decode per clip. Disabling removes both costs.
        """
        if self._dynamo_disabled:
            return
        try:
            if importlib.util.find_spec("triton") is None:
                torch._dynamo.config.disable = True
            self._dynamo_disabled = True
            logger.info("[KyutaiSTT] torch.compile disabled (no triton) — "
                        "measured 0.6s clip 2.17s->1.73s, cold shape 9.6s->2.6s")
        except Exception as e:
            logger.debug("[KyutaiSTT] dynamo disable unavailable: %s", e)

    def _enter_permanent_fallback(self, reason: str) -> None:
        with self._lock:
            if self._fallback is None:
                logger.error("[KyutaiSTT] %s — falling back to faster-whisper permanently", reason)
                self._fallback = FasterWhisperSTT()
                self.model = None
                self._load_ok = False

    # ==================================================
    # 🎙️ TRANSCRIBE
    # ==================================================

    def transcribe(self, audio: NDArray[np.float32], language: str = "en",
                   initial_prompt: str | None = None) -> str:
        if not self._ensure_model():
            return self._fallback.transcribe(audio, language=language, initial_prompt=initial_prompt)
        if initial_prompt:
            logger.debug("[KyutaiSTT] initial_prompt unsupported by kyutai — ignored")
        try:
            return self._kyutai_transcribe(audio)
        except Exception as e:
            self._enter_permanent_fallback(f"Runtime failure: {e}")
            return self._fallback.transcribe(audio, language=language, initial_prompt=initial_prompt)

    def _kyutai_transcribe(self, audio: NDArray[np.float32]) -> str:
        x = np.asarray(audio, dtype=np.float32)
        speech_r = self.sample_rate
        if speech_r != 24000:
            from scipy.signal import resample_poly
            x = resample_poly(x, 24000, speech_r)  # 16k -> 24k = exact 3/2
        # No whole-second padding: with dynamo disabled there is no per-shape
        # retracing to protect against, and the padding itself was up to 1s of
        # extra decode per clip (measured 2.98s -> 2.47s on a 1.5s clip).

        t0 = time.perf_counter()
        with self._lock:
            model, processor = self.model, self._processor
            device = self._device
        import torch
        with torch.inference_mode():
            # positionally, ProcessorMixin.__call__ binds its first arg to
            # `images` — audio MUST be keyword-passed (empty BatchFeature otherwise)
            inputs = processor(audio=x)
            inputs = inputs.to(device)
            tokens = model.generate(**inputs)
            texts = processor.batch_decode(tokens, skip_special_tokens=True)
        dt = time.perf_counter() - t0
        self._calls += 1
        self._speech_seconds += len(x) / 24000.0
        self._stt_seconds += dt
        return texts[0].strip() if texts else ""

    # ==================================================
    # 📊 STATS
    # ==================================================

    def stats(self) -> dict:
        if self._fallback is not None:
            out = self._fallback.stats()
            out["backend"] = "kyutai(whisper fallback)"
            out["load_failed"] = True
            return out
        speech = self._speech_seconds
        rtf = (self._stt_seconds / speech) if speech > 0 else 0.0
        return {
            "backend": "kyutai",
            "sample_rate": self.sample_rate,
            "device": self._device,
            "model_path": self._model_path,
            "model_loaded": self._load_ok,
            "load_seconds": round(self._load_seconds, 1),
            "calls": self._calls,
            "speech_seconds": round(speech, 2),
            "stt_seconds": round(self._stt_seconds, 2),
            "avg_rtf": round(rtf, 3),
        }
