import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

_STOPWORDS = frozenset({
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "this", "that", "these", "those",
    "am", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having", "do", "does", "did", "doing",
    "would", "should", "could", "ought", "might", "must",
    "a", "an", "the", "and", "but", "if", "or", "because", "as",
    "until", "while", "of", "at", "by", "for", "with", "about",
    "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "to", "from", "up", "down", "in",
    "out", "on", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "just", "also", "now",
    "yes", "no", "ok", "okay", "hey", "hi", "hello", "thanks",
    "thank", "please", "sorry",
})

EXTRACTION_PROMPT = """Extract entities and relationships from the text below.

Return ONLY valid JSON with this exact structure:
{{"entities": [
    {{"name": "EntityName", "type": "person|project|technology|character|place|skill|organization"}}
  ],
  "relations": [
    {{"source": "EntityName", "relation": "uses|builds|likes|contains|works_on|created_by", "target": "EntityName"}}
  ]
}}

Rules:
- Entities are real-world nouns: people, projects, technologies, characters, places, skills, organizations
- Relations connect two entities that appear in the entities list
- Use the simplest canonical form for names (e.g. "OpenRouter" not "open router")
- Minimum 2 characters per entity name
- Skip generic words like "this", "that", "it", "thing"

Text:
{text}"""


class EntityExtractor:

    def __init__(self, llm: Optional[Any] = None):
        self.llm: Optional[Any] = llm

    def extract(self, text):
        if self.llm:
            result = self._llm_extract(text)
            if not result.get("entities"):
                fallback = self._fallback_extract(text)
                result["entities"] = fallback.get("entities", [])
                result.setdefault("relations", [])
                existing_entity_names = {e["name"].lower() for e in result["entities"]}
                for rel in fallback.get("relations", []):
                    if rel["source"].lower() in existing_entity_names or rel["target"].lower() in existing_entity_names:
                        result["relations"].append(rel)
            return result
        entities = self._fallback_extract_entities(text)
        relations = self._fallback_extract_relations(text, entities)
        return {"entities": entities, "relations": relations}

    def _llm_extract(self, text):
        assert self.llm is not None
        prompt = EXTRACTION_PROMPT.format(text=text[:2000])
        try:
            raw = self.llm.generate(
                system="You are a knowledge graph extractor. Return ONLY valid JSON.",
                user=prompt,
            )
            if not raw:
                return self._fallback_extract(text)
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end <= start:
                return self._fallback_extract(text)
            data = json.loads(raw[start:end])
            entities = data.get("entities", [])
            relations = data.get("relations", [])
            if not isinstance(entities, list):
                entities = []
            if not isinstance(relations, list):
                relations = []
            validated_entities = [
                e for e in entities
                if isinstance(e, dict) and len(e.get("name", "")) >= 2
            ]
            enames = {e["name"].lower().strip() for e in validated_entities}
            enames.add("user")
            validated_relations = [
                r for r in relations
                if isinstance(r, dict)
                and r.get("source", "").lower().strip() in enames
                and r.get("target", "").lower().strip() in enames
            ]
            return {
                "entities": validated_entities,
                "relations": validated_relations,
            }
        except Exception as e:
            logger.warning("[EntityExtractor] LLM extraction failed, falling back: %s", e)
            return self._fallback_extract(text)

    def _fallback_extract(self, text):
        entities = self._fallback_extract_entities(text)
        relations = self._fallback_extract_relations(text, entities)
        return {"entities": entities, "relations": relations}

    def _fallback_extract_entities(self, text):
        entities = []
        seen = set()
        for line in text.split("\n"):
            for match in re.finditer(r"[A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*", line):
                name = match.group(0).strip()
                if len(name) < 2:
                    continue
                key = name.lower()
                if key in seen or key in _STOPWORDS:
                    continue
                seen.add(key)
                entities.append({"name": name, "type": "unknown", "confidence": 0.3})
            for match in re.finditer(r"\b[a-z]{3,}\b", line):
                name = match.group(0).strip()
                key = name.lower()
                if key in seen or key in _STOPWORDS:
                    continue
                seen.add(key)
                entities.append({"name": name.capitalize(), "type": "unknown", "confidence": 0.2})
        return entities

    def _fallback_extract_relations(self, text, entities):
        relations = []
        entity_names = {e["name"].lower() for e in entities}
        text_lower = text.lower()
        verb_relations = {
            "builds": re.compile(r"\b(build|builds|built|making|made)\b"),
            "uses": re.compile(r"\b(use|uses|using|used)\b"),
            "likes": re.compile(r"\b(like|likes|loved|loves)\b"),
            "works_on": re.compile(r"\b(work\s+on|works\s+on|working\s+on)\b"),
            "switched_to": re.compile(r"\b(switch|switches|switched)\s+(?:from\s+\w+\s+)?to\b"),
        }
        for sentence in re.split(r"[.!?\n]", text_lower):
            entity_in_sentence = [n for n in entity_names if n in sentence]
            skip_words = {"i", "we", "you", "they"}
            targets = [e for e in entity_in_sentence if e not in skip_words]
            if not targets:
                continue
            for rel_type, vpat in verb_relations.items():
                if vpat.search(sentence):
                    for t in targets:
                        relations.append({
                            "source": "user",
                            "relation": "uses" if rel_type == "switched_to" else rel_type,
                            "target": t,
                            "confidence": 0.3,
                        })
        return relations

    def extract_from_conversation(self, user_message, ai_response):
        return self.extract(user_message)
