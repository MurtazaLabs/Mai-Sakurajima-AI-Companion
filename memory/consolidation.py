# memory/consolidation.py
import time
import logging
from memory.schema import MemoryObject
from core.utils import compute_text_overlap

logger = logging.getLogger(__name__)

_SIMILARITY_TYPE_GROUPS = {
    "preference": {"preference", "preference_negative"},
    "fact": {"identity", "employment", "location", "fact"},
    "emotional": {"emotional_state"},
    "goal": {"goal"},
    "conversation": {"conversation"},
}


def _type_group(memory_type):
    for group, types in _SIMILARITY_TYPE_GROUPS.items():
        if memory_type in types:
            return group
    return "other"





def consolidate(nodes):
    if not nodes:
        return [], nodes

    groups = {}
    for node in nodes:
        if getattr(node, "consolidated", False) or getattr(node, "archived", False):
            continue
        group = _type_group(getattr(node, "memory_type", "conversation"))
        if group not in groups:
            groups[group] = []
        groups[group].append(node)

    consolidated_entries = []
    remaining = list(nodes)

    for group_name, group_nodes in groups.items():
        if len(group_nodes) < 2:
            continue

        merged = set()
        for i, a in enumerate(group_nodes):
            if id(a) in merged:
                continue
            cluster = [a]
            merged.add(id(a))
            for j, b in enumerate(group_nodes):
                if i == j or id(b) in merged:
                    continue
                a_text = getattr(a, "text", "") or getattr(a, "content", "")
                b_text = getattr(b, "text", "") or getattr(b, "content", "")
                if compute_text_overlap(a_text, b_text) > 0.4:
                    cluster.append(b)
                    merged.add(id(b))

            if len(cluster) >= 2:
                texts = [
                    getattr(n, "text", "") or getattr(n, "content", "")
                    for n in cluster
                ]
                scores_list = []
                for n in cluster:
                    s = getattr(n, "score", None)
                    scores_list.append(s if s is not None else getattr(n, "importance", 0.5))
                avg_score = sum(scores_list) / len(cluster)
                avg_confidence = sum(
                    getattr(n, "confidence", 0.5) for n in cluster
                ) / len(cluster)

                consolidated_entries.append({
                    "cluster": cluster,
                    "summary": texts[0],
                    "score": min(1.0, avg_score + 0.1 * (len(cluster) - 1)),
                    "confidence": avg_confidence,
                    "type": group_name,
                    "source_ids": [getattr(n, "id", "") for n in cluster],
                    "timestamp": time.time(),
                })

                for n in cluster:
                    n.consolidated = True

    new_nodes = []
    for entry in consolidated_entries:

        c_node = MemoryObject(
            content=entry["summary"],
            memory_type="semantic",
            confidence=entry["confidence"],
            importance=entry["score"],
            metadata={
                "consolidated_from": entry["type"],
                "source_ids": entry["source_ids"],
                "cluster_size": len(entry["cluster"]),
            },
        )
        new_nodes.append(c_node)

    return new_nodes, remaining
