import time
import logging

logger = logging.getLogger(__name__)


class GraphReasoning:

    def __init__(self, graph_manager=None):
        self.graph_manager = graph_manager

    @property
    def _graph(self):
        if not self.graph_manager:
            return None
        g = self.graph_manager.graph if hasattr(self.graph_manager, 'graph') else None
        if g is not None and hasattr(g, 'query'):
            return g
        if hasattr(self.graph_manager, 'query'):
            return self.graph_manager
        # Support KnowledgeGraph which has get_entity_by_type but not query
        if hasattr(self.graph_manager, 'get_entity_by_type'):
            return self.graph_manager
        return None

    def neighbors(self, entity, depth=1):
        g = self._graph
        if not g:
            return []
        try:
            relations = g.query(entity, depth=depth)
            seen = set()
            results = []
            for rel in relations:
                for name in (rel.source, rel.target):
                    if name != entity.lower() and name not in seen:
                        seen.add(name)
                        ent = g.get_entity(name)
                        results.append({
                            "name": name,
                            "type": ent.type if ent else "unknown",
                            "relation": rel.relation,
                            "weight": rel.weight,
                        })
            return results
        except Exception as e:
            logger.warning("[GraphReasoning] neighbors error: %s", e)
            return []

    def shortest_path(self, source, target):
        g = self._graph
        if not g:
            return []
        source = source.lower().strip()
        target = target.lower().strip()
        if source == target:
            return [source]
        try:
            visited = {source}
            queue = [[source]]
            while queue:
                path = queue.pop(0)
                current = path[-1]
                relations = g.query(current, depth=1)
                for rel in relations:
                    neighbor = rel.target if rel.source == current else rel.source
                    if neighbor == target:
                        return path + [neighbor]
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(path + [neighbor])
            return []
        except Exception as e:
            logger.warning("[GraphReasoning] shortest_path error: %s", e)
            return []

    def query_by_type(self, entity_type):
        g = self._graph
        if not g:
            return []
        try:
            entities = g.get_entity_by_type(entity_type)
            return [{"name": e.name, "type": e.type} for e in entities]
        except Exception as e:
            logger.warning("[GraphReasoning] query_by_type error: %s", e)
            return []

    def recent_entities(self, minutes=60):
        g = self._graph
        if not g:
            return []
        try:
            cutoff = time.time() - (minutes * 60)
            all_ents = g.all_entities()
            recent = []
            for e in all_ents:
                created = getattr(e, 'created_at', 0)
                if created >= cutoff:
                    recent.append({"name": e.name, "type": e.type, "created_at": created})
            return sorted(recent, key=lambda x: x["created_at"], reverse=True)
        except Exception as e:
            logger.warning("[GraphReasoning] recent_entities error: %s", e)
            return []

    def what_connects(self, source, target):
        g = self._graph
        if not g:
            return []
        path = self.shortest_path(source, target)
        if not path:
            return []
        edges = []
        for i in range(len(path) - 1):
            relations = g.query(path[i], depth=1)
            for rel in relations:
                r_src = rel.source.lower()
                r_tgt = rel.target.lower()
                if r_src == path[i].lower() and r_tgt == path[i + 1].lower():
                    edges.append(f"{rel.source} --[{rel.relation}]--> {rel.target}")
                    break
                elif r_tgt == path[i].lower() and r_src == path[i + 1].lower():
                    edges.append(f"{rel.target} --[{rel.relation}]--> {rel.source}")
                    break
        return edges

    def answer(self, query):
        q = query.lower().strip()
        if not q:
            return "Please provide a query."

        if q.startswith("what ") and "connect" in q:
            parts = q.replace("what connects", "").replace("?", "").strip()
            tokens = [t.strip() for t in parts.split("and") if t.strip()]
            if len(tokens) >= 2:
                edges = self.what_connects(tokens[0], tokens[-1])
                if edges:
                    return "Connection: " + " → ".join(edges)
                return f"No connection found between '{tokens[0]}' and '{tokens[-1]}'."

        if q.startswith("what ") and ("related" in q or "neighbor" in q):
            target = q.replace("what", "").replace("is related to", "").replace("are the neighbors of", "").replace("?", "").strip()
            if target:
                nbrs = self.neighbors(target, depth=1)
                if nbrs:
                    lines = [f"{n['name']} ({n['type']}) — via {n['relation']}" for n in nbrs]
                    return f"Entities related to '{target}':\n" + "\n".join(lines)
                return f"No related entities found for '{target}'."

        if q.startswith("what ") and "type" in q:
            etype = q.replace("what", "").replace("type", "").replace("are the", "").replace("is", "").replace("?", "").strip()
            if etype:
                ents = self.query_by_type(etype)
                if ents:
                    names = [e["name"] for e in ents]
                    return f"Entities of type '{etype}': {', '.join(names)}"
                return f"No entities of type '{etype}' found."

        if q.startswith("path ") or q.startswith("shortest path "):
            parts = q.replace("shortest path", "").replace("path", "").replace("from", "").replace("to", "").replace("?", "").strip()
            tokens = [t.strip() for t in parts.split() if t.strip()]
            if len(tokens) >= 2:
                path = self.shortest_path(tokens[0], tokens[-1])
                if path:
                    return f"Path: {' → '.join(path)}"
                return f"No path between '{tokens[0]}' and '{tokens[-1]}'."

        return "Try: 'what connects X and Y', 'what is related to X', 'path from X to Y'."

    def format_context(self, query, max_items=5):
        g = self._graph
        if not g:
            return ""
        try:
            nbrs = self.neighbors(query, depth=1)
            if not nbrs:
                return ""
            lines = [f"[graph] {n['name']} ({n['type']}) — {n['relation']}" for n in nbrs[:max_items]]
            return "\n".join(lines)
        except Exception as e:
            logger.warning("[Reasoning] format_context: %s", e)
            return ""
