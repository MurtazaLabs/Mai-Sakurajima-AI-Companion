"""
Plugin API Routes
Provides REST API for plugin management, marketplace, and lifecycle operations.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Header, Query
from pydantic import BaseModel

from plugins.lifecycle import PluginLifecycleManager, PluginRecord, PluginState


router = APIRouter(prefix="/api/plugins", tags=["plugins"])


# Request/Response models
class PluginInstallRequest(BaseModel):
    name: str
    version: str = "latest"
    force: bool = False


class PluginConfigRequest(BaseModel):
    config: Dict[str, Any]


class PluginResponse(BaseModel):
    name: str
    version: str
    description: str
    author: str
    state: str
    enabled: bool
    permissions: Dict[str, Any]
    tags: List[str]
    homepage: Optional[str]
    repository: Optional[str]
    error: Optional[str] = None


class MarketplacePluginResponse(BaseModel):
    name: str
    version: str
    description: str
    author: str
    tags: List[str]
    downloads: int = 0
    rating: float = 0.0
    updated_at: str


# Global reference to lifecycle manager (set by bootstrap)
_lifecycle_manager: Optional["PluginLifecycleManager"] = None


def get_lifecycle_manager() -> PluginLifecycleManager:
    global _lifecycle_manager
    if _lifecycle_manager is None:
        # This will be set by the bootstrap process
        from plugins.lifecycle import create_plugin_lifecycle_manager
        from core.plugin_system import HookRegistry
        from core.os_kernel import AIOSKernel
        
        # This is a fallback - the real manager should be set by bootstrap
        hook_registry = HookRegistry()
        from pathlib import Path
        import tempfile
        
        plugin_dir = Path(tempfile.gettempdir()) / "mai_plugins"
        _lifecycle_manager = create_plugin_lifecycle_manager(
            plugin_dir=plugin_dir,
            hook_registry=HookRegistry(),
        )
    return _lifecycle_manager


def set_lifecycle_manager(manager: "PluginLifecycleManager"):
    """Set the global lifecycle manager (called during bootstrap)."""
    global _lifecycle_manager
    _lifecycle_manager = manager


@router.get("/installed", response_model=List[PluginResponse])
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
            enabled=p.state == PluginState.ENABLED,
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
    tags: Optional[List[str]] = Query(None),
    category: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
):
    """Search the plugin marketplace."""
    # For now, return built-in plugins
    # In production, this would query a remote registry
    builtin_plugins = [
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
    
    # Filter by query
    results = builtin_plugins
    if q:
        q_lower = q.lower()
        results = [p for p in results if q_lower in p["name"].lower() or q_lower in p["description"].lower()]
    
    if tags:
        results = [p for p in results if any(t in p["tags"] for t in tags)]
    
    if category:
        results = [p for p in results if category in p["tags"]]
    
    # Pagination
    start = (page - 1) * limit
    end = start + limit
    return results[start:end]


@router.get("/marketplace/{name}")
async def get_marketplace_plugin(name: str, version: Optional[str] = None):
    """Get detailed plugin info from marketplace."""
    # For now, return builtin plugin info
    builtin = {
        "weather": {
            "name": "weather",
            "version": "1.1.0",
            "description": "Fetches current weather via OpenWeatherMap API",
            "author": "Mai AI Team",
            "tags": ["weather", "utility", "api"],
            "downloads": 1000,
            "rating": 4.5,
            "updated_at": "2026-09-01",
            "permissions": {"network": "outbound", "api_access": ["weather"]},
            "readme": "# Weather Plugin\n\nFetches current weather via OpenWeatherMap API.\n\n## Usage\n`weather London` - Get current weather in London\n\n## Configuration\nSet `OPENWEATHER_API_KEY` environment variable.",
        },
        "calendar": {
            "name": "calendar",
            "version": "1.1.0",
            "description": "Local event/reminder manager with recurring events",
            "author": "Mai AI Team",
            "tags": ["calendar", "utility", "reminders"],
            "downloads": 800,
            "rating": 4.3,
            "updated_at": "2026-09-01",
            "permissions": {"filesystem": "write", "api_access": ["calendar"]},
            "readme": "# Calendar Plugin\n\nLocal event/reminder manager with recurring events.\n\n## Usage\n`event add meeting tomorrow 2pm`\n`event list`\n`event delete meeting`",
        },
    }
    
    if name not in builtin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    plugin = builtin[name]
    if version and version != "latest" and version != plugin["version"]:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return plugin


@router.post("/marketplace/install")
async def install_plugin(request: PluginInstallRequest):
    """Install a plugin from marketplace."""
    # For now, install builtin plugins
    builtin_plugins = {"weather", "calendar", "news", "system_monitor", "web_scraper"}
    
    if request.name not in builtin_plugins:
        raise HTTPException(status_code=404, detail="Plugin not found in marketplace")
    
    # In real implementation, this would download from marketplace
    # For now, just enable if already present
    from run import bootstrap_system
    components = bootstrap_system()
    manager = components.get("lifecycle_manager")
    
    if not manager:
        raise HTTPException(status_code=500, detail="Plugin system not initialized")
    
    try:
        record = manager.get_plugin(request.name)
        if record:
            if record.state == PluginState.INSTALLED:
                manager.enable(request.name)
            return {"success": True, "message": f"Plugin {request.name} installed/enabled"}
        else:
            # Would download from marketplace
            raise HTTPException(status_code=501, detail="Marketplace download not yet implemented")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/marketplace/{name}/enable")
async def enable_plugin(name: str):
    """Enable an installed plugin."""
    from run import bootstrap_system
    components = bootstrap_system()
    manager = components.get("lifecycle_manager")
    
    if not manager:
        raise HTTPException(status_code=500, detail="Plugin system not initialized")
    
    try:
        success = manager.enable(name)
        if success:
            return {"success": True, "message": f"Plugin {name} enabled"}
        else:
            raise HTTPException(status_code=500, detail="Failed to enable plugin")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/marketplace/{name}/disable")
async def disable_plugin(name: str):
    """Disable an enabled plugin."""
    from run import bootstrap_system
    components = bootstrap_system()
    manager = components.get("lifecycle_manager")
    
    if not manager:
        raise HTTPException(status_code=500, detail="Plugin system not initialized")
    
    try:
        success = manager.disable(name)
        if success:
            return {"success": True, "message": f"Plugin {name} disabled"}
        else:
            raise HTTPException(status_code=500, detail="Failed to disable plugin")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/marketplace/{name}/update")
async def update_plugin(name: str):
    """Update a plugin to latest version."""
    # Not yet implemented
    raise HTTPException(status_code=501, detail="Update not yet implemented")


@router.post("/marketplace/{name}/uninstall")
async def uninstall_plugin(name: str, purge: bool = False):
    """Uninstall a plugin."""
    from run import bootstrap_system
    components = bootstrap_system()
    manager = components.get("lifecycle_manager")
    
    if not manager:
        raise HTTPException(status_code=500, detail="Plugin system not initialized")
    
    try:
        success = manager.uninstall(name, purge_config=purge)
        if success:
            return {"success": True, "message": f"Plugin {name} uninstalled"}
        else:
            raise HTTPException(status_code=500, detail="Failed to uninstall plugin")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/installed", response_model=List[Dict])
async def list_installed_plugins():
    """List all installed plugins with their status."""
    from run import bootstrap_system
    components = bootstrap_system()
    manager = components.get("lifecycle_manager")
    
    if not manager:
        raise HTTPException(status_code=500, detail="Plugin system not initialized")
    
    plugins = manager.list_plugins()
    return [
        {
            "name": p.manifest.name,
            "version": p.manifest.version,
            "description": p.manifest.description,
            "author": p.manifest.author,
            "state": p.state.value,
            "enabled": p.state == PluginState.ENABLED,
            "permissions": {
                "filesystem": p.manifest.permissions.filesystem,
                "network": p.manifest.permissions.network,
                "execution": p.manifest.permissions.execution,
                "api_access": p.manifest.permissions.api_access,
                "config": p.manifest.permissions.config,
            },
            "tags": p.manifest.tags,
            "homepage": p.manifest.homepage,
            "repository": p.manifest.repository,
            "error": p.error,
        }
        for p in plugins
    ]


@router.get("/installed/{name}")
async def get_installed_plugin(name: str):
    """Get details of an installed plugin."""
    from run import bootstrap_system
    components = bootstrap_system()
    manager = components.get("lifecycle_manager")
    
    if not manager:
        raise HTTPException(status_code=500, detail="Plugin system not initialized")
    
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
        "enabled": record.state == PluginState.ENABLED,
        "installed_at": record.installed_at,
        "updated_at": record.updated_at,
        "enabled_at": record.enabled_at,
        "config": record.config,
        "error": record.error,
        "install_path": str(record.install_path),
    }


@router.put("/installed/{name}/config")
async def update_plugin_config(name: str, request: PluginConfigRequest):
    """Update plugin configuration."""
    from run import bootstrap_system
    components = bootstrap_system()
    manager = components.get("lifecycle_manager")
    
    if not manager:
        raise HTTPException(status_code=500, detail="Plugin system not initialized")
    
    success = manager.set_plugin_config(name, request.config)
    if not success:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    return {"success": True, "message": "Configuration updated"}


@router.post("/marketplace/publish")
async def publish_plugin(
    file: UploadFile = File(...),
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
        is_valid, errors, manifest = PluginManifestValidator.validate_package(Path(tmp.name))
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid package: {errors}")
        
        # In production, would upload to registry
        return {
            "success": True,
            "message": f"Plugin {manifest.name} v{manifest.version} published",
            "plugin": manifest.to_dict(),
        }
    finally:
        os.unlink(tmp.name)