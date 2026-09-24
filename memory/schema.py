# memory/schema.py
import time
import uuid
import threading


class MemoryObject:

    def __init__(
        self,
        content="",
        memory_type="conversation",
        confidence=0.5,
        importance=0.5,
        timestamp=None,
        metadata=None,
        embeddings=None,
        links=None,
        user_id="",
        emotion_experience=None,
    ):
        self.lock = threading.RLock()

        self.id = str(uuid.uuid4())
        self.type = str(memory_type or "conversation").lower()
        self.content = str(content or "").strip()
        self.confidence = max(0.0, min(1.0, float(confidence)))
        self.importance = max(0.0, min(1.0, float(importance)))
        self.timestamp = timestamp if timestamp is not None else time.time()
        self.metadata = dict(metadata or {})
        self.embeddings = embeddings if embeddings is not None else None
        self.links = list(links or [])
        self.vector_id: str = ""
        self.version = 1
        self.archived = False
        self.consolidated = False
        self.user_id = str(user_id)
        # M6 · additive optional experiential field (schema migration-safe)
        self.emotion_experience = (
            dict(emotion_experience) if isinstance(emotion_experience, dict)
            else None
        )

    def to_dict(self):
        data = {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "confidence": self.confidence,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
            "embeddings": self.embeddings,
            "links": list(self.links),
            "version": self.version,
            "archived": self.archived,
            "consolidated": self.consolidated,
            "user_id": self.user_id,
        }
        if self.emotion_experience is not None:
            data["emotion_experience"] = dict(self.emotion_experience)
        return data

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            data = {}
        obj = cls(
            content=data.get("content", ""),
            memory_type=data.get("type", "conversation"),
            confidence=data.get("confidence", 0.5),
            importance=data.get("importance", 0.5),
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
            embeddings=data.get("embeddings"),
            links=data.get("links", []),
            user_id=data.get("user_id", ""),
            emotion_experience=data.get("emotion_experience"),
        )
        obj.id = data.get("id", obj.id)
        obj.version = int(data.get("version", 1))
        obj.archived = bool(data.get("archived", False))
        obj.consolidated = bool(data.get("consolidated", False))
        return obj

    def __repr__(self):
        return (
            f"<MemoryObject "
            f"type={self.type} "
            f"confidence={round(self.confidence, 2)}>"
        )
