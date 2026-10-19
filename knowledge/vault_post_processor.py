from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from memory.state import MemoryState


def _memory_state():
    from memory.state import IdentityFact, KnowledgeEntry, MemoryState
    return MemoryState, IdentityFact, KnowledgeEntry

logger = logging.getLogger(__name__)

VAULT_EXTRACT_PROMPT = """Extract personal information from this conversation turn.

Return ONLY valid JSON with this exact structure:
{{
  "identity": [
    {{"fact": "I am 20 years old", "category": "age"}},
    {{"fact": "I work as a software engineer", "category": "work"}}
  ],
  "preferences": {{
    "likes": ["coding", "coffee"],
    "dislikes": ["mornings", "bugs"]
  }},
  "dreams": ["travel to Japan"],
  "knowledge": [
    {{"topic": "Python", "fact": "Python is a programming language"}}
  ]
}}

Categories for identity: age, name, work, study, location, personality, appearance, hobby, background
Topic for knowledge: the subject of the fact (e.g. "Python", "Tokyo", "AI")

Rules:
- Extract ONLY facts explicitly stated by the user about themselves or their world
- Skip generic chitchat, greetings, questions
- Each fact must be a complete, meaningful statement
- Maximum 3 items per array
- Return empty arrays/sections if nothing found

User: {user}
Mai: {ai}"""


