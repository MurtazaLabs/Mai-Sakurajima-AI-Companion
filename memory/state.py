import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class IdentityFact:
    fact: str
    category: str = "general"
    timestamp: str = ""


@dataclass
class KnowledgeEntry:
    topic: str
    fact: str
    timestamp: str = ""


@dataclass
class MemoryState:
    SCHEMA_VERSION = 1
    MAX_IDENTITY_FACTS = 200
    MAX_PREFERENCES = 200
    MAX_DREAMS = 200

    schema_version: int = SCHEMA_VERSION
    identity: list[IdentityFact] = field(default_factory=list)
    likes: list[str] = field(default_factory=list)
    dislikes: list[str] = field(default_factory=list)
    dreams: list[str] = field(default_factory=list)
    knowledge: list[KnowledgeEntry] = field(default_factory=list)
    people: list[dict] = field(default_factory=list)
    places: list[dict] = field(default_factory=list)
    projects: list[dict] = field(default_factory=list)
    entity_count: int = 0
    relation_count: int = 0
    interaction_count: int = 0

    def _cap_list(self, lst, max_size):
        if len(lst) > max_size:
            return lst[-max_size:]
        return lst

    def merge_identity(self, new_facts: list[IdentityFact]):
        existing = {(f.category.lower(), f.fact.lower()): f for f in self.identity}
        for f in new_facts:
            key = (f.category.lower(), f.fact.lower())
            if key in existing and not f.timestamp:
                f.timestamp = existing[key].timestamp
            existing[key] = f
        self.identity = self._cap_list(list(existing.values()), self.MAX_IDENTITY_FACTS)

    def merge_preferences(self, likes: list[str], dislikes: list[str]):
        current_likes = {l.lower() for l in self.likes}
        current_dislikes = {d.lower() for d in self.dislikes}
        for l in likes:
            key = l.lower()
            if key not in current_likes:
                self.likes.append(l)
                current_likes.add(key)
            if key in current_dislikes:
                self.dislikes = [d for d in self.dislikes if d.lower() != key]
        for d in dislikes:
            key = d.lower()
            if key not in current_dislikes:
                self.dislikes.append(d)
                current_dislikes.add(key)
            if key in current_likes:
                self.likes = [l for l in self.likes if l.lower() != key]
        self.likes = self._cap_list(self.likes, self.MAX_PREFERENCES)
        self.dislikes = self._cap_list(self.dislikes, self.MAX_PREFERENCES)

    MAX_KNOWLEDGE_ENTRIES = 500

    def merge_knowledge(self, new_entries: list[KnowledgeEntry]):
        existing = {(e.topic.lower(), e.fact.lower()): e for e in self.knowledge}
        for e in new_entries:
            key = (e.topic.lower(), e.fact.lower())
            if key in existing and not e.timestamp:
                e.timestamp = existing[key].timestamp
            existing[key] = e
        merged = list(existing.values())
        # Keep most recent entries if over cap
        if len(merged) > self.MAX_KNOWLEDGE_ENTRIES:
            merged.sort(key=lambda x: x.timestamp, reverse=True)
            merged = merged[:self.MAX_KNOWLEDGE_ENTRIES]
        self.knowledge = merged

    def add_dream(self, dream: str):
        if dream not in self.dreams:
            self.dreams.append(dream)
        self.dreams = self._cap_list(self.dreams, self.MAX_DREAMS)

    def add_entity(self, name: str, confidence: float, date_str: str):
        self.people.append({"name": name, "confidence": confidence, "last_seen": date_str})

    def load_from_file(self, path: Path, folder: str):
        if not path.exists():
            return
        try:
            content = path.read_text(encoding="utf-8")
            self._parse_file(content, folder)
        except Exception as e:
            logger.info("[MemoryState] load %s: %s", folder, e)

    @staticmethod
    def _parse_date(line: str, default: str = "") -> str:
        if "—" in line:
            after = line.rsplit("—", 1)[1].strip()
            if after and not after.startswith("_") and not after.startswith("(confidence"):
                return after
        return default

    def _parse_file(self, content: str, folder: str):
        if folder == "identity":
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("- [") and "]" in line:
                    end = line.index("]")
                    cat = line[3:end].strip()
                    rest = line[end + 1:].strip()
                    ts = self._parse_date(rest)
                    fact = rest.split("—")[0].strip() if "—" in rest else rest
                    self.identity.append(IdentityFact(fact=fact, category=cat, timestamp=ts))
        elif folder == "preferences":
            section = None
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("## Likes"):
                    section = "likes"
                elif line.startswith("## Dislikes"):
                    section = "dislikes"
                elif line.startswith("- ") and section:
                    item = line[2:].strip()
                    if "—" in item:
                        item = item.split("—")[0].strip()
                    if section == "likes":
                        pref_likes = [l for l in self.likes if l.lower() != item.lower()]
                        self.likes = pref_likes + [item]
                    else:
                        pref_dislikes = [d for d in self.dislikes if d.lower() != item.lower()]
                        self.dislikes = pref_dislikes + [item]
        elif folder == "knowledge":
            seen = {(e.topic.lower(), e.fact.lower()) for e in self.knowledge}
            loaded = 0
            for line in content.splitlines():
                if loaded >= self.MAX_KNOWLEDGE_ENTRIES:
                    break
                line = line.strip()
                if line.startswith("- **") and "**" in line:
                    topic = line.split("**")[1].strip()
                    rest = line.split("**", 2)[-1].strip()
                    ts = self._parse_date(rest)
                    content_after_topic = rest.lstrip("— ").strip()
                    if "—" in content_after_topic:
                        fact = content_after_topic.split("—")[0].strip()
                    else:
                        fact = content_after_topic
                    key = (topic.lower(), fact.lower())
                    if key in seen:
                        continue
                    seen.add(key)
                    self.knowledge.append(KnowledgeEntry(topic=topic, fact=fact, timestamp=ts if ts and ts != fact else ""))
                    loaded += 1
        elif folder == "dreams":
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("- ") and "—" in line:
                    parts = line[2:].split("—", 1)
                    dream = parts[0].strip()
                    ts = parts[1].strip() if len(parts) > 1 else ""
                    if dream and ts:
                        self.dreams.append(dream)
        elif folder in ("people", "places", "projects"):
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("- **") and "**" in line:
                    name = line.split("**")[1].strip()
                    rest = line[len(line.split("**")[0]) + len(name) + 4:].strip()
                    confidence = 0.5
                    date = ""
                    if "confidence:" in rest.lower():
                        m = re.search(r"confidence:\s*([0-9.]+)", rest.lower())
                        if m:
                            confidence = float(m.group(1))
                    if "last seen" in rest.lower():
                        dm = re.search(r"last seen ([0-9-]+)", rest.lower())
                        if dm:
                            date = dm.group(1)
                    self._add_to_folder(folder, name, confidence, date)

    def _add_to_folder(self, folder: str, name: str, confidence: float, date: str):
        entry = {"name": name, "confidence": confidence, "last_seen": date}
        target = getattr(self, folder, None)
        if target is not None and not any(e["name"].lower() == name.lower() for e in target):
            target.append(entry)

    def load_statistics_from_file(self, path: Path):
        if not path.exists():
            return
        try:
            content = path.read_text(encoding="utf-8")
            m_conv = re.search(r"total_conversations:\s*(\d+)", content)
            if m_conv:
                self.interaction_count = int(m_conv.group(1))
            m_ent = re.search(r"total_entities:\s*(\d+)", content)
            if m_ent:
                self.entity_count = int(m_ent.group(1))
            m_rel = re.search(r"total_relations:\s*(\d+)", content)
            if m_rel:
                self.relation_count = int(m_rel.group(1))
        except Exception as e:
            logger.debug("[MemoryState] load statistics: %s", e)
