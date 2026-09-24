# Mai_ai/memory/decay.py
import time
import threading
import logging
from collections import defaultdict

from memory.consolidation import consolidate as core_consolidate
from app.config_loader import Settings

logger = logging.getLogger(__name__)

class MemoryDecay:

    MAX_ARCHIVED = 5000
    MAX_CONSOLIDATED = 1000

    def __init__(self):

        # 🧠 CONFIG

        self.min_score = Settings.MEMORY_MIN_SCORE

        self.archive_score = Settings.MEMORY_ARCHIVE_SCORE

        self.max_consolidation = Settings.MEMORY_MAX_CONSOLIDATION

        # 📦 STORAGE

        self.archived = set()

        self.consolidated = []

        # 🧠 THREAD SAFETY

        self.lock = threading.RLock()

        # 🧠 DECAY CURVES

        self.type_decay = {

            "conversation": Settings.DECAY_CONVERSATION,

            "emotion": Settings.DECAY_EMOTION,

            "relationship": Settings.DECAY_RELATIONSHIP,

            "identity": Settings.DECAY_IDENTITY,

            "reflection": Settings.DECAY_REFLECTION,

            "important": Settings.DECAY_IMPORTANT,

            "general": Settings.DECAY_GENERAL,
        }

    # 🧠 MAIN DECAY SYSTEM

    def apply(self, nodes):

        if not isinstance(nodes, list):
            return []

        active = []

        now = time.time()

        with self.lock:

            for node in nodes:

                try:

                    if node is None:
                        continue

                    # 🧠 SAFE ATTRIBUTES

                    memory_type = getattr(
                        node,
                        "memory_type",
                        "general"
                    )

                    score = self._safe_float(
                        getattr(
                            node,
                            "score",
                            0.5
                        ),
                        0.5
                    )

                    importance = self._safe_float(
                        getattr(
                            node,
                            "importance",
                            0.5
                        ),
                        0.5
                    )

                    emotional_weight = self._safe_float(
                        getattr(
                            node,
                            "emotional_weight",
                            0.5
                        ),
                        0.5
                    )

                    reinforcement = int(
                        getattr(
                            node,
                            "reinforcement",
                            1
                        )
                    )

                    last_accessed = getattr(
                        node,
                        "last_accessed",
                        now
                    )

                    # 🕒 AGE FACTOR

                    age_hours = max(
                        1.0,
                        (now - last_accessed) / 3600
                    )

                    age_penalty = min(
                        Settings.MEMORY_MAX_AGE_PENALTY,
                        (
                            age_hours
                            *
                            Settings.MEMORY_AGE_DECAY_RATE
                        )
                    )

                    recency_factor = 1.0 - age_penalty

                    recency_factor = max(
                        Settings.MEMORY_MIN_RECENCY_FACTOR,
                        recency_factor
                    )

                    # 🧠 BASE DECAY

                    decay = self.type_decay.get(
                        memory_type,
                        Settings.DECAY_GENERAL
                    )

                    # 🛡️ PROTECTIONS

                    emotional_protection = (
                        emotional_weight
                        *
                        Settings.MEMORY_EMOTIONAL_PROTECTION
                    )

                    importance_protection = (
                        importance
                        *
                        Settings.MEMORY_IMPORTANCE_PROTECTION
                    )

                    reinforcement_protection = min(
                        Settings.MEMORY_MAX_REINFORCEMENT_PROTECTION,
                        (
                            reinforcement
                            *
                            Settings.MEMORY_REINFORCEMENT_PROTECTION
                        )
                    )

                    final_decay = (

                        decay

                        +

                        emotional_protection

                        +

                        importance_protection

                        +

                        reinforcement_protection
                    )

                    final_decay = min(
                        Settings.MEMORY_MAX_DECAY,
                        max(
                            Settings.MEMORY_MIN_DECAY,
                            final_decay
                        )
                    )

                    # 📉 APPLY DECAY

                    new_score = (
                        score
                        *
                        final_decay
                        *
                        recency_factor
                    )

                    node.score = round(
                        max(0.0, new_score),
                        4
                    )

                    # 📦 ARCHIVE LOGIC

                    if node.score < self.archive_score:

                        if node not in self.archived:

                            node.archived = True

                            self.archived.add(
                                node
                            )

                        continue

                    active.append(node)

                except Exception as e:

                    logger.error(
                        f"[DECAY APPLY ERROR] {e}"
                    )

                    active.append(node)

        return active

    # 🔁 REINFORCE MEMORY

    def reinforce(
        self,
        node,
        amount=None
    ):

        if node is None:
            return None

        with self.lock:

            try:

                if amount is None:

                    amount = Settings.MEMORY_REINFORCE_AMOUNT

                amount = max(
                    0.0,
                    float(amount)
                )

                current = self._safe_float(
                    getattr(
                        node,
                        "score",
                        0.5
                    ),
                    0.5
                )

                node.score = min(
                    1.0,
                    current + amount
                )

                current_reinforcement = int(
                    getattr(
                        node,
                        "reinforcement",
                        1
                    )
                )

                node.reinforcement = current_reinforcement + 1

                node.last_accessed = (
                    time.time()
                )

                node.archived = False

                return node

            except Exception as e:

                logger.error(
                    f"[REINFORCE ERROR] {e}"
                )

                return node

    # 🧠 REVIVE MEMORY

    def revive(self, node):

        if node is None:
            return False

        with self.lock:

            try:

                if node in self.archived:

                    self.archived.discard(node)

                    node.archived = False

                    node.score = max(
                        Settings.MEMORY_REVIVE_SCORE,
                        getattr(
                            node,
                            "score",
                            0.0
                        )
                    )

                    node.last_accessed = (
                        time.time()
                    )

                    return True

                return False

            except Exception as e:

                logger.error(
                    f"[REVIVE ERROR] {e}"
                )

                return False

    # 🧠 CONSOLIDATE MEMORIES

    def consolidate(self, nodes, store_fn=None):

        if not isinstance(nodes, list):
            return []

        with self.lock:

            try:

                new_objects, remaining = core_consolidate(nodes)

                if remaining:
                    logger.debug("[Consolidation] %d nodes remaining after consolidation", len(remaining))

                consolidated_nodes = []
                for obj in new_objects:
                    meta = obj.metadata or {}
                    consolidated_nodes.append({
                        "memory_type": "semantic",
                        "summary": obj.content,
                        "source_count": len(meta.get("source_ids", [])),
                        "score": getattr(obj, "importance", 0.5),
                        "importance": getattr(obj, "importance", 0.5),
                        "emotional_weight": 0.5,
                        "reinforcement": 1,
                        "tags": meta.get("consolidated_from", "other"),
                        "created_at": time.time(),
                        "last_accessed": time.time(),
                    })

                self.consolidated.extend(consolidated_nodes)
                self._enforce_caps()

                if store_fn and new_objects:
                    for obj in new_objects:
                        try:
                            store_fn(obj)
                        except Exception as e:
                            logger.error("[Consolidation] store_fn failed: %s", e)

                return consolidated_nodes

            except Exception as e:

                logger.error("[CONSOLIDATION ERROR] %s", e)

                return []

    # 🧠 CAP ENFORCEMENT

    def _enforce_caps(self):
        if len(self.archived) > self.MAX_ARCHIVED:
            with self.lock:
                sorted_archived = sorted(
                    self.archived,
                    key=lambda n: getattr(n, "score", 0.0),
                )
                to_remove = len(self.archived) - self.MAX_ARCHIVED
                for node in sorted_archived[:to_remove]:
                    self.archived.discard(node)
                logger.info("[MemoryDecay] Trimmed %d archived nodes", to_remove)
        if len(self.consolidated) > self.MAX_CONSOLIDATED:
            with self.lock:
                self.consolidated.sort(key=lambda x: x.get("score", 0.0))
                self.consolidated = self.consolidated[-self.MAX_CONSOLIDATED:]
                logger.info("[MemoryDecay] Trimmed consolidated list to %d", self.MAX_CONSOLIDATED)

    # 📊 STATS

    def stats(self, active_nodes=None):

        if active_nodes is None:
            active_nodes = []

        return {

            "active_memories":
                len(active_nodes),

            "archived_memories":
                len(self.archived),

            "consolidated_memories":
                len(self.consolidated),

            "min_score": self.min_score,

            "archive_score": self.archive_score,
        }

    # 🧹 CLEAR ARCHIVE

    def clear_archive(self):

        with self.lock:

            self.archived.clear()

    # 🧹 CLEAR CONSOLIDATED

    def clear_consolidated(self):

        with self.lock:

            self.consolidated.clear()

    # 🛡️ SAFE FLOAT

    def _safe_float(
        self,
        value,
        default=0.0
    ):

        try:

            return float(value)

        except Exception as e:
            logger.debug("Failed to parse value as float: %r", value)
            return default

