"""VaultJanitor — one-time graph hygiene sweep.

Removes low-quality entity pollution left by the rule-based extractor fallback
(e.g. ``siad``, ``pormise``, ``messing``). These entities were stored at
confidence 0.2 (lowercase tokens) / 0.3 (capitalized tokens) with ``type:
unknown`` and were never meaningful graph notes.

The sweep operates in two layers:

1. **In-memory graph** — remove junk entities from the KnowledgeGraph so the
   next ``GraphExporter.sync()`` stops re-writing their note files.
2. **Vault files** — optionally delete orphan ``graph/*.md`` notes that are
   stopwords / single-character / nested-junk with no matching entity.

`dry_run=True` is the default so operators can preview before touching data.

Note: the runtime guard in ``GraphManager.process_conversation`` prevents new
junk from entering after this sweep; this module only cleans history.
"""

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

# Tokens that should never be graph entities regardless of capitalization.
JUNK_TOKENS = frozenset({
    "siad", "said", "poromising", "pormise", "promise", "messing", "ohh",
    "yeah", "yep", "yeeeeessssss", "wont", "wouldnt", "thats", "oh", "ah",
    "hmm", "lol", "lmao", "omg", "wow", "okay", "okok", "heh", "eh", "uh",
    "umm", "huh", "ha", "ya", "gonna", "wanna", "gotta", "lemme", "k",
    "bi", "lots", "lotz", "thx", "ty", "woah", "whoa", "cmon", "cmonn",
})

_STOPWORD_RE = re.compile(r"\b(?:i|me|my|we|you|your|us|it|its|this|that|the|a|an|and|but|or|to|of|in|is|are|was|were|be|been|have|has|had|do|does|did|not|no|yes|so|then|now|just|really|very|actually|like|love|want|would|could|should)\b")

# Two-letter tokens that are never entities (kept separate from the
# uppercase-acronym preservation rule in ``_is_junk_name``).
_SHORT_STOPWORD_RE = re.compile(r"\b(?:go|no|ok|hi|he|she|we|my|me|us|is|am|do|if|as|on|up|an|by|be|at|to|of|in|it|so)\b")


class VaultJanitor:
    """Sweep junk entities out of the graph and remove orphan junk notes."""

    def __init__(self, graph=None, vault_root=None):
        self.graph = graph
        self.vault_root = Path(vault_root) if vault_root else None
        if self.graph is None:
            from knowledge.graph import KnowledgeGraph
            self.graph = KnowledgeGraph()

    # ── classification ──

    @staticmethod
    def _is_junk_name(name):
        """True for stopword / typo / junk entity names.

        Single characters are never entities. Two-letter names are only junk
        when they match a known junk token or a short stopword — otherwise
        they are preserved (``AI``/``ai``, ``JS``, ``ML`` are legitimate and
        the graph normalizes them to lowercase, so casing cannot distinguish
        an acronym here).
        """
        n = str(name or "").strip().lower()
        if not n:
            return True
        if len(n) == 1:
            return True
        if len(n) == 2:
            return bool(n in JUNK_TOKENS or _SHORT_STOPWORD_RE.search(f" {n} "))
        if n in JUNK_TOKENS:
            return True
        stripped = re.sub(r"[\W_]+", "", n)
        if len(stripped) == 0:
            return True
        if _STOPWORD_RE.search(f" {n} "):
            return True
        return False

    def _low_conf_unknown(self, entity):
        """True when entity is an unknown-typed node with junk confidence."""
        etype = str(getattr(entity, "type", "") or "").lower()
        if etype != "unknown":
            return False
        meta = getattr(entity, "metadata", {}) or {}
        confidence = meta.get("confidence", 0.5)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.0
        return confidence < 0.25

    # ── operations ──

    def find_junk_entities(self):
        """List entities that should be removed from the graph."""
        junk = []
        for ent in self.graph.all_entities():
            name = getattr(ent, "name", "")
            if self._is_junk_name(name) or self._low_conf_unknown(ent):
                junk.append(ent)
        return junk

    def sweep_entities(self, dry_run=True):
        """Remove junk entities from the in-memory graph."""
        in_memory = self.find_junk_entities()
        removed = []
        if not dry_run:
            for ent in in_memory:
                try:
                    if self.graph.remove_entity(ent.name):
                        removed.append(ent.name)
                except Exception as e:
                    logger.warning("[VaultJanitor] remove %s: %s", ent.name, e)
        else:
            removed = [e.name for e in in_memory]
        return {"removed": len(removed), "dry_run": dry_run, "names": removed[:100]}

    def sweep_note_files(self, dry_run=True):
        """Delete orphan junk notes from ``graph/`` that have no living entity."""
        if not self.vault_root:
            return {"removed": 0, "dry_run": dry_run, "error": "no vault_root"}
        graph_dir = self.vault_root / "graph"
        if not graph_dir.is_dir():
            return {"removed": 0, "dry_run": dry_run}
        living_by_lower = {
            getattr(e, "name", "").strip().lower(): e
            for e in self.graph.all_entities()
        }
        removed = []
        for fpath in sorted(graph_dir.glob("*.md")):
            name = fpath.stem
            stem = name.lower()
            if stem in ("entities", "relations"):
                continue
            if stem.startswith("mem-"):
                continue  # raw memory nodes are legitimate
            live_ent = living_by_lower.get(stem)
            if live_ent is not None and not self._is_junk_name(getattr(live_ent, "name", "")):
                continue  # legitimate living entity note (e.g. AI.md) is protected
            if self._is_junk_name(name):
                if not dry_run:
                    try:
                        fpath.unlink()
                    except Exception as e:
                        logger.warning("[VaultJanitor] unlink %s: %s", fpath, e)
                removed.append(fpath.name)
                continue
        return {"removed": len(removed), "dry_run": dry_run, "files": removed[:100]}

    def sweep(self, dry_run=True):
        """Run full sweep (graph entities + orphan notes)."""
        graph_result = self.sweep_entities(dry_run=dry_run)
        files_result = self.sweep_note_files(dry_run=dry_run)
        return {
            "entities": graph_result,
            "note_files": files_result,
            "dry_run": dry_run,
        }