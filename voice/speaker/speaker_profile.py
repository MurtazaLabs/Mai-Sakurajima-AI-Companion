from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field


@dataclass
class SpeakerProfile:
    name: str
    embedding: list[float] | None = None
    confidence: float = 0.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    sample_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SpeakerProfile:
        return cls(**data)
