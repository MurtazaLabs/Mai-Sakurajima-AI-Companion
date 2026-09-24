"""
MemoryManager — the single gate through which all memories pass.

Architecture direction: MemoryManager delegates to MemoryPipeline (the new,
cleaner path) for all storage operations. The old Memory class is kept as a
backward-compatible fallback.

Migration status (Phase 3 of 3):
- Phase 1: ✅ MemoryPipeline created with extract/validate/consolidation/lifecycle
- Phase 2: ✅ MemoryPipeline.store() added — full store path via optional plugins
- Phase 3: ➡ MemoryManager.pipeline.store() is now the primary write path;
           old Memory.store() is the fallback when no pipeline is configured.
"""
import time
import logging
import threading

from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class MemoryManager:

    def __init__(self, memory, pipeline=None, event_bus=None,
                 tagger=None, emotion_analyzer=None, vector_store=None,
                 obsidian_writer=None, router=None, intelligence=None,
                 graph=None, relationship_updater=None):
        self.memory = memory
        self.pipeline = pipeline
        self.event_bus = event_bus or EventBus()
        self._lock = threading.RLock()

        if self.pipeline is not None:
            self.pipeline.tagger = tagger or self.pipeline.tagger
            self.pipeline.emotion_analyzer = emotion_analyzer or self.pipeline.emotion_analyzer
            self.pipeline.vector_store = vector_store or self.pipeline.vector_store
            self.pipeline.obsidian_writer = obsidian_writer or self.pipeline.obsidian_writer
            self.pipeline.router = router or self.pipeline.router
            self.pipeline.intelligence = intelligence or self.pipeline.intelligence
            self.pipeline.graph = graph or self.pipeline.graph
            self.pipeline.relationship_updater = relationship_updater or self.pipeline.relationship_updater

    def process(self, user_input, response="", speaker="User", skip_relationship=False):
        if not user_input:
            return None

        with self._lock:
            extracted = []
            if self.pipeline:
                extracted = self.pipeline.extract(user_input)
                node = self.pipeline.store(user_input, response, speaker=speaker, skip_relationship=skip_relationship)
            else:
                node = None

            if node is None and self.memory and hasattr(self.memory, "store"):
                node = self.memory.store(user_input, response, speaker=speaker)

            from core.event_specs import MEMORY_EXTRACTED
            from core.mai_message import publish_event
            publish_event(self.event_bus, MEMORY_EXTRACTED, {
                "user_input": user_input,
                "response": response,
                "extracted": [e.to_dict() for e in extracted],
                "node_id": getattr(node, "id", None) if node else None,
                "timestamp": time.time(),
            }, source="memory")

        return node

    def store(self, user, ai, speaker="User", skip_relationship=False, user_id=""):
        with self._lock:
            node = None
            if self.pipeline and hasattr(self.pipeline, "store"):
                node = self.pipeline.store(user, ai, speaker=speaker, skip_relationship=skip_relationship, user_id=user_id)
            if node is None and self.memory and hasattr(self.memory, "store"):
                node = self.memory.store(user, ai, speaker=speaker)
        return node

    def get_context(self, limit=5):
        if self.memory and hasattr(self.memory, "get_context"):
            return self.memory.get_context(limit)
        return []

    def get_structured(self):
        if self.memory and hasattr(self.memory, "get_structured"):
            return self.memory.get_structured()
        return {}

    def recall(self, query, limit=5):
        if self.memory and hasattr(self.memory, "recall"):
            return self.memory.recall(query, limit)
        return ""

    def extract(self, text):
        if self.pipeline:
            return self.pipeline.extract(text)
        return []

    def validate(self, text):
        if self.pipeline:
            return self.pipeline.validate(text)
        return True

    def run_consolidation(self, nodes=None):
        if self.pipeline:
            return self.pipeline.run_consolidation(nodes or [])
        return [], nodes or []

    def run_lifecycle(self, nodes=None):
        if self.pipeline:
            return self.pipeline.run_lifecycle(nodes or [])
        return (nodes or []), [], []

    @classmethod
    def from_memory(cls, memory, pipeline=None, event_bus=None,
                    vector_store=None, **kwargs):
        mgr = cls(memory=memory, pipeline=pipeline, event_bus=event_bus, **kwargs)
        if hasattr(memory, "tagger"):
            mgr.configure_pipeline(tagger=memory.tagger)
        if hasattr(memory, "emotion"):
            mgr.configure_pipeline(emotion_analyzer=memory.emotion)
        if hasattr(memory, "intel"):
            mgr.configure_pipeline(intelligence=memory.intel)
        if hasattr(memory, "writer"):
            mgr.configure_pipeline(obsidian_writer=memory.writer)
        if hasattr(memory, "router"):
            mgr.configure_pipeline(router=memory.router)
        if hasattr(memory, "rel_updater"):
            mgr.configure_pipeline(relationship_updater=memory.rel_updater)
        if vector_store is not None:
            mgr.configure_pipeline(vector_store=vector_store)
        return mgr

    def configure_pipeline(self, tagger=None, emotion_analyzer=None,
                            vector_store=None, obsidian_writer=None,
                            router=None, intelligence=None,
                            graph=None, relationship_updater=None,
                            vault_post_processor=None):
        with self._lock:
            if self.pipeline is None:
                return
            need_journal = False
            if tagger is not None:
                self.pipeline.tagger = tagger
            if emotion_analyzer is not None:
                self.pipeline.emotion_analyzer = emotion_analyzer
            if vector_store is not None:
                self.pipeline.vector_store = vector_store
                need_journal = True
            if obsidian_writer is not None:
                self.pipeline.obsidian_writer = obsidian_writer
            if router is not None:
                self.pipeline.router = router
            if intelligence is not None:
                self.pipeline.intelligence = intelligence
            if graph is not None:
                self.pipeline.graph = graph
                need_journal = True
            if relationship_updater is not None:
                self.pipeline.relationship_updater = relationship_updater
            if vault_post_processor is not None:
                self.pipeline.vault_post_processor = vault_post_processor
                need_journal = True
            if need_journal:
                self.pipeline._configure_journal()

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if self.memory and hasattr(self.memory, name):
            return getattr(self.memory, name)
        raise AttributeError(
            f"'MemoryManager' has no attribute '{name}'"
        )
