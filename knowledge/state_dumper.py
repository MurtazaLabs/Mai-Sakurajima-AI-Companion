import time
import threading
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class StateDumper:
    def __init__(self, vault_root):
        self.vault_root = Path(vault_root)
        self._lock = threading.RLock()

    def dump(self, state, date_str):
        if not self.vault_root:
            return
        from memory.state import MemoryState
        self._dump_identity(state, date_str)
        self._dump_preferences(state, date_str)
        self._dump_knowledge(state, date_str)
        self._dump_dreams(state, date_str)
        self._dump_entities("people", state.people, date_str)
        self._dump_entities("places", state.places, date_str)
        self._dump_entities("projects", state.projects, date_str)
        self._dump_statistics(state, date_str)
        logger.info("[StateDumper] dump complete — %d identity, %d likes, %d dislikes, "
                     "%d dreams, %d knowledge, %d people, %d places, "
                     "%d projects",
                     len(state.identity), len(state.likes), len(state.dislikes),
                     len(state.dreams), len(state.knowledge), len(state.people),
                     len(state.places), len(state.projects))

    def _dump_identity(self, state, date_str):
        if not state.identity:
            return
        path = self.vault_root / "identity" / "user.md"
        lines = ["# User Identity", ""]
        for f in state.identity:
            ts = f.timestamp if f.timestamp else date_str
            lines.append(f"- [{f.category}] {f.fact} — {ts}")
        lines.append("")
        lines.append(f"_Updated: {date_str}_")
        with self._lock:
            try:
                path.write_text("\n".join(lines), encoding="utf-8")
            except Exception as e:
                logger.error("[StateDumper] dump identity: %s", e)

    def _dump_preferences(self, state, date_str):
        if not state.likes and not state.dislikes:
            return
        path = self.vault_root / "preferences" / "preferences.md"
        lines = ["# Preferences", ""]
        lines.append("## Likes")
        lines.append("")
        for item in state.likes:
            lines.append(f"- {item} — {date_str}")
        lines.append("")
        lines.append("## Dislikes")
        lines.append("")
        for item in state.dislikes:
            lines.append(f"- {item} — {date_str}")
        lines.append("")
        lines.append(f"_Updated: {date_str}_")
        with self._lock:
            try:
                path.write_text("\n".join(lines), encoding="utf-8")
            except Exception as e:
                logger.error("[StateDumper] dump preferences: %s", e)

    def _dump_knowledge(self, state, date_str):
        path = self.vault_root / "knowledge" / "knowledge.md"
        if not state.knowledge:
            with self._lock:
                try:
                    path.write_text(f"# Knowledge\n\n_Updated: {date_str}_\n", encoding="utf-8")
                except Exception as e:
                    logger.error("[StateDumper] dump knowledge: %s", e)
            return
        entries = state.knowledge
        seen = {}
        for e in entries:
            key = (e.topic.lower().strip(), e.fact.lower().strip())
            seen[key] = e
        entries = list(seen.values())
        if len(entries) > 500:
            entries = sorted(entries, key=lambda x: x.timestamp, reverse=True)[:500]
        lines = ["# Knowledge", ""]
        for e in entries:
            ts = e.timestamp if e.timestamp else date_str
            lines.append(f"- **{e.topic}** — {e.fact} — {ts}")
        lines.append("")
        lines.append(f"_Updated: {date_str}_")
        with self._lock:
            try:
                path.write_text("\n".join(lines), encoding="utf-8")
            except Exception as e:
                logger.error("[StateDumper] dump knowledge: %s", e)

    def _dump_dreams(self, state, date_str):
        if not state.dreams:
            return
        path = self.vault_root / "dreams" / "dreams.md"
        lines = ["# Dreams", ""]
        for d in state.dreams:
            lines.append(f"- {d} — {date_str}")
        lines.append("")
        lines.append(f"_Updated: {date_str}_")
        with self._lock:
            try:
                path.write_text("\n".join(lines), encoding="utf-8")
            except Exception as e:
                logger.error("[StateDumper] dump dreams: %s", e)

    def _dump_entities(self, folder, entities, date_str):
        if not entities:
            return
        filename = {"people": "people.md", "places": "places.md", "projects": "projects.md"}.get(folder, f"{folder}.md")
        path = self.vault_root / folder / filename
        incoming = {}
        for ent in entities:
            name = ent.get("name", "").strip()
            if not name:
                continue
            incoming[name.lower()] = ent
        existing_lines = []
        existing_names = set()
        if path.exists():
            try:
                for line in path.read_text(encoding="utf-8").splitlines():
                    if line.startswith("- **") and "**" in line:
                        name = line.split("**")[1].strip().lower()
                        if name in incoming or name in existing_names:
                            continue
                        existing_names.add(name)
                        existing_lines.append(line)
                    elif not line.startswith("#") and "_Updated:" not in line:
                        existing_lines.append(line)
            except Exception as e:
                logger.warning("[StateDumper] dedup read error: %s", e)
        lines = [f"# {folder.capitalize()}", ""]
        for line in existing_lines:
            if line.strip():
                lines.append(line)
        for ent in incoming.values():
            name = ent.get("name", "").strip()
            confidence = ent.get("confidence", 0.5)
            last_seen = ent.get("last_seen") or date_str
            lines.append(f"- **{name}** (confidence: {confidence:.2f}) — last seen {last_seen}")
        lines.append("")
        lines.append(f"_Updated: {date_str}_")
        with self._lock:
            try:
                path.write_text("\n".join(lines), encoding="utf-8")
            except Exception as e:
                logger.error("[StateDumper] dump %s: %s", folder, e)

    def _vault_first_met(self, date_str):
        """Derive first meeting date from the earliest conversation file.

        Prefers the date embedded in the conversation filename (YYYY-MM-DD.md);
        falls back to scanning timestamps inside file frontmatter. If no
        conversation is found, returns ``date_str``.
        """
        conv_dir = self.vault_root / "conversation"
        if not conv_dir.is_dir():
            return date_str
        import re
        candidates = []
        try:
            for fpath in conv_dir.glob("*.md"):
                stem_date = re.match(r"(\d{4}-\d{2}-\d{2})", fpath.stem)
                if stem_date:
                    candidates.append(stem_date.group(1))
                    continue
                try:
                    head = fpath.read_text(encoding="utf-8", errors="replace")[:400]
                    m = re.search(r"t?imestamp:\s*(\d{4}-\d{2}-\d{2})", head)
                    if m:
                        candidates.append(m.group(1))
                except Exception as e:
                    logger.debug("[StateDumper] read file failed in first-talk scan: %s", e)
                    continue
        except Exception as e:
            logger.warning("[StateDumper] vault first-talk scan: %s", e)
        if not candidates:
            return date_str
        return min(candidates)

    def _vault_conversation_turns(self):
        """Count actual user turns persisted in ``conversation/*.md``."""
        conv_dir = self.vault_root / "conversation"
        if not conv_dir.is_dir():
            return 0
        count = 0
        try:
            for fpath in conv_dir.glob("*.md"):
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                except Exception as e:
                    logger.debug("[StateDumper] read file failed in conversation count: %s", e)
                    continue
                count += content.count("### 👤 User")
        except Exception as e:
            logger.warning("[StateDumper] conversation count scan: %s", e)
        return count

    def _stats_metrics(self, state, date_str):
        """Compute honest stats: first_met / days / conversation totals.

        ``total_conversations`` is derived from actual persisted turns rather
        than the inflated relationship interaction counter, so the metrics
        reflect the real vault instead of runtime/test-run noise.
        """
        now = datetime.now()
        real_turns = self._vault_conversation_turns()
        total_conversations = real_turns if real_turns > 0 else state.interaction_count
        total_messages = total_conversations * 2 if total_conversations > 0 else 0
        first_met = self._vault_first_met(date_str)
        try:
            first_dt = datetime.strptime(first_met, "%Y-%m-%d")
            days_together = max(1, (now.date() - first_dt.date()).days + 1)
        except Exception as e:
            logger.debug("[StateDumper] first_met parse failed: %s", e)
            days_together = 1
        return {
            "now": now,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "first_met": first_met,
            "days_together": days_together,
            "last_interaction": now.strftime("%Y-%m-%d"),
        }

    def _dump_statistics(self, state, date_str):
        now = datetime.now()
        m = self._stats_metrics(state, date_str)
        entry = f"""
---
last_updated: {now.strftime("%Y-%m-%d %H:%M:%S")}
total_conversations: {m['total_conversations']}
total_messages: {m['total_messages']}
total_memories: {state.entity_count}
total_reflections: 0
total_entities: {state.entity_count}
total_relations: {state.relation_count}
first_met: {m['first_met']}
last_interaction: {m['last_interaction']}
days_together: {m['days_together']}
---

# 📊 Session Statistics

| Metric | Value |
|--------|-------|
| Total Conversations | {m['total_conversations']} |
| Total Messages | {m['total_messages']} |
| Total Memories Stored | {state.entity_count} |
| Total Reflections | 0 |
| Total Entities | {state.entity_count} |
| Total Relations | {state.relation_count} |
| First Met | {m['first_met']} |
| Last Interaction | {m['last_interaction']} |
| Days Together | {m['days_together']} |
"""
        path = self.vault_root / "statistics" / "stats.md"
        with self._lock:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(entry.strip())
            except Exception as e:
                logger.error("[StateDumper] dump statistics: %s", e)

    def write_relationship(self, relationship_state):
        try:
            now = int(getattr(relationship_state, "last_interaction_unix", 0)) or int(time.time())
            now_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
            content = f"""
Closeness: {relationship_state.closeness:.2f}
Trust: {relationship_state.trust:.2f}
Interactions: {relationship_state.interactions}
LastInteraction: {now_str}
LastInteractionUnix: {now}
"""
            path = self.vault_root / "relationship" / "relationship.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            with self._lock:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(content.strip())
        except Exception as e:
            logger.error("[StateDumper] write_relationship: %s", e)

    def write_statistics(self, total_conversations=0, total_messages=0,
                         total_memories=0, total_reflections=0,
                         first_met=None, total_days=0,
                         total_entities=0, total_relations=0):
        try:
            now = datetime.now()
            entry = f"""
---
last_updated: {now.strftime("%Y-%m-%d %H:%M:%S")}
total_conversations: {total_conversations}
total_messages: {total_messages}
total_memories: {total_memories}
total_reflections: {total_reflections}
total_entities: {total_entities}
total_relations: {total_relations}
first_met: {first_met or now.strftime("%Y-%m-%d")}
last_interaction: {now.strftime("%Y-%m-%d")}
days_together: {total_days or 1}
---

# 📊 Session Statistics

| Metric | Value |
|--------|-------|
| Total Conversations | {total_conversations} |
| Total Messages | {total_messages} |
| Total Memories Stored | {total_memories} |
| Total Reflections | {total_reflections} |
| Total Entities | {total_entities} |
| Total Relations | {total_relations} |
| First Met | {first_met or now.strftime("%Y-%m-%d")} |
| Last Interaction | {now.strftime("%Y-%m-%d")} |
| Days Together | {total_days or 1} |
"""
            path = self.vault_root / "statistics" / "stats.md"
            with self._lock:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(entry.strip())
            return True
        except Exception as e:
            logger.error("[StateDumper] statistics write error: %s", e)
            return False
