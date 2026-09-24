# Mai_ai/memory/node.py
import time
import uuid
import threading
import logging

from app.config_loader import Settings

logger = logging.getLogger(__name__)
from memory.schema import MemoryObject


class MemoryNode(MemoryObject):

    def __init__(
        self,
        text="",
        score=None,
        tags=None,
        emotion=None,
        memory_type="conversation",
        emotional_weight=None,
        importance=None,
        confidence=None,
        source="user",
        created_at=None,
        last_accessed=None,
    ):

        super().__init__(
            content=text,
            memory_type=memory_type,
            confidence=(
                confidence
                if confidence is not None
                else Settings.MEMORY_NODE_DEFAULT_CONFIDENCE
            ),
            importance=(
                importance
                if importance is not None
                else Settings.MEMORY_NODE_DEFAULT_IMPORTANCE
            ),
            timestamp=created_at,
        )

        self.id = str(uuid.uuid4())
        self.vector_id: str = ""
        self.text = str(text or "").strip()
        self.score = self._clamp(
            score
            if score is not None
            else Settings.MEMORY_NODE_DEFAULT_SCORE
        )
        self.tags = self._clean_tags(tags or [])
        self.emotion = self._clean_emotion(emotion)
        self.memory_type = str(memory_type or "conversation").lower()
        self.emotional_weight = self._clamp(
            emotional_weight
            if emotional_weight is not None
            else Settings.MEMORY_NODE_DEFAULT_EMOTIONAL_WEIGHT
        )
        self.importance = self._clamp(
            importance
            if importance is not None
            else Settings.MEMORY_NODE_DEFAULT_IMPORTANCE
        )
        self.confidence = self._clamp(
            confidence
            if confidence is not None
            else Settings.MEMORY_NODE_DEFAULT_CONFIDENCE
        )

        self.links = []
        self.link_strengths = {}
        self.reinforcement = Settings.MEMORY_NODE_DEFAULT_REINFORCEMENT
        self.reinforcement_count = Settings.MEMORY_NODE_DEFAULT_REINFORCEMENT_COUNT
        self.access_count = Settings.MEMORY_NODE_DEFAULT_ACCESS_COUNT

        now = time.time()
        self.created_at = created_at if created_at is not None else now
        self.last_accessed = last_accessed if last_accessed is not None else now
        self.source = str(source or "user")

        self.archived = False
        self.consolidated = False

        self.content = self.text
        self.type = self.memory_type
        self.timestamp = self.created_at

    def _clamp(self, value):
        try:
            value = float(value)
        except Exception as e:
            logger.warning("[MemoryNode] Failed to parse score value as float: %r | %s", value, e)
            value = Settings.MEMORY_NODE_DEFAULT_SCORE
        return max(
            Settings.MEMORY_NODE_MIN_VALUE,
            min(Settings.MEMORY_NODE_MAX_VALUE, value)
        )

    def _clean_tags(self, tags):
        if not isinstance(tags, list):
            return []
        cleaned = []
        for tag in tags:
            if not tag:
                continue
            tag = str(tag).strip().lower()
            if tag and tag not in cleaned:
                cleaned.append(tag)
        return cleaned

    def _clean_emotion(self, emotion):
        if not isinstance(emotion, dict):
            emotion = {}
        return {
            "type": str(
                emotion.get("type", Settings.MEMORY_NODE_DEFAULT_EMOTION_TYPE)
            ),
            "intensity": self._clamp(
                emotion.get("intensity", Settings.MEMORY_NODE_DEFAULT_EMOTION_INTENSITY)
            ),
        }

    def reinforce(self, amount=None):
        with self.lock:
            amount = (
                amount
                if amount is not None
                else Settings.MEMORY_NODE_REINFORCE_AMOUNT
            )
            amount = max(0.0, float(amount))
            self.reinforcement += 1
            self.reinforcement_count += 1
            self.access_count += 1
            self.last_accessed = time.time()

            boost = amount * (
                1 / (1 + (self.reinforcement * Settings.MEMORY_NODE_REINFORCEMENT_DECAY))
            )
            boost *= (1 + (self.emotional_weight * Settings.MEMORY_NODE_EMOTIONAL_BOOST))

            self.score = self._clamp(self.score + boost)
            self.importance = self._clamp(
                self.importance + (boost * Settings.MEMORY_NODE_IMPORTANCE_BOOST)
            )
            return self.score

    def add_link(self, node, strength=None):
        with self.lock:
            if not node:
                return
            if not hasattr(node, "id"):
                return
            if node.id == self.id:
                return

            strength = self._clamp(
                strength
                if strength is not None
                else Settings.MEMORY_NODE_DEFAULT_LINK_STRENGTH
            )

            if node not in self.links:
                self.links.append(node)
                self.link_strengths[node.id] = strength
            else:
                current = self.link_strengths.get(
                    node.id, Settings.MEMORY_NODE_DEFAULT_LINK_STRENGTH
                )
                self.link_strengths[node.id] = self._clamp(
                    current + Settings.MEMORY_NODE_LINK_INCREMENT
                )

    def decay(self, rate=None):
        with self.lock:
            rate = max(
                Settings.MEMORY_NODE_MIN_DECAY,
                float(rate if rate is not None else Settings.MEMORY_NODE_DEFAULT_DECAY_RATE)
            )
            resistance = self.reinforcement * Settings.MEMORY_NODE_REINFORCEMENT_RESISTANCE
            emotional_resistance = self.emotional_weight * Settings.MEMORY_NODE_EMOTIONAL_RESISTANCE
            final_decay = max(
                Settings.MEMORY_NODE_MIN_DECAY,
                rate - resistance - emotional_resistance
            )
            self.score = max(Settings.MEMORY_NODE_MIN_VALUE, self.score - final_decay)
            return self.score

    def access(self):
        with self.lock:
            self.access_count += 1
            self.last_accessed = time.time()
            self.reinforce(Settings.MEMORY_NODE_ACCESS_REINFORCE)
            return self.score

    def age(self):
        return max(0, time.time() - self.created_at)

    def to_dict(self):
        with self.lock:
            data = {
                "id": self.id,
                "vector_id": self.vector_id,
                "text": self.text,
                "score": self.score,
                "tags": self.tags,
                "emotion": self.emotion,
                "memory_type": self.memory_type,
                "emotional_weight": self.emotional_weight,
                "importance": self.importance,
                "confidence": self.confidence,
                "reinforcement": self.reinforcement,
                "reinforcement_count": self.reinforcement_count,
                "access_count": self.access_count,
                "created_at": self.created_at,
                "last_accessed": self.last_accessed,
                "source": self.source,
                "archived": self.archived,
                "consolidated": self.consolidated,
                "version": self.version,
                "links": [
                    n.id if hasattr(n, "id") else n for n in self.links
                ],
            }
            return data

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            data = {}

        node = cls(
            text=data.get("text", ""),
            score=data.get("score", Settings.MEMORY_NODE_DEFAULT_SCORE),
            tags=data.get("tags", []),
            emotion=data.get("emotion", {}),
            memory_type=data.get("memory_type", "conversation"),
            emotional_weight=data.get("emotional_weight", Settings.MEMORY_NODE_DEFAULT_EMOTIONAL_WEIGHT),
            importance=data.get("importance", Settings.MEMORY_NODE_DEFAULT_IMPORTANCE),
            confidence=data.get("confidence", Settings.MEMORY_NODE_DEFAULT_CONFIDENCE),
            source=data.get("source", "user"),
            created_at=data.get("created_at"),
            last_accessed=data.get("last_accessed"),
        )

        node.id = data.get("id", node.id)
        node.vector_id = str(data["vector_id"]) if "vector_id" in data else node.vector_id
        node.reinforcement = int(data.get("reinforcement", Settings.MEMORY_NODE_DEFAULT_REINFORCEMENT))
        node.reinforcement_count = int(data.get("reinforcement_count", Settings.MEMORY_NODE_DEFAULT_REINFORCEMENT_COUNT))
        node.access_count = int(data.get("access_count", Settings.MEMORY_NODE_DEFAULT_ACCESS_COUNT))
        node.archived = bool(data.get("archived", False))
        node.consolidated = bool(data.get("consolidated", False))
        node.version = int(data.get("version", 1))

        node.content = node.text
        node.type = node.memory_type
        node.timestamp = node.created_at

        return node

    def __repr__(self):
        return (
            f"<MemoryNode "
            f"type={self.memory_type} "
            f"score={round(self.score, 2)} "
            f"tags={self.tags}>"
        )
