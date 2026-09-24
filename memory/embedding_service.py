import hashlib
import logging
import os
import threading
from collections import OrderedDict
from typing import Optional

os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "5")

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

from app.config_loader import EMBEDDING_MODEL, ENABLE_CACHE


class EmbeddingService:

    def __init__(self, model_name: Optional[str] = None, cache_enabled: bool = True, cache_max: int = 20000):
        self.model_name = model_name or EMBEDDING_MODEL
        self.model: Optional[SentenceTransformer] = None
        self.is_available = False

        try:
            self.model = SentenceTransformer(self.model_name)
        except Exception as e:
            logger.error("[EmbeddingService] Model load failed: %s", e)
            return

        self.is_available = True
        self._cache_max = cache_max
        self._cache_enabled = cache_enabled and bool(ENABLE_CACHE)
        self._cache: OrderedDict[str, list] = OrderedDict()
        try:
            cfg = str(self.model.get_config_dict())
        except Exception as e:
            logger.debug("Embedding model config unavailable: %s", e)
            cfg = self.model_name
        self._model_fingerprint = hashlib.sha256(cfg.encode()).hexdigest()[:8]
        self._cache_tag = f"{self.model_name}:{self._model_fingerprint}"
        self._cache_lock = threading.RLock()

    def embed(self, text: str) -> Optional[list]:
        if not text or not self.is_available or self.model is None:
            return None

        key = f"{self._cache_tag}:{hash(text)}"

        if self._cache_enabled:
            with self._cache_lock:
                cached = self._cache.get(key)
                if cached is not None:
                    self._cache.move_to_end(key)
                    return cached

        try:
            result = self.model.encode(text, convert_to_numpy=True)
            emb = result.tolist()
        except Exception as e:
            logger.error("[EmbeddingService] Encode error: %s", e)
            return None

        if self._cache_enabled:
            with self._cache_lock:
                if key in self._cache:
                    self._cache.move_to_end(key)
                else:
                    while len(self._cache) >= self._cache_max:
                        self._cache.popitem(last=False)
                self._cache[key] = emb

        return emb

    def warmup(self, texts: list[str]) -> int:
        if not self.is_available or not texts:
            return 0
        count = 0
        for t in texts:
            if self.embed(t) is not None:
                count += 1
        logger.info("[EmbeddingService] Warmed up %s embeddings", count)
        return count

    def stats(self) -> dict:
        with self._cache_lock:
            cache_size = len(self._cache)
        return {
            "model": self.model_name,
            "available": self.is_available,
            "cache_size": cache_size,
            "cache_enabled": self._cache_enabled,
        }
