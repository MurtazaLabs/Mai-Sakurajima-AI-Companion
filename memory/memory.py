# Mai_ai/memory/memory.py
# >>> UPDATED VERSION — includes MemoryRouter integration <<<
import logging
import os
import threading
import time
from collections import deque

logger = logging.getLogger(__name__)

from app.config_loader import OBSIDIAN_VAULT
from core.event_bus import EventBus
from memory.emotion_analyzer import EmotionAnalyzer
from memory.intelligence import MemoryIntelligence
from memory.relationship_updater import RelationshipUpdater
from memory.router import MemoryRouter
from memory.scoring import MemoryScorer
from memory.tagger import Tagger
from memory.vector_store import VectorStore


class Memory:

    def __init__(
        self,
        vault_path=None,
        event_bus=None,
        obsidian_reader=None,
        obsidian_writer=None,
    ):

        # 🧠 default vault path
        vault_path = vault_path or str(OBSIDIAN_VAULT)

        # 🧠 thread safety
        self._lock = threading.RLock()

        # 🧠 event bus
        self.event_bus = event_bus or EventBus()

        # 🧠 short-term memory
        self.short = deque(maxlen=20)

        # 🧠 obsidian systems
        if obsidian_reader is not None:
            self.reader = obsidian_reader
        else:
            from knowledge.obsidian_reader import ObsidianReader
            self.reader = ObsidianReader(vault_path)

        if obsidian_writer is not None:
            self.writer = obsidian_writer
        else:
            from knowledge.obsidian_writer import ObsidianWriter
            self.writer = ObsidianWriter(vault_path)

        # 🧠 routing system
        self.router = MemoryRouter()

        # 🧠 relationship system
        self.rel_updater = RelationshipUpdater(
            os.path.join(
                vault_path,
                "relationship",
                "relationship.md"
            )
        )

        # 🧠 analyzers
        self.tagger = Tagger()

        self.emotion = EmotionAnalyzer()

        # 🧠 intelligence system
        self.intel = MemoryIntelligence(
            self.tagger,
            self.emotion,
            writer=self.writer,
        )

        # 🧠 vector semantic memory
        self.vector = VectorStore()

        # 🧠 runtime state
        self.current_topic = None

        self.last_user_message = None

    # ==================================================
    # 🧠 STORE MEMORY
    # ==================================================

    def store(self, user, ai, speaker="User"):

        if not user:
            return None

        if not hasattr(self, '_scorer'):
            self._scorer = MemoryScorer()
        if self._scorer.score(user) < 0.3:
            return None

        try:

            # 🏷️ extract tags safely
            tags = self.tagger.extract_tags(user) or []

            # ❤️ analyze emotion safely
            emo = self.emotion.analyze(user) or {
                "type": "neutral",
                "intensity": 0.5
            }

            # 🧠 short-term memory object
            memory_object = {
                "user": user,
                "ai": ai,
                "tags": tags,
                "emotion": emo,
                "timestamp": time.time(),
                "speaker": speaker,
            }

            # 🧠 working memory (thread-safe)
            with self._lock:
                self.short.append(memory_object)

            # ❤️ relationship learning
            self.rel_updater.update(user)

            # 🧠 intelligence pipeline
            node = self.intel.process(user, ai)

            # 🧠 semantic vector memory
            combined = f"""
USER:
{user}

AI:
{ai}
"""

            vector_id = self.vector.add(
                text=combined,
                metadata={
                    "tags": tags,
                    "emotion": emo,
                    "timestamp": time.time(),
                    "importance": getattr(
                        node,
                        "score",
                        0.5
                    ),
                    "speaker": speaker,
                    "memory_type": "conversation",
                }
            )

            if node and vector_id:
                node.vector_id = vector_id

            # ==================================================
            # 🧠 ROUTE MEMORY
            # ==================================================

            route = self.router.route(
                text=user,
                score=getattr(
                    node,
                    "score",
                    0.5
                ),
                tags=tags,
                emotion=emo
            )

            # ==================================================
            # 🧠 WRITE TO OBSIDIAN
            # ==================================================

            self.writer.write_memory(
                routes=route["routes"],
                user=user,
                ai=ai,
                tags=tags,
                emotion=emo,
                score=getattr(
                    node,
                    "score",
                    0.5
                ),
                metadata={
                    "topic": self.current_topic
                }
            )

            # 🧠 runtime updates (thread-safe)
            with self._lock:
                self.last_user_message = user
                if tags:
                    self.current_topic = tags[0]

            # 🧠 publish conversation.finished
            from core.event_specs import CONVERSATION_FINISHED
            from core.mai_message import publish_event
            publish_event(self.event_bus, CONVERSATION_FINISHED, {
                "user_input": user,
                "response": ai,
                "emotion": emo,
                "tags": tags,
                "node_id": getattr(node, "id", None),
                "speaker": speaker,
            }, source="memory")

            return node

        except Exception as e:
            logger.exception("[MEMORY STORE ERROR] %s", e)
            return None

    # ==================================================
    # 🧠 SHORT-TERM CONTEXT
    # ==================================================

    def get_context(self, limit=5):

        recent = list(self.short)[-limit:]

        formatted = []

        for mem in recent:

            formatted.append(
                f"\nUser: {mem['user']}\nMai: {mem['ai']}\n"
            )

        return formatted

    # ==================================================
    # 🧠 HYBRID MEMORY RECALL
    # ==================================================

    def recall(self, query, limit=5):

        if not query:
            return ""

        try:

            # 🏷️ tags
            self.tagger.extract_tags(query) or []

            # 🔍 vector semantic search
            vector_memories = self.vector.search(
                query,
                top_k=limit
            )

            # 🧠 intelligence graph recall
            graph_memories = self.intel.recall(query)

            merged = []

            seen = set()

            # ==================================================
            # 🧠 VECTOR RESULTS
            # ==================================================

            if vector_memories:

                for mem in vector_memories:

                    if isinstance(mem, dict):

                        text = mem.get("text", "")

                    else:

                        text = str(mem)

                    if text and text not in seen:

                        merged.append(text)

                        seen.add(text)

            # ==================================================
            # 🧠 GRAPH RESULTS
            # ==================================================

            if graph_memories:

                if isinstance(graph_memories, dict):

                    text = graph_memories.get(
                        "memory",
                        ""
                    )

                    if text and text not in seen:

                        merged.append(text)

                        seen.add(text)

                    for related in graph_memories.get(
                        "related",
                        []
                    ):

                        if related and related not in seen:

                            merged.append(related)

                            seen.add(related)

                elif isinstance(graph_memories, list):

                    for mem in graph_memories:

                        text = getattr(
                            mem,
                            "text",
                            str(mem)
                        )

                        if text and text not in seen:

                            merged.append(text)

                            seen.add(text)

            # ==================================================
            # ❤️ EMOTIONAL RECALL
            # ==================================================

            emotional = self._emotionally_related(
                query
            )

            for mem in emotional:

                if mem not in seen:

                    merged.append(mem)

                    seen.add(mem)

            # 🛡️ safe return
            if not merged:
                return ""

            merged = merged[:limit]

            return "\n\n".join(merged)

        except Exception as e:
            logger.exception("[MEMORY RECALL ERROR] %s", e)
            return ""

    # ==================================================
    # ❤️ EMOTIONAL RECALL
    # ==================================================

    def _emotionally_related(self, query):

        emotional = []

        query_emo = self.emotion.analyze(query) or {
            "type": "neutral"
        }

        target_type = query_emo.get(
            "type",
            "neutral"
        )

        for mem in self.short:

            mem_type = mem["emotion"].get(
                "type",
                "neutral"
            )

            if mem_type == target_type:

                emotional.append(
                    f"\nUser: {mem['user']}\nMai: {mem['ai']}\n"
                )

        return emotional[:2]

    # ==================================================
    # 🧠 STRUCTURED OBSIDIAN MEMORY
    # ==================================================

    def get_structured(self):

        try:

            data = self.reader.get_all()

            if not isinstance(data, dict):
                logger.warning("[MEMORY WARNING] Structured memory was not a dict. Resetting.")

                return {
                    "relationship": {},
                    "preferences": {},
                    "reflections": {},
                    "system": ""
                }

            data.setdefault(
                "relationship",
                {}
            )

            data.setdefault(
                "preferences",
                {}
            )

            data.setdefault(
                "reflections",
                {}
            )

            data.setdefault(
                "system",
            ""
            )

            if not isinstance(
                data["relationship"],
                dict
            ):
                data["relationship"] = {}

            if not isinstance(
                data["preferences"],
                dict
            ):
                data["preferences"] = {}

            if not isinstance(
                data["reflections"],
                dict
            ):
                data["reflections"] = {}

            if not isinstance(
                data["system"],
                str
            ):
                data["system"] = str(
                    data["system"]
                )

            return data

        except Exception as e:
            logger.exception("[STRUCTURED MEMORY ERROR] %s", e)

            return {
                "relationship": {},
                "preferences": {},
                "reflections": {},
                "system": ""
            }

    # ==================================================
    # 🧠 SESSION STATE
    # ==================================================

    def session_state(self):

        return {
            "short_term_memories": len(self.short),
            "current_topic": self.current_topic,
            "last_user_message": self.last_user_message,
        }

    # ==================================================
    # 📊 MEMORY STATS
    # ==================================================

    def stats(self):

        return {
            "working_memory": len(self.short),
            "graph_nodes": len(
                self.intel.graph.nodes
            ),
            "current_topic": self.current_topic,
        }
