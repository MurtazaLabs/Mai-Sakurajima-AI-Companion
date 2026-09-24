import json
import logging
import re
import time
from pathlib import Path
from memory.schema import MemoryObject
from memory.state import MemoryState

logger = logging.getLogger(__name__)

# Confidence assigned to replayed (historical) memories so they rank below
# freshly observed ones but still surface in recall.
REPLAY_CONFIDENCE = 0.6
REPLAY_IMPORTANCE = 0.6


def load_vault_into_memory(reader, memory_manager, vector_store, memory_hierarchy,
                           knowledge_graph=None):
    """Replay persisted Obsidian vault data into the in-memory stores at boot.

    The vault is the system's durable memory layer. On a fresh boot the
    MemoryHierarchy and VectorStore start empty, so the memory/graph OS pages
    show nothing and recall cannot use prior context. This loader reads the
    vault (conversation notes + structured MemoryState files) and re-populates
    the in-memory stores so history survives restarts.

    Deduplication:
      - VectorStore.add() keys on an md5 of the text, so identical entries are
        naturally skipped.
      - MemoryHierarchy stores are keyed by fact/trait key, so repeats merge.

    Returns a dict summary of what was loaded.
    """
    if reader is None:
        return {"loaded": 0, "skipped": True}

    summary = {"conversations": 0, "semantic": 0, "autobiographical": 0,
               "entities": 0, "relations": 0, "errors": 0}

    # ── 1. Conversation history ──────────────────────────────────────────
    try:
        entries = reader.load_memories()
    except Exception as e:
        logger.error("[VAULT LOADER] load_memories failed: %s", e)
        entries = []

    for entry in entries:
        user = (entry.get("user") or "").strip()
        ai = (entry.get("ai") or "").strip()
        if not user:
            continue
        try:
            ts = _parse_ts(entry.get("timestamp"))
            importance = float(entry.get("importance") or REPLAY_IMPORTANCE)
            tags = entry.get("tags") or []
            emotion = {"type": entry.get("emotion") or "neutral",
                       "intensity": float(entry.get("intensity") or 0.5)}

            # Vector store (md5 key → dedupe)
            if vector_store is not None:
                combined = f"\nUSER:\n{user}\n\nAI:\n{ai}\n"
                vector_store.add(
                    text=combined,
                    metadata={
                        "tags": tags,
                        "emotion": emotion,
                        "timestamp": ts,
                        "importance": importance,
                        "speaker": "User",
                        "memory_type": "conversation",
                    },
                )

            # Memory hierarchy (classified by content)
            if memory_hierarchy is not None:
                obj = MemoryObject(
                    content=user,
                    memory_type="conversation",
                    confidence=REPLAY_CONFIDENCE,
                    importance=importance,
                    timestamp=ts,
                    metadata={"tags": tags, "emotion": emotion, "ai": ai},
                )
                memory_hierarchy.store_from_memory_object(obj, source="vault_replay")
            summary["conversations"] += 1
        except Exception as e:
            summary["errors"] += 1
            logger.debug("[VAULT LOADER] conversation replay error: %s", e)

    # ── 2. Structured MemoryState files ─────────────────────────────────
    try:
        state = MemoryState()
        vault = reader.vault_root
        for folder, filename in [
            ("identity", "user.md"),
            ("preferences", "preferences.md"),
            ("knowledge", "knowledge.md"),
            ("dreams", "dreams.md"),
        ]:
            state.load_from_file(vault / folder / filename, folder)
    except Exception as e:
        logger.error("[VAULT LOADER] structured state load failed: %s", e)
        state = None

    if state is not None and memory_hierarchy is not None:
        for fact in state.identity:
            try:
                memory_hierarchy.store_autobiographical(
                    fact.fact[:40].strip().lower(),
                    fact.fact,
                    confidence=REPLAY_CONFIDENCE,
                    importance=0.8,
                )
                summary["autobiographical"] += 1
            except Exception as e:
                logger.warning("[VaultLoader] Failed to store autobiographical memory: %.40s: %s", fact.fact, e)
                summary["errors"] += 1

        for entry in state.knowledge:
            try:
                fact_key = f"{entry.topic}: {entry.fact}"[:60].strip().lower()
                memory_hierarchy.store_semantic(
                    fact_key,
                    f"{entry.topic}: {entry.fact}",
                    confidence=REPLAY_CONFIDENCE,
                    tags=[entry.topic],
                    source="vault",
                )
                summary["semantic"] += 1
            except Exception as e:
                logger.warning("[VaultLoader] Failed to store semantic memory: %s: %.40s: %s", entry.topic, entry.fact, e)
                summary["errors"] += 1

    # ── 3. KnowledgeGraph reconstruction from vault entity notes ─────────
    if knowledge_graph is not None and reader is not None:
        try:
            ents, rels = _reconstruct_graph(reader, knowledge_graph)
            summary["entities"] = ents
            summary["relations"] = rels
        except Exception as e:
            logger.error("[VAULT LOADER] graph reconstruction failed: %s", e)
            summary["errors"] += 1

    # ── 4. Entity links from conversation entries ─────────────────────────
    if knowledge_graph is not None:
        try:
            entity_links_count = _load_entity_links_from_conversations(entries, knowledge_graph)
            summary["entity_links"] = entity_links_count
        except Exception as e:
            logger.error("[VAULT LOADER] entity links from conversations failed: %s", e)
            summary["errors"] += 1

    total = summary["conversations"] + summary["semantic"] + summary["autobiographical"]
    summary["loaded"] = total
    logger.info(
        "[VAULT LOADER] replayed %s memories "
        "(conversations=%s, "
        "semantic=%s, "
        "autobiographical=%s, "
        "entities=%s, "
        "relations=%s, "
        "errors=%s)",
        total, summary['conversations'],
        summary['semantic'], summary['autobiographical'],
        summary['entities'], summary['relations'],
        summary['errors']
    )
    return summary


