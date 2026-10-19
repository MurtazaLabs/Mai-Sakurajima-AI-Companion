import hashlib
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

from knowledge.link_integrity import LinkIntegrity

logger = logging.getLogger(__name__)

# Windows caps a full path at MAX_PATH (260 chars). An entity note filename is
# the sanitized entity name, so a name that came from a whole memory dump
# produces a path the OS refuses. Truncation keeps the note writable; the
# digest keeps two long names that share a prefix from colliding.
MAX_NAME_STEM = 80


def sanitize_entity_stem(name):
    """Filename stem for an entity note.

    Single source of truth: the graph exporter writes ``<stem>.md`` and the
    memory writer resolves ``[[links]]`` against the same name, so the two must
    never drift.
    """
    raw = (name or "").strip().lower().replace(" ", "_")
    safe = "".join(c for c in raw if c.isalnum() or c in ("_", "-"))
    if len(safe) > MAX_NAME_STEM:
        # Keep a readable prefix, then disambiguate on the *full* name so two
        # long names sharing a prefix stay distinct files.
        digest = hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest()[:8]
        safe = f"{safe[:MAX_NAME_STEM]}_{digest}"
    return safe or "unnamed"


class GraphExporter:
    def __init__(self, graph_manager=None, vault_path=None, subdir="graph"):
        from config.paths import OBSIDIAN_VAULT
        self.graph = graph_manager
        vault = Path(vault_path or OBSIDIAN_VAULT)
        self.entity_dir = (vault / subdir) if subdir else vault
        self.entity_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._write_count = 0
        self._delete_count = 0

    def sync(self):
        if not self.graph:
            return {"written": 0, "deleted": 0, "total": 0, "path": str(self.entity_dir)}
        with self._lock:
            self._write_count = 0
            self._delete_count = 0
        all_entities = self.graph.all_entities()
        # Filter out memory-type entities (raw memory nodes with no semantic content)
        all_entities = [e for e in all_entities if getattr(e, "type", "") != "memory"]
        current = set()
        failed = 0
        for entity in all_entities:
            # One unwritable entity must not abort the whole export: a single
            # bad name used to raise out of sync() and silently zero out every
            # other entity note.
            try:
                self.write_entity(entity)
                current.add(self._sanitize(entity.name))
            except Exception as e:
                failed += 1
                logger.warning("[GraphExporter] entity note failed for %r: %s",
                               str(getattr(entity, "name", ""))[:80], e)
        self._delete_stale(current)
        stats = {
            "written": self._write_count,
            "deleted": self._delete_count,
            "total": len(all_entities),
            "failed": failed,
            "path": str(self.entity_dir),
        }
        try:
            integrity = LinkIntegrity(self.entity_dir.parent)
            report = integrity.report(dry_run=True)
            if report["broken_entity_links"]:
                logger.warning("[GraphExporter] %d broken wiki-links detected after sync",
                               report["broken_entity_links"])
            stats["broken_links"] = report["broken_entity_links"]
        except Exception as e:
            logger.debug("[GraphExporter] link integrity check: %s", e)
        logger.info("[GraphExporter] graph sync: %s", stats)
        return stats

    def write_entity(self, entity):
        content = self._build_content(entity)
        filename = self._sanitize(entity.name) + ".md"
        filepath = self.entity_dir / filename
        filepath.write_text(content, encoding="utf-8")
        with self._lock:
            self._write_count += 1

    def _build_content(self, entity):
        lines = []
        lines.append("---")
        lines.append(f'type: "{entity.type}"')
        created = getattr(entity, "created_at", time.time())
        created_str = datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S") if isinstance(created, (int, float)) else str(created)
        lines.append(f"created_at: {created_str}")
        metadata = getattr(entity, "metadata", {}) or {}
        for k, v in metadata.items():
            if isinstance(v, str):
                lines.append(f'{k}: "{v}"')
            else:
                lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append("")
        lines.append(f"# {entity.name}")
        lines.append("")
        related = self.graph.get_relations_for(entity.name) if self.graph and hasattr(self.graph, "get_relations_for") else []
        if related:
            lines.append("## Relations")
            lines.append("")
            for rel in related:
                if rel.source == rel.target:
                    continue
                if rel.source == entity.name:
                    lines.append(f"- {rel.relation} → [[{rel.target}]]")
                else:
                    lines.append(f"- [[{rel.source}]] → {rel.relation}")
            lines.append("")
        backlinks = self._find_backlinks(entity.name)
        if backlinks:
            lines.append("## Referenced By")
            lines.append("")
            for name in sorted(backlinks):
                lines.append(f"- [[{name}]]")
            lines.append("")
        return "\n".join(lines)

    def _find_backlinks(self, entity_name):
        if not self.graph:
            return set()
        backlinks = set()
        all_entities = self.graph.all_entities()
        for ent in all_entities:
            if ent.name == entity_name:
                continue
            rels = self.graph.get_relations_for(ent.name) if hasattr(self.graph, "get_relations_for") else []
            for rel in rels:
                if rel.target == entity_name or rel.source == entity_name:
                    backlinks.add(ent.name)
        return backlinks

    def _delete_stale(self, current_names):
        for fpath in self.entity_dir.iterdir():
            if fpath.suffix != ".md":
                continue
            stem = fpath.stem.lower()
            if stem not in current_names:
                try:
                    fpath.unlink()
                    with self._lock:
                        self._delete_count += 1
                except Exception as e:
                    logger.warning("[GraphExporter] failed to delete %s: %s", fpath, e)

    def _sanitize(self, name):
        return sanitize_entity_stem(name)

    def export_graph(self, graph_dir, graph_manager=None):
        graph_dir = Path(graph_dir)
        graph_dir.mkdir(parents=True, exist_ok=True)
        graph = graph_manager or self.graph
        if not graph:
            return {"written": 0, "path": str(graph_dir)}
        written = 0
        try:
            all_entities = graph.all_entities()
            # Filter out memory-type entities (raw memory nodes with no semantic content)
            all_entities = [e for e in all_entities if getattr(e, "type", "") != "memory"]
        except Exception as e:
            logger.warning("[GraphExporter] all_entities failed: %s", e)
            all_entities = []
        ent_lines = ["# Entities", ""]
        for ent in all_entities:
            ent_lines.append(f"- **{ent.name}** (`{getattr(ent, 'type', 'unknown')}`)")
        (graph_dir / "entities.md").write_text("\n".join(ent_lines), encoding="utf-8")
        written += 1
        rel_lines = ["# Relations", ""]
        try:
            for ent in all_entities:
                rels = graph.get_relations_for(ent.name) if hasattr(graph, "get_relations_for") else []
                for r in rels:
                    if r.source == ent.name:
                        rel_lines.append(f"- {r.source} → {r.relation} → [[{r.target}]]")
        except Exception as e:
            logger.warning("[GraphExporter] relation dump error: %s", e)
        (graph_dir / "relations.md").write_text("\n".join(rel_lines), encoding="utf-8")
        written += 1
        try:
            data = [{"name": e.name, "type": getattr(e, "type", "unknown")} for e in all_entities]
            (graph_dir / "graph.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
            written += 1
        except Exception as e:
            logger.warning("[GraphExporter] graph.json write error: %s", e)
        sync_result = self.sync()
        return {"written": written, "path": str(graph_dir), "sync": sync_result}
