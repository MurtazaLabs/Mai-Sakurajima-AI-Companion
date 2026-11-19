"""Contract checks for the HTTP surface clients depend on.

The smoke test proves the stack is alive; these pin its shapes, so a renamed
route or a dropped field fails loudly instead of surfacing in the UI.
"""
from __future__ import annotations

import pytest
from api_probe import ApiClient, stack_available

client = ApiClient()

pytestmark = [
    pytest.mark.skipif(not stack_available(client), reason=f"no Mai API at {client.base_url}"),
]

CORE_PATHS = ("/api/health", "/api/status", "/api/memory", "/api/knowledge/ingest")


def test_openapi_advertises_the_core_routes():
    status, document = client.get_json("/openapi.json", authenticated=False)
    assert status == 200
    missing = [path for path in CORE_PATHS if path not in document["paths"]]
    assert not missing, f"routes missing from OpenAPI: {missing}"


def test_health_payload_shape():
    status, payload = client.get_json("/api/health", authenticated=False)
    assert status == 200
    assert set(payload) == {"status", "ready"}
    assert isinstance(payload["ready"], bool)


def test_unauthorized_responses_keep_the_detail_shape():
    status, payload = client.get_json("/api/status", authenticated=False)
    assert status == 401
    assert "detail" in payload
