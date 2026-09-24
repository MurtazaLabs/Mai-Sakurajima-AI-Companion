import time
import threading

import pytest
from fastapi import HTTPException

from api.middleware.rate_limiter import RateLimiter


class TestRateLimitBuckets:

    def test_buckets_capped(self):
        rl = RateLimiter(max_buckets=64)
        for i in range(200):
            rl.check(f"1.2.3.{i}", "/api/chat", "POST")
            rl.check(f"1.2.3.{i}", "/api/status", "GET")
        assert len(rl._buckets) <= 64

    def test_normal_path_untouched_after_cap(self):
        rl = RateLimiter(max_buckets=64)
        for i in range(200):
            rl.check(f"1.2.3.{i}", "/api/chat", "POST")
        r = rl.check("9.9.9.9", "/api/health", "GET")
        assert r["remaining"] > 0

    def test_stale_buckets_pruned_within_cap(self):
        rl = RateLimiter(max_buckets=64)
        now = time.time()
        # Seed one bucket far in the past so it looks stale
        rl._buckets["old:chat"] = [now - 120.0]
        rl.check("1.1.1.1", "/api/chat", "POST")
        assert "old:chat" not in rl._buckets

    def test_rate_limit_enforced(self):
        rl = RateLimiter(max_buckets=64)
        rl.configure(chat=3)
        for _ in range(3):
            rl.check("1.1.1.1", "/api/chat", "POST")
        with pytest.raises(HTTPException) as exc:
            rl.check("1.1.1.1", "/api/chat", "POST")
        assert exc.value.status_code == 429

    def test_route_groups(self):
        rl = RateLimiter.__new__(RateLimiter)
        assert rl._route_group("/api/chat", "POST") == "chat"
        assert rl._route_group("/api/health", "GET") == "health"
        assert rl._route_group("/api/auth/login", "POST") == "auth"
        assert rl._route_group("/api/status", "GET") == "status"
        assert rl._route_group("/api/other", "GET") == "general"

    def test_static_paths(self):
        assert RateLimiter.is_static_path("/js/app.js") is True
        assert RateLimiter.is_static_path("/") is True
        assert RateLimiter.is_static_path("/api/chat") is False