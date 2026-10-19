"""
Plugin API Routes
Provides REST API for plugin management, marketplace, and lifecycle operations.

Phase 2d wiring:
- Marketplace search/detail/install are backed by the real
  ``plugins.marketplace_client`` (local ``plugins/registry.json`` via file://
  URL, built-in catalog as offline fallback).
- The lifecycle manager is the app-wired instance (set by the runtime
  builder via ``set_lifecycle_manager``); routes no longer boot the whole
  system per request.
- Mutating routes require auth (``api.auth.get_current_user`` — the same
  single source the server's ``_require_auth`` delegates to).
"""
import logging
import os
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel

from api.auth import get_current_user
from plugins.lifecycle import (
    PluginLifecycleError,
    PluginLifecycleManager,
    PluginState,
)

logger = logging.getLogger("Mai.Plugins")

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


# Request/Response models
class PluginInstallRequest(BaseModel):
    name: str
    version: str = "latest"
    force: bool = False


class PluginConfigRequest(BaseModel):
    config: dict[str, Any]


class PluginResponse(BaseModel):
    name: str
    version: str
    description: str
    author: str
    state: str
    enabled: bool
    permissions: dict[str, Any]
    tags: list[str]
    homepage: str | None
    repository: str | None
    error: str | None = None


class MarketplacePluginResponse(BaseModel):
    name: str
    version: str
    description: str
    author: str
    tags: list[str]
    downloads: int = 0
    rating: float = 0.0
    updated_at: str


# Global reference to lifecycle manager (set by the runtime builder)
_lifecycle_manager: Optional["PluginLifecycleManager"] = None

# Lazily built marketplace client (local registry file, remote fallback)
_marketplace_client = None


def get_lifecycle_manager() -> PluginLifecycleManager:
    """Return the app-wired lifecycle manager (set by the runtime builder)."""
    if _lifecycle_manager is None:
        raise HTTPException(status_code=503, detail="Plugin system not initialized")
    return _lifecycle_manager


def set_lifecycle_manager(manager: "PluginLifecycleManager"):
    """Set the global lifecycle manager (called during bootstrap)."""
    global _lifecycle_manager
    _lifecycle_manager = manager


def _get_marketplace_client():
    """Lazily build a MarketplaceClient backed by the local registry file."""
    global _marketplace_client
    if _marketplace_client is None:
        from plugins.marketplace_client import create_marketplace_client

        registry_path = (
            Path(__file__).resolve().parents[1] / "plugins" / "registry.json"
        )
        if registry_path.exists():
            # file:///E:/Mai_ai/plugins/registry.json — client handles the
            # Windows drive-letter form and never touches the network.
            _marketplace_client = create_marketplace_client(
                f"file:///{registry_path.as_posix()}"
            )
        else:
            _marketplace_client = create_marketplace_client()
    return _marketplace_client


def _registry_plugin_summary(p) -> dict[str, Any]:
    return {
        "name": p.name,
        "version": p.version,
        "description": p.description,
        "author": p.author,
        "tags": p.tags,
        "downloads": p.downloads,
        "rating": p.rating,
        "updated_at": p.updated_at,
    }


def _registry_plugin_detail(p) -> dict[str, Any]:
    data = _registry_plugin_summary(p)
    data.update(
        {
            "entry_point": p.entry_point,
            "api_version": p.api_version,
            "permissions": p.permissions,
            "dependencies": p.dependencies,
            "hooks": p.hooks,
            "min_mai_version": p.min_mai_version,
            "max_mai_version": p.max_mai_version,
            "homepage": p.homepage,
            "repository": p.repository,
            "license": p.license,
            "package_url": p.package_url,
            "source": "registry",
        }
    )
    return data


# Offline fallback catalog (used only when the registry cannot be read)
_BUILTIN_MARKETPLACE = [
    {
        "name": "weather",
        "version": "1.1.0",
        "description": "Fetches current weather via OpenWeatherMap API",
        "author": "Mai AI Team",
        "tags": ["weather", "utility", "api"],
        "downloads": 1000,
        "rating": 4.5,
        "updated_at": "2026-09-01",
    },
    {
        "name": "calendar",
        "version": "1.1.0",
        "description": "Local event/reminder manager with recurring events",
        "author": "Mai AI Team",
        "tags": ["calendar", "utility", "reminders"],
        "downloads": 800,
        "rating": 4.3,
        "updated_at": "2026-09-01",
    },
    {
        "name": "news",
        "version": "1.0.0",
        "description": "Fetches news headlines from multiple sources",
        "author": "Mai AI Team",
        "tags": ["news", "utility", "api"],
        "downloads": 500,
        "rating": 4.0,
        "updated_at": "2026-09-01",
    },
    {
        "name": "system_monitor",
        "version": "1.0.0",
        "description": "System resource monitoring and alerts",
        "author": "Mai AI Team",
        "tags": ["system", "monitoring", "utility"],
        "downloads": 300,
        "rating": 4.2,
        "updated_at": "2026-09-01",
    },
    {
        "name": "web_scraper",
        "version": "1.0.0",
        "description": "Web content extraction and summarization",
        "author": "Mai AI Team",
        "tags": ["web", "scraper", "utility"],
        "downloads": 200,
        "rating": 3.8,
        "updated_at": "2026-09-01",
    },
]

