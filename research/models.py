"""Research job model."""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
CANCELLED = "cancelled"
TERMINAL = (DONE, FAILED, CANCELLED)


@dataclass
class ResearchJob:
    query: str = ""
    id: str = field(default_factory=lambda: "res_" + uuid.uuid4().hex[:10])
    seed_urls: list = field(default_factory=list)
    depth: str = "standard"
    status: str = QUEUED
    step: int = 0
    sources: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    artifact_path: str = ""
    error: str = ""
    autonomous: bool = False
    reported: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    started_at: float = 0.0
    finished_at: float = 0.0

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> ResearchJob:
        known = {field_name for field_name in cls.__dataclass_fields__}
        return cls(**{key: value for key, value in (data or {}).items() if key in known})

    def summary(self) -> dict:
        return {
            "id": self.id,
            "query": self.query,
            "status": self.status,
            "depth": self.depth,
            "sources": len(self.sources),
            "artifact": self.artifact_path,
            "error": self.error,
            "created_at": self.created_at,
        }
