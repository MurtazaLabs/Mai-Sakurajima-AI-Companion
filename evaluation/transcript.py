# evaluation/transcript.py
# M9 · Session transcript — per-turn records (input, response, runtime
# evidence snapshot) persisted as JSONL. Tolerant load; never the source of
# truth for runtime state — a review artifact only.
import json
import logging
import time

logger = logging.getLogger(__name__)


class TurnRecord:
    """One evaluated turn: what the user said, what Mai said, and the
    dev-side evidence snapshot captured right after generation."""

    __slots__ = ("evidence", "index", "response", "timestamp", "user_input")

    def __init__(self, index=0, user_input="", response="", evidence=None, timestamp=None):
        self.index = int(index or 0)
        self.user_input = str(user_input or "")
        self.response = str(response or "")
        self.evidence = dict(evidence or {})
        self.timestamp = timestamp if timestamp is not None else time.time()

    def to_dict(self):
        return {
            "index": self.index,
            "user_input": self.user_input,
            "response": self.response,
            "evidence": dict(self.evidence),
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict):
            return None
        return cls(
            index=data.get("index", 0),
            user_input=data.get("user_input", ""),
            response=data.get("response", ""),
            evidence=data.get("evidence"),
            timestamp=data.get("timestamp"),
        )


class SessionTranscript:
    """Ordered turn list with JSONL persistence.

    The transcript is append-only per session; `save` writes the full log,
    `load` restores tolerantly (bad lines skipped, never fatal).
    """

    def __init__(self, turns=None):
        self._turns = list(turns or [])

    def add(self, user_input, response, evidence=None):
        record = TurnRecord(
            index=len(self._turns),
            user_input=user_input,
            response=response,
            evidence=evidence,
        )
        self._turns.append(record)
        return record

    def __len__(self):
        return len(self._turns)

    def __iter__(self):
        return iter(self._turns)

    def __getitem__(self, idx):
        return self._turns[idx]

    def turns(self):
        return list(self._turns)

    def to_dict(self):
        return [t.to_dict() for t in self._turns]

    def save(self, path):
        path = str(path)
        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(json.dumps(t.to_dict(), ensure_ascii=False) + "\n" for t in self._turns)

    @classmethod
    def load(cls, path):
        transcript = cls()
        try:
            with open(str(path), "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = TurnRecord.from_dict(json.loads(line))
                        if record is not None:
                            transcript._turns.append(record)
                    except Exception as e:
                        logger.debug("[SessionTranscript] skip bad line: %s", e)
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug("[SessionTranscript] load failed: %s", e)
        return transcript
