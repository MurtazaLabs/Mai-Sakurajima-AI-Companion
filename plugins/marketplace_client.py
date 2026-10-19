"""
Plugin Marketplace Client
Fetches plugins from remote registry, downloads packages, and handles installation
with dependency resolution and version compatibility checks.
"""
import hashlib
import json
import os
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from plugins.dependency_resolver import (
    CircularDependencyError,
    DependencyResolver,
    VersionConflictError,
)
from plugins.plugin_manifest import PluginManifest
from plugins.signing import verify_plugin_package


def _unsigned_installs_allowed() -> bool:
    """Unsigned marketplace installs are a developer opt-in only.

    Packages are verified against trusted keys by default; physically absorbing
    an unsigned install means running arbitrary untrusted code, so it requires
    MAI_ALLOW_UNSIGNED_PLUGINS=1 to accept.
    """
    return os.environ.get("MAI_ALLOW_UNSIGNED_PLUGINS", "").strip().lower() in (
        "1", "true", "yes"
    )


@dataclass
class RegistryPlugin:
    """Plugin entry from the marketplace registry."""
    name: str
    version: str
    description: str
    author: str
    entry_point: str
    api_version: str
    permissions: dict[str, Any]
    dependencies: list[dict[str, Any]]
    hooks: list[str]
    min_mai_version: str
    max_mai_version: str | None
    homepage: str | None
    repository: str | None
    license: str
    tags: list[str]
    downloads: int
    rating: float
    updated_at: str
    package_url: str
    checksum: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RegistryPlugin":
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            author=data["author"],
            entry_point=data["entry_point"],
            api_version=data["api_version"],
            permissions=data["permissions"],
            dependencies=data["dependencies"],
            hooks=data["hooks"],
            min_mai_version=data["min_mai_version"],
            max_mai_version=data.get("max_mai_version"),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
            license=data["license"],
            tags=data["tags"],
            downloads=data.get("downloads", 0),
            rating=data.get("rating", 0.0),
            updated_at=data["updated_at"],
            package_url=data["package_url"],
            checksum=data["checksum"],
        )

    def to_manifest(self) -> PluginManifest:
        """Convert to PluginManifest for dependency resolution."""
        from plugins.plugin_manifest import PluginDependency, PluginPermission
        permissions = PluginPermission(
            filesystem=self.permissions.get("filesystem", "none"),
            network=self.permissions.get("network", "none"),
            execution=self.permissions.get("execution", "none"),
            api_access=self.permissions.get("api_access", []),
            config=self.permissions.get("config", "none"),
        )
        dependencies = [
            PluginDependency(name=d["name"], version=d["version"], optional=d.get("optional", False))
            for d in self.dependencies
        ]
        return PluginManifest(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            entry_point=self.entry_point,
            api_version=self.api_version,
            permissions=permissions,
            dependencies=dependencies,
            hooks=self.hooks,
            min_mai_version=self.min_mai_version,
            max_mai_version=self.max_mai_version,
            homepage=self.homepage,
            repository=self.repository,
            license=self.license,
            tags=self.tags,
        )


