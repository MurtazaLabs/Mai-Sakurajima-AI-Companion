"""Smoke test for the real container stack (``docker-compose.test.yml``).

The CI integration stage brings the stack up before running this module. A
plain ``pytest`` run skips it, so no Docker is needed for the ordinary suite.
"""
from __future__ import annotations

import pytest
from api_probe import ApiClient, stack_available

client = ApiClient()

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not stack_available(client), reason=f"no Mai API at {client.base_url}"),
]


def test_health_is_public_and_ready():
    status, payload = client.get_json("/api/health", authenticated=False)
    assert status == 200
    assert payload["ready"] is True


def test_protected_route_refuses_anonymous_requests():
    status, _, _ = client.get("/api/status", authenticated=False)
    assert status == 401


def test_status_returns_a_state_snapshot():
    status, payload = client.get_json("/api/status")
    assert status == 200
    assert isinstance(payload, dict)
    assert payload


def test_web_ui_is_served():
    status, content_type, body = client.get("/")
    assert status == 200
    assert "text/html" in content_type
    assert "<html" in body.lower()
