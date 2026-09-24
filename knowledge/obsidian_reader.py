import os
import time
import hashlib
import logging
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ObsidianReader:

    def __init__(self, vault_path=None, entity_subdir="graph"):
        from config.paths import OBSIDIAN_VAULT
        vault = Path(vault_path or OBSIDIAN_VAULT)
        self.vault_root = vault
        self.entity_dir = vault / entity_subdir if entity_subdir else vault
        self._lock = threading.RLock()
        self.cache = {}
        self.file_hashes = {}
        self.last_reload = 0
        self.reload_interval = 5

    # ==================================================
    # 📖 SAFE FILE READ
    # ==================================================

    def _read(self, folder, file):
        try:
            path = self.vault_root / folder / file
            if not path.exists():
                return ""
            current_hash = self._file_hash(path)
            with self._lock:
                cached_hash = self.file_hashes.get(str(path))
                if str(path) in self.cache and cached_hash == current_hash:
                    return self.cache[str(path)]
            content = path.read_text(encoding="utf-8")
            with self._lock:
                self.cache[str(path)] = content
                self.file_hashes[str(path)] = current_hash
            return content
        except Exception as e:
            logger.warning("[ObsidianReader] read error: %s", e)
            return ""

    def _file_hash(self, path):
        try:
            return hashlib.md5(path.read_bytes()).hexdigest()
        except Exception as e:
            logger.warning("[ObsidianReader] file_hash: %s", e)
            return ""

    # ==================================================
    # 🧠 STRUCTURED MEMORY EXPORT (legacy compat)
    # ==================================================

    def get_all(self) -> dict[str, Any]:
        data = {
            "identity": self._parse_markdown(self._read("identity", "user.md")),
            "preferences": self._parse_markdown(self._read("preferences", "preferences.md")),
            "relationship": self._parse_markdown(self._read("relationship", "relationship.md")),
            "reflections": self._parse_markdown(self._read("reflections", "reflections.md")),
            "statistics": self._parse_markdown(self._read("statistics", "stats.md")),
        }
        if isinstance(data.get("relationship"), dict):
            closeness = self._safe_float(data["relationship"].get("closeness"), 0.5)
            trust = self._safe_float(data["relationship"].get("trust"), 0.5)
            data["relationship"]["stage"] = self._derive_stage(closeness, trust)
        return data

    def _derive_stage(self, closeness: float, trust: float) -> str:
        avg = (closeness + trust) / 2
        if avg < 0.3:
            return "distant"
        if avg < 0.5:
            return "familiar"
        if avg < 0.65:
            return "trusted"
        if avg < 0.8:
            return "close"
        return "deeply_attached"

    def load_memories(self):
        memories = []
        folders = [
            "conversation", "identity",
            "preferences", "relationship", "reflections", "archive",
            "knowledge", "projects", "people", "places", "dreams",
        ]
        try:
            for folder in folders:
                folder_path = self.vault_root / folder
                if not folder_path.exists():
                    continue
                for filename in os.listdir(str(folder_path)):
                    if not filename.endswith(".md"):
                        continue
                    content = self._read(folder, filename)
                    parsed = self._extract_entries(content)
                    memories.extend(parsed)
            return memories
        except Exception as e:
            logger.warning("[ObsidianReader] load_memories error: %s", e)
            return []

    # ==================================================
    # 🧠 ENTITY NOTE READING
    # ==================================================

    def read_entity(self, name):
        sanitized = name.strip().lower().replace(" ", "_")
        sanitized = "".join(c for c in sanitized if c.isalnum() or c in ("_", "-"))
        filepath = self.entity_dir / f"{sanitized}.md"
        if not filepath.exists():
            return None
        content = filepath.read_text(encoding="utf-8")
        return {"name": name, "content": content, "path": str(filepath)}

    def list_entities(self):
        if not self.entity_dir.exists():
            return []
        entities = []
        for fpath in self.entity_dir.iterdir():
            if fpath.suffix != ".md":
                continue
            entities.append(fpath.stem)
        return sorted(entities)

    # ==================================================
    # 🧠 ENTRY PARSING (legacy compat)
    # ==================================================

    def _extract_entries(self, content):
        if not content:
            return []
        entries = []
        chunks = content.split("\n---")
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                raw_entities = self._extract_section(chunk, "### 👥 Related Entities")
                parsed_entities = self._parse_entity_links(raw_entities)
                memory = {
                    "id": self._extract_field(chunk, "id"),
                    "timestamp": self._extract_field(chunk, "timestamp"),
                    "importance": self._safe_float(self._extract_field(chunk, "importance"), 0.5),
                    "emotion": self._extract_field(chunk, "emotion"),
                    "intensity": self._safe_float(self._extract_field(chunk, "intensity"), 0.5),
                    "user": self._extract_section(chunk, "### 👤 User"),
                    "ai": self._extract_section(chunk, "### 🌸 Mai"),
                    "tags": self._extract_tags(chunk),
                    "entity_links": parsed_entities,
                }
                if not memory["user"]:
                    continue
                entries.append(memory)
            except Exception as e:
                logger.warning("[ObsidianReader] entry parse: %s", e)
        return entries

    def _extract_field(self, text, field):
        try:
            for line in text.splitlines():
                line = line.strip()
                if line.startswith(f"{field}:"):
                    return line.split(":", 1)[1].strip()
            return ""
        except Exception as e:
            logger.warning("[ObsidianReader] extract_field: %s", e)
            return ""

    def _extract_section(self, text, section):
        try:
            lines = text.splitlines()
            capture = False
            collected = []
            for line in lines:
                if line.strip() == section:
                    capture = True
                    continue
                if capture and line.startswith("### "):
                    break
                if capture:
                    collected.append(line)
            return "\n".join(collected).strip()
        except Exception as e:
            logger.warning("[ObsidianReader] extract_section: %s", e)
            return ""

    def _extract_tags(self, text):
        tags = []
        try:
            for line in text.splitlines():
                if line.startswith("tags:"):
                    raw = line.split(":", 1)[1].strip()
                    raw = raw.replace("[", "").replace("]", "")
                    for tag in raw.split(","):
                        cleaned = tag.strip().replace("'", "").replace('"', "")
                        if cleaned:
                            tags.append(cleaned)
            return list(dict.fromkeys(tags))
        except Exception as e:
            logger.warning("[ObsidianReader] extract_tags: %s", e)
            return []

    # ==================================================
    # 🧠 UTILITY
    # ==================================================

    def _safe_float(self, value, default=0.0):
        try:
            return float(value)
        except Exception as e:
            logger.debug("[ObsidianReader] safe_float: %s", e)
            return default

    def _parse_entity_links(self, raw_section):
        if not raw_section:
            return []
        import re
        return re.findall(r"\[\[([^\]]+?)\]\]", raw_section)

    def _parse_markdown(self, content) -> dict[str, Any]:
        if not content:
            return {}
        result: dict[str, Any] = {}
        try:
            for line in content.splitlines():
                line = line.strip()
                if ": " in line and not line.startswith("#"):
                    key, _, value = line.partition(": ")
                    key = key.strip().lower()
                    value = value.strip()
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    result[key] = value
            return result
        except Exception as e:
            logger.debug("[ObsidianReader] markdown parse: %s", e)
            return {}

    def clear_cache(self):
        with self._lock:
            self.cache.clear()
            self.file_hashes.clear()

    def stats(self):
        with self._lock:
            return {
                "vault": str(self.vault_root),
                "cached_files": len(self.cache),
                "tracked_hashes": len(self.file_hashes),
            }
