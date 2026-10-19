import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

WIKI_LINK_RE = re.compile(r"\[\[([^\]]+?)\]\]")


class LinkIntegrity:
    """Detect and repair broken wiki-links in the Obsidian vault.

    Scans entity files (``graph/*.md``) and conversation files for ``[[links]]``
    that don't resolve to any existing entity file.  Reports broken links and
    can optionally remove them from entity files.
    """

    def __init__(self, vault_root):
        self.vault_root = Path(vault_root)
        self.entity_dir = self.vault_root / "graph"

    def scan_entity_files(self):
        """Scan all entity files and return broken link details."""
        broken = []
        entities = self._entity_names()
        for fpath in sorted(self.entity_dir.glob("*.md")):
            if fpath.stem == "entities" or fpath.stem == "relations":
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.warning("[LinkIntegrity] read error %s: %s", fpath, e)
                continue
            for match in WIKI_LINK_RE.finditer(content):
                target = match.group(1).strip().lower()
                sanitized = target.replace(" ", "_")
                if sanitized not in entities and target not in entities:
                    if fpath.stem.lower() == sanitized:
                        continue
                    broken.append({
                        "file": str(fpath),
                        "entity": fpath.stem,
                        "link": match.group(1),
                        "line_start": self._find_line(content, match.start()),
                    })
        return broken

    def scan_conversation_links(self):
        """Scan conversation files for entity wiki-links and show resolution status."""
        results = []
        conv_dir = self.vault_root / "conversation"
        entities = self._entity_names()
        for fpath in sorted(conv_dir.glob("*.md")):
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for match in WIKI_LINK_RE.finditer(content):
                target = match.group(1).strip().lower()
                sanitized = target.replace(" ", "_")
                resolved = sanitized in entities or target in entities
                results.append({
                    "file": str(fpath),
                    "link": match.group(1),
                    "resolved": resolved,
                    "line_start": self._find_line(content, match.start()),
                })
        return results

    def remove_broken_links(self, dry_run=True):
        """Remove broken wiki-links from entity files.  Returns list of changes."""
        changes = []
        broken = self.scan_entity_files()
        for b in broken:
            try:
                fpath = Path(b["file"])
                content = fpath.read_text(encoding="utf-8", errors="replace")
                link_str = f"[[{b['link']}]]"
                if link_str not in content:
                    continue
                new_content = content.replace(link_str, b["link"])
                full_line = f"- [[{b['link']}]]"
                if full_line in new_content:
                    new_content = new_content.replace(full_line + "\n", "")
                    new_content = new_content.replace(full_line, "")
                if not dry_run:
                    fpath.write_text(new_content, encoding="utf-8")
                changes.append({
                    "file": b["file"],
                    "link": b["link"],
                    "removed": not dry_run,
                })
            except Exception as e:
                logger.warning("[LinkIntegrity] repair error %s: %s", b["file"], e)
        return changes

    def report(self, dry_run=True):
        """Generate a full integrity report."""
        entity_broken = self.scan_entity_files()
        conv_links = self.scan_conversation_links()
        conv_broken = [c for c in conv_links if not c["resolved"]]
        return {
            "entity_dir": str(self.entity_dir),
            "entity_files": len(list(self.entity_dir.glob("*.md"))),
            "broken_entity_links": len(entity_broken),
            "broken_entity_details": entity_broken[:20],
            "conversation_links_total": len(conv_links),
            "conversation_broken": len(conv_broken),
            "conversation_broken_details": conv_broken[:10],
        }

    def _entity_names(self):
        names = set()
        for fpath in self.entity_dir.glob("*.md"):
            if fpath.stem in ("entities", "relations"):
                continue
            names.add(fpath.stem.lower())
        return names

    @staticmethod
    def _find_line(content, pos):
        return content[:pos].count("\n") + 1
