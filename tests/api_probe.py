"""HTTP probe shared by the integration and contract tests.

Both suites talk to the stack from ``docker-compose.test.yml`` (or any instance
at ``MAI_TEST_URL``) and skip when nothing answers, so an ordinary test run
still works without Docker.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_URL = "http://127.0.0.1:8000"
DEFAULT_TOKEN = "ci-integration-token"
TIMEOUT_SECONDS = 10.0


class ApiClient:
    """Minimal JSON-over-HTTP client for a running Mai API."""

    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        timeout: float = TIMEOUT_SECONDS,
    ) -> None:
        self.base_url = (base_url or os.environ.get("MAI_TEST_URL") or DEFAULT_URL).rstrip("/")
        self.token = token if token is not None else os.environ.get("MAI_TEST_TOKEN", DEFAULT_TOKEN)
        self.timeout = timeout

    def request(
        self, path: str, data: bytes | None = None, authenticated: bool = True
    ) -> tuple[int, str, str]:
        """Return ``(status, content_type, body)``; HTTP errors are returned, not raised."""
        headers = {"Accept": "application/json"}
        if authenticated and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(f"{self.base_url}{path}", data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return (
                    response.status,
                    response.headers.get("Content-Type", ""),
                    response.read().decode("utf-8", "replace"),
                )
        except urllib.error.HTTPError as exc:
            return (
                exc.code,
                exc.headers.get("Content-Type", ""),
                exc.read().decode("utf-8", "replace"),
            )

    def get(self, path: str, authenticated: bool = True) -> tuple[int, str, str]:
        return self.request(path, authenticated=authenticated)

    def get_json(self, path: str, authenticated: bool = True) -> tuple[int, Any]:
        status, _, body = self.get(path, authenticated=authenticated)
        try:
            return status, json.loads(body) if body else {}
        except json.JSONDecodeError:
            return status, body


def stack_available(client: ApiClient | None = None) -> bool:
    """True when an API answers its health probe (the probe needs no token)."""
    probe = client or ApiClient()
    try:
        status, _, _ = probe.get("/api/health")
    except OSError:
        return False
    return status == 200
