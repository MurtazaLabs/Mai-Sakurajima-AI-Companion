"""Phase 2d — plugin CLI/marketplace exposure + duplicate-copy cleanup.

Verifies:
- The shadowed flat plugin copies (plugins/<name>.py) are gone; the canonical
  <name>/manifest.json layout remains and is what PluginLoader loads.
- PluginState bugs are fixed (no ENABLED/INSTALLED members; ACTIVATED used).
- The lifecycle registry lives at plugins/data/lifecycle_registry.json, NOT in
  the marketplace catalog file (plugins/registry.json).
- The marketplace client works against the local file:// registry.
- /api/plugins routes use the app-wired lifecycle manager, the client-driven
  catalog (with built-in offline fallback), and auth on mutating endpoints.
- The CLI entry point runs (python -m plugins.cli).
"""
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes_plugins import (
    _BUILTIN_MARKETPLACE,
    router,
    set_lifecycle_manager,
)
from core.plugin_system import HookRegistry, PluginLoader
from plugins.lifecycle import (
    PluginRegistry,
    PluginRecord,
    PluginState,
    create_plugin_lifecycle_manager,
)
from plugins.marketplace_client import create_marketplace_client
from plugins.plugin_manifest import PluginManifestValidator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_URL = f"file:///{(PROJECT_ROOT / 'plugins' / 'registry.json').as_posix()}"

FLAT_PLUGINS = ["news", "weather", "system_monitor", "web_scraper", "example_plugin"]

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture
def manager(tmp_path):
    """An isolated lifecycle manager per test; routes wired to it."""
    mgr = create_plugin_lifecycle_manager(tmp_path / "plugins", HookRegistry())
    set_lifecycle_manager(mgr)
    yield mgr
    set_lifecycle_manager(None)


# ── Dedup: canonical layout only ─────────────────────────────────


def test_flat_duplicates_deleted():
    for name in FLAT_PLUGINS:
        assert not (PROJECT_ROOT / "plugins" / f"{name}.py").exists(), (
            f"shadowed flat copy plugins/{name}.py still present"
        )
        assert (PROJECT_ROOT / "plugins" / name / f"{name}.py").exists()
        assert (PROJECT_ROOT / "plugins" / name / "manifest.json").exists()


def test_loader_prefers_manifest_dir():
    loader = PluginLoader(HookRegistry(), str(PROJECT_ROOT / "plugins"))
    plugin = loader.load("example_plugin")
    assert plugin is not None
    # The loader initializes the plugin (on_load ran); lifecycle.enable()
    # is what transitions the state to "loaded".
    assert plugin.initialized is True


# ── PluginState fixes ────────────────────────────────────────────


def test_no_phantom_state_members():
    assert not hasattr(PluginState, "ENABLED")
    assert not hasattr(PluginState, "INSTALLED")
    assert hasattr(PluginState, "ACTIVATED")
    assert hasattr(PluginState, "DISCOVERED")


def test_get_enabled_plugins_returns_activated(tmp_path):
    is_valid, _errors, manifest = PluginManifestValidator.validate_manifest_file(
        PROJECT_ROOT / "plugins" / "example_plugin" / "manifest.json"
    )
    assert is_valid
    registry = PluginRegistry(tmp_path / "registry.json")
    record = PluginRecord(manifest=manifest, state=PluginState.ACTIVATED)
    registry.register(record)
    from plugins.lifecycle import PluginLifecycleManager

    mgr = PluginLifecycleManager(
        plugin_dir=tmp_path,
        registry=registry,
        hook_registry=HookRegistry(),
    )
    enabled = mgr.get_enabled_plugins()
    assert len(enabled) == 1
    assert enabled[0].manifest.name == "example_plugin"


def test_lifecycle_registry_lives_under_data(tmp_path):
    mgr = create_plugin_lifecycle_manager(tmp_path / "plugins", HookRegistry())
    assert mgr.registry.registry_path == tmp_path / "plugins" / "data" / "lifecycle_registry.json"
    # The marketplace catalog file must never be parsed as lifecycle records.
    assert not (tmp_path / "plugins" / "registry.json").exists() or (
        json.loads((tmp_path / "plugins" / "registry.json").read_text(encoding="utf-8")).get("plugins")
        is not None
    )


# ── Marketplace client (local file registry) ─────────────────────


def test_client_reads_local_registry():
    client = create_marketplace_client(REGISTRY_URL)
    results = client.search("weather")
    assert len(results) == 1
    assert results[0].name == "weather"
    assert results[0].package_url.startswith("file:")


