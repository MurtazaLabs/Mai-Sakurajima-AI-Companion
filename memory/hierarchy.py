import time
import uuid
import logging
import threading
from enum import Enum

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"
    AUTOBIOGRAPHICAL = "autobiographical"


class MemoryCode:
    def __init__(self, memory_type, content, confidence=0.5, importance=0.5,
                 timestamp=None, metadata=None, tags=None, source=None):
        self.id = str(uuid.uuid4())
        self.type = MemoryType(memory_type) if isinstance(memory_type, str) else memory_type
        self.content = content
        self.confidence = max(0.0, min(1.0, confidence))
        self.importance = max(0.0, min(1.0, importance))
        self.timestamp = timestamp or time.time()
        self.metadata = metadata or {}
        self.tags = tags or []
        self.source = source or "conversation"
        self.access_count = 0
        self.last_accessed = self.timestamp
        self.decay_factor = self._default_decay()
        self._lock = threading.RLock()

    def _default_decay(self):
        decay_map = {
            MemoryType.SEMANTIC: 0.95,
            MemoryType.EPISODIC: 0.85,
            MemoryType.PROCEDURAL: 0.90,
            MemoryType.AUTOBIOGRAPHICAL: 0.98,
        }
        return decay_map.get(self.type, 0.9)

    def access(self):
        with self._lock:
            self.access_count += 1
            self.last_accessed = time.time()

    def apply_decay(self, elapsed_hours):
        with self._lock:
            decay = self.decay_factor ** elapsed_hours
            self.confidence *= decay
            self.importance *= decay

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "confidence": self.confidence,
            "importance": self.importance,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "tags": self.tags,
            "source": self.source,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data):
        obj = cls(
            memory_type=data["type"],
            content=data["content"],
            confidence=data.get("confidence", 0.5),
            importance=data.get("importance", 0.5),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
            source=data.get("source", "conversation"),
        )
        obj.id = data.get("id", obj.id)
        obj.access_count = data.get("access_count", 0)
        obj.last_accessed = data.get("last_accessed", obj.timestamp)
        return obj

    def __repr__(self):
        return f"<MemoryCode type={self.type.value} conf={self.confidence:.2f}>"


class SemanticMemoryStore:
    def __init__(self):
        self._facts = {}
        self._lock = threading.RLock()

    def __len__(self):
        with self._lock:
            return len(self._facts)

    def add(self, fact_key, content, confidence=0.5, tags=None, source=None):
        with self._lock:
            if fact_key in self._facts:
                existing = self._facts[fact_key]
                existing.confidence = max(existing.confidence, confidence)
                existing.access_count += 1
                existing.last_accessed = time.time()
                return existing
            code = MemoryCode(MemoryType.SEMANTIC, content,
                              confidence=confidence, tags=tags, source=source)
            self._facts[fact_key] = code
            return code

    def get(self, fact_key):
        with self._lock:
            code = self._facts.get(fact_key)
            if code:
                code.access()
            return code

    def query(self, text, limit=5):
        with self._lock:
            results = []
            text_lower = text.lower()
            for key, code in self._facts.items():
                score = 0.0
                if text_lower in key.lower():
                    score += 0.5
                if any(t.lower() in text_lower for t in code.tags):
                    score += 0.3
                score *= code.confidence * code.importance
                if score > 0:
                    results.append((code, score))
            results.sort(key=lambda x: x[1], reverse=True)
            return [r[0] for r in results[:limit]]

    def all(self):
        with self._lock:
            return list(self._facts.values())


