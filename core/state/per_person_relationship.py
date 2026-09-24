import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("Mai.PerPersonRelationship")


_DEFAULT_RELATIONSHIP = {
    "trust": 0.5,
    "comfort": 0.5,
    "respect": 0.5,
    "affection": 0.3,
    "familiarity": 0.1,
}


class PerPersonRelationshipManager:

    def __init__(self, storage_dir: str | Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, dict] = {}
        self._lock = threading.RLock()

    def _path(self, name: str) -> Path:
        safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in name)
        return self.storage_dir / f"{safe}.json"

    def get(self, name: str) -> dict:
        with self._lock:
            if name in self._cache:
                return self._cache[name]

            path = self._path(name)
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    self._cache[name] = data
                    return data
                except Exception as exc:
                    logger.debug("get(%s) failed: %s", name, exc)

            default = dict(_DEFAULT_RELATIONSHIP)
            self._cache[name] = default
            return default

    def update(self, name: str, trust_delta=0.0, comfort_delta=0.0,
               respect_delta=0.0, affection_delta=0.0,
               familiarity_delta=0.0) -> dict:
        with self._lock:
            rel = self.get(name)
            rel["trust"] = max(0.0, min(1.0, rel.get("trust", 0.5) + trust_delta))
            rel["comfort"] = max(0.0, min(1.0, rel.get("comfort", 0.5) + comfort_delta))
            rel["respect"] = max(0.0, min(1.0, rel.get("respect", 0.5) + respect_delta))
            rel["affection"] = max(0.0, min(1.0, rel.get("affection", 0.3) + affection_delta))
            rel["familiarity"] = max(0.0, min(1.0, rel.get("familiarity", 0.1) + familiarity_delta))
            rel["last_seen"] = time.time()
            self._save(name, rel)
            return rel

    def _save(self, name: str, data: dict):
        with self._lock:
            try:
                path = self._path(name)
                path.write_text(json.dumps(data, indent=2), encoding="utf-8")
                self._cache[name] = data
            except Exception as exc:
                logger.debug("_save(%s) failed: %s", name, exc)

    def list_all(self) -> list[dict]:
        with self._lock:
            results = []
            for fpath in self.storage_dir.glob("*.json"):
                try:
                    data = json.loads(fpath.read_text(encoding="utf-8"))
                    results.append(data)
                except Exception as exc:
                    logger.debug("list_all skipped %s: %s", fpath.name, exc)
            return results

    def delete(self, name: str) -> bool:
        with self._lock:
            path = self._path(name)
            if path.exists():
                try:
                    path.unlink()
                    self._cache.pop(name, None)
                    return True
                except Exception as exc:
                    logger.debug("delete(%s) failed: %s", name, exc)
                    return False
            return False

    def stats(self) -> dict:
        profiles = self.list_all()
        return {
            "total": len(profiles),
            "profiles": [
                {
                    "name": p.get("_name", f"speaker_{i}"),
                    "trust": round(p.get("trust", 0.5), 3),
                    "comfort": round(p.get("comfort", 0.5), 3),
                    "familiarity": round(p.get("familiarity", 0.1), 3),
                }
                for i, p in enumerate(profiles)
            ],
        }
