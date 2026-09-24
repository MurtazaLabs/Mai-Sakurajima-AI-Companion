import logging
from datetime import datetime

from app.config_loader import MEMORY_MAX_VECTOR_ROWS

logger = logging.getLogger(__name__)


class VectorLifecycle:
    """Cap enforcement and pruning for VectorStore — extracted from the original
    VectorStore god class."""

    def __init__(self, collection):
        self.collection = collection

    def enforce_cap(self, max_rows=None):
        if not self.collection:
            return 0
        max_rows = max_rows or MEMORY_MAX_VECTOR_ROWS
        try:
            current = self.collection.count()
            overflow = current - max_rows
            if overflow <= 0:
                return 0
            all_data = self.collection.get()
            scored = []
            for i, mid in enumerate(all_data["ids"]):
                meta = all_data["metadatas"][i] if all_data["metadatas"] else {}
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
                    age_days = (datetime.now() - ts).total_seconds() / 86400
                except Exception:
                    age_days = 0.0
                score = importance * 0.6 + min(age_days / 365.0, 1.0) * 0.4
                scored.append((score, mid))
            scored.sort(key=lambda x: x[0])
            max_evict = max(1, int(current * 0.2))
            to_delete = [mid for _, mid in scored[:min(overflow, max_evict)]]
            if to_delete:
                self.collection.delete(ids=to_delete)
                logger.info(
                    "[VectorLifecycle] Cap enforced: removed %s lowest-value memories "
                    "(count %s -> %s)",
                    len(to_delete), current, current - len(to_delete)
                )
            return len(to_delete)
        except Exception as e:
            logger.error("[VectorLifecycle] Enforce cap error: %s", e)
            return 0

    def prune(self, max_age_days=90.0, min_importance=0.2):
        if not self.collection:
            return 0
        try:
            all_data = self.collection.get()
            now = datetime.now()
            to_delete = []
            for i, mid in enumerate(all_data["ids"]):
                meta = all_data["metadatas"][i] if all_data["metadatas"] else {}
                ts_str = meta.get("timestamp", "")
                importance = float(meta.get("importance", 0.5))
                try:
                    try:
                        ts = datetime.fromisoformat(str(ts_str))
                    except (ValueError, TypeError):
                        ts = datetime.fromtimestamp(float(ts_str))
                    age_days = (now - ts).total_seconds() / 86400
                except Exception:
                    age_days = 0.0
                if age_days > max_age_days and importance < min_importance:
                    to_delete.append(mid)
            if to_delete:
                self.collection.delete(ids=to_delete)
                logger.info("[VectorLifecycle] Pruned %s old/low-importance memories", len(to_delete))
            return len(to_delete)
        except Exception as e:
            logger.error("[VectorLifecycle] Prune error: %s", e)
            return 0
