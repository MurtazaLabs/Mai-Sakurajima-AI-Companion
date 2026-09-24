# memory/extractor.py
import re
import time
import logging

logger = logging.getLogger(__name__)

_EXTRACTION_PATTERNS = [
    ("preference", re.compile(
        r"\bmy favorite\s+\w+\s+is\s+(.+?)(?:[\.!]|$)",
        re.IGNORECASE
    )),
    ("preference", re.compile(
        r"\bi (?:like|enjoy|love)\s+(.+?)(?:[\.!]|$)",
        re.IGNORECASE
    )),
    ("preference_negative", re.compile(
        r"\bi (?:don't like|hate|dislike)\s+(.+?)(?:[\.!]|$)",
        re.IGNORECASE
    )),
    ("identity", re.compile(
        r"\bmy name is\s+(.+?)(?:[\.!]|$)",
        re.IGNORECASE
    )),
    ("identity", re.compile(
        r"\bi'?m\s+(.+?)(?:[\.!]|$)",
        re.IGNORECASE
    )),
    ("employment", re.compile(
        r"\bi work (?:at|as|for)\s+(.+?)(?:[\.!]|$)",
        re.IGNORECASE
    )),
    ("location", re.compile(
        r"\bi live (?:in|at|near)\s+(.+?)(?:[\.!]|$)",
        re.IGNORECASE
    )),
    ("goal", re.compile(
        r"\bi (?:want to|wanna|'?m going to)\s+(.+?)(?:[\.!]|$)",
        re.IGNORECASE
    )),
    ("goal", re.compile(
        r"\bi'?m learning\s+(.+?)(?:[\.!]|$)",
        re.IGNORECASE
    )),
    ("goal", re.compile(
        r"\bi'?ve (?:always )?dreamed of\s+(.+?)(?:[\.!]|$)",
        re.IGNORECASE
    )),
    ("emotional_state", re.compile(
        r"\bi feel\s+(.+?)(?:[\.!]|$)",
        re.IGNORECASE
    )),
]


class ExtractedKnowledge:

    def __init__(self, fact_type, value, confidence=0.6, source="fast"):
        self.type = fact_type
        self.value = str(value).strip()
        self.confidence = max(0.0, min(1.0, float(confidence)))
        self.source = source
        self.timestamp = time.time()

    def to_dict(self):
        return {
            "type": self.type,
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp,
        }

    def __repr__(self):
        return (
            f"<ExtractedKnowledge "
            f"type={self.type} "
            f"value={self.value[:30]}...>"
        )


class FastExtractor:

    def extract(self, text):
        if not text:
            return []

        text = str(text).strip()
        results = []
        seen = set()

        for fact_type, pattern in _EXTRACTION_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                value = match.strip().rstrip(".")
                if not value:
                    continue
                key = (fact_type, value.lower())
                if key not in seen:
                    seen.add(key)
                    confidence = 0.6
                    if fact_type in ("identity", "employment", "location"):
                        confidence = 0.8
                    results.append(
                        ExtractedKnowledge(
                            fact_type=fact_type,
                            value=value,
                            confidence=confidence,
                            source="fast",
                        )
                    )

        return results
