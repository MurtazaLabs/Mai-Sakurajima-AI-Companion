import logging
import threading
from pathlib import Path

from knowledge.graph_exporter import GraphExporter
from knowledge.memory_writer import MemoryWriter
from knowledge.state_dumper import StateDumper

logger = logging.getLogger(__name__)

from config.paths import OBSIDIAN_VAULT


class ObsidianWriter:

    def __init__(self, graph_manager=None, vault_path=None, subdir="graph", user_id: str | None = None):
        vault = Path(vault_path or OBSIDIAN_VAULT)
        if user_id:
            vault = vault / "users" / user_id
        self.vault_root = vault
        self.user_id = user_id
        self.graph = graph_manager
        self._graph_exporter = GraphExporter(graph_manager=graph_manager, vault_path=vault, subdir=subdir)
        self._state_dumper = StateDumper(vault_root=vault)
        self._memory_writer = MemoryWriter(vault_root=vault)
        self._lock = threading.RLock()

    @property
    def entity_dir(self):
        return self._graph_exporter.entity_dir

    def sync(self):
        if not self.graph:
            return {"written": 0, "deleted": 0, "total": 0, "path": str(self.entity_dir)}
        with self._lock:
            return self._graph_exporter.sync()

    def write_entity(self, entity):
        self._graph_exporter.write_entity(entity)

    def export_graph(self, graph_dir, graph_manager=None):
        return self._graph_exporter.export_graph(graph_dir, graph_manager=graph_manager or self.graph)

    # Memory write delegation
    def write(self, folder, user, ai, tags, emotion, score, metadata=None, entity_names=None):
        return self._memory_writer.write(folder, user, ai, tags, emotion, score, metadata, entity_names=entity_names)

    def write_memory(self, routes, user, ai, tags, emotion, score, metadata=None, entity_names=None):
        return self._memory_writer.write_memory(routes, user, ai, tags, emotion, score, metadata, entity_names=entity_names)

    def write_important(self, text, tags=None, emotion=None, score=0.9):
        return self._memory_writer.write_important(text, tags, emotion, score)

    def write_reflection(self, reflection):
        return self._memory_writer.write_reflection(reflection)

    def archive(self, text):
        return self._memory_writer.archive(text)

    # State dump delegation
    def dump(self, state, date_str):
        self._state_dumper.dump(state, date_str)

    def write_relationship(self, relationship_state):
        self._state_dumper.write_relationship(relationship_state)

    def write_statistics(self, total_conversations=0, total_messages=0,
                         total_memories=0, total_reflections=0,
                         first_met=None, total_days=0,
                         total_entities=0, total_relations=0):
        return self._state_dumper.write_statistics(
            total_conversations, total_messages, total_memories, total_reflections,
            first_met, total_days, total_entities, total_relations,
        )

    @property
    def hash_cache(self):
        return self._memory_writer.hash_cache

    def clear_cache(self):
        self._memory_writer.clear_cache()

    def stats(self):
        with self._lock:
            mem_stats = self._memory_writer.stats()
            return {
                "vault": str(self.vault_root),
                "entity_dir": str(self._graph_exporter.entity_dir),
                "cached_hashes": mem_stats["cached_hashes"],
                "memory_writes": mem_stats["memory_writes"],
            }