_BUILTIN_DETAILS = {
    "weather": {
        **_BUILTIN_MARKETPLACE[0],
        "permissions": {"network": "outbound", "api_access": ["weather"]},
        "readme": "# Weather Plugin\n\nFetches current weather via OpenWeatherMap API.\n\n## Usage\n`weather London` - Get current weather in London\n\n## Configuration\nSet `OPENWEATHER_API_KEY` environment variable.",
    },
    "calendar": {
        **_BUILTIN_MARKETPLACE[1],
        "permissions": {"filesystem": "write", "api_access": ["calendar"]},
        "readme": "# Calendar Plugin\n\nLocal event/reminder manager with recurring events.\n\n## Usage\n`event add meeting tomorrow 2pm`\n`event list`\n`event delete meeting`",
    },
}


def _query_marketplace(q: str, tags: list[str] | None, category: str | None) -> list[dict[str, Any]]:
    """Query the marketplace registry; fall back to the built-in catalog."""
    try:
        client = _get_marketplace_client()
        plugins = client.search(query=q or "", tags=tags, category=category)
        return [_registry_plugin_summary(p) for p in plugins]
    except Exception as exc:
        logger.warning(
            "[Plugins] Marketplace registry unavailable (%s) — using built-in catalog",
            exc,
        )
        results = _BUILTIN_MARKETPLACE
        if q:
            q_lower = q.lower()
            results = [
                p
                for p in results
                if q_lower in p["name"].lower()
                or q_lower in p["description"].lower()
            ]
        if tags:
            results = [p for p in results if any(t in p["tags"] for t in tags)]
        if category:
            results = [p for p in results if category in p["tags"]]
        return results


@router.get("/installed", response_model=list[PluginResponse])
async def list_installed_plugins():
    """List all installed plugins with their status."""
    manager = get_lifecycle_manager()
    plugins = manager.list_plugins()

    return [
        PluginResponse(
            name=p.manifest.name,
            version=p.manifest.version,
            description=p.manifest.description,
            author=p.manifest.author,
            state=p.state.value,
            enabled=p.state == PluginState.ACTIVATED,
            permissions={
                "filesystem": p.manifest.permissions.filesystem,
                "network": p.manifest.permissions.network,
                "execution": p.manifest.permissions.execution,
                "api_access": p.manifest.permissions.api_access,
                "config": p.manifest.permissions.config,
            },
            tags=p.manifest.tags,
            homepage=p.manifest.homepage,
            repository=p.manifest.repository,
            error=p.error,
        )
        for p in plugins
    ]


@router.get("/marketplace/search")
async def search_marketplace(
    q: str = "",
    tags: list[str] | None = Query(None),  # noqa: B008  FastAPI DI idiom
    category: str | None = None,
    page: int = 1,
    limit: int = 20,
):
    """Search the plugin marketplace (local registry, built-in fallback)."""
    results = _query_marketplace(q, tags, category)

    # Pagination
    start = (page - 1) * limit
    end = start + limit
    return results[start:end]


@router.get("/marketplace/{name}")
async def get_marketplace_plugin(name: str, version: str | None = None):
    """Get detailed plugin info from the marketplace registry."""
    try:
        client = _get_marketplace_client()
        plugin = client.get_plugin(name, version)
        if plugin is not None:
            return _registry_plugin_detail(plugin)
    except Exception as exc:
        logger.warning(
            "[Plugins] Marketplace registry unavailable (%s) — using built-in catalog",
            exc,
        )

    builtin = _BUILTIN_DETAILS.get(name)
    if builtin is None:
        raise HTTPException(status_code=404, detail="Plugin not found")

    if version and version != "latest" and version != builtin["version"]:
        raise HTTPException(status_code=404, detail="Version not found")

    return builtin