class EpisodicMemoryStore:
    def __init__(self):
        self._episodes = []
        self._lock = threading.RLock()

    def add(self, content, confidence=0.5, importance=0.5, tags=None, source=None, metadata=None):
        with self._lock:
            code = MemoryCode(MemoryType.EPISODIC, content,
                              confidence=confidence, importance=importance,
                              tags=tags, source=source, metadata=metadata)
            self._episodes.append(code)
            return code

    def recall(self, query=None, limit=5):
        with self._lock:
            if not query:
                results = sorted(self._episodes, key=lambda x: x.timestamp, reverse=True)[:limit]
                for r in results:
                    r.access()
                return results
            text_lower = query.lower()
            scored = []
            for code in self._episodes:
                score = 0.0
                if text_lower in code.content.lower():
                    score += 0.4
                if any(t.lower() in text_lower for t in code.tags):
                    score += 0.3
                recency = 1.0 / (1.0 + (time.time() - code.timestamp) / 3600.0)
                score += 0.3 * recency
                score *= code.confidence * code.importance
                if score > 0:
                    scored.append((code, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            results = [r[0] for r in scored[:limit]]
            for r in results:
                r.access()
            return results

    def all(self):
        with self._lock:
            return list(self._episodes)

    def __len__(self):
        with self._lock:
            return len(self._episodes)


class ProceduralMemoryStore:
    def __init__(self):
        self._rules = {}
        self._lock = threading.RLock()

    def add(self, trigger, action, confidence=0.5, context=None):
        with self._lock:
            rule_key = f"{trigger}:{action}"
            if rule_key in self._rules:
                existing = self._rules[rule_key]
                existing.confidence = min(1.0, existing.confidence + 0.1)
                existing.access_count += 1
                return existing
            code = MemoryCode(MemoryType.PROCEDURAL,
                              f"When {trigger}, then {action}",
                              confidence=confidence, importance=0.6,
                              tags=[trigger], source="experience",
                              metadata={"trigger": trigger, "action": action, "context": context or {}})
            self._rules[rule_key] = code
            return code

    def find(self, trigger, context=None):
        with self._lock:
            results = []
            text_lower = trigger.lower()
            for key, code in self._rules.items():
                score = 0.0
                trig = code.metadata.get("trigger", "")
                if text_lower in trig.lower():
                    score += 0.5
                if context and code.metadata.get("context"):
                    ctx = code.metadata["context"]
                    score += sum(1 for k, v in context.items()
                                 if ctx.get(k) == v) * 0.1
                score *= code.confidence
                if score > 0:
                    results.append((code, score))
            results.sort(key=lambda x: x[1], reverse=True)
            for r, _ in results:
                r.access()
            return [r[0] for r in results[:3]]

    def all(self):
        with self._lock:
            return list(self._rules.values())


class AutobiographicalMemoryStore:
    def __init__(self):
        self._traits = {}
        self._history = []
        self._lock = threading.RLock()

    def add(self, trait_key, content, confidence=0.5, importance=0.8):
        with self._lock:
            if trait_key in self._traits:
                existing = self._traits[trait_key]
                existing.confidence = max(existing.confidence, confidence)
                existing.last_accessed = time.time()
                return existing
            code = MemoryCode(MemoryType.AUTOBIOGRAPHICAL, content,
                              confidence=confidence, importance=importance,
                              tags=[trait_key], source="self")
            self._traits[trait_key] = code
            self._history.append({"key": trait_key, "content": content, "timestamp": time.time()})
            return code

    def get(self, trait_key):
        with self._lock:
            code = self._traits.get(trait_key)
            if code:
                code.access()
            return code

    def query(self, topic, limit=3):
        with self._lock:
            results = []
            text_lower = topic.lower()
            for key, code in self._traits.items():
                score = 0.0
                if text_lower in key.lower() or text_lower in code.content.lower():
                    score += 0.5
                score *= code.importance
                if score > 0:
                    results.append((code, score))
            results.sort(key=lambda x: x[1], reverse=True)
            return [r[0] for r in results[:limit]]

    def __len__(self):
        with self._lock:
            return len(self._traits)

    def history(self):
        with self._lock:
            return list(self._history)

    def all(self):
        with self._lock:
            return list(self._traits.values())


class MemoryHierarchy:
    def __init__(self, brain_graph=None, event_bus=None):
        self.semantic = SemanticMemoryStore()
        self.episodic = EpisodicMemoryStore()
        self.procedural = ProceduralMemoryStore()
        self.autobiographical = AutobiographicalMemoryStore()
        self.brain_graph = brain_graph
        self.event_bus = event_bus

    def store_semantic(self, fact_key, content, confidence=0.5, tags=None, source=None, emotion=None):
        code = self.semantic.add(fact_key, content, confidence, tags, source)
        self._sync_to_brain_graph(code, emotion=emotion)
        return code

    def store_episodic(self, content, confidence=0.5, importance=0.5,
                       tags=None, source=None, metadata=None, emotion=None):
        code = self.episodic.add(content, confidence, importance, tags, source, metadata)
        self._sync_to_brain_graph(code, emotion=emotion)
        return code

    def store_procedural(self, trigger, action, confidence=0.5, context=None):
        code = self.procedural.add(trigger, action, confidence, context)
        self._sync_to_brain_graph(code)
        return code

    def store_autobiographical(self, trait_key, content, confidence=0.5, importance=0.8):
        code = self.autobiographical.add(trait_key, content, confidence, importance)
        self._sync_to_brain_graph(code)
        return code

    def store_from_memory_object(self, memory_obj, source="conversation"):
        content = memory_obj.content
        tags = memory_obj.metadata.get("tags", [])
        emotion = memory_obj.metadata.get("emotion", {})
        confidence = memory_obj.confidence
        importance = memory_obj.importance
        text_lower = content.lower()

        is_factual = any(word in text_lower for word in [
            "is", "are", "was", "were", "called", "known as",
            "located", "capital", "means",
        ])
        is_identity = any(word in text_lower for word in [
            "i am", "my name", "i'm", "i was", "i have",
        ])
        is_event = any(word in text_lower for word in [
            "today", "yesterday", "just", "happened", "went",
            "did", "saw", "heard", "felt",
        ])
        is_rule = any(word in text_lower for word in [
            "always", "never", "should", "must", "when",
            "if", "then",
        ])

        results = []
        if is_factual and not is_identity:
            fact_key = content[:60].strip().lower()
            code = self.store_semantic(fact_key, content, confidence, tags, source, emotion=emotion)
            results.append(code)

        if is_event or not (is_factual or is_identity or is_rule):
            code = self.store_episodic(content, confidence, importance, tags, source,
                                       metadata={"emotion": emotion}, emotion=emotion)
            results.append(code)

        if is_rule:
            parts = content.split(",")
            trigger = parts[0].replace("if", "").replace("when", "").strip() if parts else content
            action = parts[-1].strip() if len(parts) > 1 else content
            code = self.store_procedural(trigger, action, confidence)
            results.append(code)

        if is_identity:
            trait_key = content[:40].strip().lower()
            code = self.store_autobiographical(trait_key, content, confidence)
            results.append(code)

        return results

    def query(self, text, memory_types=None, limit=5):
        types = [MemoryType(t) if isinstance(t, str) else t
                 for t in (memory_types or list(MemoryType))]
        results = []
        if MemoryType.SEMANTIC in types:
            results.extend(self.semantic.query(text, limit))
        if MemoryType.EPISODIC in types:
            results.extend(self.episodic.recall(text, limit))
        if MemoryType.PROCEDURAL in types:
            results.extend(self.procedural.find(text))
        if MemoryType.AUTOBIOGRAPHICAL in types:
            results.extend(self.autobiographical.query(text, limit))
        results.sort(key=lambda x: x.importance * x.confidence, reverse=True)
        seen = set()
        deduped = []
        for r in results:
            if r.id not in seen:
                seen.add(r.id)
                deduped.append(r)
        return deduped[:limit]

    def apply_decay(self, elapsed_hours=1.0):
        for store in [self.semantic, self.episodic, self.procedural, self.autobiographical]:
            for code in store.all():
                code.apply_decay(elapsed_hours)

    def stats(self):
        return {
            "semantic": len(self.semantic.all()),
            "episodic": len(self.episodic.all()),
            "procedural": len(self.procedural.all()),
            "autobiographical": len(self.autobiographical.all()),
            "total": sum(len(s.all()) for s in [
                self.semantic, self.episodic, self.procedural, self.autobiographical
            ]),
        }

    def to_dict(self):
        return {
            "semantic": [c.to_dict() for c in self.semantic.all()],
            "episodic": [c.to_dict() for c in self.episodic.all()],
            "procedural": [c.to_dict() for c in self.procedural.all()],
            "autobiographical": [c.to_dict() for c in self.autobiographical.all()],
        }

    def _sync_to_brain_graph(self, code, emotion=None):
        if not self.brain_graph:
            return
        try:
            self.brain_graph.add_memory_node(
                memory_id=code.id,
                text=code.content,
                memory_type=code.type.value,
                score=code.confidence,
                tags=code.tags,
                importance=code.importance,
                source=code.source,
                emotion=emotion,
            )
        except Exception as e:
            logger.debug("[MemoryHierarchy] BrainGraph sync error: %s", e)
