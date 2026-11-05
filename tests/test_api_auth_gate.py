"""API auth gate — middleware coverage (audit Oct 25 2026, finding 3).

Verifies:
- auth is forced on whenever the configured API host is not loopback;
- /api/* is rejected with 401 when auth is on, except the explicitly open
  set (login/refresh to obtain a token, SSO redirects, /api/health probe);
- the default loopback desktop setup is unchanged (no auth).
"""
import pytest
from fastapi.testclient import TestClient

from api.auth import api_auth_required
from api.server import app
from app import config_loader

# No lifespan context → mai stays unbootstrapped: fast, side-effect free.
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_warn_flag():
    api_auth_required.warned = False
    yield
    api_auth_required.warned = False


def _set_auth(monkeypatch, host="127.0.0.1", enabled=False):
    monkeypatch.setattr(config_loader, "API_HOST", host)
    monkeypatch.setattr(config_loader, "API_REQUIRE_AUTH", enabled)


def test_loopback_host_keeps_auth_opt_in(monkeypatch):
    _set_auth(monkeypatch)
    assert api_auth_required() is False


def test_non_loopback_ip_forces_auth(monkeypatch):
    _set_auth(monkeypatch, host="0.0.0.0")
    assert api_auth_required() is True


def test_non_loopback_hostname_forces_auth(monkeypatch):
    _set_auth(monkeypatch, host="maipc")
    assert api_auth_required() is True


def test_memory_routes_401_when_forced_on(monkeypatch):
    _set_auth(monkeypatch, host="0.0.0.0")
    resp = client.get("/api/memory")
    assert resp.status_code == 401


def test_memory_routes_ok_when_auth_off(monkeypatch):
    _set_auth(monkeypatch)
    resp = client.get("/api/memory")
    assert resp.status_code != 401


def test_exempt_paths_stay_open_under_forced_auth(monkeypatch):
    _set_auth(monkeypatch, host="0.0.0.0")
    health = client.get("/api/health")
    assert health.status_code == 200
    # OIDC provider start is an SSO redirect target: middleware must not 401
    # it first — unknown provider answers 404 from the handler itself.
    oidc = client.get("/api/auth/oidc/login/unknown")
    assert oidc.status_code == 404


def test_health_401_never_leaks_when_gated(monkeypatch):
    _set_auth(monkeypatch, enabled=True)
    resp = client.get("/api/system/config")
    assert resp.status_code == 401
