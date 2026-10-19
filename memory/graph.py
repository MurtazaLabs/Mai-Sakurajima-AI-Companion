# Mai_ai/memory/graph.py
import json
import logging
import threading
import time
from collections import defaultdict

logger = logging.getLogger(__name__)

from memory.node import MemoryNode


class MemoryGraph:

    MAX_NODES = 10000

    def __init__(self, brain_graph=None):

        # 🧠 memory storage
        self.nodes = []

        # 🔗 adjacency graph
        self.edges = defaultdict(set)

        # 🧠 lookup cache
        self.node_index = {}

        # 🧠 similarity threshold
        self.link_threshold = 0.35

        # 🧠 max links per node
        self.max_links = 15

        # 🧠 thread safety
        self.lock = threading.RLock()

        # 🧠 runtime stats
        self.total_links = 0

        # 🧠 brain graph bridge
        self.brain_graph = brain_graph

    # ADD NODE
    def add(self, node):

        if node is None:
            return None

        with self.lock:

            node_id = self._node_id(node)

            # ✅ duplicate prevention
            if node_id in self.node_index:

                existing = self.node_index[node_id]

                # 🔁 reinforce existing memory
                existing.score = min(
                    1.0,
                    getattr(existing, "score", 0.5) + 0.05
                )

                existing.reinforcement_count = (
                    getattr(
                        existing,
                        "reinforcement_count",
                        0
                    ) + 1
                )

                existing.last_accessed = time.time()

                return existing

            # 🧠 safe defaults
            if not hasattr(node, "reinforcement_count"):
                node.reinforcement_count = 0

            if not hasattr(node, "connections"):
                node.connections = []

            self.nodes.append(node)

            self.node_index[node_id] = node

            if len(self.nodes) > self.MAX_NODES:
                self._evict_lowest_score()

        if self.brain_graph:
            self.brain_graph.add_memory_node(
                memory_id=node.id,
                text=getattr(node, "text", ""),
                memory_type=getattr(node, "memory_type", "conversation"),
                score=getattr(node, "score", 0.5),
                tags=getattr(node, "tags", []),
                emotion=getattr(node, "emotion", {}),
                importance=getattr(node, "importance", 0.5),
                source=getattr(node, "source", "user"),
            )

        return node

    def _evict_lowest_score(self):
        excess = len(self.nodes) - self.MAX_NODES
        sorted_nodes = sorted(self.nodes, key=lambda n: getattr(n, "score", 0.0))
        victims = sorted_nodes[:excess]
        for v in victims:
            vid = self._node_id(v)
            self.node_index.pop(vid, None)
            self.edges.pop(vid, None)
            for e in self.edges.values():
                e.discard(vid)
        self.nodes = [n for n in self.nodes if n not in victims]

    # LINK NODES
    def link_nodes(self):

        with self.lock:

            total = len(self.nodes)

            if total < 2:
                return

            # ✅ only compare newest node
            newest = self.nodes[-1]

            newest_id = self._node_id(newest)

            linked = 0

            # compare against recent memories only
            recent_nodes = self.nodes[-100:-1]

            for other in recent_nodes:

                other_id = self._node_id(other)

                if newest is other:
                    continue

                similarity = self._similarity(
                    newest,
                    other
                )

                if similarity < self.link_threshold:
                    continue

                # 🔗 bidirectional edges
                self.edges[newest_id].add(other_id)

                self.edges[other_id].add(newest_id)

                linked += 1

                self.total_links += 1

                # 🧠 optional node-level connections
                if hasattr(newest, "connections"):

                    if other_id not in newest.connections:
                        newest.connections.append(
                            other_id
                        )

                if hasattr(other, "connections"):

                    if newest_id not in other.connections:
                        other.connections.append(
                            newest_id
                        )

                if self.brain_graph and hasattr(newest, "id") and hasattr(other, "id"):
                    self.brain_graph.add_memory_link(
                        newest.id, other.id, weight=similarity
                    )

                # ✅ prevent graph explosion
                if linked >= self.max_links:
                    break

    # SIMILARITY ENGINE
    def _similarity(self, a, b):

        try:

            score = 0.0

            # 🏷️ TAG OVERLAP
            tags_a = set(
                getattr(a, "tags", [])
            )

            tags_b = set(
                getattr(b, "tags", [])
            )

            if tags_a and tags_b:

                overlap = len(
                    tags_a.intersection(tags_b)
                )

                union = len(
                    tags_a.union(tags_b)
                )

                if union > 0:
                    score += (
                        overlap / union
                    ) * 0.5

            # 🧠 MEMORY TYPE
            type_a = getattr(
                a,
                "memory_type",
                ""
            )

            type_b = getattr(
                b,
                "memory_type",
                ""
            )

            if (
                type_a
                and
                type_a == type_b
            ):
                score += 0.2

            # ❤️ EMOTION TYPE
            emo_a = getattr(
                a,
                "emotion",
                {}
            )

            emo_b = getattr(
                b,
                "emotion",
                {}
            )

            if (
                isinstance(emo_a, dict)
                and
                isinstance(emo_b, dict)
            ):

                if (
                    emo_a.get("type")
                    ==
                    emo_b.get("type")
                ):
                    score += 0.2

            # 📝 TEXT OVERLAP
            text_a = set(
                str(
                    getattr(a, "text", "")
                ).lower().split()
            )

            text_b = set(
                str(
                    getattr(b, "text", "")
                ).lower().split()
            )

            if text_a and text_b:

                overlap = len(
                    text_a.intersection(text_b)
                )

                union = len(
                    text_a.union(text_b)
                )

                if union > 0:
                    score += (
                        overlap / union
                    ) * 0.3

            return round(
                min(score, 1.0),
                3
            )

        except Exception as e:
            logger.exception("Graph similarity error: %s", e)
            return 0.0

    # GET CONNECTED MEMORIES
    def connected(self, node):

        with self.lock:

            node_id = self._node_id(node)

            connections = self.edges.get(
                node_id,
                set()
            )

            result = []

            for conn_id in connections:

                memory = self.node_index.get(
                    conn_id
                )

                if memory:
                    result.append(memory)

            return result

    # REMOVE NODE
    def remove(self, node):

        with self.lock:

            node_id = self._node_id(node)

            if node in self.nodes:
                self.nodes.remove(node)

            if node_id in self.node_index:
                del self.node_index[node_id]

            # 🔗 remove graph edges
            if node_id in self.edges:

                connected = self.edges[node_id]

                for other_id in connected:

                    if other_id in self.edges:

                        self.edges[other_id].discard(
                            node_id
                        )

                del self.edges[node_id]

    # MEMORY SEARCH
    def search_by_tag(self, tag):

        with self.lock:

            results = []

            for node in self.nodes:

                tags = getattr(
                    node,
                    "tags",
                    []
                )

                if tag in tags:
                    results.append(node)

            return results

    # SAFE NODE ID
    def _node_id(self, node):

        node_uuid = getattr(
            node,
            "id",
            None
        )

        if node_uuid:
            return str(node_uuid)

        return str(id(node))

    # DEBUG STATS
    def stats(self):

        with self.lock:

            edge_count = sum(
                len(v)
                for v in self.edges.values()
            )

            return {

                "nodes": len(self.nodes),

                "edges": edge_count,

                "indexed_nodes": len(self.node_index),

                "total_links": self.total_links,

                "link_threshold": self.link_threshold,
            }

    # SERIALIZATION

    def save(self, path):

        with self.lock:

            data = {
                "nodes": [
                    n.to_dict() for n in self.nodes
                ],
                "edges": {
                    k: list(v)
                    for k, v in self.edges.items()
                },
                "link_threshold": self.link_threshold,
                "max_links": self.max_links,
                "total_links": self.total_links,
            }

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path):

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        graph = cls()
        graph.link_threshold = data.get(
            "link_threshold", 0.35
        )
        graph.max_links = data.get(
            "max_links", 15
        )
        graph.total_links = data.get(
            "total_links", 0
        )

        for node_data in data.get("nodes", []):
            node = MemoryNode.from_dict(node_data)
            graph.nodes.append(node)
            graph.node_index[
                graph._node_id(node)
            ] = node

        for src_id, targets in data.get(
            "edges", {}
        ).items():
            graph.edges[src_id] = set(targets)

        return graph