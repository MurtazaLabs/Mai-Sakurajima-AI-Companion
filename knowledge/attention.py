# knowledge/attention.py
import logging
import threading
import time

logger = logging.getLogger(__name__)


class AttentionFocus:

    def __init__(self, topic, areas=None, weights=None):
        self.topic = str(topic).strip().lower()
        self.areas = list(areas or [])
        self.weights = dict(weights or {})
        self.created_at = time.time()

    def to_dict(self):
        return {
            "topic": self.topic,
            "areas": list(self.areas),
            "weights": dict(self.weights),
            "created_at": self.created_at,
        }

    def __repr__(self):
        return f"<AttentionFocus topic={self.topic} areas={len(self.areas)}>"


class AttentionSystem:

    def __init__(self, knowledge_graph=None, belief_engine=None):
        self._lock = threading.RLock()
        self._current_focus = None
        self._topic_history = []
        self._max_history = 10
        self.knowledge_graph = knowledge_graph
        self.belief_engine = belief_engine

        self._topic_areas = {
            "programming": {"python", "code", "software", "development", "tech"},
            "python": {"programming", "code", "development"},
            "anime": {"japanese", "animation", "shows", "entertainment"},
            "music": {"audio", "songs", "entertainment", "art"},
            "game": {"gaming", "entertainment", "development"},
            "food": {"cooking", "preferences", "health"},
            "travel": {"places", "culture", "geography"},
            "work": {"career", "job", "employment", "professional"},
            "learning": {"education", "skills", "growth", "programming"},
            "health": {"wellness", "exercise", "mental", "food"},
        }

    def focus(self, topic, cognitive_state=None):
        topic = str(topic).strip().lower() if topic else ""

        areas = set()
        for kw, related in self._topic_areas.items():
            if kw in topic or topic in kw:
                areas.update(related)

        if self.knowledge_graph:
            relations = self.knowledge_graph.query(topic, depth=1)
            for rel in relations:
                areas.add(rel.target)

        if self.belief_engine:
            beliefs = self.belief_engine.query(topic)
            for b in beliefs:
                areas.add(b.object.lower()[:30])

        weights = {area: 1.0 for area in areas}

        with self._lock:
            self._current_focus = AttentionFocus(
                topic=topic,
                areas=list(areas),
                weights=weights,
            )

            if topic:
                self._topic_history.append(topic)
                if len(self._topic_history) > self._max_history:
                    self._topic_history = self._topic_history[-self._max_history:]

        return self._current_focus

    def current(self):
        with self._lock:
            return self._current_focus

    def history(self):
        with self._lock:
            return list(self._topic_history)

    def retrieve(self, focus=None):
        if focus is None:
            with self._lock:
                focus = self._current_focus

        if focus is None:
            return []

        results = []

        if self.knowledge_graph:
            for area in focus.areas:
                relations = self.knowledge_graph.query(area, depth=1)
                for rel in relations:
                    weight = focus.weights.get(area, 0.5)
                    results.append({
                        "source": "knowledge_graph",
                        "content": f"{rel.source} {rel.relation} {rel.target}",
                        "relevance": weight * 0.8,
                        "area": area,
                    })

        results.sort(key=lambda r: r["relevance"], reverse=True)
        return results[:10]
