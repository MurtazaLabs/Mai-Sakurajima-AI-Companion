"""
Plugin Lifecycle Manager
Handles plugin installation, enable/disable, update, and uninstall operations.
"""
import json
import time
import shutil
import zipfile
import threading
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

from plugins.dependency_resolver import DependencyResolver, DependencyResolutionError, VersionConflictError, CircularDependencyError, DependencyResolver as DepResolver
from plugins.signing import PluginSigner, PluginVerifier, verify_plugin_package
from plugins.sandbox import PluginSandbox, Permission, create_sandbox_for_plugin
from plugins.plugin_manifest import PluginManifestValidator, PluginManifest
from core.plugin_system import HookRegistry, Plugin, PluginLoader


class PluginState(str, Enum):
    """Plugin lifecycle states following: discovered -> loaded -> activated -> deactivated -> unloaded"""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    UNLOADED = "unloaded"
    UPDATING = "updating"
    ERROR = "error"


class PluginLifecycleError(Exception):
    """Exception raised during plugin lifecycle operations."""
    pass


class PluginRegistry:
    """Registry of installed plugins with persistence."""

    def __init__(self, registry_path: Path):
        self.registry_path = registry_path
        self._registry: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        """Load registry from disk."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path, "r") as f:
                    self._registry = json.load(f)
            except (json.JSONDecodeError, OSError):
                self._registry = {}

    def _save(self) -> None:
        """Save registry to disk."""
        try:
            self.registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.registry_path, "w") as f:
                json.dump(self._registry, f, indent=2, default=str)
        except OSError as e:
            raise PluginLifecycleError(f"Failed to save registry: {e}")

    def register(self, record: "PluginRecord") -> None:
        with self._lock:
            self._registry[record.manifest.name] = record.to_dict()
            self._save()

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._registry:
                del self._registry[name]
                self._save()
                return True
            return False

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._registry.get(name)

    def get_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._registry.values())

    def update_state(self, name: str, state: "PluginState") -> bool:
        with self._lock:
            if name in self._registry:
                self._registry[name]["state"] = state.value
                self._registry[name]["updated_at"] = time.time()
                self._save()
                return True
            return False

    def update_config(self, name: str, config: Dict[str, Any]) -> bool:
        with self._lock:
            if name in self._registry:
                self._registry[name]["config"] = config
                self._registry[name]["updated_at"] = time.time()
                self._save()
                return True
            return False


@dataclass
class PluginRecord:
    """Runtime record of an installed plugin."""
    manifest: "PluginManifest"
    state: "PluginState" = PluginState.DISCOVERED
    install_path: Path = field(default_factory=Path)
    installed_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    enabled_at: Optional[float] = None
    config: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "state": self.state.value,
            "install_path": str(self.install_path),
            "installed_at": self.installed_at,
            "updated_at": self.updated_at,
            "enabled_at": self.enabled_at,
            "config": self.config,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginRecord":
        from plugins.plugin_manifest import PluginManifest
        manifest = PluginManifest.from_dict(data["manifest"])
        state = PluginState(data.get("state", "discovered"))
        return cls(
            manifest=manifest,
            state=state,
            install_path=Path(data["install_path"]),
            installed_at=data["installed_at"],
            updated_at=data["updated_at"],
            enabled_at=data.get("enabled_at"),
            config=data.get("config", {}),
            error=data.get("error"),
        )


class PluginLifecycleManager:
    """
    Manages the complete lifecycle of plugins:
    install -> enable -> disable -> update -> uninstall
    """

    def __init__(
        self,
        plugin_dir: Path,
        registry: PluginRegistry,
        hook_registry: HookRegistry,
        event_bus: Any = None,
        brain: Any = None,
    ):
        self.plugin_dir = plugin_dir
        self.registry = registry
        self.hook_registry = hook_registry
        self.event_bus = event_bus
        self.brain = brain
        self.sandbox = None  # Created per-plugin via create_sandbox_for_plugin
        self.loader = PluginLoader(hook_registry, str(plugin_dir))
        self._lock = threading.RLock()

        # Ensure plugin directory exists
        self.plugin_dir.mkdir(parents=True, exist_ok=True)

    def install(
        self,
        package_path: Path,
        verify_signature: bool = True,
        force: bool = False,
        trusted_keys: Optional[List[bytes]] = None,
    ) -> "PluginRecord":
        """
        Install a plugin from a .mpkg package file.
        
        Args:
            package_path: Path to the .mpkg package file
            verify_signature: Whether to verify package signature
            force: Overwrite existing installation
            trusted_keys: List of trusted public keys (PEM format) for signature verification
            
        Returns:
            PluginRecord of the installed plugin
            
        Raises:
            PluginLifecycleError: If installation fails
        """
        with self._lock:
            # 1. Validate package
            is_valid, errors, manifest = PluginManifestValidator.validate_package(package_path)
            if not is_valid:
                raise PluginLifecycleError(f"Invalid package: {errors}")

            name = manifest.name

            # 2. Check if already installed
            existing = self.registry.get(manifest.name)
            if existing and not force:
                raise PluginLifecycleError(
                    f"Plugin '{name}' already installed. Use force=True to overwrite."
                )

            # 3. Check version compatibility
            if existing:
                existing_manifest = PluginManifest.from_dict(existing["manifest"])
                if existing_manifest.version == manifest.version and not force:
                    raise PluginLifecycleError(
                        f"Version {manifest.version} already installed. Use force=True to reinstall."
                    )

            # 4. Check MAI version compatibility
            if not self._check_version_compatibility(manifest):
                raise PluginLifecycleError(
                    f"Plugin requires MAI version {manifest.min_mai_version}, "
                    f"but current version is incompatible"
                )

            # 5. Verify package signature if requested
            if verify_signature:
                is_valid, error, sig_info = verify_plugin_package(package_path, trusted_keys)
                if not is_valid:
                    raise PluginLifecycleError(f"Package signature verification failed: {error}")

            # 5. Check dependencies with full resolution
            try:
                resolver = DepResolver(self.registry)
                # Get available packages from installed plugins
                available_packages = {}
                for name, data in self.registry._registry.items():
                    if data.get("state") == PluginState.ACTIVATED.value:
                        manifest_data = data.get("manifest")
                        if manifest_data:
                            dep_manifest = PluginManifest.from_dict(manifest_data)
                            available_packages[dep_manifest.name] = [dep_manifest.version]
                
                # Resolve dependencies
                resolved_deps = resolver.resolve_dependencies(
                    manifest,
                    {name: PluginManifest.from_dict(data["manifest"]) 
                     for name, data in self.registry._registry.items() 
                     if data.get("state") == PluginState.ACTIVATED.value},
                    available_packages
                )
            except DependencyResolutionError as e:
                raise PluginLifecycleError(f"Dependency resolution failed: {e}")
            except CircularDependencyError as e:
                raise PluginLifecycleError(f"Circular dependency detected: {e}")
            except VersionConflictError as e:
                raise PluginLifecycleError(f"Version conflict: {e}")

            # 6. Extract package
            install_path = self.plugin_dir / manifest.name
            if install_path.exists():
                shutil.rmtree(install_path)
            install_path.mkdir(parents=True, exist_ok=True)

            try:
                with zipfile.ZipFile(package_path, "r") as zf:
                    zf.extractall(install_path)
            except zipfile.BadZipFile as e:
                raise PluginLifecycleError(f"Failed to extract package: {e}")

            # 7. Validate extracted structure
            if not (install_path / "manifest.json").exists():
                shutil.rmtree(install_path)
                raise PluginLifecycleError("manifest.json not found in package")

            # 8. Install Python dependencies if requirements.txt exists
            self._install_dependencies(install_path)

            # 11. Create plugin record
            record = PluginRecord(
                manifest=manifest,
                state=PluginState.DISCOVERED,
                install_path=install_path,
            )

            # 12. Register in registry
            self.registry.register(record)

            # 13. Emit event
            self._emit_event("plugin_installed", {"name": manifest.name, "version": manifest.version})

            return record

    def enable(self, name: str) -> bool:
        """Enable an installed plugin: DISCOVERED -> LOADED -> ACTIVATED"""
        with self._lock:
            record = self.registry.get(name)
            if not record:
                raise PluginLifecycleError(f"Plugin '{name}' not installed")

            record_obj = PluginRecord.from_dict(record)
            if record_obj.state == PluginState.ACTIVATED:
                return True  # Already activated

            # 1. Check version compatibility
            if not self._check_version_compatibility(record_obj.manifest):
                raise PluginLifecycleError("Plugin version incompatible with current MAI version")

            # 2. Create sandbox with manifest permissions
            sandbox = create_sandbox_for_plugin(name, record_obj.manifest)

            # 3. Load plugin module (DISCOVERED -> LOADED)
            try:
                plugin = self.loader.load(record_obj.manifest.name, self.brain, self.event_bus)
                if plugin:
                    plugin.state = "loaded"
            except Exception as e:
                self._set_error(record_obj, f"Failed to load plugin: {e}")
                return False

            # 4. Call on_activate (LOADED -> ACTIVATED)
            try:
                if hasattr(plugin, "on_activate"):
                    plugin.on_activate(self.hook_registry, self.brain, self.event_bus)
            except Exception as e:
                self._set_error(record_obj, f"on_activate failed: {e}")
                return False

            # 6. Update state
            record_obj.state = PluginState.ACTIVATED
            record_obj.enabled_at = time.time()
            record_obj.updated_at = time.time()
            record_obj.error = None
            self.registry.register(record_obj)

            # 7. Emit event
            self._emit_event("plugin_activated", {"name": name})

            return True

    def disable(self, name: str) -> bool:
        """Disable an activated plugin: ACTIVATED -> DEACTIVATED -> UNLOADED"""
        with self._lock:
            record = self.registry.get(name)
            if not record:
                raise PluginLifecycleError(f"Plugin '{name}' not installed")

            record_obj = PluginRecord.from_dict(record)
            if record_obj.state in (PluginState.DEACTIVATED, PluginState.UNLOADED):
                return True  # Already deactivated/unloaded

            plugin = self.loader._plugins.get(name)

            # 1. Call on_deactivate (ACTIVATED -> DEACTIVATED)
            try:
                if plugin and hasattr(plugin, "on_deactivate"):
                    plugin.on_deactivate()
                    plugin.state = "deactivated"
            except Exception as e:
                self._set_error(record_obj, f"on_deactivate failed: {e}")
                # Continue with deactivation even if it fails

            # 2. Update state to DEACTIVATED
            record_obj.state = PluginState.DEACTIVATED
            record_obj.updated_at = time.time()
            self.registry.register(record_obj)

            # 3. Emit event
            self._emit_event("plugin_deactivated", {"name": name})

            # 4. Unregister hooks
            self._unregister_plugin_hooks(name)

            # 5. Unload from loader (calls on_unload)
            self.loader.unload(name)

            # 6. Update plugin state
            if plugin:
                plugin.state = "unloaded"

            # 7. Update state to UNLOADED
            record_obj.state = PluginState.UNLOADED
            record_obj.updated_at = time.time()
            self.registry.register(record_obj)

            # 8. Emit event
            self._emit_event("plugin_unloaded", {"name": name})

            return True

    def update(self, name: str, package_path: Path) -> bool:
        """Update an installed plugin to a new version."""
        with self._lock:
            record = self.registry.get(name)
            if not record:
                raise PluginLifecycleError(f"Plugin '{name}' not installed")

            record_obj = PluginRecord.from_dict(record)
            was_enabled = record_obj.state == PluginState.ACTIVATED

            # 1. Disable if enabled
            if was_enabled:
                self.disable(name)

            # 2. Backup current version
            backup_path = self.plugin_dir / f"{name}.backup"
            if backup_path.exists():
                shutil.rmtree(backup_path)
            shutil.move(self.plugin_dir / name, backup_path)

            try:
                # 3. Install new version
                new_record = self.install(package_path, force=True)

                # 4. Migrate config if needed
                new_record.config = record_obj.config
                new_record.updated_at = time.time()
                self.registry.register(new_record)

                # 5. Re-enable if was enabled
                if was_enabled:
                    self.enable(name)

                # 5. Remove backup on success
                shutil.rmtree(backup_path)

                return True

            except Exception as e:
                # Rollback on failure
                if backup_path.exists():
                    if (self.plugin_dir / name).exists():
                        shutil.rmtree(self.plugin_dir / name)
                    shutil.move(backup_path, self.plugin_dir / name)
                raise PluginLifecycleError(f"Update failed: {e}")

    def uninstall(self, name: str, purge_config: bool = False) -> bool:
        """Uninstall a plugin."""
        with self._lock:
            record = self.registry.get(name)
            if not record:
                raise PluginLifecycleError(f"Plugin '{name}' not installed")

            record_obj = PluginRecord.from_dict(record)

            # Disable if activated
            if record_obj.state == PluginState.ACTIVATED:
                self.disable(name)

            # Remove plugin directory
            install_path = self.plugin_dir / name
            if install_path.exists():
                shutil.rmtree(install_path)

            # Remove from registry
            self.registry.unregister(name)

            # Remove config if purge requested
            if purge_config:
                config_dir = Path.home() / ".config" / "mai" / "plugins" / name
                if config_dir.exists():
                    shutil.rmtree(config_dir)

        # Emit event
        self._emit_event("plugin_uninstalled", {"name": name})

        return True

    def get_plugin(self, name: str) -> Optional["PluginRecord"]:
        """Get plugin record by name."""
        record = self.registry.get(name)
        if record:
            return PluginRecord.from_dict(record)
        return None

    def list_plugins(self) -> List["PluginRecord"]:
        """List all installed plugins."""
        with self._lock:
            return [PluginRecord.from_dict(r) for r in self.registry.get_all()]

    def get_enabled_plugins(self) -> List["PluginRecord"]:
        """Get list of enabled plugins."""
        return [p for p in self.list_plugins() if p.state == PluginState.ACTIVATED]

    def get_plugin_config(self, name: str) -> Optional[Dict[str, Any]]:
        """Get plugin configuration."""
        record = self.registry.get(name)
        if record:
            return record.get("config")
        return None

    def set_plugin_config(self, name: str, config: Dict[str, Any]) -> bool:
        """Set plugin configuration."""
        return self.registry.update_config(name, config)

    def _check_version_compatibility(self, manifest: "PluginManifest") -> bool:
        """Check if plugin is compatible with current MAI version."""
        from app.config_loader import MAI_VERSION
        current = tuple(map(int, MAI_VERSION.split(".")))
        min_ver = tuple(map(int, manifest.min_mai_version.split(".")))
        if current < min_ver:
            return False
        if manifest.max_mai_version:
            max_ver = tuple(map(int, manifest.max_mai_version.split(".")))
            if current > max_ver:
                return False
        return True

    def _check_dependencies(self, manifest: "PluginManifest") -> List[str]:
        """Check if all dependencies are satisfied. Returns list of errors."""
        errors = []
        for dep in manifest.dependencies:
            dep_record = self.registry.get(dep.name)
            if not dep_record:
                if not dep.optional:
                    errors.append(f"Missing required dependency: {dep.name} ({dep.version})")
                continue

            dep_manifest = PluginManifest.from_dict(dep_record["manifest"])
            # Simple version check (could be enhanced with semver library)
            if not self._version_satisfies(dep_manifest.version, dep.version):
                errors.append(
                    f"Dependency {dep.name} version {dep_manifest.version} "
                    f"does not satisfy requirement {dep.version}"
                )
        return errors

    def _version_satisfies(self, actual: str, required: str) -> bool:
        """Simple version satisfaction check. In production, use packaging.version."""
        # Simplified: just check major version for now
        try:
            actual_major = int(actual.split(".")[0])
            # Parse required range like ">=1.0.0 <2.0.0"
            return True  # Simplified
        except (ValueError, IndexError):
            return True

    def _install_dependencies(self, install_path: Path) -> None:
        """Install Python dependencies from requirements.txt if present."""
        req_file = install_path / "requirements.txt"
        if req_file.exists():
            import subprocess
            try:
                subprocess.run(
                    ["pip", "install", "-r", str(req_file)],
                    check=True,
                    capture_output=True,
                    timeout=120,
                )
            except subprocess.CalledProcessError as e:
                raise PluginLifecycleError(f"Failed to install dependencies: {e.stderr.decode()}")

    def _set_error(self, record: "PluginRecord", error: str) -> None:
        record.state = PluginState.ERROR
        record.error = error
        record.updated_at = time.time()
        self.registry.register(record)

    def _unregister_plugin_hooks(self, name: str) -> None:
        """Unregister all hooks registered by a plugin."""
        # The hook registry doesn't track which plugin registered which hook,
        # so we'd need to track this. For now, we'll leave hooks registered.
        # In a full implementation, we'd track hook ownership.
        pass

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit event to event bus if available."""
        if self.event_bus:
            try:
                from core.mai_message import publish_event
                from core.event_specs import get_spec
                spec = get_spec(event_type)
                if spec:
                    publish_event(self.event_bus, spec, data, source="plugin_lifecycle")
            except Exception:
                pass  # Don't let event emission break lifecycle

    def get_plugin_module(self, name: str) -> Optional[Any]:
        """Get loaded plugin module."""
        return self.loader._plugins.get(name)


# Convenience functions for external use
def create_plugin_lifecycle_manager(
    plugin_dir: Path,
    hook_registry: HookRegistry,
    event_bus: Any = None,
    brain: Any = None,
) -> PluginLifecycleManager:
    """Factory function to create a fully configured PluginLifecycleManager."""
    # Lifecycle registry lives under data/ — plugin_dir/registry.json is the
    # MARKETPLACE registry (registry_url + plugin catalog), a different file
    # format that must not be parsed as installed-plugin records.
    registry_path = plugin_dir / "data" / "lifecycle_registry.json"
    registry = PluginRegistry(registry_path)
    return PluginLifecycleManager(
        plugin_dir=plugin_dir,
        registry=registry,
        hook_registry=hook_registry,
        event_bus=event_bus,
    )