# ── Routes ────────────────────────────────────────────────────────


def test_installed_route_uses_wired_manager(manager):
    resp = client.get("/api/plugins/installed")
    assert resp.status_code == 200
    assert resp.json() == []  # empty lifecycle registry, no AttributeError


def test_installed_route_503_without_manager():
    set_lifecycle_manager(None)
    resp = client.get("/api/plugins/installed")
    assert resp.status_code == 503


def test_marketplace_search_uses_registry(manager):
    resp = client.get("/api/plugins/marketplace/search", params={"q": "weather"})
    assert resp.status_code == 200
    data = resp.json()
    assert data and data[0]["name"] == "weather"
    assert data[0]["downloads"] > 0


def test_marketplace_search_falls_back_to_builtins(manager, monkeypatch):
    bad = MagicMock()
    bad.search.side_effect = RuntimeError("registry offline")
    monkeypatch.setattr("api.routes_plugins._marketplace_client", bad)

    resp = client.get("/api/plugins/marketplace/search", params={"q": "monitor"})
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert names == ["system_monitor"]
    assert len(_BUILTIN_MARKETPLACE) >= 5


def test_marketplace_detail_from_registry(manager):
    resp = client.get("/api/plugins/marketplace/news")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "news"
    assert body["source"] == "registry"
    assert body["package_url"].startswith("file:")


def test_marketplace_detail_unknown_404(manager):
    resp = client.get("/api/plugins/marketplace/does_not_exist")
    assert resp.status_code == 404


def test_install_via_api_end_to_end(manager, monkeypatch):
    # The local example_plugin is unsigned; the API-side policy gate requires
    # an explicit developer opt-in for unsigned packages.
    monkeypatch.setenv("MAI_ALLOW_UNSIGNED_PLUGINS", "1")
    resp = client.post(
        "/api/plugins/marketplace/install",
        json={"name": "example_plugin", "version": "latest", "force": False},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True

    listed = client.get("/api/plugins/installed").json()
    entry = next(p for p in listed if p["name"] == "example_plugin")
    assert entry["state"] == PluginState.DISCOVERED.value
    assert entry["enabled"] is False


def test_unsigned_install_blocked_by_default(manager):
    resp = client.post(
        "/api/plugins/marketplace/install",
        json={"name": "example_plugin", "version": "latest", "force": False},
    )
    assert resp.status_code == 400
    assert "unsigned" in resp.json()["detail"].lower()


def test_unsigned_install_opt_in_allows(manager, monkeypatch):
    monkeypatch.setenv("MAI_ALLOW_UNSIGNED_PLUGINS", "1")
    resp = client.post(
        "/api/plugins/marketplace/install",
        json={"name": "example_plugin", "version": "latest", "force": False},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True


def test_bogus_trusted_key_blocks_install(manager, monkeypatch, tmp_path):
    # The +trusted_keys surface is client-level only (the API never trusts
    # caller-supplied keys). A failed signature check must abort the install.
    monkeypatch.setenv("MAI_ALLOW_UNSIGNED_PLUGINS", "0")
    monkeypatch.setattr(
        "plugins.marketplace_client.verify_plugin_package",
        lambda *a, **k: (False, "signature did not match", None),
    )
    client_obj = create_marketplace_client(REGISTRY_URL)
    success, message, _path = client_obj.install_plugin(
        name="example_plugin",
        version="latest",
        force=False,
        trusted_keys=["kid-server-config"],
        lifecycle_manager=manager,
    )
    assert success is False
    assert "signature" in message.lower()


def test_enable_unknown_plugin_400(manager):
    resp = client.post("/api/plugins/marketplace/does_not_exist/enable")
    assert resp.status_code == 400
    assert "not installed" in resp.json()["detail"].lower()


def test_mutating_routes_require_auth(manager, monkeypatch):
    monkeypatch.setattr("app.config_loader.API_REQUIRE_AUTH", True)
    resp = client.post(
        "/api/plugins/marketplace/install", json={"name": "example_plugin"}
    )
    assert resp.status_code == 401


# ── CLI entry point ──────────────────────────────────────────────


def test_cli_help_runs():
    result = subprocess.run(
        [sys.executable, "-m", "plugins.cli", "--help"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert "Mai AI Plugin Manager" in result.stdout


def test_cli_list_runs_against_empty_dir(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "plugins.cli", "--plugin-dir", str(tmp_path), "list"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0
    assert "No plugins installed." in result.stderr
