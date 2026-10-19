# Mai_ai/memory/intelligence.py
import logging
import threading
import time

from memory.scoring import MemoryScorer

logger = logging.getLogger(__name__)
from memory.decay import MemoryDecay
from memory.graph import MemoryGraph
from memory.node import MemoryNode
from memory.recall import RecallEngine
from memory.reflection import MemoryReflectionEngine
from memory.router import MemoryRouter


class MemoryIntelligence:

    def __init__(
        self,
        tagger,
        emotion,
        scorer=None,
        graph=None,
        recall_engine=None,
        router=None,
        writer=None,
        reflector=None,
        decay=None,
    ):

        self.tagger = tagger
        self.emotion = emotion

        self.scorer = scorer if scorer is not None else MemoryScorer()
        self.graph = graph if graph is not None else MemoryGraph()
        self.recall_engine = recall_engine if recall_engine is not None else RecallEngine()
        self.router = router if router is not None else MemoryRouter()
        if writer is not None:
            self.writer = writer
        else:
            from knowledge.obsidian_writer import ObsidianWriter
            self.writer = ObsidianWriter()
        self.reflector = reflector if reflector is not None else MemoryReflectionEngine()
        self.decay = decay if decay is not None else MemoryDecay()

        # 🧠 thread safety
        self.lock = threading.RLock()

        # ⚡ runtime state
        self.working_memory = []  # 🧠 Volatile Short-Term Context Buffer
        self.last_reflection = time.time()

        # 🧠 reflection interval
        self.reflection_interval = 900

        # 🧠 minimum memory threshold
        self.memory_threshold = 0.25

    # 🧠 MAIN MEMORY PIPELINE
    def process(self, user, ai, entity_names=None):

        if not user:
            return None

        user = str(user).strip()
        ai = str(ai or "").strip()

        if not user:
            return None

        with self.lock:

            # 🏷️ TAG EXTRACTION

            try:

                tags = self.tagger.extract_tags(user)

                if not isinstance(tags, list):
                    tags = []

                # ❤️ EMOTION ANALYSIS

                emo = self.emotion.analyze(user)

                if not isinstance(emo, dict):

                    emo = {"type": "neutral", "intensity": 0.5}

                intensity = float(
                    emo.get("intensity", 0.5)
                )

                intensity = max(
                    0.0,
                    min(1.0, intensity)
                )

                # ⭐ MEMORY SCORING

                score = self.scorer.score(
                    text=user,
                    emotion=emo
                )

                try:
                    score = float(score)

                except Exception as e:
                    logger.warning("[Intelligence] Failed to parse scorer output as float: %r | %s", score, e)
                    score = 0.5

                # 🧠 emotional weighting
                score += intensity * 0.15

                score = round(
                    max(0.0, min(score, 1.0)),
                    3
                )

                # 🏛️ ATKINSON-SHIFFRIN WORKING MEMORY BUFFER

                # Every interaction is tracked here dynamically
                # so short-term conversation context is never dropped
                self.working_memory.append({
                    "user": user,
                    "ai": ai,
                    "tags": tags,
                    "emotion": emo,
                    "score": score,
                    "timestamp": time.time()
                })

                if len(self.working_memory) > 10:
                    self.working_memory.pop(0)

                # 🚫 FILTER LOW VALUE MEMORIES FOR LONG-TERM STORAGE

                if score < self.memory_threshold:
                    return None

            except Exception as e:
                logger.error("[PIPELINE: EXTRACTION] %s", e)
                return None

            # 🧠 MEMORY TYPE DETECTION

            try:

                memory_type = self._detect_memory_type(
                    tags,
                    emo,
                    user
                )

                # Fact-update: archive old identity statements
                if memory_type == "identity":
                    stale = [
                        n for n in self.graph.nodes
                        if getattr(n, "memory_type", "") == "identity"
                    ]
                    for old in stale:
                        self.graph.remove(old)
                        old.archived = True

                # 🧠 CREATE MEMORY NODE

                now = time.time()

                node = MemoryNode(
                    text=user,
                    score=score,
                    tags=tags,
                    emotion=emo,
                    memory_type=memory_type,
                    created_at=now,
                    last_accessed=now,
                    emotional_weight=intensity,
                    importance=score,
                )

                # 🔗 INSERT INTO GRAPH

                existing = self.graph.add(node)

            except Exception as e:
                logger.error("[PIPELINE: NODE CREATION] %s", e)
                return None

            # 🧠 only link brand new memories
            if existing == node:

                try:
                    self.graph.link_nodes()

                except Exception as e:
                    logger.error(
                        "[GRAPH LINK ERROR] %s", e
                    )

            # 🧠 CONSOLIDATION

            if (
                len(self.graph.nodes) > 0
                and
                len(self.graph.nodes) % 25 == 0
            ):

                try:

                    consolidated = (
                        self.decay.consolidate(
                            self.graph.nodes
                        )
                    )

                    if consolidated:

                        logger.info(
                            "[MEMORY] Consolidated %s memories",
                            len(consolidated)
                        )

                        for entry in consolidated:
                            try:
                                c_node = MemoryNode(
                                    text=entry.get("summary", ""),
                                    score=entry.get("score", 0.5),
                                    tags=entry.get("tags", []),
                                    memory_type="semantic",
                                    emotional_weight=entry.get(
                                        "emotional_weight", 0.5
                                    ),
                                    importance=entry.get(
                                        "importance", 0.5
                                    ),
                                    source="system",
                                )
                                self.graph.add(c_node)
                            except Exception as e:
                                logger.error(
                                    "[CONSOLIDATED NODE ERROR] %s", e
                                )
                        self.graph.link_nodes()

                except Exception as e:
                    logger.error(
                        "[CONSOLIDATION ERROR] %s", e
                    )

            # 🧭 MEMORY ROUTING

            try:

                routing = self.router.route(
                    user,
                    score,
                    tags,
                    emo
                )

                # ✅ FIXED: router returns dict
                folder = routing.get(
                    "primary",
                    "conversation"
                )

            except Exception as e:

                logger.error(
                    "[ROUTER ERROR] %s", e
                )

                folder = "conversation"

            # 💾 OBSIDIAN WRITE

            try:

                self.writer.write(
                    folder=folder,
                    user=user,
                    ai=ai,
                    tags=tags,
                    emotion=emo,
                    score=score,
                    metadata={
                        "memory_type":
                            memory_type,
                        "reinforcement_count":
                            getattr(
                                node,
                                "reinforcement_count",
                                0
                            )
                    },
                    entity_names=entity_names,
                )

            except Exception as e:
                logger.error(
                    "[OBSIDIAN WRITE ERROR] %s", e
                )

            # ⭐ IMPORTANT MEMORY — write to important/ folder for high-score entries
            if score >= 0.8:
                try:
                    self.writer.write_important(
                        text=user,
                        tags=tags,
                        emotion=emo,
                        score=score,
                    )
                except Exception as e:
                    logger.error("[INTELLIGENCE] write_important error: %s", e)

            # 🧠 REFLECTION SYSTEM

            try:
                self._maybe_reflect(
                    tags,
                    emo,
                    score
                )
            except Exception as e:
                logger.error("[PIPELINE: REFLECTION] %s", e)

            return node

    # 🧠 MEMORY RECALL
    def recall(self, query):

        if not query:
            return None

        query = str(query).strip()

        if not query:
            return None

        with self.lock:

            try:

                tags = self.tagger.extract_tags(
                    query
                )

                if not isinstance(tags, list):
                    tags = []

                recalled = self.recall_engine.recall(
                    self.graph.nodes,
                    tags
                )

                # 🔁 MEMORY REINFORCEMENT

                if (
                    recalled
                    and
                    isinstance(recalled, dict)
                ):

                    recalled_text = recalled.get(
                        "memory",
                        ""
                    )

                    if recalled_text:

                        for node in self.graph.nodes:

                            node_text = getattr(
                                node,
                                "text",
                                ""
                            )

                            if node_text == recalled_text:

                                try:
                                    self.decay.reinforce(
                                        node
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"[REINFORCE ERROR] {e}"
                                    )

                                break

                return recalled

            except Exception as e:

                logger.error(
                    f"[RECALL ERROR] {e}"
                )

                return None

    # 🧠 REFLECTION SYSTEM
    def _maybe_reflect(
        self,
        tags,
        emo,
        score
    ):

        now = time.time()

        if (
            now - self.last_reflection
            < self.reflection_interval
        ):
            return

        try:

            reflection = self.reflector.generate(
                self.graph.nodes
            )

            if not reflection:
                return

            # ✅ FIXED: reflection engine returns dict
            reflection_text = reflection.get(
                "reflection",
                ""
            )

            if not reflection_text:
                return

            reflection_text = str(
                reflection_text
            ).strip()

            if not reflection_text:
                return

            self.writer.write(
                folder="reflections",
                user=reflection_text,
                ai="",
                tags=tags + ["reflection"],
                emotion=emo,
                score=score,
                metadata={
                    "confidence":
                        reflection.get(
                            "confidence",
                            0.5
                        ),
                    "total_patterns":
                        reflection.get(
                            "total_patterns",
                            0
                        )
                }
            )

            self.last_reflection = now

        except Exception as e:

            logger.error(
                f"[REFLECTION ERROR] {e}"
            )

    # 🧠 MEMORY TYPE DETECTION
    def _detect_memory_type(
        self,
        tags,
        emo,
        text
    ):

        t = str(text).lower()

        if any(
            w in t for w in [
                "my name",
                "i am",
                "about me",
            ]
        ):
            return "identity"

        if any(
            w in t for w in [
                "you",
                "us",
                "together",
                "miss you",
            ]
        ):
            return "relationship"

        if emo.get(
            "intensity",
            0
        ) > 0.7:
            return "emotion"

        if "task" in tags:
            return "task"

        if "personal" in tags:
            return "reflection"

        return "conversation"

    # 🧠 MANUAL MEMORY DECAY
    def decay_memories(self):

        with self.lock:

            try:

                self.graph.nodes = (
                    self.decay.apply(
                        self.graph.nodes
                    )
                )

                return True

            except Exception as e:

                logger.error(
                    f"[MEMORY DECAY ERROR] {e}"
                )

                return False

    # 🧠 MANUAL CONSOLIDATION
    def consolidate(self):

        with self.lock:

            try:

                return self.decay.consolidate(
                    self.graph.nodes
                )

            except Exception as e:

                logger.error(
                    f"[MANUAL CONSOLIDATION ERROR] {e}"
                )

                return []

    # 📊 DEBUG STATS
    def stats(self):

        return {
            "nodes":
                len(self.graph.nodes),
            "graph":
                self.graph.stats(),
            "decay":
                self.decay.stats(
                    self.graph.nodes
                ),
            "reflection_interval":
                self.reflection_interval,
            "memory_threshold":
                self.memory_threshold,
            "last_reflection":
                self.last_reflection,
            "working_memory_depth":
                len(self.working_memory)
        }