def _reconstruct_graph(reader, knowledge_graph):
    """Replay persisted `graph/graph.json` + `graph/relations.md` into the
    in-memory KnowledgeGraph at boot.

    ``graph.json`` is the canonical entity list (written by
    ``GraphExporter.export_graph()``).
    ``relations.md`` contains relation lines of the form::

        - Source → relation → [[Target]]

    Returns ``(entity_count, relation_count)``.
    """
    vault = Path(reader.vault_root) if hasattr(reader, "vault_root") else Path(".")
    graph_dir = vault / "graph"
    entity_count = 0
    relation_count = 0

    graph_json_path = graph_dir / "graph.json"
    if graph_json_path.exists():
        try:
            data = json.loads(graph_json_path.read_text(encoding="utf-8"))
            for item in data if isinstance(data, list) else data.get("entities", []):
                name = (item.get("name") or "").strip()
                etype = item.get("type", "unknown")
                if name:
                    knowledge_graph.add_entity(name, entity_type=etype)
                    entity_count += 1
        except Exception as e:
            logger.warning("[VAULT LOADER] graph.json parse error: %s", e)

    relations_path = graph_dir / "relations.md"
    if relations_path.exists():
        try:
            content = relations_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                m = re.match(r"-\s+(.+?)\s+→\s+(.+?)\s+→\s+\[\[(.+?)\]\]", line)
                if m:
                    source = m.group(1).strip()
                    rel_type = m.group(2).strip().lower()
                    target = m.group(3).strip().lower()
                    knowledge_graph.add_relation(source, rel_type, target)
                    relation_count += 1
        except Exception as e:
            logger.warning("[VAULT LOADER] relations.md parse error: %s", e)

    logger.info(
        "[VAULT LOADER] graph reconstruction: %s entities, %s relations",
        entity_count, relation_count
    )
    return entity_count, relation_count


def verify_consistency(reader, vector_store, knowledge_graph, memory_hierarchy):
    """Compare vault content against in-memory stores and log discrepancies.

    This is an advisory check — it does *not* block boot or repair data.
    Returns a dict of consistency metrics.
    """
    result = {"vault_entries": 0, "vector_entries": 0,
              "graph_entities": 0, "hierarchy_entries": 0,
              "ok": True, "warnings": []}
    if reader is not None:
        try:
            memories = reader.load_memories()
            result["vault_entries"] = len(memories)
        except Exception as e:
            result["warnings"].append(f"vault read failed: {e}")
    if vector_store is not None:
        try:
            result["vector_entries"] = vector_store.count()
        except Exception as e:
            result["warnings"].append(f"vector_store count failed: {e}")
    if knowledge_graph is not None:
        try:
            result["graph_entities"] = len(knowledge_graph._entities)
        except Exception as e:
            result["warnings"].append(f"graph count failed: {e}")
    if memory_hierarchy is not None:
        try:
            s = memory_hierarchy.semantic
            st = memory_hierarchy.episodic
            lt = memory_hierarchy.autobiographical
            result["hierarchy_entries"] = len(s) + len(st) + len(lt)
        except Exception as e:
            result["warnings"].append(f"hierarchy count failed: {e}")
    if result["warnings"]:
        result["ok"] = False
        for w in result["warnings"]:
            logger.warning("[VAULT CONSISTENCY] %s", w)
    else:
        logger.info(
            "[VAULT CONSISTENCY] vault=%s vector=%s graph=%s hierarchy=%s — OK",
            result['vault_entries'], result['vector_entries'],
            result['graph_entities'], result['hierarchy_entries']
        )
    return result


def _load_entity_links_from_conversations(entries, knowledge_graph):
    entity_links_count = 0
    seen = set()
    for entry in entries:
        links = entry.get("entity_links") or []
        user = entry.get("user", "")
        for link in links:
            key = (user, link)
            if key in seen:
                continue
            seen.add(key)
            clean = link.strip()
            if not clean:
                continue
            if knowledge_graph.get_entity(clean) is None:
                knowledge_graph.add_entity(clean, entity_type="entity_from_link",
                                           metadata={"source": "conversation_link"})
                entity_links_count += 1
            knowledge_graph.add_relation(user or "user", "mentioned_in", clean,
                                         weight=0.5, metadata={"source": "conversation_link"})
    logger.info("[VAULT LOADER] loaded %d entity links from conversation files", entity_links_count)
    return entity_links_count


def _parse_ts(value):
    if not value:
        return time.time()
    if isinstance(value, (int, float)):
        return float(value)
    try:
        # "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return time.mktime(time.strptime(value, fmt))
            except ValueError:
                continue
    except Exception as e:
        logger.warning("Unexpected error parsing timestamp: %s", e)
    return time.time()
