# Mai_ai/memory/vector_store.py
import os
import time
import uuid
import json
import hashlib
import threading
import logging
from collections import OrderedDict
from datetime import datetime
from typing import Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger(__name__)

from memory.schema_migrator import migrate_collection
from memory.embedding_service import EmbeddingService
from memory.search_engine import SearchEngine
from memory.vector_lifecycle import VectorLifecycle
from core.utils import TTLCache

from app.config_loader import (
    MEMORY_SIMILARITY,
    MAX_MEMORY_RESULTS,
    MEMORY_MAX_VECTOR_ROWS,
    MEMORY_PRUNE_KEEP_MIN_IMPORTANCE,
)


class VectorStore:

    SCHEMA_VERSION = 1

    @staticmethod
    def _build_metadata_where(filters: dict) -> dict:
        """Build a Chroma ``where`` clause from metadata filters.

        Chroma requires exactly one top-level operator per ``where`` dict, so
        multi-filter deletes must be wrapped in ``$and``.
        """
        if len(filters) <= 1:
            return {k: {"$eq": v} for k, v in filters.items()}
        return {"$and": [{k: {"$eq": v}} for k, v in filters.items()]}

    def __init__(self, embed_service: Optional[EmbeddingService] = None):
        self.is_available = False
        self.collection: Optional[Any] = None
        self.client: Optional[Any] = None
        self._embed_service = embed_service or EmbeddingService()
        self._lock = threading.RLock()

        from config.paths import VECTOR_DB_DIR
        VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)

        try:
            self.client = chromadb.PersistentClient(
                path=str(VECTOR_DB_DIR),
                settings=ChromaSettings(anonymized_telemetry=False)
            )
        except TypeError:
            self.client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

        try:
            self.collection = self.client.get_or_create_collection(
                name="mai_memory",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error("[VectorStore] Collection init failed: %s", e)
            return

        if not self._embed_service.is_available:
            logger.error("[VectorStore] EmbeddingService not available")
            return

        self.is_available = True
        self._search_engine = SearchEngine(
            embed_service=self._embed_service,
            collection=self.collection,
            search_cache_ttl=30.0,
        )
        self._lifecycle = VectorLifecycle(collection=self.collection)
        # Persistent client — schema migration handled by migrate_collection
        self._migrate()

        # Track indexed files for incremental sync
        self._indexed_files = {}  # file_path -> (mtime, hash)

    # ==================================================
    # 🔧 SAFE METADATA
    # ==================================================

    def _safe_meta(self, metadata):

        safe = {}

        if not metadata:
            return safe

        for key, value in metadata.items():

            try:

                if isinstance(
                    value,
                    (str, int, float, bool)
                ):

                    safe[key] = value

                elif isinstance(value, dict):

                    safe[key] = json.dumps(value)

                elif isinstance(value, list):

                    safe[key] = json.dumps(value)

                elif value is None:

                    safe[key] = ""

                else:

                    safe[key] = str(value)

            except Exception as e:
                logger.warning("[VectorStore] Failed to sanitize metadata key %r: %s", key, e)
                safe[key] = str(value)

        return safe

    # ==================================================
    # 🗃️ SCHEMA MIGRATION
    # ==================================================

    def _migrate(self):
        if not self._check_ready(need_model=False, need_collection=True):
            return
        migrate_collection(self.collection, self.SCHEMA_VERSION)

    # ==================================================
    # 🧠 ADD MEMORY
    # ==================================================

    def _check_ready(self, need_model=True, need_collection=True, need_client=False):
        if not self.is_available:
            return False
        if need_model and (self._embed_service is None or not self._embed_service.is_available):
            logger.warning("[VectorStore] embedding service not available")
            return False
        if need_collection and self.collection is None:
            logger.warning("[VectorStore] collection is None")
            return False
        if need_client and self.client is None:
            logger.warning("[VectorStore] client is None")
            return False
        return True

    def _embed(self, text):
        return self._embed_service.embed(text)

    def add(self, text, metadata=None):
        with self._lock:
            if not text:
                return ""

            if not self._check_ready(need_model=True, need_collection=True):
                return ""

            assert self._embed_service is not None and self._embed_service.is_available
            assert self.collection is not None

            try:
                text = str(text).strip()
                if not text:
                    return ""

                embedding = self._embed(text)

                memory_id = hashlib.md5(text.encode()).hexdigest()

                existing = self.collection.get(ids=[memory_id])
                if existing["ids"]:
                    return memory_id

                # Semantic deduplication: check for similar existing memories
                superseded_ids = self._find_superseded_memories(embedding, text)
                if superseded_ids:
                    self._mark_superseded(superseded_ids, memory_id)

                meta = {
                    "timestamp": datetime.now().isoformat(),
                    "importance": 0.5,
                    "emotion": json.dumps({
                        "type": "neutral",
                        "intensity": 0.5
                    }),
                    "emotion_type": "neutral",
                    "tags": json.dumps([]),
                    "reinforcement": 1,
                    "access_count": 0,
                    "schema_version": self.SCHEMA_VERSION,
                    "supersedes": json.dumps(superseded_ids),  # IDs this memory supersedes
                    "superseded_by": json.dumps([]),  # IDs that supersede this memory
                }

                if metadata:
                    safe_metadata = self._safe_meta(metadata)
                    meta.update(safe_metadata)

                if self.collection is not None:
                    self.collection.add(
                        documents=[text],
                        embeddings=[embedding],
                        metadatas=[meta],
                        ids=[memory_id]
                    )

                self._add_count = getattr(self, "_add_count", 0) + 1
                if self._add_count % 5 == 0:
                    self.enforce_cap()

                return memory_id

            except Exception as e:
                logger.error("[VECTOR ADD ERROR] %s", e)
                return ""

    # ==================================================
    # 🧠 SEMANTIC SEARCH
    # ==================================================

    def search(
        self,
        query,
        k=None,
        min_similarity=None,
        top_k=None,
        metadata_filter=None
    ):
        with self._lock:
            if not query:
                return []
            if not self._check_ready(need_model=True, need_collection=True):
                return []
            try:
                return self._search_engine.search(
                    query, k=k, min_similarity=min_similarity,
                    top_k=top_k, metadata_filter=metadata_filter,
                )
            except Exception as e:
                logger.error("[VECTOR SEARCH ERROR] %s", e)
                return []

    # ==================================================
    # 🧠 SEMANTIC DEDUPLICATION & SUPERSESSION
    # ==================================================

    def _find_superseded_memories(self, embedding, text, similarity_threshold=0.95):
        """Find memories that are semantically similar to the new text and should be superseded."""
        if not self._check_ready(need_model=True, need_collection=True):
            return []
        
        try:
            # Search for similar memories
            results = self.collection.query(
                query_embeddings=[embedding],
                n_results=10,
                include=["metadatas", "documents", "distances"]
            )
            
            superseded_ids = []
            if results and results["ids"]:
                for i, doc_id in enumerate(results["ids"][0]):
                    distance = results["distances"][0][i]
                    similarity = 1.0 - distance  # cosine distance to similarity
                    
                    if similarity >= similarity_threshold:
                        # Check if it's not already superseded
                        meta = results["metadatas"][0][i]
                        superseded_by = json.loads(meta.get("superseded_by", "[]"))
                        if not superseded_by:
                            superseded_ids.append(doc_id)
            
            return superseded_ids
        except Exception as e:
            logger.warning("[VectorStore] Superseded search failed: %s", e)
            return []

    def _mark_superseded(self, superseded_ids, new_memory_id):
        """Mark memories as superseded by a new memory."""
        if not superseded_ids:
            return
        
        try:
            with self._lock:
                if not self._check_ready(need_model=False, need_collection=True):
                    return
                
                for old_id in superseded_ids:
                    # Get current metadata
                    existing = self.collection.get(ids=[old_id])
                    if not existing["ids"]:
                        continue
                    
                    meta = existing["metadatas"][0].copy()
                    superseded_by = json.loads(meta.get("superseded_by", "[]"))
                    
                    if new_memory_id not in superseded_by:
                        superseded_by.append(new_memory_id)
                        meta["superseded_by"] = json.dumps(superseded_by)
                        
                        # Update the old memory's metadata
                        self.collection.update(
                            ids=[old_id],
                            metadatas=[meta]
                        )
            
            logger.info("[VectorStore] Marked %d memories as superseded by %s", len(superseded_ids), new_memory_id)
        except Exception as e:
            logger.warning("[VectorStore] Failed to mark superseded: %s", e)

    # ==================================================
    # 🧠 MMR DIVERSIFICATION
    # ==================================================

    def _mmr_diversify(self, results, lambda_param=0.7):
        return self._search_engine._mmr_diversify(results, lambda_param=lambda_param)

    def _parse_result(self, doc, dist, meta, memory_id, min_similarity):
        return self._search_engine._parse_result(doc, dist, meta, memory_id, min_similarity)

    # ==================================================
    # 🧠 HARD CAP ENFORCEMENT
    # ==================================================

    def enforce_cap(self, max_rows: int = None) -> int:
        with self._lock:
            if not self._check_ready(need_model=False, need_collection=True):
                return 0
            return self._lifecycle.enforce_cap(max_rows=max_rows)

    # ==================================================
    # 🧠 MEMORY COUNT
    # ==================================================

    def count(self):
        with self._lock:
            if not self._check_ready(need_model=False, need_collection=True):
                return 0
            assert self.collection is not None
            try:
                return self.collection.count()
            except Exception as e:
                logger.error("[VECTOR COUNT ERROR] %s", e)
                return 0

    # ==================================================
    # 🧠 PRUNE OLD / LOW-IMPORTANCE MEMORIES
    # ==================================================

    def prune(self, max_age_days: float = 90.0, min_importance: float = 0.2) -> int:
        with self._lock:
            if not self._check_ready(need_model=False, need_collection=True):
                return 0
            return self._lifecycle.prune(max_age_days, min_importance)

    # ==================================================
    # 🧠 DELETE MEMORY
    # ==================================================

    def delete(self, memory_id):
        with self._lock:
            if not memory_id:
                return False

            if not self._check_ready(need_model=False, need_collection=True):
                return False

            assert self.collection is not None

            try:
                self.collection.delete(ids=[memory_id])
                return True
            except Exception as e:
                logger.error("[VECTOR DELETE ERROR] %s", e)
                return False

    def delete_by_metadata(self, **filters):
        with self._lock:
            if not filters:
                return False

            if not self._check_ready(need_model=False, need_collection=True):
                return False

            assert self.collection is not None

            where = self._build_metadata_where(dict(filters))

            try:
                self.collection.delete(where=where)
                return True
            except Exception as e:
                logger.error("[VECTOR DELETE-BY-METADATA ERROR] %s", e)
                return False

    # ==================================================
    # 🧠 CLEAR DATABASE
    # ==================================================

    def clear(self):
        with self._lock:
            if not self._check_ready(need_model=False, need_collection=True, need_client=True):
                return False

            assert self.client is not None

            try:
                self.client.delete_collection("mai_memory")
                self.collection = self.client.get_or_create_collection(name="mai_memory")
                return True
            except Exception as e:
                logger.error("[VECTOR CLEAR ERROR] %s", e)
                return False

    # ==================================================
    # 📊 DEBUG INFO
    # ==================================================

    def stats(self):
        with self._lock:
            return {
                "memory_count": self.count(),
                "model": self._embed_service.model_name if self._embed_service else "none",
                "store_type": "ephemeral (rebuilt from vault on boot)",
                "embed_cache_size": len(self._embed_service._cache) if self._embed_service and hasattr(self._embed_service, "_cache") else 0,
            }

    @property
    def search_engine(self):
        """Expose the SearchEngine for direct access (backward compat)."""
        return self._search_engine

    @property
    def lifecycle(self):
        """Expose the VectorLifecycle for direct access (backward compat)."""
        return self._lifecycle