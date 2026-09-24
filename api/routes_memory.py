"""Memory domain logic for the Mai API.

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for how this is composed.
"""
import logging
from typing import Any
from api.errors import safe_error

logger = logging.getLogger("api.server")


class MemoryMixin:
    """Memory search, statistics, and timeline handlers."""

    # Set by MaiAPI at runtime — declared here for type checker
    _ready: bool = False
    brain: Any = None
    memory_hierarchy: Any = None
    vector_store: Any = None

    def memory_query(self, query, top_k=5):
        if not self._ready or not self.brain:
            return {"error": "system_not_ready"}
        try:
            retriever = getattr(self.brain, "retriever", None)
            if retriever is not None and hasattr(retriever, "retrieve"):
                raw = retriever.retrieve(query, top_k=top_k)
                results = []
                for item in raw if isinstance(raw, list) else []:
                    if not isinstance(item, dict):
                        continue
                    content = str(item.get("content", "")).strip()
                    if not content:
                        continue
                    results.append({
                        "content": content,
                        "score": round(float(item.get("score", 0.0)), 4),
                        "source": item.get("source", ""),
                    })
                return {"results": results}
            mem = self.brain.memory
            results = []
            if mem is not None and hasattr(mem, "recall"):
                raw = mem.recall(query, limit=top_k)
                if isinstance(raw, list):
                    results = raw
                elif isinstance(raw, str) and raw.strip():
                    results = [{"content": raw}]
            return {"results": results}
        except Exception as e:
            return {"error": safe_error(e)}

    def memory_stats(self):
        if not self._ready or not self.brain:
            return {"error": "system_not_ready"}
        stats = {}
        try:
            if self.memory_hierarchy:
                stats["hierarchy"] = self.memory_hierarchy.stats()
            if self.vector_store and hasattr(self.vector_store, "count"):
                try:
                    stats["vector_count"] = self.vector_store.count()
                except Exception as e:
                    logger.exception("[Memory] vector count: %s", e)
            mem = self.brain.memory
            if hasattr(mem, "short"):
                stats["recent_count"] = len(mem.short)
        except Exception as e:
            logger.exception("[Memory] stats: %s", e)
        return stats

    def memory_timeline(self, limit=50):
        if not self._ready or not self.brain:
            return {"error": "system_not_ready"}
        try:
            merged = []
            if self.memory_hierarchy:
                grouped = self.memory_hierarchy.to_dict()
                for type_name, items in grouped.items():
                    for item in items:
                        item["type"] = type_name
                        merged.append(item)
            mem = self.brain.memory
            if hasattr(mem, "short"):
                for entry in mem.short:
                    merged.append({
                        "type": "conversation",
                        "content": f"{entry.get('user','')[:120]}",
                        "timestamp": entry.get("timestamp", 0),
                        "metadata": {"speaker": entry.get("speaker", ""), "tags": entry.get("tags", [])},
                    })
            merged.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
            return {"timeline": merged[:limit]}
        except Exception as e:
            return {"error": safe_error(e)}
