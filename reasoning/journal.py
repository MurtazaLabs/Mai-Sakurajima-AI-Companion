# reasoning/journal.py
import time
import json
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ThoughtJournal:

    def __init__(self, path: Optional[str] = None, brain_graph=None):
        self._lock = threading.RLock()
        self._thoughts = []
        self._path: Optional[str] = path
        self.brain_graph = brain_graph

        if path:
            with self._lock:
                self._load()

    def store(self, thought):
        entry = {
            "id": str(time.time()) + "-" + str(hash(str(thought.get("query", ""))) % 10000),
            "query": thought.get("query", ""),
            "retrieved_evidence": thought.get("retrieved_evidence", []),
            "known_facts": thought.get("known_facts", []),
            "unknowns": thought.get("unknowns", []),
            "reasoning_steps": thought.get("reasoning_steps", []),
            "confidence": float(thought.get("confidence", 0.5)),
            "conclusion": thought.get("conclusion", ""),
            "timestamp": time.time(),
        }

        with self._lock:
            self._thoughts.append(entry)
            if self._path:
                self._save(entry)

        if self.brain_graph:
            self.brain_graph.add_thought_node(
                thought_id=entry["id"],
                query=entry["query"],
                conclusion=entry["conclusion"],
                confidence=entry["confidence"],
                reasoning_steps=entry["reasoning_steps"],
            )

        return entry

    def store_monologue(self, packet, query=""):
        """Journal a ThoughtPacket's private fields (never spoken) alongside
        the spoken response. The packet response is also journaled for
        traceability; speech strips it via the caller."""
        entry = {
            "id": str(time.time()) + "-" + str(hash(str(query)) % 10000),
            "query": query,
            "thought": packet.thought,
            "decision": packet.decision,
            "speech_plan": dict(packet.speech_plan),
            "response": packet.response,
            "timestamp": time.time(),
        }
        with self._lock:
            self._thoughts.append(entry)
            if self._path:
                self._save(entry)
        return entry

    def recent(self, n=10):
        with self._lock:
            return list(self._thoughts[-n:])

    def search(self, topic):
        topic = str(topic).strip().lower()
        results = []
        with self._lock:
            results = [
                t for t in self._thoughts
                if topic in t["query"].lower()
                or topic in t["conclusion"].lower()
                or any(topic in str(f).lower() for f in t.get("known_facts", []))
            ]
        if self.brain_graph:
            graph_nodes = self.brain_graph.search_entities(topic, node_type="thought")
            graph_ids = {n.metadata.get("thought_id", "") for n in graph_nodes}
            local_ids = {t["id"] for t in results}
            for n in graph_nodes:
                tid = n.metadata.get("thought_id", "")
                if tid and tid not in local_ids:
                    results.append({
                        "id": tid,
                        "query": n.metadata.get("query", ""),
                        "conclusion": n.metadata.get("conclusion", ""),
                        "confidence": n.metadata.get("confidence", 0.5),
                        "reasoning_steps": n.metadata.get("reasoning_steps", []),
                        "timestamp": n.metadata.get("created_at", 0),
                    })
        return results

    def count(self):
        with self._lock:
            return len(self._thoughts)

    def _save(self, entry=None):
        """Append a single entry — O(1) per write instead of rewriting the
        whole journal every thought (P-3).  Append-mode JSONL lines keep the
        file bounded: one JSON object per line."""
        if self._path is None:
            return
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                if entry is None:
                    for e in self._thoughts:
                        f.write(json.dumps(e, ensure_ascii=False) + "\n")
                else:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("[ThoughtJournal] Save error: %s", e)

    def _load(self):
        if self._path is None:
            return
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                self._thoughts = []
                return
            if content.lstrip().startswith("["):
                # Legacy format: whole journal was one JSON array.  Migrate
                # the file to JSONL once so subsequent appends stay valid.
                self._thoughts = json.loads(content)
                try:
                    with open(self._path, "w", encoding="utf-8") as f:
                        for e in self._thoughts:
                            f.write(json.dumps(e, ensure_ascii=False) + "\n")
                except Exception as e:
                    logger.error("[ThoughtJournal] Legacy migration error: %s", e)
                return
            # JSONL: one object per line.
            self._thoughts = [
                json.loads(line) for line in content.splitlines()
                if line.strip()
            ]
        except (FileNotFoundError, json.JSONDecodeError):
            self._thoughts = []
        except Exception as e:
            logger.error("[ThoughtJournal] Load error: %s", e)
            self._thoughts = []
