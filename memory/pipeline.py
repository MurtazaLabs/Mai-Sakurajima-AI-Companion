import hashlib
import logging
import threading
import time
from collections import deque
from typing import Any

from memory.consolidation import consolidate
from memory.extractor import FastExtractor
from memory.lifecycle import MemoryLifecycle
from memory.schema import MemoryObject

logger = logging.getLogger(__name__)


class MemoryPipeline:

    def __init__(self, fast_extractor=None, lifecycle=None, event_bus=None,
                 tagger=None, emotion_analyzer=None, vector_store=None,
                 obsidian_writer=None, router=None, intelligence=None,
                 graph=None, relationship_updater=None,
                 memory_hierarchy=None, vault_post_processor=None,
                 write_journal=None, experience_store=None):
        self.fast_extractor = fast_extractor or FastExtractor()
        self.lifecycle = lifecycle or MemoryLifecycle()
        self.event_bus = event_bus
        self.tagger = tagger
        self.emotion_analyzer = emotion_analyzer
        self.vector_store = vector_store
        self.obsidian_writer = obsidian_writer
        self.router = router
        self.intelligence = intelligence
        self.graph = graph
        self.relationship_updater = relationship_updater
        self.memory_hierarchy = memory_hierarchy
        self.vault_post_processor = vault_post_processor
        self.experience_store = experience_store
        self.preference_evolution = None
        self._lock = threading.RLock()
        self._journal = write_journal

        if write_journal is not None:
            self._configure_journal()

        self.short: deque[dict[str, Any]] = deque(maxlen=20)
        self.current_topic = None
        self.last_user_message = None

    def _configure_journal(self):
        j = self._journal
        if j is None:
            return
        if self.vector_store is not None:
            vs = self.vector_store
            def _vs_batch(entries):
                for args, kwargs in entries:
                    vs.add(*args, **kwargs)
            j.register("vector_store", _vs_batch)
        else:
            j.register("vector_store", lambda _: None)

        if self.vault_post_processor is not None:
            vpp = self.vault_post_processor
            def _vpp_batch(entries):
                for args, kwargs in entries:
                    vpp.process(*args, **kwargs)
            j.register("vault_post_processor", _vpp_batch)
        else:
            j.register("vault_post_processor", lambda _: None)

        if self.graph is not None:
            g = self.graph
            pipeline_self = self
            def _graph_batch(entries):
                for args, kwargs in entries:
                    user, ai = args[0], args[1]
                    g.process_conversation(user, ai)
                    new_entity_names = pipeline_self._match_entity_names(f"{user} {ai or ''}")
                    added = [n for n in new_entity_names if n not in (kwargs.get("entity_names") or [])]
                    if added and pipeline_self.obsidian_writer:
                        pipeline_self.obsidian_writer._memory_writer.add_entity_links(
                            folder="conversation", user=user, ai=ai, entity_names=added,
                        )
            j.register("knowledge_graph", _graph_batch)
        else:
            j.register("knowledge_graph", lambda _: None)

        if self.memory_hierarchy is not None:
            mh = self.memory_hierarchy
            def _mh_batch(entries):
                for args, kwargs in entries:
                    mh.store_from_memory_object(*args, **kwargs)
            j.register("memory_hierarchy", _mh_batch)

    @property
    def write_journal(self):
        return self._journal

    @write_journal.setter
    def write_journal(self, j):
        self._journal = j
        self._configure_journal()

    def extract(self, text):
        if not text:
            return []
        text = str(text).strip()
        return self.fast_extractor.extract(text)

    def validate(self, text):
        if not text:
            return False
        text = str(text).strip()
        if len(text) < 2:
            return False
        if text.lower() in ("ok", "okay", "yes", "no", "hi", "hello", "hey"):
            return False
        return True

    def store(self, user, ai, speaker="User", skip_relationship=False, user_id=""):
        from core.mai_message import ensure_correlation
        with ensure_correlation("memory"):
            return self._store_impl(
                user, ai, speaker=speaker,
                skip_relationship=skip_relationship, user_id=user_id,
            )

    def _store_impl(self, user, ai, speaker="User", skip_relationship=False, user_id=""):
        if not self.validate(user):
            return None

        self.extract(user)

        # ==================================================
        # Intelligence.process() handles: tag extraction, emotion analysis,
        # scoring, node creation, graph insert, routing, obsidian write,
        # and reflection internally. When available, reuse its results
        # instead of duplicating those operations here.
        # ==================================================
        node = None
        tags: list[str] = []
        emo: dict[str, Any] = {}

        entity_names = self._match_entity_names(f"{user} {ai or ''}")
        if self.intelligence:
            node = self.intelligence.process(user, ai, entity_names=entity_names)
            if node is not None:
                tags = node.tags if isinstance(getattr(node, "tags", None), list) else []
                emo = node.emotion if isinstance(getattr(node, "emotion", None), dict) else {}

        if node is None:
            tags = self.tagger.extract_tags(user) if self.tagger else []
            emo = (self.emotion_analyzer.analyze(user) or
                   {"type": "neutral", "intensity": 0.5}) if self.emotion_analyzer else {}

        obj = MemoryObject(content=user, memory_type="conversation", user_id=user_id)
        if node is None and self.vector_store:
            node = obj
        if tags:
            obj.metadata["tags"] = tags
        if emo:
            obj.metadata["emotion"] = emo
        obj.metadata["speaker"] = speaker

        # M6 · Cheap emotional-experience ingest: record emotionally charged
        # turns on the ExperienceStore for later lazy reflection during dreaming.
        if self.experience_store is not None:
            significance = float(emo.get("intensity", 0.5) or 0.5) if emo else 0.5
            if significance >= 0.6:
                exp = self.experience_store.record_event(
                    event=user[:500],
                    emotion=emo,
                    relationship_impact={"speaker": speaker},
                    significance=significance,
                )
                if self.event_bus is not None and exp is not None:
                    from core.event_specs import EXPERIENCE_RECORDED
                    from core.mai_message import publish_event
                    publish_event(self.event_bus, EXPERIENCE_RECORDED, {
                        "id": exp.id,
                        "significance": exp.significance,
                    }, source="memory")

        # M6 · Evidence-based preference evolution: scan the turn for
        # approval/disapproval phrases against the extracted entities/tags.
        if self.preference_evolution is not None:
            topics = list(entity_names) + list(tags)
            if topics:
                try:
                    self.preference_evolution.scan_turn(user, topics)
                except Exception as e:
                    logger.debug("[MemoryPipeline] preference scan failed: %s", e)

        with self._lock:
            self.short.append({"user": user, "ai": ai, "tags": tags, "emotion": emo,
                               "timestamp": time.time(), "speaker": speaker})

        if self.relationship_updater and not skip_relationship:
            self.relationship_updater.update(user)

        if self.vector_store:
            combined = f"\nUSER:\n{user}\n\nAI:\n{ai}\n"
            vector_id = hashlib.md5(combined.encode()).hexdigest()
            if node:
                node.vector_id = vector_id
            if self._journal:
                meta = {
                    "tags": tags, "emotion": emo, "timestamp": time.time(),
                    "importance": getattr(node, "confidence", 0.5) if node else 0.5,
                    "speaker": speaker, "memory_type": "conversation",
                }
                if user_id:
                    meta["user_id"] = user_id
                self._journal.enqueue("vector_store", combined, metadata=meta)
            else:
                meta = {
                    "tags": tags, "emotion": emo, "timestamp": time.time(),
                    "importance": getattr(node, "confidence", 0.5) if node else 0.5,
                    "speaker": speaker, "memory_type": "conversation",
                }
                if user_id:
                    meta["user_id"] = user_id
                vector_store_id = self.vector_store.add(text=combined, metadata=meta)
                if node and vector_store_id:
                    node.vector_id = vector_store_id

        # Router and obsidian writer are handled inside intelligence.process()
        # when intelligence is available. Only invoke them when it is not.
        if self.intelligence is None or node is None:
            route = {}
            if self.router:
                route = self.router.route(
                    text=user,
                    score=0.5,
                    tags=tags,
                    emotion=emo,
                )

            if self.obsidian_writer:
                self.obsidian_writer.write_memory(
                    routes=route.get("routes") if route else [],
                    user=user,
                    ai=ai,
                    tags=tags,
                    emotion=emo,
                    score=0.5,
                    metadata={"topic": self.current_topic},
                )

        if self._journal:
            if self.vault_post_processor:
                self._journal.enqueue("vault_post_processor", user, ai, tags, emo)
            if self.graph:
                self._journal.enqueue("knowledge_graph", user, ai, entity_names=entity_names)
            if self.memory_hierarchy:
                self._journal.enqueue("memory_hierarchy", obj)
        else:
            if self.vault_post_processor:
                try:
                    self.vault_post_processor.process(user, ai, tags, emo)
                except Exception as e:
                    logger.error("[VAULT POST PROCESSOR ERROR] %s", e)

            if self.graph:
                try:
                    self.graph.process_conversation(user, ai)
                    new_entity_names = self._match_entity_names(f"{user} {ai or ''}")
                    added = [n for n in new_entity_names if n not in entity_names]
                    if added and self.obsidian_writer:
                        self.obsidian_writer._memory_writer.add_entity_links(
                            folder="conversation",
                            user=user,
                            ai=ai,
                            entity_names=added,
                        )
                        entity_names.extend(added)
                except Exception as e:
                    logger.error("[GRAPH PROCESS ERROR] %s", e)

            if self.memory_hierarchy:
                try:
                    self.memory_hierarchy.store_from_memory_object(obj)
                except Exception as e:
                    logger.debug("[MEMORY HIERARCHY ERROR] %s", e)

        with self._lock:
            self.current_topic = tags[0] if tags else self.current_topic
            self.last_user_message = user

        if self.event_bus:
            from core.event_specs import CONVERSATION_FINISHED
            from core.mai_message import publish_event
            publish_event(self.event_bus, CONVERSATION_FINISHED, {
                "user_input": user,
                "response": ai,
                "emotion": emo,
                "tags": tags,
                "node_id": getattr(node, "id", None) if node else None,
            }, source="memory")

        return node

    def process(self, user_input, response=None, existing_pipeline=None):
        from core.mai_message import ensure_correlation
        with ensure_correlation("memory"):
            return self._process_impl(
                user_input, response=response, existing_pipeline=existing_pipeline,
            )

    def _process_impl(self, user_input, response=None, existing_pipeline=None):
        if not self.validate(user_input):
            return None

        event_data = {
            "user_input": user_input,
            "response": response or "",
            "extracted": [],
            "timestamp": time.time(),
        }

        if self.event_bus:
            from core.event_specs import MEMORY_EXTRACTED
            from core.mai_message import publish_event
            publish_event(self.event_bus, MEMORY_EXTRACTED, event_data, source="memory")

        if existing_pipeline is not None:
            try:
                node = existing_pipeline(user_input, response or "")
                if node:
                    event_data["node_id"] = getattr(node, "id", None)
                    if self.event_bus:
                        from core.event_specs import MEMORY_STORED, STATE_MEMORY_UPDATED
                        from core.mai_message import publish_event
                        publish_event(self.event_bus, MEMORY_STORED, event_data, source="memory")
                        publish_event(self.event_bus, STATE_MEMORY_UPDATED, {
                            "kind": getattr(node, "memory_type", "conversation"),
                            "node_id": event_data.get("node_id"),
                            "consolidated": False,
                        }, source="memory")
                return node
            except Exception as e:
                logger.error("[MemoryPipeline] Pipeline error: %s", e)
                return None

        if self.event_bus:
            from core.event_specs import MEMORY_STORED, STATE_MEMORY_UPDATED
            from core.mai_message import publish_event
            publish_event(self.event_bus, MEMORY_STORED, event_data, source="memory")
            publish_event(self.event_bus, STATE_MEMORY_UPDATED, {
                "kind": "conversation",
                "node_id": None,
                "consolidated": False,
            }, source="memory")

        return event_data

    def run_consolidation(self, nodes):
        if not nodes:
            return [], nodes
        new_nodes, remaining = consolidate(nodes)
        if new_nodes and self.event_bus:
            from core.event_specs import MEMORY_CONSOLIDATED, STATE_MEMORY_UPDATED
            from core.mai_message import publish_event
            publish_event(self.event_bus, MEMORY_CONSOLIDATED, {
                "count": len(new_nodes),
                "source_count": len(nodes),
            }, source="memory")
            publish_event(self.event_bus, STATE_MEMORY_UPDATED, {
                "kind": "consolidated",
                "consolidated": True,
                "merged": len(new_nodes),
            }, source="memory")
        return new_nodes, remaining

    def _match_entity_names(self, text):
        if not text or not self.graph or not hasattr(self.graph, "graph"):
            return []
        try:
            known = self.graph.graph.all_entities()
            known_map = {e.name.lower(): e.name for e in known}
            words = text.split()
            found = set()
            for w in words:
                clean = w.strip(".,!?;:'\"()[]{}")
                lowered = clean.lower()
                if lowered in known_map:
                    found.add(known_map[lowered])
            return sorted(found)
        except Exception as e:
            logger.debug("[PIPELINE] _match_entity_names: %s", e)
            return []

    def run_lifecycle(self, nodes):
        if not nodes:
            return [], [], []
        active, to_archive, to_delete = self.lifecycle.apply_lifecycle(nodes)
        if to_archive and self.event_bus:
            from core.event_specs import MEMORY_LIFECYCLE
            from core.mai_message import publish_event
            publish_event(self.event_bus, MEMORY_LIFECYCLE, {
                "archived": len(to_archive),
                "deleted": len(to_delete),
            }, source="memory")
        return active, to_archive, to_delete
