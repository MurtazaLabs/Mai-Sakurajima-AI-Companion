# knowledge/retriever.py
import time
import threading
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import OrderedDict

from app.config_loader import MEMORY_SIMILARITY_THRESHOLD

logger = logging.getLogger(__name__)

# Cross-encoder model name for re-ranking
CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class QueryCache:
    """Simple TTL cache for query results."""
    
    def __init__(self, maxsize=100, ttl=30.0):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache = OrderedDict()
        self._lock = threading.RLock()
    
    def _make_key(self, query: str, **filters) -> str:
        """Create a cache key from query and filters."""
        key_parts = [query]
        for k, v in sorted(filters.items()):
            if v is not None:
                key_parts.append(f"{k}:{v}")
        return "|".join(key_parts)
    
    def get(self, query: str, **filters) -> list | None:
        """Get cached results if not expired."""
        key = self._make_key(query, **filters)
        with self._lock:
            if key in self._cache:
                result, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl:
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    return result
                else:
                    # Expired
                    del self._cache[key]
        return None
    
    def set(self, query: str, results: list, **filters) -> None:
        """Cache results with TTL."""
        key = self._make_key(query, **filters)
        with self._lock:
            # Remove oldest if at capacity
            if len(self._cache) >= self.maxsize:
                self._cache.popitem(last=False)
            self._cache[key] = (results, time.time())
    
    def clear(self) -> None:
        """Clear all cached results."""
        with self._lock:
            self._cache.clear()