@router.post("/marketplace/install")
async def install_plugin(
    request: PluginInstallRequest, _: None = Depends(get_current_user)
):
    """Install a plugin from the marketplace via the marketplace client."""
    manager = get_lifecycle_manager()
    try:
        client = _get_marketplace_client()
        success, message, _package_path = client.install_plugin(
            name=request.name,
            version=request.version,
            force=request.force,
            lifecycle_manager=manager,
        )
    except PluginLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.warning("[Plugins] Install failed for %s: %s", request.name, exc)
        raise HTTPException(status_code=500, detail=str(exc))

    if not success:
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)
    return {"success": True, "message": message}


@router.post("/marketplace/{name}/enable")
async def enable_plugin(name: str, _: None = Depends(get_current_user)):
    """Enable an installed plugin."""
    manager = get_lifecycle_manager()
    try:
        success = manager.enable(name)
        if success:
            return {"success": True, "message": f"Plugin {name} enabled"}
        raise HTTPException(status_code=500, detail="Failed to enable plugin")
    except PluginLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/marketplace/{name}/disable")
async def disable_plugin(name: str, _: None = Depends(get_current_user)):
    """Disable an enabled plugin."""
    manager = get_lifecycle_manager()
    try:
        success = manager.disable(name)
        if success:
            return {"success": True, "message": f"Plugin {name} disabled"}
        raise HTTPException(status_code=500, detail="Failed to disable plugin")
    except PluginLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/marketplace/{name}/update")
async def update_plugin(name: str, _: None = Depends(get_current_user)):
    """Update a plugin to latest version."""
    # Not yet implemented
    raise HTTPException(status_code=501, detail="Update not yet implemented")


@router.post("/marketplace/{name}/uninstall")
async def uninstall_plugin(
    name: str, purge: bool = False, _: None = Depends(get_current_user)
):
    """Uninstall a plugin."""
    manager = get_lifecycle_manager()
    try:
        success = manager.uninstall(name, purge_config=purge)
        if success:
            return {"success": True, "message": f"Plugin {name} uninstalled"}
        raise HTTPException(status_code=500, detail="Failed to uninstall plugin")
    except PluginLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/installed/{name}")
async def get_installed_plugin(name: str):
    """Get details of an installed plugin."""
    manager = get_lifecycle_manager()
    record = manager.get_plugin(name)
    if not record:
        raise HTTPException(status_code=404, detail="Plugin not found")

    return {
        "name": record.manifest.name,
        "version": record.manifest.version,
        "description": record.manifest.description,
        "author": record.manifest.author,
        "entry_point": record.manifest.entry_point,
        "api_version": record.manifest.api_version,
        "permissions": {
            "filesystem": record.manifest.permissions.filesystem,
            "network": record.manifest.permissions.network,
            "execution": record.manifest.permissions.execution,
            "api_access": record.manifest.permissions.api_access,
            "config": record.manifest.permissions.config,
        },
        "dependencies": [
            {"name": d.name, "version": d.version, "optional": d.optional}
            for d in record.manifest.dependencies
        ],
        "hooks": record.manifest.hooks,
        "min_mai_version": record.manifest.min_mai_version,
        "max_mai_version": record.manifest.max_mai_version,
        "homepage": record.manifest.homepage,
        "repository": record.manifest.repository,
        "license": record.manifest.license,
        "tags": record.manifest.tags,
        "state": record.state.value,
        "enabled": record.state == PluginState.ACTIVATED,
        "installed_at": record.installed_at,
        "updated_at": record.updated_at,
        "enabled_at": record.enabled_at,
        "config": record.config,
        "error": record.error,
        "install_path": str(record.install_path),
    }


@router.put("/installed/{name}/config")
async def update_plugin_config(
    name: str, request: PluginConfigRequest, _: None = Depends(get_current_user)
):
    """Update plugin configuration."""
    manager = get_lifecycle_manager()
    success = manager.set_plugin_config(name, request.config)
    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found")

    return {"success": True, "message": "Configuration updated"}


@router.post("/marketplace/publish")
async def publish_plugin(
    file: UploadFile = File(...),  # noqa: B008  FastAPI DI idiom
    api_key: str = Header(..., alias="X-API-Key"),
):
    """Publish a plugin to the marketplace (authenticated)."""
    # Verify API key
    if not api_key or not api_key.startswith("mai_plugins_"):
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Validate package
    if not file.filename.endswith(".mpkg"):
        raise HTTPException(status_code=400, detail="Package must be .mpkg file")

    content = await file.read()

    # Save to temp and validate
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mpkg", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from plugins.plugin_manifest import PluginManifestValidator
        is_valid, errors, manifest = PluginManifestValidator.validate_package(Path(tmp_path))

        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid package: {errors}")

        # In production, would upload to registry
        return {
            "success": True,
            "message": f"Plugin {manifest.name} v{manifest.version} published",
            "plugin": manifest.to_dict(),
        }
    finally:
        os.unlink(tmp_path)