class VaultPostProcessor:

    FOLDER_CONFIG = {
        "people": {
            "filename": "people.md",
            "entity_type": "person",
        },
        "places": {
            "filename": "places.md",
            "entity_type": "place",
        },
        "projects": {
            "filename": "projects.md",
            "entity_type": "project",
        },
        "knowledge": {
            "filename": "knowledge.md",
            "entity_type": None,
        },
        "dreams": {
            "filename": "dreams.md",
            "entity_type": None,
        },
    }

    def __init__(self, compiler, graph_manager=None, llm=None, relationship_updater=None):
        self.compiler = compiler
        self.writer = getattr(compiler, "_writer", None)
        self.graph_manager = graph_manager
        self.llm = llm
        self.relationship_updater = relationship_updater
        self.vault_root = self.writer.vault_root if self.writer else None

    def process(self, user, ai, tags, emotion):
        if not self.vault_root:
            return
        date_str = datetime.now().strftime("%Y-%m-%d")

        MemoryState, _, _ = _memory_state()
        state = MemoryState()

        self._load_existing_state(state)

        entities = self._get_entities()

        llm_data = self._llm_extract(user, ai)

        if llm_data:
            self._populate_from_llm(state, llm_data)
            if not llm_data.get("identity"):
                self._populate_identity_regex(state, user)
            if not llm_data.get("preferences"):
                self._populate_preferences_regex(state, user)
            if not llm_data.get("dreams"):
                self._populate_dreams_regex(state, user)
            self._populate_knowledge_regex(state, user, tags)
        else:
            self._populate_from_regex(state, user, ai, tags, emotion)

        for folder, config in self.FOLDER_CONFIG.items():
            if config["entity_type"]:
                matched = [e for e in entities if e.get("type") == config["entity_type"]]
                for ent in matched:
                    name = ent.get("name", "").strip()
                    confidence = ent.get("confidence", ent.get("metadata", {}).get("confidence", 0.5))
                    if name:
                        target = getattr(state, folder, None)
                        if target is not None:
                            target.append({"name": name, "confidence": confidence, "last_seen": date_str})

        self._populate_statistics(state)

        self.compiler.compile_state(state, date_str)
        try:
            self.compiler.logger.conversation_processed(
                f"chars={len(user or '') + len(ai or '')}"
            )
        except Exception as e:
            logger.warning("[VPP] conversation_processed log failed: %s", e)

    def _populate_from_llm(self, state: MemoryState, llm_data: dict):
        _, IdentityFact, KnowledgeEntry = _memory_state()
        if "identity" in llm_data:
            today = datetime.now().strftime("%Y-%m-%d")
            facts = []
            for e in llm_data["identity"]:
                fact = e.get("fact", "").strip().rstrip(".!,").strip()
                category = (e.get("category") or "general").strip().lower()
                if fact and len(fact) > 2:
                    facts.append(IdentityFact(fact=fact, category=category, timestamp=today))
            if facts:
                state.merge_identity(facts)

        if "preferences" in llm_data:
            prefs = llm_data["preferences"]
            likes = [l for l in prefs.get("likes", []) if len(l.strip()) > 2]
            dislikes = [d for d in prefs.get("dislikes", []) if len(d.strip()) > 2]
            if likes or dislikes:
                state.merge_preferences(likes, dislikes)

        if "dreams" in llm_data:
            dreams = [d.strip() for d in llm_data["dreams"] if d and len(d.strip()) > 3]
            if dreams:
                for d in dreams:
                    state.add_dream(d)

        if "knowledge" in llm_data:
            today = datetime.now().strftime("%Y-%m-%d")
            entries = []
            for e in llm_data["knowledge"]:
                if isinstance(e, dict) and e.get("topic") and e.get("fact"):
                    entries.append(KnowledgeEntry(topic=e["topic"].strip(), fact=e["fact"].strip().rstrip(".!,"), timestamp=today))
                elif isinstance(e, str) and ":" in e:
                    topic, fact = e.split(":", 1)
                    entries.append(KnowledgeEntry(topic=topic.strip(), fact=fact.strip().rstrip(".!,"), timestamp=today))
            if entries:
                state.merge_knowledge(entries)

    def _populate_from_regex(self, state: MemoryState, user, ai, tags, emotion):
        self._populate_identity_regex(state, user)
        self._populate_preferences_regex(state, user)
        self._populate_dreams_regex(state, user)
        self._populate_knowledge_regex(state, user, tags)

    def _populate_identity_regex(self, state: MemoryState, user: str):
        _, IdentityFact, _ = _memory_state()
        user_lower = (user or "").lower()
        patterns = [
            (r"(?:i\s+)?(?:am|'m)\s+(?:a|an|the)?\s*(.+)", "general"),
            (r"my\s+name\s+(?:is|'s)\s+(.+)", "name"),
            (r"i\s+work\s+(?:as|at)\s+(.+)", "work"),
            (r"i\s+(?:study|studies)\s+(.+)", "study"),
            (r"i\s+live\s+(?:in|at)\s+(.+)", "location"),
            (r"my\s+(?:age|birthday)\s+(?:is|'s)\s+(.+)", "age"),
        ]
        facts = []
        for pattern, category in patterns:
            matches = re.findall(pattern, user_lower, re.IGNORECASE)
            for m in matches:
                fact = m.strip().rstrip(".!,").strip()
                if fact and len(fact) > 2:
                    facts.append(IdentityFact(fact=fact, category=category))
        if facts:
            state.merge_identity(facts)

    def _populate_preferences_regex(self, state: MemoryState, user: str):
        user_lower = (user or "").lower()
        likes = []
        dislikes = []
        like_patterns = [
            (r"i\s+(?:like|love|enjoy|adore)\s+(.+)",),
            (r"(?:my\s+)?favou?rite\s+(?:is|are)\s+(.+)",),
            (r"i\s+(?:really\s+)?(?:like|love)\s+it\s+when\s+(.+)",),
            (r"i\s+(?:am\s+)?(?:excited|passionate)\s+about\s+(.+)",),
            (r"i\s+(?:really\s+)?(?:care|love)\s+about\s+(.+)",),
            (r"i\s+(?:am\s+)?interested\s+in\s+(.+)",),
            (r"i\s+(?:am\s+)?fascinated\s+by\s+(.+)",),
        ]
        for pat in like_patterns:
            for m in re.findall(pat[0], user_lower, re.IGNORECASE):
                cleaned = m.strip().rstrip(".!,").strip()
                if cleaned and len(cleaned) > 2:
                    likes.append(cleaned)
        dislike_patterns = [
            r"i\s+(?:don't|do\s+not|hate|dislike)\s+(?:like|love)?\s*(.+)",
            r"i\s+hate\s+(.+)",
        ]
        for pat in dislike_patterns:
            for m in re.findall(pat, user_lower, re.IGNORECASE):
                cleaned = m.strip().rstrip(".!,").strip()
                if cleaned and len(cleaned) > 2:
                    dislikes.append(cleaned)
        if likes or dislikes:
            state.merge_preferences(likes, dislikes)

    def _populate_dreams_regex(self, state: MemoryState, user: str):
        user_lower = (user or "").lower()
        if not user_lower:
            return
        patterns = [
            r"(?:i\s+)?(?:wish|dream|hope|aspire|want\s+to|would\s+love\s+to)\s+(.+?)[\.!]",
            r"(?:my\s+)?(?:dream|goal|ambition)\s+(?:is|would\s+be)\s+(.+?)[\.!]",
            r"(?:someday|one\s+day|in\s+the\s+future)\s+(?:i\s+)?(?:want|will|would)\s+(.+?)[\.!]",
        ]
        for pattern in patterns:
            for m in re.findall(pattern, user_lower, re.IGNORECASE):
                cleaned = m.strip().rstrip(".!,").strip()
                if cleaned and len(cleaned) > 5:
                    state.add_dream(cleaned)

    def _populate_knowledge_regex(self, state: MemoryState, user: str, tags):
        _, _, KnowledgeEntry = _memory_state()
        user_lower = (user or "").lower()
        patterns = [
            r"(?:is|are|was|were)\s+(?:a|an|the|my|our)?\s*(.+)",
            r"(?:works?|studies?|lives?)\s+(?:as|at|in|with)\s+(.+)",
            r"(?:has|have|had)\s+(?:a|an|the|been)\s*(.+)",
        ]
        entries = []
        for pattern in patterns:
            for m in re.findall(pattern, user_lower):
                cleaned = m.strip().rstrip(".!,").strip()
                if len(cleaned) > 5:
                    entries.append(KnowledgeEntry(topic="general", fact=cleaned))
        # Only create knowledge entries for meaningful tags, not every tag on every message
        meaningful_tags = {t.lower() for t in (tags or [])} - {"reflection", "archive", "important", "conversation", "memory", "chat", "general"}
        for tag in meaningful_tags:
            entries.append(KnowledgeEntry(topic=tag, fact=f"topic mentioned: {tag}"))
        if entries:
            state.merge_knowledge(entries)

    def _populate_statistics(self, state: MemoryState):
        if self.graph_manager and hasattr(self.graph_manager, "graph"):
            try:
                state.entity_count = self.graph_manager.graph.entity_count()
            except Exception as e:
                logger.warning("[VPP] entity_count failed: %s", e)
            try:
                state.relation_count = self.graph_manager.graph.relation_count()
            except Exception as e:
                logger.warning("[VPP] relation_count failed: %s", e)
        if self.relationship_updater:
            try:
                stats_text = self.relationship_updater.stats()
                m = re.search(r"Interactions:\s*(\d+)", stats_text)
                if m:
                    state.interaction_count = int(m.group(1))
            except Exception as e:
                logger.warning("[VPP] interaction count failed: %s", e)

    def _load_existing_state(self, state: MemoryState):
        vault = self.vault_root
        if not vault:
            return
        for folder, filename in [
            ("identity", "user.md"),
            ("preferences", "preferences.md"),
            ("knowledge", "knowledge.md"),
            ("dreams", "dreams.md"),
            ("people", "people.md"),
            ("places", "places.md"),
            ("projects", "projects.md"),
        ]:
            path = vault / folder / filename
            state.load_from_file(path, folder)
        stats_path = vault / "statistics" / "stats.md"
        state.load_statistics_from_file(stats_path)

    def _get_entities(self):
        g = None
        if self.graph_manager:
            if hasattr(self.graph_manager, 'graph'):
                g = self.graph_manager.graph
            elif hasattr(self.graph_manager, 'all_entities'):
                g = self.graph_manager
        if g:
            try:
                raw = g.all_entities()
                return [e.to_dict() if hasattr(e, "to_dict") else e for e in raw]
            except Exception as e:
                logger.warning("[VaultPostProcessor] entity fetch: %s", e)
        return []

    def _llm_extract(self, user, ai) -> dict | None:
        if not self.llm or not self._llm_available():
            return None
        prompt = VAULT_EXTRACT_PROMPT.format(user=(user or "")[:1000], ai=(ai or "")[:1000])
        try:
            raw = self.llm.generate(
                system="You are a personal information extractor. Return ONLY valid JSON.",
                user=prompt,
            )
            if not raw:
                return None
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end <= start:
                return None
            data = json.loads(raw[start:end])
            validated = {}
            if "identity" in data and isinstance(data["identity"], list):
                validated["identity"] = [
                    {"fact": str(e["fact"]).strip(), "category": str(e.get("category", "general")).strip()}
                    for e in data["identity"] if isinstance(e, dict) and e.get("fact")
                ]
            if "preferences" in data and isinstance(data["preferences"], dict):
                prefs = {}
                if "likes" in data["preferences"] and isinstance(data["preferences"]["likes"], list):
                    prefs["likes"] = [str(i).strip() for i in data["preferences"]["likes"] if i and len(str(i).strip()) > 2]
                if "dislikes" in data["preferences"] and isinstance(data["preferences"]["dislikes"], list):
                    prefs["dislikes"] = [str(i).strip() for i in data["preferences"]["dislikes"] if i and len(str(i).strip()) > 2]
                if prefs:
                    validated["preferences"] = prefs
            for key in ("dreams",):
                if key in data and isinstance(data[key], list):
                    items = [str(i).strip() for i in data[key] if i and len(str(i).strip()) > 3]
                    if items:
                        validated[key] = items
            if "knowledge" in data and isinstance(data["knowledge"], list):
                validated["knowledge"] = [
                    f"{e['topic']}: {e['fact']}" if isinstance(e, dict) and e.get("topic") and e.get("fact")
                    else str(e).strip()
                    for e in data["knowledge"] if e
                ]
            if validated:
                logger.info("[VaultPostProcessor] LLM extracted: %s", list(validated.keys()))
            return validated or None
        except Exception as e:
            logger.warning("[VaultPostProcessor] LLM extraction failed: %s", e)
            return None

    def _llm_available(self):
        if self.llm is None:
            return False
        if hasattr(self.llm, "is_available"):
            try:
                return self.llm.is_available()
            except Exception as e:
                logger.warning("[VPP] llm.is_available failed: %s", e)
                return False
        return True


