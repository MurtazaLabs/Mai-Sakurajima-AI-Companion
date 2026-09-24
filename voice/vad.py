import os
import hashlib
import logging
import threading
import numpy as np
import torch

logger = logging.getLogger(__name__)


class VAD:
    _shared_model = None
    _shared_lock = threading.Lock()
    _shared_load_failed = False
    _DOWNLOAD_TIMEOUT = 30

    def __init__(self, threshold=0.5, sample_rate=16000, frame_size=512):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self._model = None
        self._load_failed = False
        self._lock = threading.RLock()

    def _load_model(self):
        with VAD._shared_lock:
            if VAD._shared_model is not None:
                self._model = VAD._shared_model
                return
        if self._load_failed or VAD._shared_load_failed:
            return
        if self._model is not None:
            return
        with VAD._shared_lock:
            if VAD._shared_model is not None:
                self._model = VAD._shared_model
                return
            if self._model is not None:
                return
            try:
                model_path = os.path.join(
                    os.path.expanduser("~"), ".cache", "silero_vad", "silero_vad.jit"
                )
                if not os.path.exists(model_path):
                    os.makedirs(os.path.dirname(model_path), exist_ok=True)
                    import urllib.request
                    url = "https://github.com/snakers4/silero-vad/raw/master/src/silero_vad/data/silero_vad.jit"
                    tmp_path = model_path + ".part"
                    with urllib.request.urlopen(url, timeout=VAD._DOWNLOAD_TIMEOUT) as resp:
                        with open(tmp_path, "wb") as out:
                            while True:
                                block = resp.read(65536)
                                if not block:
                                    break
                                out.write(block)
                    os.replace(tmp_path, model_path)
                    expected_sha256 = "e1122837f4154c511485fe0b9c64455f7b929c96fbb8d79fbdb336383ebd3720"
                    with open(model_path, "rb") as f:
                        actual = hashlib.sha256(f.read()).hexdigest()
                    if actual != expected_sha256:
                        os.remove(model_path)
                        raise RuntimeError(f"VAD model checksum mismatch: expected {expected_sha256}, got {actual}")
                self._model = torch.jit.load(model_path, map_location="cpu")
                self._model.eval()
                VAD._shared_model = self._model
                logger.info("[VAD] Model loaded")
            except Exception as e:
                logger.error("[VAD] Load failed (latched, no more retries): %s", e)
                self._model = None
                self._load_failed = True
                VAD._shared_load_failed = True

    def is_speech(self, chunk):
        if len(chunk) != self.frame_size:
            chunk = self._resample_frame(chunk)
        with self._lock:
            self._load_model()
            if self._model is None:
                return False
            try:
                with torch.no_grad():
                    tensor = torch.from_numpy(chunk)
                    sr = torch.tensor(self.sample_rate)
                    prob = self._model(tensor, sr).item()
                return prob > self.threshold
            except Exception as e:
                logger.warning("[VAD] Inference error: %s", e)
                return False

    def speech_prob(self, chunk):
        if len(chunk) != self.frame_size:
            chunk = self._resample_frame(chunk)
        with self._lock:
            self._load_model()
            if self._model is None:
                return 0.0
            try:
                with torch.no_grad():
                    tensor = torch.from_numpy(chunk)
                    sr = torch.tensor(self.sample_rate)
                    return self._model(tensor, sr).item()
            except Exception as e:
                logger.warning("[VAD] Inference error: %s", e)
                return 0.0

    def _resample_frame(self, chunk):
        if len(chunk) > self.frame_size:
            return chunk[:self.frame_size]
        result = np.zeros(self.frame_size, dtype=np.float32)
        result[:len(chunk)] = chunk
        return result
