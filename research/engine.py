"""Research engine — queue, worker, verified artifacts, honest failures."""
from __future__ import annotations

import logging
import threading
import time

import config.research as cfg
from research.artifacts import ResearchArtifacts
from research.fetch import fetch_text
from research.models import (
    CANCELLED,
    DONE,
    FAILED,
    QUEUED,
    RUNNING,
    ResearchJob,
)
from research.search import search_web
from research.store import ResearchStore

logger = logging.getLogger(__name__)


class ResearchEngine:

    def __init__(self, store: ResearchStore, artifacts=None, fetcher=None,
                 searcher=None, event_bus=None, continuity=None, presence=None,
                 max_sources=None, max_chars=None, timeout=None, max_queue=None,
                 search_enabled=None, search_url=None, search_results=None,
                 autonomous_allowed=None, worker=True, browser_mode=None,
                 browser_fetcher=None):
        self.store = store
        self.artifacts = artifacts or ResearchArtifacts(cfg.RESEARCH_ARTIFACT_DIR)
        self.fetcher = fetcher or fetch_text
        self.searcher = searcher or search_web
        self.event_bus = event_bus
        self.continuity = continuity
        self.presence = presence
        self.max_sources = int(max_sources or cfg.RESEARCH_MAX_SOURCES)
        self.max_chars = int(max_chars or cfg.RESEARCH_MAX_CHARS)
        self.timeout = float(timeout or cfg.RESEARCH_FETCH_TIMEOUT)
        self.max_queue = max(1, int(max_queue or cfg.RESEARCH_MAX_QUEUE))
        self.search_enabled = (
            cfg.RESEARCH_SEARCH_ENABLED if search_enabled is None else bool(search_enabled)
        )
        self.search_url = search_url or cfg.RESEARCH_SEARCH_URL
        self.search_results = int(search_results or cfg.RESEARCH_SEARCH_RESULTS)
        self.autonomous_allowed = (
            cfg.RESEARCH_AUTONOMOUS if autonomous_allowed is None else bool(autonomous_allowed)
        )
        self.default_depth = cfg.RESEARCH_DEFAULT_DEPTH
        self.browser_mode = (browser_mode or cfg.RESEARCH_BROWSER).strip().lower()
        self.browser_fetcher = browser_fetcher
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._thread = None
        self.resumed = self.resume_interrupted()
        if worker:
            self.start_worker()

    # -- lifecycle ----------------------------------------------------

    def start_worker(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="ResearchWorker")
        self._thread.start()

    def stop_worker(self) -> None:
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=3.0)
        self._thread = None

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._wake.wait(2.0)
            self._wake.clear()
            if self._stop.is_set():
                break
            try:
                while self.process_next() is not None and not self._stop.is_set():
                    pass
            except Exception as exc:
                logger.exception("[Research] worker loop error: %s", exc)

    def resume_interrupted(self) -> int:
        """Jobs left ``running`` by a dead process become queued again."""
        resumed = 0
        for job in self.store.all():
            if job.status == RUNNING:
                job.status = QUEUED
                job.error = "interrupted; requeued"
                self.store.upsert(job)
                resumed += 1
        if resumed:
            logger.info("[Research] requeued %d interrupted job(s)", resumed)
        return resumed

    # -- public API ---------------------------------------------------

    def start(self, query: str = "", depth: str | None = None, urls=None,
              autonomous: bool = False) -> dict:
        if autonomous:
            blocked = self._autonomous_block()
            if blocked:
                return {"error": blocked}

        clean_urls = [str(url).strip() for url in (urls or []) if str(url).strip()]
        query = str(query or "").strip()
        if not query and not clean_urls:
            return {"error": "query required"}
        if not clean_urls and not self.search_enabled:
            return {"error": "search disabled; provide seed URLs"}

        depth = (depth or self.default_depth).strip().lower()
        if depth not in cfg.RESEARCH_DEPTHS:
            return {"error": f"unknown depth: {depth}"}
        if self.store.count_status(QUEUED) + self.store.count_status(RUNNING) >= self.max_queue:
            return {"error": "queue_full"}

        job = ResearchJob(
            query=query or clean_urls[0],
            seed_urls=clean_urls,
            depth=depth,
            autonomous=bool(autonomous),
        )
        self.store.upsert(job)
        self._publish_state()
        self._wake.set()
        logger.info("[Research] queued %s (%s)", job.id, job.query[:80])
        return {"job": job.summary()}

    def process_next(self) -> dict | None:
        queued = self.store.queued()
        if not queued:
            return None
        return self.process(queued[0].id)

    def process(self, job_id: str) -> dict | None:
        job = self.store.get(job_id)
        if job is None or job.status != QUEUED:
            return None
        job.status = RUNNING
        job.started_at = time.time()
        job.step = 1
        job.error = ""
        self.store.upsert(job)
        self._publish("data.research.started", {
            "id": job.id, "query": job.query, "depth": job.depth,
        })
        self._publish_state()
        self._checkpoint(job, "started")

        try:
            self._collect(job)
            if self._is_cancelled(job):
                return self._finish_cancelled(job)

            notes = job.notes
            if not any(note.get("summary") for note in notes):
                raise RuntimeError("no readable sources fetched")
            artifact, error = self.artifacts.write(job, notes)
            if error:
                raise RuntimeError(error)
            job.artifact_path = artifact
            job.status = DONE
            job.finished_at = time.time()
            job.step = 4
            self.store.upsert(job)
            self._clear_checkpoint(job)
            self._publish("data.research.finished", {
                "id": job.id, "query": job.query, "sources": len(job.sources),
                "artifact": artifact,
            })
            self._publish_state()
            logger.info("[Research] %s done (%d source(s))", job.id, len(job.sources))
            return job.summary()
        except Exception as exc:
            job.status = FAILED
            job.error = str(exc)
            job.finished_at = time.time()
            self.store.upsert(job)
            self._clear_checkpoint(job)
            self._publish("data.research.failed", {
                "id": job.id, "query": job.query, "error": job.error,
            })
            self._publish_state()
            logger.warning("[Research] %s failed: %s", job.id, job.error)
            return job.summary()

    # -- collection ---------------------------------------------------

    def _collect(self, job: ResearchJob) -> None:
        urls = list(job.seed_urls)
        if not urls:
            found = self._search(job.query)
            urls = [item["url"] for item in found]

        budget = min(cfg.RESEARCH_DEPTHS.get(job.depth, 2), self.max_sources)
        urls = urls[:budget]
        if not urls:
            raise RuntimeError("no sources found")

        for url in urls:
            if self._is_cancelled(job):
                return
            result = self._fetch(url)
            source = {
                "url": result.get("final_url") or url,
                "title": result.get("title") or "",
                "chars": int(result.get("chars") or 0),
                "error": result.get("error") or "",
            }
            job.sources = job.sources + [source]
            text = (result.get("text") or "").strip()
            if text:
                job.notes = job.notes + [{
                    "url": source["url"],
                    "title": source["title"],
                    "summary": self._summarize(text),
                }]
            job.step = min(3, job.step + 1)
            self.store.upsert(job)
            self._checkpoint(job, f"fetched {source['url'][:80]}")
            self._publish("data.research.source_fetched", {
                "id": job.id, "url": source["url"], "chars": source["chars"],
                "error": source["error"],
            })

    def _fetch(self, url: str) -> dict:
        """Headless browser when configured and available, urllib otherwise."""
        if self.browser_mode != "urllib":
            fetcher = self.browser_fetcher
            if fetcher is None and self.browser_mode == "playwright":
                from research.browser import fetch_with_browser, playwright_available
                if not playwright_available():
                    return {"url": url, "final_url": url, "title": "", "text": "",
                            "chars": 0, "truncated": False,
                            "error": "playwright not installed"}
                fetcher = lambda target: fetch_with_browser(
                    target, timeout=self.timeout, max_chars=self.max_chars
                )
            elif fetcher is None:
                from research.browser import fetch_with_browser, playwright_available
                if playwright_available():
                    fetcher = lambda target: fetch_with_browser(
                        target, timeout=self.timeout, max_chars=self.max_chars
                    )
            if fetcher is not None:
                result = fetcher(url)
                if result.get("text") or not result.get("error"):
                    return result
                logger.info("[Research] browser fetch failed, using HTTP: %s",
                            result.get("error"))
        return self.fetcher(url, timeout=self.timeout, max_chars=self.max_chars)

    def _search(self, query: str) -> list[dict]:
        if not self.search_enabled:
            return []
        result = self.searcher(
            query, limit=self.search_results, endpoint=self.search_url,
            timeout=self.timeout,
        )
        if result.get("error") and not result.get("results"):
            logger.info("[Research] search unavailable: %s", result.get("error"))
        return list(result.get("results") or [])

    @staticmethod
    def _summarize(text: str, limit: int = 1200) -> str:
        clean = " ".join(text.split())
        return clean[:limit]

    # -- reporting ----------------------------------------------------

    def status(self) -> dict:
        stats = self.store.stats()
        statuses = stats.get("statuses", {})
        return {
            "enabled": True,
            "queued": statuses.get(QUEUED, 0),
            "running": statuses.get(RUNNING, 0),
            "done": statuses.get(DONE, 0),
            "failed": statuses.get(FAILED, 0),
            "cancelled": statuses.get(CANCELLED, 0),
            "total": stats.get("total", 0),
            "ready": len(self._ready()),
            "artifact_dir": str(self.artifacts.root),
            "resumed": self.resumed,
        }

    def list(self, limit: int = 20) -> list[dict]:
        limit = max(1, min(int(limit or 20), 100))
        return [job.summary() for job in self.store.all()[:limit]]

    def get(self, job_id: str) -> dict | None:
        job = self.store.get(job_id)
        return job.to_dict() if job is not None else None

    def report(self, job_id: str, mark_reported: bool = True) -> dict:
        job = self.store.get(job_id)
        if job is None:
            return {"error": "unknown_job"}
        if job.status not in (DONE, FAILED, CANCELLED):
            return {"error": "job_not_finished", "status": job.status}
        text = ""
        if job.artifact_path:
            try:
                from pathlib import Path
                text = Path(job.artifact_path).read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning("[Research] artifact unreadable: %s", exc)
        if not text:
            lines = [f"# {job.query}", ""]
            for note in job.notes:
                lines.append(f"- {note.get('title') or note.get('url')}: "
                             f"{(note.get('summary') or '')[:300]}")
            text = "\n".join(lines)
        if mark_reported and job.status == DONE and not job.reported:
            job.reported = True
            self.store.upsert(job)
            self._publish_state()
        return {
            "id": job.id,
            "query": job.query,
            "status": job.status,
            "artifact": job.artifact_path,
            "sources": len(job.sources),
            "error": job.error,
            "text": text,
        }

    def cancel(self, job_id: str) -> dict:
        job = self.store.get(job_id)
        if job is None:
            return {"error": "unknown_job"}
        if job.status in (DONE, FAILED, CANCELLED):
            return {"error": "already_finished", "status": job.status}
        job.status = CANCELLED
        job.finished_at = time.time()
        self.store.upsert(job)
        self._clear_checkpoint(job)
        self._publish_state()
        return {"cancelled": job.id}

    def brief_line(self) -> str:
        ready = self._ready()
        if not ready:
            return ""
        latest = ready[0]
        count = len(ready)
        noun = "report" if count == 1 else "reports"
        return f"Research: {count} {noun} ready (latest: {latest.query[:60]})"

    def tick(self) -> dict:
        before = self.store.count_status(QUEUED)
        result = self.process_next()
        return {
            "ran": result is not None,
            "queued": self.store.count_status(QUEUED),
            "was_queued": before,
            "result": result,
        }

    def health(self) -> dict:
        ready = self._ready()
        return {
            "status": "ok",
            "running": bool(self._thread and self._thread.is_alive()),
            "queued": self.store.count_status(QUEUED),
            "ready": len(ready),
            "last_error": next(
                (job.error for job in self.store.all() if job.status == FAILED), ""
            ),
        }

    # -- internals ----------------------------------------------------

    def _ready(self) -> list[ResearchJob]:
        return [job for job in self.store.all() if job.status == DONE and not job.reported]

    def _autonomous_block(self) -> str:
        if not self.autonomous_allowed:
            return "autonomous_disabled"
        presence = self.presence
        if presence is None:
            return ""
        try:
            if getattr(presence, "quiet_mode", False):
                return "quiet_mode"
            activity = getattr(presence, "activity", "idle")
            if activity != "idle":
                return f"activity_{activity}"
        except Exception as exc:
            logger.warning("[Research] presence gate failed: %s", exc)
        return ""

    def _is_cancelled(self, job: ResearchJob) -> bool:
        current = self.store.get(job.id)
        return current is not None and current.status == CANCELLED

    def _finish_cancelled(self, job: ResearchJob) -> dict:
        job.status = CANCELLED
        job.finished_at = time.time()
        self.store.upsert(job)
        self._clear_checkpoint(job)
        self._publish_state()
        return job.summary()

    def _checkpoint(self, job: ResearchJob, note: str) -> None:
        if self.continuity is None:
            return
        try:
            self.continuity.checkpoints.save(
                task_id=f"research:{job.id}",
                step=job.step,
                state={"query": job.query, "sources": len(job.sources)},
                note=note[:200],
            )
        except Exception as exc:
            logger.warning("[Research] checkpoint failed: %s", exc)

    def _clear_checkpoint(self, job: ResearchJob) -> None:
        if self.continuity is None:
            return
        try:
            self.continuity.checkpoints.clear(f"research:{job.id}")
        except Exception as exc:
            logger.warning("[Research] checkpoint clear failed: %s", exc)

    def _publish(self, topic: str, payload: dict) -> None:
        if self.event_bus is None:
            return
        try:
            from core.mai_message import publish_event
            publish_event(self.event_bus, topic, payload, source="research")
        except Exception as exc:
            logger.warning("[Research] publish %s failed: %s", topic, exc)

    def _publish_state(self) -> None:
        statuses = self.status()
        self._publish("state.research.updated", {
            "queued": statuses["queued"],
            "running": statuses["running"],
            "done": statuses["done"],
            "ready": statuses["ready"],
        })
