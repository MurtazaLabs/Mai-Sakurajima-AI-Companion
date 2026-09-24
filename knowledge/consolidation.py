import difflib
import logging
import re

logger = logging.getLogger(__name__)

NOISE_WORDS = frozenset({
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "with",
    "and", "or", "is", "are", "was", "were", "this", "that",
})


class ConsolidationEngine:

    def normalize_name(self, name):
        name = str(name).strip().lower()
        name = re.sub(r"\s+", " ", name)
        parts = [p for p in name.split() if p not in NOISE_WORDS]
        return " ".join(parts) if parts else name

    def merge_candidates(self, entities):
        if not entities:
            return []
        normalized = [(e, self.normalize_name(e)) for e in entities]
        groups = []
        assigned = set()
        for i, (orig, norm) in enumerate(normalized):
            if i in assigned:
                continue
            group = [orig]
            assigned.add(i)
            for j in range(i + 1, len(normalized)):
                if j in assigned:
                    continue
                other_norm = normalized[j][1]
                score = difflib.SequenceMatcher(None, norm, other_norm).ratio()
                if score >= 0.8:
                    group.append(normalized[j][0])
                    assigned.add(j)
            groups.append(group)
        return groups

    def deduplicate(self, graph, entities, relations):
        if not entities and not relations:
            return [], []

        existing_names = {e.name for e in graph.all_entities()}
        norm_to_existing = {}
        for ename in existing_names:
            norm_to_existing[self.normalize_name(ename)] = ename

        deduped_entities = []
        name_map = {}

        for ent in entities:
            if not isinstance(ent, dict):
                continue
            raw_name = ent.get("name", "").strip()
            if not raw_name or len(raw_name) < 2:
                continue
            norm = self.normalize_name(raw_name)
            if norm in norm_to_existing:
                name_map[raw_name.lower()] = norm_to_existing[norm]
            else:
                canonical = raw_name
                name_map[raw_name.lower()] = canonical
                norm_to_existing[norm] = canonical
                deduped_entities.append(ent)

        deduped_relations = []
        for rel in relations:
            if not isinstance(rel, dict):
                continue
            src = rel.get("source", "").strip().lower()
            tgt = rel.get("target", "").strip().lower()
            mapped_src = name_map.get(src, src)
            mapped_tgt = name_map.get(tgt, tgt)
            if mapped_src == mapped_tgt:
                continue
            deduped_relations.append({
                "source": mapped_src,
                "relation": rel.get("relation", "related_to"),
                "target": mapped_tgt,
                "confidence": rel.get("confidence", 0.5),
            })

        return deduped_entities, deduped_relations
