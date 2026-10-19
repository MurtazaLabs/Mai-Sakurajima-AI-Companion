"""Backfill all conversation entries through the fixed extraction pipelines.

Reads every conversation entry from the Obsidian vault and re-processes it
through the now-fixed pipelines:
  - EntityExtractor: lowercase regex + fallback supplement → KnowledgeGraph
  - VaultPostProcessor: regex-only extraction → identity/preferences/dreams/knowledge

Accumulates state in-memory and writes once for maximum speed.

Usage:
    python scripts/backfill_conversations.py
"""

import logging
import sys
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill")

logging.getLogger("knowledge").setLevel(logging.WARNING)
logging.getLogger("memory").setLevel(logging.WARNING)


def _populate_identity_regex(state, user):
    from memory.state import IdentityFact
    user_lower = (user or "").lower()
    patterns = [
        (r"(?:i\s+)?(?:am|'m)\s+(?:a|an|the)?\s*(.+)", "general"),
        (r"my\s+name\s+(?:is|'s)\s+(.+)", "name"),
        (r"i\s+work\s+(?:as|at)\s+(.+)", "work"),
        (r"i\s+(?:study|studies)\s+(.+)", "study"),
        (r"i\s+live\s+(?:in|at)\s+(.+)", "location"),
        (r"my\s+(?:age|birthday)\s+(?:is|'s)\s+(.+)", "age"),
    ]
    facts = []
    for pattern, category in patterns:
        for m in __import__("re").findall(pattern, user_lower, __import__("re").IGNORECASE):
            fact = m.strip().rstrip(".!,").strip()
            if fact and len(fact) > 2:
                facts.append(IdentityFact(fact=fact, category=category))
    if facts:
        state.merge_identity(facts)


def _populate_preferences_regex(state, user):
    user_lower = (user or "").lower()
    likes = []
    dislikes = []
    like_patterns = [
        r"i\s+(?:like|love|enjoy|adore)\s+(.+)",
        r"(?:my\s+)?favou?rite\s+(?:is|are)\s+(.+)",
        r"i\s+(?:really\s+)?(?:like|love)\s+it\s+when\s+(.+)",
        r"i\s+(?:am\s+)?(?:excited|passionate)\s+about\s+(.+)",
        r"i\s+(?:really\s+)?(?:care|love)\s+about\s+(.+)",
        r"i\s+(?:am\s+)?interested\s+in\s+(.+)",
        r"i\s+(?:am\s+)?fascinated\s+by\s+(.+)",
    ]
    import re as re_mod
    for pat in like_patterns:
        for m in re_mod.findall(pat, user_lower, re_mod.IGNORECASE):
            cleaned = m.strip().rstrip(".!,").strip()
            if cleaned and len(cleaned) > 2:
                likes.append(cleaned)
    dislike_patterns = [
        r"i\s+(?:don't|do\s+not|hate|dislike)\s+(?:like|love)?\s*(.+)",
        r"i\s+hate\s+(.+)",
    ]
    for pat in dislike_patterns:
        for m in re_mod.findall(pat, user_lower, re_mod.IGNORECASE):
            cleaned = m.strip().rstrip(".!,").strip()
            if cleaned and len(cleaned) > 2:
                dislikes.append(cleaned)
    if likes or dislikes:
        state.merge_preferences(likes, dislikes)


def _populate_dreams_regex(state, user):
    user_lower = (user or "").lower()
    if not user_lower:
        return
    import re as re_mod
    patterns = [
        r"(?:i\s+)?(?:wish|dream|hope|aspire|want\s+to|would\s+love\s+to)\s+(.+?)[\.!]",
        r"(?:my\s+)?(?:dream|goal|ambition)\s+(?:is|would\s+be)\s+(.+?)[\.!]",
        r"(?:someday|one\s+day|in\s+the\s+future)\s+(?:i\s+)?(?:want|will|would)\s+(.+?)[\.!]",
    ]
    for pattern in patterns:
        for m in re_mod.findall(pattern, user_lower, re_mod.IGNORECASE):
            cleaned = m.strip().rstrip(".!,").strip()
            if cleaned and len(cleaned) > 5:
                state.add_dream(cleaned)