class AdvancedRetriever:
    
    # Phatic/social query patterns - skip retrieval for these
    PHATIC_PATTERNS = {
        "greeting": ["hello", "hi", "hey", "good morning", "good evening", "good afternoon", "howdy", "hola"],
        "farewell": ["bye", "goodbye", "see you", "later", "farewell", "take care"],
        "thanks": ["thanks", "thank you", "thx", "appreciate it", "much appreciated"],
        "acknowledgment": ["ok", "okay", "sure", "got it", "understood", "cool", "nice", "great", "awesome"],
        "small_talk": ["how are you", "how's it going", "what's up", "whats up", "how do you do"],
        "affirmation": ["yes", "yeah", "yep", "yup", "sure", "absolutely", "definitely"],
        "negation": ["no", "nope", "not really", "i don't think so"],
    }
    
    @classmethod
    def is_phatic(cls, query: str) -> bool:
        """Check if query is phatic/social (no retrieval needed)."""
        if not query:
            return False
        q = query.lower().strip()
        # Short queries (1-4 words) that match phatic patterns
        words = q.split()
        if len(words) > 4:
            return False
        for category, patterns in cls.PHATIC_PATTERNS.items():
            for pattern in patterns:
                # Use word boundary matching to avoid false positives like "no" in "technology"
                import re
                if re.search(r'\b' + re.escape(pattern) + r'\b', q):
                    return True
        return False

    def __init__(self, vector_store=None, knowledge_graph=None,
                 belief_engine=None, attention=None, event_bus=None,
                 graph_reasoning=None, emotion=None,
                 max_workers=4,
                 rerank_enabled=True,
                 rerank_model_name=CROSS_ENCODER_MODEL,
                 rerank_top_n=20):
        self.vector_store = vector_store
        self.knowledge_graph = knowledge_graph
        self.belief_engine = belief_engine
        self.attention = attention
        self.event_bus = event_bus
        self.graph_reasoning = graph_reasoning
        self.emotion = emotion
        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="retriever")
        # Per-turn query cache
        self._query_cache = QueryCache(maxsize=100, ttl=30.0)
        
        # Cross-encoder re-ranking
        self.rerank_enabled = rerank_enabled
        self.rerank_model_name = rerank_model_name
        self.rerank_top_n = rerank_top_n
        self._cross_encoder = None
        self._cross_encoder_lock = threading.Lock()

    def retrieve(self, query, attention_focus=None, top_k=5, speaker=None, memory_type=None, user_id=None):
        if not query:
            return []
        
        # Skip retrieval for phatic/social queries
        if self.is_phatic(query):
            logger.debug("[Retriever] Skipping retrieval for phatic query: %s", query[:50])
            return []

        # Check cache first
        cache_key_filters = {
            "attention_focus": attention_focus,
            "top_k": top_k,
            "speaker": speaker,
            "memory_type": memory_type,
            "user_id": user_id,
        }
        cached = self._query_cache.get(query, **cache_key_filters)
        if cached is not None:
            logger.debug("[Retriever] Cache hit for query: %s", query[:50])
            return cached

        results = []
        seen_content = set()
        _lock = threading.Lock()

        def _early_exit():
            high_quality = [r for r in results if r["score"] >= 0.7]
            return len(high_quality) >= top_k

        def _finalize(r):
            if self.emotion:
                try:
                    retrieval_bias = self.emotion.influence("retrieval")
                    for item in r:
                        item["score"] = item["score"] * retrieval_bias
                except Exception as e:
                    logger.warning("[Retriever] emotion influence: %s", e)
            r.sort(key=lambda x: x["score"], reverse=True)
            r = self._diversify(r, top_k)
            return r[:top_k]

        def _merge(items):
            with _lock:
                for item in items:
                    c = item["content"]
                    if c and c not in seen_content:
                        seen_content.add(c)
                        results.append(item)

        # ── Parallel retrieval from all sources ──
        def _query_vector():
            if not self.vector_store:
                return []
            try:
                filter_kw = {}
                if memory_type:
                    filter_kw["metadata_filter"] = {"memory_type": {"$eq": memory_type}}
                if user_id:
                    user_filter = {"user_id": {"$eq": user_id}}
                    if memory_type:
                        filter_kw["metadata_filter"] = {
                            "$and": [filter_kw["metadata_filter"], user_filter]
                        }
                    else:
                        filter_kw["metadata_filter"] = user_filter
                # Apply similarity threshold to filter out low-relevance results
                filter_kw["min_similarity"] = MEMORY_SIMILARITY_THRESHOLD
                vector_results = self.vector_store.search(query, top_k=top_k, **filter_kw)
                out = []
                for item in vector_results:
                    text = ""
                    score = 0.5
                    if isinstance(item, dict):
                        text = item.get("text", item.get("content", ""))
                        score = item.get("score", item.get("relevance", 0.5))
                    else:
                        text = str(item)
                    if speaker and isinstance(item, dict):
                        meta = item.get("metadata", {}) or {}
                        if meta.get("speaker", "") and meta["speaker"] != speaker:
                            continue
                    content = str(text).strip()
                    if content:
                        out.append({"content": content, "score": float(score), "source": "vector"})
                return out
            except Exception as e:
                logger.error("[Retriever] Vector search error: %s", e)
                return []

        def _query_beliefs():
            if not self.belief_engine:
                return []
            try:
                beliefs = self.belief_engine.all_beliefs()
                return [{"content": f"{b.topic} {b.predicate} {b.object}",
                         "score": b.confidence * 0.9, "source": "belief"}
                        for b in beliefs]
            except Exception as e:
                logger.error("[Retriever] Belief query error: %s", e)
                return []

        def _query_knowledge_graph():
            if not self.knowledge_graph:
                return []
            try:
                local_seen = set()
                enriched = self._enriched_graph_retrieval(query, local_seen)
                out = list(enriched)
                for item in enriched:
                    local_seen.add(item["content"])
                if not enriched:
                    candidates = set()
                    terms = [t.lower().strip() for t in query.split() if len(t) > 2]
                    for term in terms:
                        for entity in self.knowledge_graph.all_entities():
                            if term in entity.name.lower():
                                candidates.add(entity.name)
                        seen_rels = set()
                        for cand in candidates:
                            rels = self.knowledge_graph.query(cand, depth=2, user_id=user_id)
                            for rel in rels:
                                content = f"{rel.source} -- {rel.relation} --> {rel.target}"
                                if content not in local_seen and content not in seen_rels:
                                    seen_rels.add(content)
                                    local_seen.add(content)
                                    out.append({"content": content, "score": rel.weight * 0.7,
                                                "source": "knowledge_graph"})
                return out
            except Exception as e:
                logger.error("[Retriever] Knowledge graph error: %s", e)
                return []

        def _query_attention():
            if not attention_focus or not self.attention:
                return []
            try:
                focus_results = self.attention.retrieve(attention_focus)
                return [{"content": item.get("content", ""),
                         "score": item.get("relevance", 0.5),
                         "source": "attention"}
                        for item in focus_results if item.get("content")]
            except Exception as e:
                logger.error("[Retriever] Attention error: %s", e)
                return []

        futures = {}
        pool = self._executor
        futures[pool.submit(_query_vector)] = "vector"
        futures[pool.submit(_query_beliefs)] = "beliefs"
        futures[pool.submit(_query_knowledge_graph)] = "kg"
        if attention_focus and self.attention:
            futures[pool.submit(_query_attention)] = "attention"

        for fut in as_completed(futures):
            items = fut.result()
            if items:
                _merge(items)
                if _early_exit():
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    break

        results = _finalize(results)

        if self.event_bus:
            from core.event_specs import RETRIEVER_RESULTS
            from core.mai_message import publish_event
            publish_event(self.event_bus, RETRIEVER_RESULTS, {
                "query": query,
                "count": len(results),
            }, source="knowledge")

        # Cache results for future queries
        cache_key_filters = {
            "attention_focus": attention_focus,
            "top_k": top_k,
            "speaker": speaker,
            "memory_type": memory_type,
            "user_id": user_id,
        }
        self._query_cache.set(query, results, **cache_key_filters)

        # Apply cross-encoder re-ranking if enabled
        if self.rerank_enabled and results:
            results = self._rerank(query, results, top_k)

        return results

    def _load_cross_encoder(self):
        """Lazy load the cross-encoder model."""
        if self._cross_encoder is None:
            with self._cross_encoder_lock:
                if self._cross_encoder is None:
                    try:
                        from sentence_transformers import CrossEncoder
                        logger.info("[Retriever] Loading cross-encoder model: %s", self.rerank_model_name)
                        self._cross_encoder = CrossEncoder(self.rerank_model_name)
                    except Exception as e:
                        logger.warning("[Retriever] Failed to load cross-encoder: %s", e)
                        self.rerank_enabled = False
        return self._cross_encoder

    def _rerank(self, query: str, results: list, top_k: int) -> list:
        """Re-rank results using cross-encoder."""
        if not self.rerank_enabled or not results:
            return results
        
        cross_encoder = self._load_cross_encoder()
        if cross_encoder is None:
            return results
        
        try:
            # Prepare query-document pairs
            pairs = [(query, r["content"]) for r in results[:self.rerank_top_n]]
            scores = cross_encoder.predict(pairs)
            
            # Update scores
            for i, score in enumerate(scores):
                results[i]["score"] = float(score)
                results[i]["reranked"] = True
            
            # Sort by new scores
            reranked = sorted(results[:self.rerank_top_n], key=lambda x: x["score"], reverse=True)
            
            # Keep remaining results in original order
            remaining = results[self.rerank_top_n:]
            
            return reranked[:top_k] + remaining
        except Exception as e:
            logger.warning("[Retriever] Re-ranking failed: %s", e)
            return results

    def _enriched_graph_retrieval(self, query, seen_content):
        if not self.graph_reasoning or not self.knowledge_graph:
            return []

        items = []
        seen_graph = set()
        q = query.lower().strip()

        try:
            # 1. Type-based — e.g. "what technologies does Mai use"
            type_keywords = ["type", "kind", "sort", "category", "class"]
            if any(k in q for k in type_keywords):
                type_candidates = [w for w in q.split() if len(w) > 2
                                   and w not in type_keywords]
                for tc in type_candidates:
                    ents = self.graph_reasoning.query_by_type(tc)
                    for e in ents:
                        content = f"[graph] {e['name']} ({e['type']})"
                        if content not in seen_content and content not in seen_graph:
                            seen_graph.add(content)
                            items.append({
                                "content": content,
                                "score": 0.85,
                                "source": "knowledge_graph",
                            })

            # 2. Neighbor expansion — entities related to query terms
            for term in q.split():
                if len(term) <= 2:
                    continue
                nbrs = self.graph_reasoning.neighbors(term, depth=1)
                for n in nbrs:
                    content = f"[graph] {n['name']} ({n['type']}) — {n['relation']}"
                    if content not in seen_content and content not in seen_graph:
                        seen_graph.add(content)
                        items.append({
                            "content": content,
                            "score": n.get("weight", 0.7) * 0.8,
                            "source": "knowledge_graph",
                        })

            # 3. Connection path — e.g. "what connects X and Y"
            if q.startswith("what connects") or "connect" in q:
                parts = q.replace("what connects", "").replace("?", "").strip()
                tokens = [t.strip() for t in parts.split("and") if t.strip()]
                if len(tokens) >= 2:
                    edges = self.graph_reasoning.what_connects(
                        tokens[0], tokens[-1]
                    )
                    for edge in edges:
                        if edge not in seen_graph:
                            seen_graph.add(edge)
                            items.append({
                                "content": f"[graph path] {edge}",
                                "score": 0.9,
                                "source": "knowledge_graph",
                            })

        except Exception as e:
            logger.warning("[Retriever] Enriched graph retrieval: %s", e)

        return items

    def _diversify(self, results, top_k):
        if len(results) <= 1:
            return results

        diversified = [results[0]]
        sources = {results[0]["source"]}
        seen_texts = {results[0]["content"]}

        for r in results[1:]:
            if len(diversified) >= top_k:
                break
            if r["source"] not in sources or r["content"] not in seen_texts:
                diversified.append(r)
                sources.add(r["source"])
                seen_texts.add(r["content"])

        if len(diversified) < top_k:
            for r in results[1:]:
                if len(diversified) >= top_k:
                    break
                if r["content"] not in seen_texts:
                    diversified.append(r)
                    seen_texts.add(r["content"])

        return diversified

    def shutdown(self):
        """Shutdown the thread pool executor."""
        self._executor.shutdown(wait=True)

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass