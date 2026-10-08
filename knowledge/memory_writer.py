import os
import re
import uuid
import hashlib
import logging
import threading
from pathlib import Path
from datetime import datetime

from knowledge.graph_exporter import sanitize_entity_stem

logger = logging.getLogger(__name__)

_REINFORCEMENT_RE = re.compile(r"reinforcement_count(['\"]?)\s*:\s*(\d+)")


class MemoryWriter:
    def __init__(self, vault_root):
        self.vault_root = Path(vault_root)
        self._lock = threading.RLock()
        self.hash_cache = set()
        self._mem_write_count = 0
        self.memory_folders = [
            "conversation", "identity", "preferences",
            "relationship", "reflections", "archive",
            "knowledge", "projects", "people", "places",
            "statistics", "dreams", "important",
        ]
        self.fixed_filenames = {
            "identity": "user.md",
            "preferences": "preferences.md",
            "relationship": "relationship.md",
            "reflections": "reflections.md",
            "knowledge": "knowledge.md",
            "projects": "projects.md",
            "people": "people.md",
            "places": "places.md",
            "statistics": "stats.md",
            "dreams": "dreams.md",
        }
        self.overwrite_folders = {"identity", "preferences", "relationship", "reflections",
                                   "knowledge", "projects", "people", "places", "dreams"}
        # Single-writer ownership: these folders are compiled by StateDumper /
        # VaultCompiler in structured format. Raw turn entries must never
        # replace the compiled file (dual-writer clobber) — they are redirected
        # to the chronological conversation log instead.
        self.compiler_owned_folders = {
            "identity", "preferences", "relationship", "knowledge",
            "projects", "people", "places", "dreams", "statistics",
        }
        for folder in self.memory_folders:
            (vault_root / folder).mkdir(parents=True, exist_ok=True)

    def _link_target_exists(self, name):
        """Return True if a graph note for ``name`` is present in the vault.
        
        Uses atomic open/read to avoid TOCTOU between exists() and read().
        """
        try:
            graph_dir = self.vault_root / "graph"
            if not graph_dir.is_dir():
                return False
            safe = sanitize_entity_stem(name)
            filepath = graph_dir / f"{safe}.md"
            # Atomic check: try to open the file
            with filepath.open("r", encoding="utf-8") as f:
                f.read(1)  # Read one char to verify accessibility
            return True
        except Exception as e:
            logger.debug("[MemoryWriter] link target check failed: %s", e)
            return False

    def _resolvable_links(self, names):
        """Keep only wiki-link targets that resolve to an existing note."""
        resolved = []
        for name in names:
            if name and isinstance(name, str) and self._link_target_exists(name):
                resolved.append(name)
        return resolved

    def _dedup_hit_anywhere(self, folder, user, ai):
        """Scan every file in ``folder`` for the same user turn (cross-day dedup).

        The needle spans both the user turn and the AI response so it matches
        the in-process ``md5(folder:user+ai)`` signature — otherwise the same
        turn repeated with a different response would be suppressed cross-day
        (new AI answer silently lost). Returns the path of the first file
        containing the turn, or None.
        """
        if folder in self.overwrite_folders:
            return None
        folder_path = self.vault_root / folder
        if not folder_path.is_dir():
            return None
        needle = f"### 👤 User\n{user}\n\n### 🌸 Mai\n{ai}\n"
        try:
            for fpath in folder_path.glob("*.md"):
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    logger.debug("[MemoryWriter] read file failed in dedup scan: %s", e)
                    continue
                if needle in content:
                    return fpath
        except Exception as e:
            logger.warning("[MemoryWriter] cross-day dedup scan error: %s", e)
        return None

    def _bump_reinforcement(self, fpath, user, ai):
        """Increment reinforcement_count on the matching entry's metadata line."""
        try:
            needle = f"### 👤 User\n{user}\n\n### 🌸 Mai\n{ai}\n"
            content = fpath.read_text(encoding="utf-8", errors="replace")
            start = content.find(needle)
            if start == -1:
                return
            entry_end = content.find("\n---\n", start)
            entry_block = content[start:entry_end] if entry_end != -1 else content[start:]
            match = _REINFORCEMENT_RE.search(entry_block)
            if match:
                new_count = int(match.group(2)) + 1
                quote = match.group(1)
                new_block = _REINFORCEMENT_RE.sub(
                    f"reinforcement_count{quote}: {new_count}", entry_block, count=1
                )
                content = content[:start] + new_block + content[entry_end:] if entry_end != -1 \
                    else content[:start] + new_block
                fpath.write_text(content, encoding="utf-8")
                logger.info("[MemoryWriter] reinforced canonical memory in %s (count=%d)",
                            fpath.name, new_count)
        except Exception as e:
            logger.warning("[MemoryWriter] reinforcement bump error: %s", e)

    def write(self, folder, user, ai, tags, emotion, score, metadata=None, entity_names=None):
        try:
            if not isinstance(folder, str) or folder not in self.memory_folders:
                folder = "conversation"
            if folder in self.compiler_owned_folders:
                logger.warning(
                    "[MemoryWriter] raw write to compiler-owned folder '%s' redirected "
                    "to conversation/ (compiler owns %s.md)", folder,
                    self.fixed_filenames.get(folder, folder),
                )
                folder = "conversation"
            timestamp = datetime.now()
            filename = self.fixed_filenames.get(folder, timestamp.strftime("%Y-%m-%d") + ".md")
            path = self.vault_root / folder / filename
            user = str(user or "").strip()
            ai = str(ai or "").strip()
            signature = hashlib.md5(f"{folder}:{user}{ai}".encode("utf-8")).hexdigest()
            with self._lock:
                if signature in self.hash_cache:
                    return False
                self.hash_cache.add(signature)
                if folder not in self.overwrite_folders and path.exists():
                    try:
                        tail = path.read_text(encoding="utf-8", errors="replace")
                        if tail:
                            scan = tail
                            needle = f"### 👤 User\n{user}\n"
                            if needle in scan:
                                self.hash_cache.add(signature)
                                return False
                    except Exception as e:
                        logger.warning("[MemoryWriter] hash scan error: %s", e)
                existing = self._dedup_hit_anywhere(folder, user, ai)
                if existing is not None:
                    self._bump_reinforcement(existing, user, ai)
                    return False
            metadata = metadata or {}
            tags = tags or []
            entity_names = entity_names or []
            emotion = emotion or {"type": "neutral", "intensity": 0.5}
            memory_id = str(uuid.uuid4())[:8]
            resolved_tags = self._resolvable_links(tags)
            wiki_tags = " ".join([f"[[{t}]]" for t in resolved_tags])
            md_tags = " ".join([f"#{t}" for t in tags])
            entity_links_raw = [e for e in entity_names if e and isinstance(e, str)]
            entity_links_clean = list(dict.fromkeys(entity_links_raw))
            entity_links_clean = self._resolvable_links(entity_links_clean)
            entity_wiki = " ".join([f"[[{e}]]" for e in entity_links_clean])
            entry_parts = [f"""

---

id: {memory_id}
timestamp: {timestamp.strftime("%Y-%m-%d %H:%M:%S")}
importance: {round(float(score), 2)}
emotion: {emotion.get("type")}
intensity: {emotion.get("intensity", 0.5)}
tags: {tags}
---

## 🕒 {timestamp.strftime("%H:%M:%S")}

### 👤 User
{user}

### 🌸 Mai
{ai}

### 🧠 Emotional Context
Mood: {emotion.get("type")}
Intensity: {emotion.get("intensity", 0.5)}

### 🏷️ Tags
{md_tags}

### 🔗 Memory Links
{wiki_tags}
"""]
            if entity_links_clean:
                entry_parts.append(f"""### 👥 Related Entities
{entity_wiki}
""")
            entry_parts.append(f"""### 📊 Metadata
{metadata}

---

""")
            entry = "".join(entry_parts)
            mode = "w" if folder in self.overwrite_folders else "a"
            with self._lock:
                with open(path, mode, encoding="utf-8") as f:
                    f.write(entry)
                self._mem_write_count += 1
            return True
        except Exception as e:
            logger.error("[MemoryWriter] write error: %s", e)
            return False

    def write_memory(self, routes, user, ai, tags, emotion, score, metadata=None, entity_names=None):
        if not routes:
            routes = ["conversation"]
        unique_routes = list(dict.fromkeys(routes))
        results = {}
        for folder in unique_routes:
            if folder not in self.memory_folders:
                logger.warning("[MemoryWriter] unknown folder: %s", folder)
                continue
            results[folder] = self.write(
                folder=folder, user=user, ai=ai, tags=tags,
                emotion=emotion, score=score, metadata=metadata,
                entity_names=entity_names,
            )
        return results

    def write_important(self, text, tags=None, emotion=None, score=0.9):
        return self.write(
            folder="important", user=text, ai="",
            tags=(tags or []) + ["important"], emotion=emotion or {"type": "important", "intensity": 1.0},
            score=score,
        )

    def write_reflection(self, reflection):
        return self.write(
            folder="reflections", user=reflection, ai="",
            tags=["reflection"], emotion={"type": "thoughtful", "intensity": 0.7},
            score=0.8,
        )

    def archive(self, text):
        return self.write(
            folder="archive", user=text, ai="",
            tags=["archive"], emotion={"type": "neutral", "intensity": 0.3},
            score=0.2,
        )

    def add_entity_links(self, folder, user, ai, entity_names):
        try:
            if not entity_names or not folder:
                return False
            if folder not in self.memory_folders:
                folder = "conversation"
            timestamp = datetime.now()
            filename = self.fixed_filenames.get(folder, timestamp.strftime("%Y-%m-%d") + ".md")
            path = self.vault_root / folder / filename
            if not path.exists():
                return False
            with self._lock:
                content = path.read_text(encoding="utf-8", errors="replace")
                if not content:
                    return False
                clean = list(dict.fromkeys([e for e in entity_names if e and isinstance(e, str)]))
                if not clean:
                    return False
                block = "\n### 👥 Related Entities\n" + " ".join([f"[[{e}]]" for e in clean]) + "\n"
                if block.strip() in content:
                    return False
                user_tag = f"### 👤 User\n{user}\n"
                if user_tag not in content:
                    return False
                idx = content.index(user_tag)
                entry_end = content.find("\n---\n", idx)
                if entry_end == -1:
                    entry_end = content.rfind("\n---")
                    if entry_end == -1:
                        return False
                    entry_end += 4
                else:
                    entry_end += 5
                before = content[:entry_end]
                after = content[entry_end:]
                if "### 👥 Related Entities" in before:
                    return False
                new_before = before.rstrip() + block
                path.write_text(new_before + after, encoding="utf-8")
                return True
        except Exception as e:
            logger.error("[MemoryWriter] add_entity_links error: %s", e)
            return False

    def clear_cache(self):
        with self._lock:
            self.hash_cache.clear()

    def stats(self):
        with self._lock:
            return {
                "memory_writes": self._mem_write_count,
                "cached_hashes": len(self.hash_cache),
            }
