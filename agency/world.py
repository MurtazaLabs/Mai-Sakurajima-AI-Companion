import time
import threading
import logging

logger = logging.getLogger(__name__)

from knowledge.graph import Entity

CATEGORY_PERSON = "person"
CATEGORY_PLACE = "place"
CATEGORY_PROJECT = "project"
CATEGORY_TECHNOLOGY = "technology"
CATEGORY_EVENT = "event"
CATEGORY_SKILL = "skill"
CATEGORY_MEDIA = "media"
CATEGORY_ORGANIZATION = "organization"
CATEGORY_RELATIONSHIP = "relationship"
CATEGORY_INTEREST = "interest"
CATEGORY_CHARACTER = "character"


class WorldModel:

    def __init__(self, event_bus=None, brain_graph=None):
        self._lock = threading.RLock()
        self._entities = {}
        self.event_bus = event_bus
        self.brain_graph = brain_graph

    def add_entity(self, name, category="person", attributes=None):
        if not name:
            return None
        key = name.lower().strip()
        with self._lock:
            if key in self._entities:
                existing = self._entities[key]
                if attributes:
                    existing.attributes.update(attributes)
                existing.updated_at = time.time()
                entity = existing
            else:
                entity = Entity(name, category, attributes=attributes)
                self._entities[key] = entity
        # Bridge: mirror into BrainGraph for graph-wide entity discovery
        if self.brain_graph:
            try:
                self.brain_graph.add_world_entity(name, category=category, attributes=attributes or {})
            except Exception as e:
                logger.warning("[World] BrainGraph mirror failed: %s", e)
        if self.event_bus:
            from core.event_specs import WORLD_ENTITY_ADDED
            from core.mai_message import publish_event
            publish_event(self.event_bus, WORLD_ENTITY_ADDED, entity.to_dict(), source="agency")
        return entity

    def get(self, name):
        key = name.lower().strip()
        with self._lock:
            entity = self._entities.get(key)
        if entity is None and self.brain_graph:
            # Discovery fallback: consult the graph's world entities
            try:
                nodes = self.brain_graph.get_world_entities()
                for n in nodes:
                    if n.name.lower() == key:
                        entity = Entity(
                            n.name,
                            n.entity_type or "person",
                            attributes=dict(n.metadata or {}),
                        )
                        with self._lock:
                            self._entities[key] = entity
                        break
            except Exception as e:
                logger.warning("[World] BrainGraph lookup failed: %s", e)
        return entity

    def relate(self, source, relation, target):
        s_key = source.lower().strip()
        t_key = target.lower().strip()
        with self._lock:
            s = self._entities.get(s_key)
            t = self._entities.get(t_key)
            if not s or not t:
                logger.warning("[World] Cannot relate unknown entities: %s -> %s", source, target)
                return False
            if relation not in s.relations:
                s.relations[relation] = set()
            s.relations[relation].add(t.name)
            s.updated_at = time.time()
        return True

    def query(self, name, relation=None, depth=1):
        key = name.lower().strip()
        with self._lock:
            entity = self._entities.get(key)
            if not entity:
                return []
            results = [entity.to_dict()]
            if depth > 0 and entity.relations:
                for rel, targets in entity.relations.items():
                    if relation and rel != relation:
                        continue
                    for t_name in targets:
                        t = self._entities.get(t_name.lower())
                        if t:
                            results.append({
                                "relation": rel,
                                "entity": t.to_dict(),
                            })
            return results

    def search(self, category=None, attribute_key=None, attribute_value=None):
        results = []
        with self._lock:
            for e in self._entities.values():
                if category and e.category != category:
                    continue
                if attribute_key and attribute_value:
                    val = e.attributes.get(attribute_key)
                    if val is None or attribute_value.lower() not in str(val).lower():
                        continue
                results.append(e.to_dict())
        return results

    def list_categories(self):
        cats = {}
        with self._lock:
            for e in self._entities.values():
                cats[e.category] = cats.get(e.category, 0) + 1
        return cats

    def all_entities(self):
        with self._lock:
            return [e.to_dict() for e in self._entities.values()]

    def stats(self):
        with self._lock:
            return {
                "total_entities": len(self._entities),
                "categories": self.list_categories(),
            }
