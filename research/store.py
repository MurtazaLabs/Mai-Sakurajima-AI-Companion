"""Atomic JSON persistence for research jobs."""
from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path

from research.models import ResearchJob

logger = logging.getLogger(__name__)


class ResearchStore:

    def __init__(self, path, history_limit: int = 100):
        self.path = Path(path)
        self.history_limit = max(10, int(history_limit))
        self._lock = threading.RLock()
        self._jobs: dict[str, ResearchJob] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("[Research] store unreadable (%s); starting empty", exc)
            return
        for item in raw.get("jobs", []) if isinstance(raw, dict) else []:
            try:
                job = ResearchJob.from_dict(item)
            except TypeError:
                continue
            self._jobs[job.id] = job

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        ordered = sorted(self._jobs.values(), key=lambda job: job.created_at)
        if len(ordered) > self.history_limit:
            ordered = ordered[-self.history_limit:]
            self._jobs = {job.id: job for job in ordered}
        payload = {"version": 1, "jobs": [job.to_dict() for job in ordered]}
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, self.path)

    def upsert(self, job: ResearchJob) -> ResearchJob:
        with self._lock:
            job.touch()
            self._jobs[job.id] = job
            self._save()
            return job

    def get(self, job_id: str) -> ResearchJob | None:
        with self._lock:
            return self._jobs.get(str(job_id))

    def all(self) -> list[ResearchJob]:
        with self._lock:
            return sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)

    def queued(self) -> list[ResearchJob]:
        with self._lock:
            return sorted(
                (job for job in self._jobs.values() if job.status == "queued"),
                key=lambda job: job.created_at,
            )

    def count_status(self, status: str) -> int:
        with self._lock:
            return sum(1 for job in self._jobs.values() if job.status == status)

    def stats(self) -> dict:
        with self._lock:
            statuses: dict[str, int] = {}
            for job in self._jobs.values():
                statuses[job.status] = statuses.get(job.status, 0) + 1
            return {"total": len(self._jobs), "statuses": statuses}
