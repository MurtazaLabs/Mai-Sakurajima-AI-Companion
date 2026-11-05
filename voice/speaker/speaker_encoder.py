import logging
import threading
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
import torch

logger = logging.getLogger("Mai.SpeakerEncoder")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models" / "speaker"

_REQUIRED_MODEL_FILES = (
    "hyperparams.yaml",
    "embedding_model.ckpt",
    "classifier.ckpt",
    "mean_var_norm_emb.ckpt",
)


def _apply_torch_amp_compat() -> None:
    """Shim ``torch.amp.custom_fwd/custom_bwd`` for torch builds that lack them.

    torch 2.3 (this env) exposes only ``torch.cuda.amp.custom_fwd``; newer
    SpeechBrain releases call ``torch.amp.custom_fwd(fwd, device_type=...,
    cast_inputs=...)`` unconditionally, which raises AttributeError and disables
    speaker embedding. When the ``torch.amp`` names are missing, install
    wrappers that accept (and ignore) ``device_type`` — irrelevant here because
    this env runs CPU-only autocast.
    """
    try:
        if not hasattr(torch.amp, "custom_fwd") and hasattr(torch.cuda.amp, "custom_fwd"):
            _real_fwd = torch.cuda.amp.custom_fwd

            def _compat_fwd(fwd=None, *, device_type=None, cast_inputs=None):
                return _real_fwd(fwd, cast_inputs=cast_inputs)

            torch.amp.custom_fwd = _compat_fwd
        if not hasattr(torch.amp, "custom_bwd") and hasattr(torch.cuda.amp, "custom_bwd"):
            _real_bwd = torch.cuda.amp.custom_bwd

            def _compat_bwd(fwd=None, *, device_type=None):
                return _real_bwd(fwd)

            torch.amp.custom_bwd = _compat_bwd
    except Exception:
        logger.debug("torch.amp compat shim unavailable; leaving as-is")


def _defuse_speechbrain_deprecated_redirects() -> None:
    """Neutralize speechbrain 1.x's deprecated-alias placeholders.

    ``import speechbrain`` registers lazy ``DeprecatedModuleRedirect`` entries
    in ``sys.modules`` for the old module paths it renamed in 1.x
    (``speechbrain.pretrained``, ``speechbrain.k2_integration``, ...). Any
    later ``inspect`` walk over ``sys.modules`` — torch performs one per
    ``torch.library.impl_abstract`` call, which transformers >= 4.53 triggers
    via torchvision during import — touches those ``__getattr__`` methods,
    which attempt to import the (missing) external packages behind them, and
    the unrelated import (kokoro/transformers) dies. This codebase uses only
    ``speechbrain.inference`` (grep: zero deprecated-path imports), so every
    placeholder is replaced with an inert module. Call directly after
    speechbrain imports.
    """
    try:
        import sys
        import types

        for key, placeholder in list(sys.modules.items()):
            if not key.startswith("speechbrain."):
                continue
            if type(placeholder).__name__ == "DeprecatedModuleRedirect":
                inert = types.ModuleType(key)
                inert.__doc__ = "Deprecated speechbrain alias made inert; use the speechbrain.inference equivalents."
                sys.modules[key] = inert
    except Exception as e:
        logger.debug("speechbrain deprecated-alias defusal unavailable: %s", e)


_apply_torch_amp_compat()


class SpeakerEncoder:

    def __init__(self):
        self._lock = threading.RLock()
        self._model: Any | None = None
        self._device: str | None = None
        self.ready = False
        self._load_model()

    def _validate_model_files(self) -> bool:
        missing = [fname for fname in _REQUIRED_MODEL_FILES if not (MODEL_DIR / fname).exists()]
        if missing:
            logger.error("Incomplete SpeechBrain model at %s.", MODEL_DIR)
            for fname in missing:
                logger.error("  Missing: %s", fname)
            return False
        return True

    def _load_model(self):
        with self._lock:
            try:
                self._device = "cuda" if torch.cuda.is_available() else "cpu"
                logger.info("Using device: %s", self._device)

                if not MODEL_DIR.exists():
                    logger.error(
                        "SpeechBrain model directory not found at %s. "
                        "Download the model and place it there, or run setup.",
                        MODEL_DIR,
                    )
                    self.ready = False
                    return

                if not self._validate_model_files():
                    self.ready = False
                    return

                logger.info("Loading local SpeechBrain speaker model from %s ...", MODEL_DIR)

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")

                    from speechbrain.inference.speaker import SpeakerRecognition

                _defuse_speechbrain_deprecated_redirects()

                self._model = SpeakerRecognition.from_hparams(
                    source=str(MODEL_DIR),
                    savedir=str(MODEL_DIR),
                    run_opts={"device": self._device},
                )
                self.ready = True
                logger.info("SpeakerEncoder initialized successfully on %s.", self._device)

            except Exception as exc:
                logger.error(
                    "SpeakerEncoder unavailable. Reason: %s",
                    exc,
                )
                self.ready = False

    def is_ready(self) -> bool:
        with self._lock:
            return self.ready

    def _signal_to_tensor(self, signal: np.ndarray) -> torch.Tensor:
        if signal.ndim == 1:
            signal = signal.reshape(1, -1)
        else:
            signal = signal.mean(axis=1, keepdims=True).T
        return torch.tensor(signal, dtype=torch.float32).to(self._device)

    def embed(self, audio_path: str) -> list[float] | None:
        with self._lock:
            if not self.ready or self._model is None:
                logger.warning("embed() skipped — model not loaded")
                return None

        try:
            signal, _sr = sf.read(audio_path)
            return self._embed_signal(signal)

        except Exception as exc:
            logger.warning("embed() failed for %s: %s", audio_path, exc)
            return None

    def embed_raw(self, audio: np.ndarray, sample_rate: int = 16000) -> list[float] | None:
        with self._lock:
            if not self.ready or self._model is None:
                logger.warning("embed_raw() skipped — model not loaded")
                return None

        if sample_rate != 16000:
            logger.warning(
                "Expected 16000 Hz audio but received %d Hz.",
                sample_rate,
            )

        try:
            return self._embed_signal(audio)

        except Exception as exc:
            logger.warning("embed_raw() failed: %s", exc)
            return None

    def _embed_signal(self, signal: np.ndarray) -> list[float] | None:
        with self._lock:
            model = self._model
            if model is None:
                return None
        try:
            signal = signal.astype(np.float32)

            peak = np.max(np.abs(signal))
            if peak > 0:
                signal /= peak

            signal_tensor = self._signal_to_tensor(signal)
            with torch.no_grad():
                embedding = self._model.encode_batch(signal_tensor)
            return embedding.squeeze().cpu().numpy().tolist()

        except Exception as exc:
            logger.warning("_embed_signal() failed: %s", exc)
            return None