class MarketplaceClient:
    """Client for interacting with the Mai AI Plugin Marketplace."""

    DEFAULT_REGISTRY_URL = "https://plugins.mai-ai.dev/registry.json"
    LOCAL_REGISTRY_PATH = Path.home() / ".config" / "mai" / "marketplace" / "registry.json"

    def __init__(self, registry_url: str | None = None, cache_dir: Path | None = None):
        self.registry_url = registry_url or self.DEFAULT_REGISTRY_URL
        self.cache_dir = cache_dir or (Path.home() / ".cache" / "mai" / "marketplace")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._registry_cache: dict[str, Any] | None = None
        self._registry_plugins: dict[str, RegistryPlugin] = {}

    def fetch_registry(self, force_refresh: bool = False) -> dict[str, Any]:
        """
        Fetch the plugin registry from remote URL.
        
        Args:
            force_refresh: If True, bypass cache and fetch fresh
            
        Returns:
            Registry data as dictionary
        """
        if not force_refresh and self._registry_cache is not None:
            return self._registry_cache

        # An explicitly configured file:// registry is authoritative — never
        # shadow it with the remote-fetch cache (which may hold stale or
        # placeholder entries).
        is_local_registry = self.registry_url.startswith("file://")

        # Try to load from local cache first (remote registries only)
        if (
            not is_local_registry
            and self.LOCAL_REGISTRY_PATH.exists()
            and not force_refresh
        ):
            try:
                with open(self.LOCAL_REGISTRY_PATH) as f:
                    self._registry_cache = json.load(f)
                    self._parse_registry()
                    return self._registry_cache
            except (json.JSONDecodeError, OSError):
                pass

        # Fetch from remote or local file
        try:
            # Handle file:// URLs
            if self.registry_url.startswith("file://"):
                local_path = self.registry_url[7:]  # Remove file://
                # On Windows, file:///E:/path becomes /E:/path after [7:], need to strip leading /
                if local_path.startswith("/") and len(local_path) > 2 and local_path[2] == ":":
                    local_path = local_path[1:]  # Remove leading slash for Windows drive letter
                with open(local_path, "r") as f:
                    data = json.load(f)
                self._registry_cache = data
                self._parse_registry()
                return data
            
            req = urllib.request.Request(
                self.registry_url,
                headers={"User-Agent": "MaiAI/1.0 (marketplace client)"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                self._registry_cache = data
                self._parse_registry()
                
                # Save to local cache
                self.LOCAL_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(self.LOCAL_REGISTRY_PATH, "w") as f:
                    json.dump(data, f, indent=2)
                
                return data
        except urllib.error.URLError as e:
            if self._registry_cache is not None:
                return self._registry_cache
            raise RuntimeError(f"Failed to fetch registry: {e}")
        except (OSError, json.JSONDecodeError) as e:
            if self._registry_cache is not None:
                return self._registry_cache
            raise RuntimeError(f"Failed to load registry: {e}")

    def _parse_registry(self):
        """Parse registry into RegistryPlugin objects."""
        self._registry_plugins = {}
        if self._registry_cache:
            for plugin_data in self._registry_cache.get("plugins", []):
                plugin = RegistryPlugin.from_dict(plugin_data)
                self._registry_plugins[plugin.name] = plugin

    def search(self, query: str = "", tags: list[str] | None = None,
               category: str | None = None) -> list[RegistryPlugin]:
        """
        Search the marketplace for plugins.
        
        Args:
            query: Search query string
            tags: Filter by tags
            category: Filter by category (first tag)
            
        Returns:
            List of matching RegistryPlugin objects
        """
        self.fetch_registry()
        
        results = list(self._registry_plugins.values())
        
        if query:
            q = query.lower()
            results = [p for p in results 
                      if q in p.name.lower() or q in p.description.lower()]
        
        if tags:
            results = [p for p in results if any(t in p.tags for t in tags)]
        
        if category:
            results = [p for p in results if category in p.tags]
        
        return results

    def get_plugin(self, name: str, version: str | None = None) -> RegistryPlugin | None:
        """Get a specific plugin from the registry."""
        self.fetch_registry()
        plugin = self._registry_plugins.get(name)
        if plugin and version and version != "latest" and version != plugin.version:
            return None
        return plugin

    def download_package(self, plugin: RegistryPlugin, 
                        verify_checksum: bool = True) -> Path:
        """
        Download a plugin package from the marketplace.
        
        Args:
            plugin: RegistryPlugin to download
            verify_checksum: Whether to verify SHA256 checksum
            
        Returns:
            Path to downloaded .mpkg file
        """
        package_url = plugin.package_url
        if not package_url:
            raise ValueError(f"No package URL for plugin {plugin.name}")
        
        # Download to cache
        cache_path = self.cache_dir / f"{plugin.name}-{plugin.version}.mpkg"
        
        try:
            # Handle file:// URLs
            if package_url.startswith("file://"):
                local_path = package_url[7:]  # Remove file://
                # On Windows, file:///E:/path becomes /E:/path after [7:], need to strip leading /
                if local_path.startswith("/") and len(local_path) > 2 and local_path[2] == ":":
                    local_path = local_path[1:]  # Remove leading slash for Windows drive letter
                shutil.copy2(local_path, cache_path)
            else:
                req = urllib.request.Request(
                    package_url,
                    headers={"User-Agent": "MaiAI/1.0 (marketplace client)"}
                )
                with urllib.request.urlopen(req, timeout=60) as resp:
                    with open(cache_path, "wb") as f:
                        f.write(resp.read())
        except (urllib.error.URLError, OSError) as e:
            raise RuntimeError(f"Failed to download package: {e}")
        
        # Verify checksum
        if verify_checksum:
            expected = plugin.checksum.replace("sha256:", "")
            actual = self._compute_sha256(cache_path)
            if expected and expected != actual:
                cache_path.unlink()
                raise ValueError(f"Checksum mismatch for {plugin.name}: expected {expected}, got {actual}")
        
        return cache_path

    def _compute_sha256(self, path: Path) -> str:
        """Compute SHA256 hash of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def install_plugin(self, name: str, version: str = "latest",
                      force: bool = False, trusted_keys: list[bytes] | None = None,
                      lifecycle_manager=None) -> tuple[bool, str, Path | None]:
        """
        Install a plugin from the marketplace with full dependency resolution.
        
        Args:
            name: Plugin name
            version: Version to install (or "latest")
            force: Force reinstall
            trusted_keys: Trusted public keys for signature verification
            lifecycle_manager: PluginLifecycleManager instance (required)
            
        Returns:
            Tuple of (success, message, package_path)
        """
        if lifecycle_manager is None:
            return False, "Lifecycle manager required", None
        
        # Fetch plugin info
        plugin = self.get_plugin(name, version)
        if not plugin:
            return False, f"Plugin '{name}' not found in registry", None
        
        if version == "latest":
            version = plugin.version
        
        # Check version compatibility with MAI
        from app.config_loader import MAI_VERSION
        current_version = tuple(map(int, MAI_VERSION.split(".")))
        min_version = tuple(map(int, plugin.min_mai_version.split(".")))
        if current_version < min_version:
            return False, f"Plugin requires MAI version >= {plugin.min_mai_version}, current is {MAI_VERSION}", None
        
        if plugin.max_mai_version:
            max_version = tuple(map(int, plugin.max_mai_version.split(".")))
            if current_version > max_version:
                return False, f"Plugin requires MAI version <= {plugin.max_mai_version}, current is {MAI_VERSION}", None
        
        # Check if already installed
        existing = lifecycle_manager.registry.get(name)
        if existing and not force:
            existing_manifest = PluginManifest.from_dict(existing["manifest"])
            if existing_manifest.version == plugin.version:
                return False, f"Version {plugin.version} already installed. Use force=True to reinstall.", None
        
        # Resolve dependencies
        try:
            resolver = DependencyResolver(lifecycle_manager.registry)
            installed_plugins = {}
            for pname, data in lifecycle_manager.registry._registry.items():
                if data.get("state") in ("activated", "installed", "discovered"):
                    installed_plugins[pname] = PluginManifest.from_dict(data["manifest"])
            
            available_packages = {}
            # Include this plugin and its dependencies
            available_packages[plugin.name] = [plugin.version]
            for dep in plugin.dependencies:
                dep_plugin = self.get_plugin(dep["name"])
                if dep_plugin:
                    available_packages[dep_plugin.name] = [dep_plugin.version]
            
            resolved_deps = resolver.resolve_dependencies(
                plugin.to_manifest(),
                installed_plugins,
                available_packages
            )
        except VersionConflictError as e:
            return False, f"Version conflict: {e}", None
        except CircularDependencyError as e:
            return False, f"Circular dependency: {e}", None
        except Exception as e:
            return False, f"Dependency resolution failed: {e}", None
        
        # Install dependencies first
        for dep in resolved_deps:
            if dep.name != name:  # Skip the main plugin
                dep_plugin = self.get_plugin(dep.name)
                if dep_plugin:
                    success, msg, _ = self.install_plugin(
                        dep.name, dep.resolved_version, force, trusted_keys, lifecycle_manager
                    )
                    if not success:
                        return False, f"Failed to install dependency {dep.name}: {msg}", None
        
        # Download main plugin package
        package_path = self.download_package(plugin)
        
        try:
            if trusted_keys:
                is_valid, error, _ = verify_plugin_package(package_path, trusted_keys)
                if not is_valid:
                    return False, f"Signature verification failed: {error}", package_path
            elif not _unsigned_installs_allowed():
                return False, (
                    "Package is not signed with a trusted key and unsigned installs "
                    "are disabled; provide trusted_keys or set "
                    "MAI_ALLOW_UNSIGNED_PLUGINS=1 (developer opt-in)"
                ), package_path

            # Install via lifecycle manager
            record = lifecycle_manager.install(
                package_path,
                verify_signature=bool(trusted_keys),
                force=force,
                trusted_keys=trusted_keys
            )

            return True, f"Plugin {name} v{version} installed successfully", package_path
            
        except Exception as e:
            return False, f"Installation failed: {e}", package_path


def create_marketplace_client(registry_url: str | None = None) -> MarketplaceClient:
    """Factory function to create a configured MarketplaceClient."""
    return MarketplaceClient(registry_url)


if __name__ == "__main__":
    # Test the client
    client = create_marketplace_client("file:///E:/Mai_ai/plugins/registry.json")
    plugins = client.search()
    print(f"Found {len(plugins)} plugins:")
    for p in plugins:
        print(f"  {p.name} v{p.version}: {p.description[:50]}...")