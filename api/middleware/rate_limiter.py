import logging
import threading
import time

from fastapi import HTTPException

logger = logging.getLogger("api.middleware.rate_limiter")


class RateLimiter:
    """Per-IP token-bucket rate limiter with per-route sliding windows.

    Route groups and their default limits (per 60 s window):

        chat    -> POST /api/chat ……………  60/min
        health  -> GET  /api/health ………… 300/min
        auth    -> POST /api/auth/* …………  20/min
        ingest  -> POST /api/knowledge/ingest  10/min
        status  -> frequent-poll endpoints … 120/min
        general -> everything else ………… 120/min

    Static asset paths are excluded by the middleware hook and never
    consume a token.
    """

    def __init__(self, max_buckets: int = 4096):
        self._limits: dict[str, int] = {
            "chat": 60,
            "health": 300,
            "auth": 20,
            "ingest": 10,
            "status": 120,
            "general": 120,
        }
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.RLock()
        self._max_buckets = max(64, max_buckets)

    # ── public API ──────────────────────────────────────────────────────

    def configure(
        self,
        chat: int = 60,
        health: int = 300,
        auth: int = 20,
        ingest: int = 10,
        status: int = 120,
        general: int = 120,
    ) -> None:
        """Update per-group rate limits (calls per 60 s window)."""
        with self._lock:
            self._limits.update(
                chat=chat, health=health, auth=auth,
                ingest=ingest, status=status, general=general,
            )

    def limits(self) -> dict[str, int]:
        """Return current limits copy."""
        with self._lock:
            return dict(self._limits)

    def check(
        self,
        key: str,
        path: str,
        method: str,
    ) -> dict:
        """Check *key* against the route group for *path*.

        Returns ``{"limit": …, "remaining": …, "reset": …}``.

        Raises ``HTTPException`` (429) with ``Retry-After`` header when
        the caller has exhausted their allowance.
        """
        group = self._route_group(path, method)
        with self._lock:
            limit = self._limits.get(group, 120)
            if limit <= 0:
                return {"limit": 0, "remaining": 0, "reset": 0}

            bucket_key = f"{key}:{group}"
            now = time.time()
            window_start = now - 60.0

            hits = [t for t in self._buckets.get(bucket_key, []) if t > window_start]

            if len(hits) >= limit:
                retry_after = int(60.0 - (now - hits[0]))
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Rate limit exceeded",
                        "group": group,
                        "limit": limit,
                        "reset_in": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            hits.append(now)
            self._buckets[bucket_key] = hits
            self._evict_stale(now)

            remaining = limit - len(hits)
            reset_at = int(hits[0] + 60.0) if hits else int(now + 60.0)

        return {
            "limit": limit,
            "remaining": max(remaining, 0),
            "reset": reset_at,
        }

    def _evict_stale(self, now: float) -> None:
        """Bound memory: drop buckets whose window has expired, then evict
        the oldest buckets when the map exceeds its cap."""
        if len(self._buckets) <= self._max_buckets:
            expired = [
                k for k, hits in self._buckets.items()
                if not hits or hits[-1] <= now - 60.0
            ]
            for k in expired:
                del self._buckets[k]
            return
        # Over cap: prune expired first, then drop the least-recently-active
        # buckets until within bounds.
        stale = [
            (k, hits[-1]) for k, hits in self._buckets.items()
            if not hits or hits[-1] <= now - 60.0
        ]
        stale.sort(key=lambda kv: kv[1])
        for k, _ in stale:
            self._buckets.pop(k, None)
            if len(self._buckets) <= self._max_buckets:
                break
        if len(self._buckets) > self._max_buckets:
            oldest = sorted(
                self._buckets.items(),
                key=lambda kv: kv[1][-1] if kv[1] else 0.0,
            )[:len(self._buckets) - self._max_buckets]
            for k, _ in oldest:
                self._buckets.pop(k, None)

    # ── static helpers ──────────────────────────────────────────────────

    STATIC_SUFFIXES = frozenset({
        "png", "jpg", "jpeg", "gif", "svg", "webp", "ico",
        "css", "js", "json", "woff2", "woff", "ttf", "html",
    })

    STATIC_PREFIXES = (
        "/static/", "/img/", "/css/", "/js/", "/assets/", "/favicon",
    )

    @classmethod
    def is_static_path(cls, path: str) -> bool:
        if path.startswith(cls.STATIC_PREFIXES) or path == "/":
            return True
        leaf = path.rsplit("/", 1)[-1]
        if "." in leaf and leaf.rsplit(".", 1)[-1].lower() in cls.STATIC_SUFFIXES:
            return True
        return False

    @staticmethod
    def _route_group(path: str, method: str) -> str:
        if path.startswith("/api/chat"):
            return "chat"
        if path.startswith("/api/auth/"):
            return "auth"
        if path == "/api/health":
            return "health"
        if path.startswith("/api/knowledge/ingest"):
            return "ingest"
        if path in (
            "/api/consciousness",
            "/api/voice/status",
            "/api/memory/stats",
            "/api/memory/timeline",
            "/api/status",
            "/api/stream",
        ):
            return "status"
        return "general"
