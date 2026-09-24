import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def migrate_collection(collection, schema_version: int) -> int:
    if collection is None:
        return 0
    try:
        all_data = collection.get()
        to_update = []
        for i, mid in enumerate(all_data["ids"]):
            meta = all_data["metadatas"][i] if all_data["metadatas"] else {}
            current_ver = int(meta.get("schema_version", 0))
            if current_ver < schema_version:
                updates: dict[str, Any] = {"schema_version": schema_version}
                if current_ver < 1:
                    updates["importance"] = float(meta.get("importance", 0.5))
                    updates["reinforcement"] = int(meta.get("reinforcement", 1))
                    updates["emotion_type"] = str(meta.get("emotion_type", "neutral"))
                    updates["tags"] = meta.get("tags", "[]")
                to_update.append(mid)
                collection.update(ids=[mid], metadatas=[{**meta, **updates}])
        if to_update:
            logger.info("[SchemaMigrator] Migrated %s entries to schema v%s", len(to_update), schema_version)
        return len(to_update)
    except Exception as e:
        logger.debug("[SchemaMigrator] Migration: %s", e)
        return 0
