# Mai_ai/memory/recall.py
import logging
import threading
import time
from collections import Counter

logger = logging.getLogger(__name__)


class RecallEngine:

    def __init__(self):

        # 🧠 recall tuning
        self.tag_weight = 0.45

        self.text_weight = 0.30

        self.score_weight = 0.15

        self.recency_weight = 0.10

        # 🧠 recall limits
        self.max_results = 5

        self.min_relevance = 0.30

        # 🧠 thread safety
        self.lock = threading.RLock()

    # ==================================================
    # 🧠 MAIN RECALL
    # ==================================================
    def recall(
        self,
        nodes,
        query_tags=None,
        query_text=""
    ):

        with self.lock:

            if not nodes:
                return None

            query_tags = query_tags or []

            query_text = str(
                query_text or ""
            ).lower()

            ranked = []

            now = time.time()

            for node in nodes:

                try:

                    relevance = self._relevance(

                        node=node,

                        query_tags=query_tags,

                        query_text=query_text,

                        now=now
                    )

                    if relevance < self.min_relevance:
                        continue

                    ranked.append({

                        "node": node,

                        "relevance": round(
                            relevance,
                            4
                        )
                    })

                except Exception as e:

                    logger.error(
                        f"[RECALL NODE ERROR] {e}"
                    )

            # 🚫 nothing found
            if not ranked:
                return None

            # 🧠 best first
            ranked.sort(

                key=lambda x: x["relevance"],

                reverse=True
            )

            top = ranked[:self.max_results]

            # 🧠 reinforce recalled memories
            for item in top:

                node = item["node"]

                if hasattr(node, 'lock'):
                    with node.lock:
                        node.last_accessed = now
                        node.reinforcement_count = (
                            getattr(
                                node,
                                "reinforcement_count",
                                0
                            ) + 1
                        )
                else:
                    node.last_accessed = now
                    node.reinforcement_count = (
                        getattr(
                            node,
                            "reinforcement_count",
                            0
                        ) + 1
                    )

            # 🧠 structured return
            results = []

            for item in top:

                node = item["node"]

                results.append({

                    "memory":
                        getattr(
                            node,
                            "text",
                            ""
                        ),

                    "score":
                        getattr(
                            node,
                            "score",
                            0.5
                        ),

                    "relevance":
                        item["relevance"],

                    "tags":
                        getattr(
                            node,
                            "tags",
                            []
                        ),

                    "memory_type":
                        getattr(
                            node,
                            "memory_type",
                            "general"
                        ),

                    "emotion":
                        getattr(
                            node,
                            "emotion",
                            {}
                        ),

                    "created_at":
                        getattr(
                            node,
                            "created_at",
                            0
                        ),
                })

            # ✅ single best memory shortcut
            if len(results) == 1:
                return results[0]

            return results

    # ==================================================
    # 🧠 RELEVANCE SCORING
    # ==================================================
    def _relevance(
        self,
        node,
        query_tags,
        query_text,
        now
    ):

        relevance = 0.0

        # ==================================================
        # 🏷️ TAG MATCHING
        # ==================================================

        node_tags = set(
            getattr(
                node,
                "tags",
                []
            )
        )

        query_tags = set(query_tags)

        if node_tags and query_tags:

            overlap = len(
                node_tags.intersection(
                    query_tags
                )
            )

            union = len(
                node_tags.union(
                    query_tags
                )
            )

            if union > 0:

                tag_score = overlap / union

                relevance += (
                    tag_score
                    *
                    self.tag_weight
                )

        # ==================================================
        # 📝 TEXT MATCHING
        # ==================================================

        if query_text:

            node_text = str(
                getattr(
                    node,
                    "text",
                    ""
                )
            ).lower()

            query_words = set(
                query_text.split()
            )

            node_words = set(
                node_text.split()
            )

            if query_words and node_words:

                overlap = len(
                    query_words.intersection(
                        node_words
                    )
                )

                union = len(
                    query_words.union(
                        node_words
                    )
                )

                if union > 0:

                    text_score = overlap / union

                    relevance += (
                        text_score
                        *
                        self.text_weight
                    )

        # ==================================================
        # ⭐ MEMORY IMPORTANCE
        # ==================================================

        memory_score = float(
            getattr(
                node,
                "score",
                0.5
            )
        )

        relevance += (
            memory_score
            *
            self.score_weight
        )

        # ==================================================
        # 🕒 RECENCY BOOST
        # ==================================================

        last_accessed = getattr(
            node,
            "last_accessed",
            now
        )

        age_hours = max(

            1,

            (now - last_accessed)
            / 3600
        )

        recency = min(

            1.0,

            1 / (
                age_hours * 0.08
            )
        )

        relevance += (
            recency
            *
            self.recency_weight
        )

        # ==================================================
        # ❤️ EMOTIONAL BOOST
        # ==================================================

        emotion = getattr(
            node,
            "emotion",
            {}
        )

        if isinstance(emotion, dict):

            intensity = float(
                emotion.get(
                    "intensity",
                    0.5
                )
            )

            relevance += (
                intensity * 0.05
            )

        return round(
            min(relevance, 1.0),
            4
        )

    # ==================================================
    # 🧠 SEARCH BY MEMORY TYPE
    # ==================================================
    def search_type(
        self,
        nodes,
        memory_type
    ):

        with self.lock:

            results = []

            for node in nodes:

                if getattr(
                    node,
                    "memory_type",
                    ""
                ) == memory_type:

                    results.append(node)

            return results

    # ==================================================
    # 🧠 MOST COMMON TAGS
    # ==================================================
    def common_tags(
        self,
        nodes,
        limit=10
    ):

        with self.lock:

            counter: Counter[str] = Counter()

            for node in nodes:

                tags = getattr(
                    node,
                    "tags",
                    []
                )

                counter.update(tags)

            return counter.most_common(
                limit
            )

    # ==================================================
    # 📊 DEBUG STATS
    # ==================================================
    def stats(self):

        return {

            "tag_weight":
                self.tag_weight,

            "text_weight":
                self.text_weight,

            "score_weight":
                self.score_weight,

            "recency_weight":
                self.recency_weight,

            "max_results":
                self.max_results,

            "min_relevance":
                self.min_relevance,
        }