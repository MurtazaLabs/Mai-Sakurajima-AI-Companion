# NOTE: P2-16 — consider collapsing BrainGraph/GraphManager/KnowledgeGraph into 2 layers
# knowledge/graph.py
import json
import logging
import threading
import time

from core.utils import TTLCache

logger = logging.getLogger(__name__)


class Entity:

    def __init__(self, name, entity_type="unknown", metadata=None, attributes=None, user_id=""):
        self.name = str(name).strip().lower()
        self.type = str(entity_type).strip().lower()
        self.metadata = dict(attributes or metadata or {})
        self.relations = {}
        self.created_at = time.time()
        self.updated_at = self.created_at
        self.user_id = user_id

    @property
    def category(self):
        return self.type

    @category.setter
    def category(self, value):
        self.type = str(value).strip().lower()

    @property
    def attributes(self):
        return self.metadata

    @attributes.setter
    def attributes(self, value):
        self.metadata = dict(value)

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "category": self.type,
            "metadata": dict(self.metadata),
            "attributes": dict(self.metadata),
            "relations": dict(self.relations),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def __repr__(self):
        return f"<Entity {self.name} ({self.type})>"


class Relation:

    def __init__(self, source, relation, target, weight=1.0, metadata=None, user_id=""):
        self.source = str(source).strip().lower()
        self.relation = str(relation).strip().lower()
        self.target = str(target).strip().lower()
        self.weight = max(0.0, min(1.0, float(weight)))
        self.metadata = dict(metadata or {})
        self.created_at = time.time()
        self.user_id = user_id

    def to_dict(self):
        return {
            "source": self.source,
            "relation": self.relation,
            "target": self.target,
            "weight": self.weight,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    def __repr__(self):
        return (
            f"<Relation "
            f"{self.source} --[{self.relation}]--> {self.target}>"
        )


class KnowledgeGraph:

    def __init__(self):
        self._lock = threading.RLock()
        self._entities = {}
        self._relations = []
        # Query cache for get_entity
        self._entity_cache = TTLCache(maxsize=1024, ttl=300.0)

    def add_entity(self, name, entity_type="unknown", metadata=None, user_id=""):
        name = str(name).strip().lower()
        with self._lock:
            if name not in self._entities:
                self._entities[name] = Entity(
                    name=name,
                    entity_type=entity_type,
                    metadata=metadata,
                    user_id=user_id,
                )
            else:
                if metadata:
                    self._entities[name].metadata.update(metadata)
                # Update user_id if provided
                if user_id:
                    self._entities[name].user_id = user_id
            # Invalidate cache for this entity
            self._entity_cache.set(name, self._entities[name])
            return self._entities[name]

    def get_entity(self, name):
        name = str(name).strip().lower()
        # Check cache first (outside lock for performance)
        cached = self._entity_cache.get(name)
        if cached is not None:
            return cached
        
        with self._lock:
            entity = self._entities.get(name)
            if entity is not None:
                self._entity_cache.set(name, entity)
            return entity

    def add_relation(self, source, relation, target, weight=1.0, metadata=None, user_id=""):
        source = str(source).strip().lower()
        target = str(target).strip().lower()

        with self._lock:
            if source not in self._entities:
                self._entities[source] = Entity(name=source, user_id=user_id)
            if target not in self._entities:
                self._entities[target] = Entity(name=target, user_id=user_id)

            rel = Relation(
                source=source,
                relation=relation,
                target=target,
                weight=weight,
                metadata=metadata,
                user_id=user_id,
            )
            self._relations.append(rel)
            return rel

    def query(self, entity, depth=1, user_id=""):
        entity = str(entity).strip().lower()
        with self._lock:
            visited = {entity}
            results = []
            queue = [(entity, 0)]

            while queue:
                current, d = queue.pop(0)
                if d >= depth:
                    continue

                for rel in self._relations:
                    # Filter by user_id if provided
                    if user_id and rel.user_id != user_id:
                        continue
                    if rel.source == current and rel.target not in visited:
                        results.append(rel)
                        visited.add(rel.target)
                        queue.append((rel.target, d + 1))
                    elif rel.target == current and rel.source not in visited:
                        rev_rel = Relation(
                            source=rel.target,
                            relation=rel.relation,
                            target=rel.source,
                            weight=rel.weight,
                        )
                        results.append(rev_rel)
                        visited.add(rel.source)
                        queue.append((rel.source, d + 1))

            return results

    def get_relations_for(self, entity, user_id=""):
        entity = str(entity).strip().lower()
        with self._lock:
            return [
                rel for rel in self._relations
                if (rel.source == entity or rel.target == entity)
                and (not user_id or rel.user_id == user_id)
            ]

    def all_entities(self):
        with self._lock:
            return list(self._entities.values())

    def all_relations(self):
        with self._lock:
            return list(self._relations)

    def to_dict(self):
        with self._lock:
            return {
                "entities": {
                    name: e.to_dict()
                    for name, e in self._entities.items()
                },
                "relations": [
                    r.to_dict() for r in self._relations
                ],
            }

    def save(self, path):
        with self._lock:
            data = {
                "entities": {
                    name: e.to_dict()
                    for name, e in self._entities.items()
                },
                "relations": [
                    r.to_dict() for r in self._relations
                ],
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        kg = cls()
        for name, e_data in data.get("entities", {}).items():
            kg._entities[name] = Entity(
                name=e_data.get("name", name),
                entity_type=e_data.get("type", "unknown"),
                metadata=e_data.get("metadata", {}),
                user_id=e_data.get("user_id", ""),
            )
            kg._entities[name].created_at = e_data.get("created_at", time.time())

        for r_data in data.get("relations", []):
            kg._relations.append(Relation(
                source=r_data["source"],
                relation=r_data["relation"],
                target=r_data["target"],
                weight=r_data.get("weight", 1.0),
                metadata=r_data.get("metadata", {}),
                user_id=r_data.get("user_id", ""),
            ))

        return kg

    def entity_count(self):
        with self._lock:
            return len(self._entities)

    def relation_count(self):
        with self._lock:
            return len(self._relations)

    def get_entity_by_type(self, entity_type):
        entity_type = str(entity_type).strip().lower()
        with self._lock:
            return [
                e for e in self._entities.values()
                if e.type == entity_type
            ]

    def most_connected(self, limit=10):
        with self._lock:
            degree = {}
            for rel in self._relations:
                degree[rel.source] = degree.get(rel.source, 0) + 1
                degree[rel.target] = degree.get(rel.target, 0) + 1
            sorted_nodes = sorted(
                degree.items(), key=lambda x: x[1], reverse=True
            )
            return sorted_nodes[:limit]

    def stats(self):
        with self._lock:
            total_nodes = len(self._entities)
            total_edges = len(self._relations)
            if total_nodes == 0:
                return {
                    "nodes": 0, "edges": 0, "avg_degree": 0.0,
                    "isolated": 0, "most_connected": [],
                }
            degree = {}
            for rel in self._relations:
                degree[rel.source] = degree.get(rel.source, 0) + 1
                degree[rel.target] = degree.get(rel.target, 0) + 1
            avg_degree = sum(degree.values()) / total_nodes if total_nodes else 0.0
            isolated = sum(1 for e in self._entities if degree.get(e, 0) == 0)
            sorted_nodes = sorted(
                degree.items(), key=lambda x: x[1], reverse=True
            )[:5]
            return {
                "nodes": total_nodes,
                "edges": total_edges,
                "avg_degree": round(avg_degree, 2),
                "isolated": isolated,
                "most_connected": sorted_nodes,
            }

    def remove_entity(self, name):
        name = str(name).strip().lower()
        with self._lock:
            if name not in self._entities:
                return False
            del self._entities[name]
            self._relations = [
                rel for rel in self._relations
                if rel.source != name and rel.target != name
            ]
            # Invalidate cache
            self._entity_cache.clear()
            return True

    def remove_relation(self, source, relation, target):
        source = str(source).strip().lower()
        relation = str(relation).strip().lower()
        target = str(target).strip().lower()
        with self._lock:
            before = len(self._relations)
            self._relations = [
                rel for rel in self._relations
                if not (rel.source == source and rel.relation == relation and rel.target == target)
            ]
            return len(self._relations) < before

    def search(self, query, user_id=""):
        query = str(query).strip().lower()
        if not query:
            return []
        with self._lock:
            return [
                e for name, e in self._entities.items()
                if query in name and (not user_id or e.user_id == user_id)
            ]

    def count_by_type(self):
        with self._lock:
            counts = {}
            for e in self._entities.values():
                t = e.type or "unknown"
                counts[t] = counts.get(t, 0) + 1
            return counts

    def stats_by_type(self):
        with self._lock:
            return {
                "total_nodes": len(self._entities),
                "total_edges": len(self._relations),
                "by_type": self.count_by_type(),
            }

    def search_entities(self, query, node_type=None, user_id=""):
        query = str(query).strip().lower()
        if not query:
            return []
        with self._lock:
            results = []
            for name, e in self._entities.items():
                if node_type and e.type != node_type:
                    continue
                if user_id and e.user_id != user_id:
                    continue
                if query in name or any(query in str(v).lower() for v in e.metadata.values()):
                    results.append(e)
            return results

    def prune_feedback_loop_nodes(self):
        """Remove belief nodes created by the `update_from_graph` feedback loop.
        
        The giveaway pattern: belief nodes whose name contains nested "belief:"
        (e.g. ``belief:architecture:believe:belief:architecture:improves:retrieval``).
        These have no semantic value — they exist only because each belief node
        added a relation that was then re-processed as a new "fact".
        """
        removed = 0
        with self._lock:
            to_remove = []
            for name, ent in self._entities.items():
                if ent.type == "belief" and name.count("belief:") > 1:
                    to_remove.append(name)
            for name in to_remove:
                del self._entities[name]
                self._relations = [
                    r for r in self._relations
                    if r.source != name and r.target != name
                ]
                removed += 1
        return removed

    def remove_entities_by_type(self, entity_type):
        """Remove all entities of a given type and their relations."""
        removed = 0
        with self._lock:
            names = [n for n, e in self._entities.items() if e.type == entity_type]
            for name in names:
                del self._entities[name]
                self._relations = [
                    r for r in self._relations
                    if r.source != name and r.target != name
                ]
                removed += 1
        return removed

    def import_from_memory_graph(self, memory_graph):
        for node in getattr(memory_graph, "nodes", []):
            text = getattr(node, "text", "") or getattr(node, "content", "")
            mem_type = getattr(node, "memory_type", "") or getattr(node, "type", "")
            tags = getattr(node, "tags", [])

            if tags:
                for tag in tags:
                    self.add_entity(tag, entity_type="topic")
                    self.add_relation("memory", "tagged", tag)

            if mem_type in ("identity", "employment", "location"):
                self.add_entity("user", entity_type="person")
                self.add_relation(
                    "user",
                    mem_type,
                    text[:100],
                )
