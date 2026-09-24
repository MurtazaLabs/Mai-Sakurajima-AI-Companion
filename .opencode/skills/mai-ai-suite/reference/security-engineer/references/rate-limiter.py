"""RateLimiter — Per-IP token-bucket + sliding-window rate limiter for FastAPI.

Load this file when the user needs the full RateLimiter implementation.
Usage:
    limiter = RateLimiter()
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
"""

import time
import logging
import threading
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, Request

logger = logging.getLogger("api.middleware.rate_limiter")

_STATIC_PREFIXES = ("/static/", "/css/", "/js/", "/img/", "/assets/", "/favicon")
_STATIC_SUFFIXES = (".css", ".js", ".png", ".jpg", ".svg", ".ico", ".woff2", ".json")


class TokenBucket:
    """Token bucket for burst tolerance.

    Refills at rate tokens/second up to burst capacity.
    A request passes if at least 1.0 tokens are available.
    """

    __slots__ = ("rate", "burst", "tokens", "last_refill")

    def __init__(self, rate: float, burst: int) -> None:
        self.rate = rate
        self.burst = float(burst)
        self.tokens = float(burst)
        self.last_refill = time.time()

    def consume(self, now: float) -> bool:
        delta = now - self.last_refill
        self.tokens = min(self.burst, self.tokens + delta * self.rate)
        self.last_refill = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False


class SlidingWindow:
    """Sliding window log for sustained rate enforcement.

    Stores timestamps of requests in the current 60-second window.
    """

    __slots__ = ("limit", "timestamps")

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.timestamps: List[float] = []

    def allow(self, now: float) -> Tuple[bool, int]:
        window_start = now - 60.0
        self.timestamps = [t for t in self.timestamps if t > window_start]
        if len(self.timestamps) < self.limit:
            self.timestamps.append(now)
            return True, self.limit - len(self.timestamps)
        return False, 0


class RateLimiter:
    """Per-IP token-bucket + sliding-window rate limiter.

    Combines token-bucket (burst tolerance) with sliding-window (sustained rate).
    Both must pass for the request to be allowed.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._limits: Dict[str, int] = {
            "chat": 60,
            "health": 300,
            "auth": 20,
            "ingest": 10,
            "status": 120,
            "general": 120,
        }
        self._burst: Dict[str, int] = {
            "chat": 10,
            "health": 30,
            "auth": 5,
            "ingest": 3,
            "status": 15,
            "general": 15,
        }
        self._buckets: Dict[str, Dict[str, "TokenBucket"]] = {}
        self._windows: Dict[str, Dict[str, "SlidingWindow"]] = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300.0

    def configure(
        self,
        chat: int = 60,
        health: int = 300,
        auth: int = 20,
        ingest: int = 10,
        status: int = 120,
        general: int = 120,
    ) -> None:
        with self._lock:
            self._limits.update(
                chat=chat, health=health, auth=auth,
                ingest=ingest, status=status, general=general,
            )

    def limits(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._limits)

    def check_request(self, request: Request) -> bool:
        path = request.url.path
        if self._is_static(path):
            return True
        group = self._route_group(path, request.method)
        client_ip = request.client.host if request.client else "unknown"
        return self._check(client_ip, group, time.time())

    def _check(self, key: str, group: str, now: float) -> bool:
        with self._lock:
            self._maybe_cleanup(now)
            limit = self._limits.get(group, self._limits["general"])
            burst = self._burst.get(group, self._burst["general"])

            bucket = self._buckets.setdefault(key, {}).setdefault(
                group, TokenBucket(limit / 60.0, burst)
            )
            window = self._windows.setdefault(key, {}).setdefault(
                group, SlidingWindow(limit)
            )

            if not bucket.consume(now):
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests — burst limit exceeded",
                    headers={"Retry-After": "1"},
                )
            allowed, remaining = window.allow(now)
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests — rate limit exceeded",
                    headers={"Retry-After": "60"},
                )
            return True

    def _route_group(self, path: str, method: str) -> str:
        if path.startswith("/api/chat"):
            return "chat"
        if path.startswith("/api/health"):
            return "health"
        if path.startswith("/api/auth/"):
            return "auth"
        if path.startswith("/api/knowledge/ingest"):
            return "ingest"
        if path.startswith(("/api/status", "/api/system/status")):
            return "status"
        return "general"

    def _is_static(self, path: str) -> bool:
        if path.startswith(_STATIC_PREFIXES):
            return True
        if any(path.endswith(suffix) for suffix in _STATIC_SUFFIXES):
            return True
        return False

    def _maybe_cleanup(self, now: float) -> None:
        if now - self._last_cleanup < self._cleanup_interval:
            return
        self._last_cleanup = now
        cutoff = now - 120.0
        for key in list(self._windows.keys()):
            for group in list(self._windows[key].keys()):
                sw = self._windows[key][group]
                sw.timestamps = [t for t in sw.timestamps if t > cutoff]
                if not sw.timestamps:
                    del self._windows[key][group]
                    self._buckets[key].pop(group, None)
            if not self._windows[key]:
                del self._windows[key]
                self._buckets.pop(key, None)
