import json
import time
import logging
from datetime import datetime

from core.utils import compute_text_overlap
from app.config_loader import MAX_MEMORY_RESULTS, MEMORY_SIMILARITY

logger = logging.getLogger(__name__)


class SearchEngine:
    """Search, diversification, and result parsing extracted from VectorStore."""

    def __init__(self, embed_service, collection, search_cache_ttl=30.0):
        self._embed_service = embed_service
        self.collection = collection
        self._search_cache: dict[str, tuple[float, list]] = {}
        self._search_cache_ttl = search_cache_ttl

    def search(self, query, k=None, min_similarity=None, top_k=None, metadata_filter=None):
        if not query or not self.collection:
            return []

        query = str(query).strip()
        if not query:
            return []

        # Query cache check
        filter_str = json.dumps(metadata_filter, sort_keys=True) if metadata_filter else ""
        cache_key = f"{query}:{k}:{min_similarity}:{filter_str}"
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            cached_at, cached_results = cached
            if time.time() - cached_at < self._search_cache_ttl:
                return cached_results

        if top_k is not None:
            k = top_k
        k = k or MAX_MEMORY_RESULTS
        min_similarity = min_similarity if min_similarity is not None else MEMORY_SIMILARITY

        try:
            collection_count = self.collection.count()
            if collection_count <= 0:
                return []

            embedding = self._embed_service.embed(query)

            query_kwargs = dict(
                query_embeddings=[embedding],
                n_results=min(k, collection_count),
            )
            if metadata_filter:
                query_kwargs["where"] = metadata_filter
            results = self.collection.query(**query_kwargs)

            docs = results["documents"][0] if results["documents"] else []
            distances = results["distances"][0] if results["distances"] else []
            metas_raw = results["metadatas"][0] if results["metadatas"] else []
            ids = results["ids"][0] if results["ids"] else []

            if not docs:
                return []

            filtered = []
            for doc, dist, meta, memory_id in zip(docs, distances, metas_raw, ids):
                result = self._parse_result(doc, dist, meta, memory_id, min_similarity)
                if result is not None:
                    filtered.append(result)

            if not filtered:
                return []

            for hit in filtered:
                ac = hit["access_count"] + 1
                hit["_reinforcement"] = min(ac / 50.0, 1.0)

            filtered.sort(
                key=lambda x: (
                    x["similarity"] * 0.45
                    + x["importance"] * 0.15
                    + x["recency"] * 0.30
                    + x["_reinforcement"] * 0.10
                ),
                reverse=True
            )

            # Update access counts
            self._update_access_counts(filtered)

            result = self._mmr_diversify(filtered)
            self._search_cache[cache_key] = (time.time(), result)
            return result

        except Exception as e:
            logger.error("[SEARCH ERROR] %s", e)
            return []

    def _update_access_counts(self, hits):
        try:
            for hit in hits:
                existing_meta = dict(hit.get("metadata", {}))
                existing_meta["access_count"] = hit["access_count"] + 1
                self.collection.update(
                    ids=[hit["id"]],
                    metadatas=[existing_meta],
                )
        except Exception as e:
            logger.debug("[SearchEngine] Access count update failed: %s", e)

    def _parse_result(self, doc, dist, meta, memory_id, min_similarity):
        try:
            similarity = 1 - float(dist)
            if similarity < min_similarity:
                return None
            if not isinstance(meta, dict):
                meta = {}

            tags = meta.get("tags", "[]")
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except Exception:
                    tags = []

            emotion = meta.get("emotion", "{}")
            if isinstance(emotion, str):
                try:
                    emotion = json.loads(emotion)
                except Exception:
                    emotion = {"type": emotion, "intensity": 0.5}

            try:
                importance = float(meta.get("importance", 0.5) or 0.5)
            except Exception:
                importance = 0.5

            try:
                raw_ts = meta.get("timestamp", "")
                try:
                    ts = datetime.fromisoformat(str(raw_ts))
                except (ValueError, TypeError):
                    ts = datetime.fromtimestamp(float(raw_ts))
                days = (datetime.now() - ts).total_seconds() / 86400
                recency = round(1.0 / (1.0 + days), 3)
            except Exception:
                recency = 0.5

            try:
                access_count = int(meta.get("access_count", 0))
            except (ValueError, TypeError):
                access_count = 0

            return {
                "id": memory_id,
                "text": str(doc),
                "similarity": round(similarity, 3),
                "metadata": meta,
                "tags": tags,
                "emotion": emotion,
                "importance": importance,
                "recency": recency,
                "access_count": access_count,
            }
        except Exception as e:
            logger.error("[PARSE RESULT ERROR] %s", e)
            return None

    def _mmr_diversify(self, results, lambda_param=0.7):
        if len(results) <= 1:
            return results

        selected = []
        candidates = list(results)
        selected.append(candidates.pop(0))

        while candidates and len(selected) < len(results):
            mmr_scores = []
            for i, candidate in enumerate(candidates):
                relevance = (
                    candidate["similarity"] * 0.5
                    + candidate["importance"] * 0.2
                    + candidate["recency"] * 0.3
                )
                max_sim = 0.0
                for sel in selected:
                    sim = compute_text_overlap(
                        candidate.get("text", ""),
                        sel.get("text", "")
                    )
                    max_sim = max(max_sim, sim)
                mmr = lambda_param * relevance - (1 - lambda_param) * max_sim
                mmr_scores.append(mmr)
            best_idx = mmr_scores.index(max(mmr_scores))
            selected.append(candidates.pop(best_idx))
        return selected