def _populate_knowledge_regex(state, user, tags):
    from memory.state import KnowledgeEntry
    user_lower = (user or "").lower()
    import re as re_mod
    patterns = [
        r"(?:is|are|was|were)\s+(?:a|an|the|my|our)?\s*(.+)",
        r"(?:works?|studies?|lives?)\s+(?:as|at|in|with)\s+(.+)",
        r"(?:has|have|had)\s+(?:a|an|the|been)\s*(.+)",
    ]
    entries = []
    for pattern in patterns:
        for m in re_mod.findall(pattern, user_lower):
            cleaned = m.strip().rstrip(".!,").strip()
            if len(cleaned) > 5:
                entries.append(KnowledgeEntry(topic="general", fact=cleaned))
    meaningful = {t.lower() for t in (tags or [])} - {"reflection", "archive", "important",
                                                       "conversation", "memory", "chat", "general"}
    for tag in meaningful:
        entries.append(KnowledgeEntry(topic=tag, fact=f"topic mentioned: {tag}"))
    if entries:
        state.merge_knowledge(entries)


def load_existing_state(vault):
    from memory.state import MemoryState
    state = MemoryState()
    for folder, filename in [
        ("identity", "user.md"),
        ("preferences", "preferences.md"),
        ("knowledge", "knowledge.md"),
        ("dreams", "dreams.md"),
        ("people", "people.md"),
        ("places", "places.md"),
        ("projects", "projects.md"),
    ]:
        path = vault / folder / filename
        state.load_from_file(path, folder)
    return state


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    from config.paths import OBSIDIAN_VAULT
    from knowledge.extractor import EntityExtractor
    from knowledge.graph import KnowledgeGraph
    from knowledge.graph_manager import GraphManager
    from knowledge.obsidian_reader import ObsidianReader
    from knowledge.obsidian_writer import ObsidianWriter
    from knowledge.vault_compiler import VaultCompiler

    vault = Path(OBSIDIAN_VAULT)
    logger.info("Vault: %s", vault)

    # ── Components ──
    graph = KnowledgeGraph()
    graph_manager = GraphManager(graph=graph, extractor=EntityExtractor(llm=None))
    writer = ObsidianWriter(vault_path=vault, graph_manager=graph_manager)
    compiler = VaultCompiler(writer)

    # ── Load entries ──
    reader = ObsidianReader(vault_path=vault)
    entries = reader.load_memories()
    logger.info("Loaded %d conversation entries", len(entries))
    if not entries:
        logger.warning("No entries found — nothing to backfill")
        return

    # ── Load existing state once ──
    state = load_existing_state(vault)
    logger.info("Existing state: %d identity, %d likes, %d dreams",
                len(state.identity), len(state.likes), len(state.dreams))

    start = time.time()
    processed = 0
    errors = 0

    for i, entry in enumerate(entries):
        try:
            user = (entry.get("user") or "").strip()
            ai = (entry.get("ai") or "").strip()
            if not user:
                continue
            tags = entry.get("tags", [])

            # Entity extraction → KnowledgeGraph (in-memory, fast)
            graph_manager.process_conversation(user, ai)

            # VPP regex extraction (in-memory, no disk I/O)
            _populate_identity_regex(state, user)
            _populate_preferences_regex(state, user)
            _populate_dreams_regex(state, user)
            _populate_knowledge_regex(state, user, tags)

            processed += 1
            if (i + 1) % 200 == 0:
                el = time.time() - start
                logger.info("  %d/%d (%.0f%%) — %.1f/s",
                            i + 1, len(entries),
                            (i + 1) / len(entries) * 100,
                            (i + 1) / el if el > 0 else 0)
        except Exception as e:
            errors += 1
            logger.warning("Entry %d error: %s", i, e)

    elapsed = time.time() - start

    # ── Write state files once ──
    from datetime import datetime
    date_str = datetime.now().strftime("%Y-%m-%d")
    compiler.compile_state(state, date_str)
    logger.info("State written — %d identity, %d likes, %d dislikes, %d dreams, %d knowledge",
                len(state.identity), len(state.likes), len(state.dislikes),
                len(state.dreams), len(state.knowledge))

    # ── Export graph ──
    sync_result = writer.export_graph(vault / "graph", graph_manager)
    e_count = graph.entity_count()
    r_count = graph.relation_count()

    logger.info("Sync: %s", sync_result)
    logger.info("KnowledgeGraph: %d entities, %d relations", e_count, r_count)
    logger.info("Total: %.1fs (%.0f ms/entry)", elapsed,
                (elapsed / processed * 1000) if processed else 0)
    print(f"\nDone — {e_count} entities, {r_count} relations from {processed} conversations")


if __name__ == "__main__":
    main()
