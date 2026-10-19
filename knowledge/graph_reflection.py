import logging
import time

logger = logging.getLogger(__name__)


class GraphReflection:
    """Analyze knowledge graph structure: cluster detection, isolated entities, relation suggestions.

    Uses BFS for clustering, identifies unconnected entities, and suggests
    cross-cluster relations to bridge disconnected subgraphs.
    """

    def __init__(self, graph):
        self.graph = graph

    def identify_clusters(self):
        all_ents = self.graph.all_entities()
        all_rels = self.graph.all_relations()
        if not all_ents:
            return []
        adj: dict[str, set[str]] = {e.name: set() for e in all_ents}
        for rel in all_rels:
            adj.setdefault(rel.source, set()).add(rel.target)
            adj.setdefault(rel.target, set()).add(rel.source)
        visited = set()
        clusters = []
        for node in adj:
            if node in visited:
                continue
            cluster = []
            queue = [node]
            while queue:
                current = queue.pop(0)
                if current in visited:
                    continue
                visited.add(current)
                cluster.append(current)
                for nbr in adj.get(current, set()):
                    if nbr not in visited:
                        queue.append(nbr)
            clusters.append(cluster)
        clusters.sort(key=len, reverse=True)
        return clusters

    def isolated_entities(self):
        all_rels = self.graph.all_relations()
        connected = set()
        for rel in all_rels:
            connected.add(rel.source)
            connected.add(rel.target)
        return [e for e in self.graph.all_entities() if e.name not in connected]

    def suggest_new_relations(self, max_suggestions=5):
        clusters = self.identify_clusters()
        if len(clusters) < 2:
            return []
        suggestions: list = []
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                for src_name in clusters[i][:3]:
                    for tgt_name in clusters[j][:3]:
                        if len(suggestions) >= max_suggestions:
                            return suggestions
                        existing = self.graph.get_relations_for(src_name)
                        already = any(
                            r.source == tgt_name or r.target == tgt_name
                            for r in existing
                        )
                        if not already:
                            suggestions.append({
                                "source": src_name,
                                "target": tgt_name,
                                "suggested_relation": "related_to",
                                "reason": "bridges two clusters",
                            })
        return suggestions

    def summary(self):
        clusters = self.identify_clusters()
        isolated = self.isolated_entities()
        suggestions = self.suggest_new_relations(max_suggestions=3)
        total = self.graph.entity_count()
        rels = self.graph.relation_count()
        return {
            "total_entities": total,
            "total_relations": rels,
            "clusters": len(clusters),
            "largest_cluster_size": len(clusters[0]) if clusters else 0,
            "isolated_count": len(isolated),
            "suggested_new_relations": len(suggestions),
            "suggestions": suggestions,
        }

    def recent_activity(self, minutes=60):
        cutoff = time.time() - (minutes * 60)
        recent_ents = [
            e for e in self.graph.all_entities()
            if getattr(e, "created_at", 0) >= cutoff
        ]
        recent_rels = [
            r for r in self.graph.all_relations()
            if getattr(r, "created_at", 0) >= cutoff
        ]
        return {
            "recent_entities": len(recent_ents),
            "recent_relations": len(recent_rels),
            "entities": [e.name for e in recent_ents],
            "relations": [
                f"{r.source} --{r.relation}--> {r.target}"
                for r in recent_rels
            ],
        }
