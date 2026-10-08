"""Phase 2b — Prometheus /metrics endpoint + OTel opt-in gate.

Verifies:
- ``/metrics`` is registered on the app and auth-gated via ``_require_auth``
  (401 when API_REQUIRE_AUTH=true, anonymous pass-through when disabled).
- Scraping returns the Prometheus text exposition format containing the
  ``mai_*`` families recorded by PrometheusMiddleware.
- POST bodies flow intact through PrometheusMiddleware (login parse path).
- ``MAI_OTEL_ENABLED`` is strictly opt-in: default off; enabling it succeeds
  even without the opentelemetry-instrumentation-* extras installed.
"""
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from api.server import app, _maybe_init_otel, _require_auth

# No lifespan context → mai stays unbootstrapped: fast, side-effect free.
client = TestClient(app)


# ── /metrics registration + auth gate ────────────────────────────


def test_metrics_route_registered_with_auth_dependency():
    routes = [r for r in app.routes if getattr(r, "path", "") == "/metrics"]
    assert routes, "/metrics route missing"
    dep_names = [
        getattr(dep.call, "__name__", "")
        for route in routes
        for dep in route.dependant.dependencies
    ]
    assert "_require_auth" in dep_names


def test_metrics_scrape_returns_prometheus_format():
    from api.server import _prometheus_active
    assert _prometheus_active is True, "PrometheusMiddleware failed to mount"

    # One request first so PrometheusMiddleware records an actual sample.
    health = client.get("/api/health")
    assert health.status_code == 200

    metrics = client.get("/metrics")
    if metrics.status_code == 401:
        pytest.skip("API_REQUIRE_AUTH enabled in this environment")
    assert metrics.status_code == 200
    assert metrics.headers["content-type"].startswith("text/plain")
    # A real labeled series (not just the # TYPE header) proves the middleware
    # is recording requests.
    assert "mai_http_requests_total{" in metrics.text


def test_metrics_auth_enforced_when_enabled(monkeypatch):
    bare_request = Request(
        scope={"type": "http", "method": "GET", "path": "/metrics", "headers": []}
    )

    monkeypatch.setattr("app.config_loader.API_REQUIRE_AUTH", True)
    with pytest.raises(HTTPException) as excinfo:
        _require_auth(bare_request)
    assert excinfo.value.status_code == 401

    # Auth disabled → the dependency passes through (returns None) and the
    # underlying resolver yields the anonymous user.
    monkeypatch.setattr("app.config_loader.API_REQUIRE_AUTH", False)
    assert _require_auth(bare_request) is None

    from api.auth import get_current_user
    assert get_current_user(bare_request) == "anonymous"


# ── POST body flows through the metrics middleware ────────────────


def test_post_body_flows_through_prometheus_middleware():
    # Valid LoginRequest body with unknown user → deterministic 401 (or 503
    # when the profile store is unavailable). A 422 would mean the body never
    # reached FastAPI's parser through the middleware chain.
    response = client.post(
        "/api/auth/login", json={"username": "metrics_test", "password": "wrongpw"}
    )
    assert response.status_code in (401, 503)


# ── OTel opt-in gate ──────────────────────────────────────────────


def test_otel_default_off(monkeypatch):
    monkeypatch.delenv("MAI_OTEL_ENABLED", raising=False)
    assert _maybe_init_otel() is False


def test_otel_opt_in_degrades_without_instrumentation_packages(monkeypatch):
    monkeypatch.setenv("MAI_OTEL_ENABLED", "true")
    # The opentelemetry-instrumentation-* extras are NOT installed in this
    # environment; init must still succeed via the guarded optional imports.
    assert _maybe_init_otel() is True

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    assert isinstance(trace.get_tracer_provider(), TracerProvider)


@pytest.mark.parametrize("value", ["1", "on", "yes"])
def test_otel_truthy_variants(monkeypatch, value):
    monkeypatch.setenv("MAI_OTEL_ENABLED", value)
    assert _maybe_init_otel() is True
