import builtins
import importlib
import json
import logging
import os
import shutil
import sys
import threading
import zipfile
from pathlib import Path
from types import ModuleType
from typing import Any, Optional

from plugins.plugin_manifest import PluginManifestValidator
from plugins.sandbox import PluginSandbox, create_sandbox_for_plugin

logger = logging.getLogger(__name__)


class HookRegistry:

    def __init__(self):
        self._hooks = {}
        self._lock = threading.RLock()

    def register(self, hook_name, callback, priority=0):
        if not callable(callback):
            return False
        with self._lock:
            if hook_name not in self._hooks:
                self._hooks[hook_name] = []
            self._hooks[hook_name].append((priority, callback))
            self._hooks[hook_name].sort(key=lambda x: x[0], reverse=True)
            return True

    def unregister(self, hook_name, callback):
        with self._lock:
            if hook_name not in self._hooks:
                return False
            before = len(self._hooks[hook_name])
            self._hooks[hook_name] = [(p, c) for p, c in self._hooks[hook_name] if c != callback]
            return len(self._hooks[hook_name]) < before

    def run(self, hook_name, *args, **kwargs) -> list:
        results: list = []
        with self._lock:
            callbacks = list(self._hooks.get(hook_name, []))
        for priority, callback in callbacks:
            try:
                result = callback(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error("[Hooks] Error in %s.%s: %s", hook_name, getattr(callback, '__name__', '?'), e)
        return results

    def list_hooks(self):
        with self._lock:
            return {k: [(p, c.__name__) for p, c in v] for k, v in self._hooks.items()}


class Plugin:
    """Base plugin class for backward compatibility."""

    def __init__(self, name="", version="1.0.0", description=""):
        self.name = name
        self.version = version
        self.description = description
        self.module: ModuleType | None = None
        self.initialized = False
        self._sandbox: PluginSandbox | None = None
        self._state: str = "discovered"

    def on_load(self, hooks, brain, event_bus):
        """Called when plugin is loaded (after discovery)."""

    def on_activate(self, hooks, brain, event_bus):
        """Called when plugin is activated (enabled and ready to handle events)."""

    def on_deactivate(self):
        """Called when plugin is deactivated (disabled but still loaded)."""

    def on_unload(self):
        """Called when plugin is completely unloaded."""

    def get_sandbox(self) -> Optional["PluginSandbox"]:
        return self._sandbox

    def set_sandbox(self, sandbox: "PluginSandbox"):
        self._sandbox = sandbox

    @property
    def state(self) -> str:
        return self._state

    @state.setter
    def state(self, value: str):
        self._state = value


class PluginLoader:
    """Enhanced plugin loader with manifest support, sandbox, and package management."""

    def __init__(self, hooks, plugin_dir="plugins", sandbox_manager=None):
        self.hooks = hooks
        self.plugin_dir = Path(plugin_dir).resolve()
        self._plugins = {}
        self._lock = threading.RLock()
        self.sandbox_manager = sandbox_manager

        # Ensure plugin directory exists
        self.plugin_dir.mkdir(parents=True, exist_ok=True)

    def discover(self) -> list[str]:
        """Discover available plugins using plugins.json manifest, fallback to filesystem scan."""
        # Ensure plugin directory exists
        if not self.plugin_dir.is_dir():
            self.plugin_dir.mkdir(parents=True, exist_ok=True)
            return []
        
        # Add plugin directory to path
        if str(self.plugin_dir) not in sys.path:
            sys.path.insert(0, str(self.plugin_dir))
        
        # Try to load from plugins.json first
        manifest_path = self.plugin_dir / "plugins.json"
        found = []
        
        if manifest_path.exists():
            try:
                with open(manifest_path, "r") as f:
                    data = json.load(f)
                
                for plugin_info in data.get("plugins", []):
                    name = plugin_info.get("name")
                    if name and name not in found:
                        found.append(name)
                logger.debug("[Plugins] Discovered %d plugins from plugins.json", len(found))
                return found
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("[Plugins] Failed to load plugins.json: %s, falling back to filesystem scan", e)
        
        # Fallback: filesystem scan
        found = []
        for fn in os.listdir(self.plugin_dir):
            if fn.endswith(".py") and not fn.startswith("_"):
                found.append(fn[:-3])
        logger.debug("[Plugins] Discovered %d plugins from filesystem scan", len(found))
        return found

    def load(self, name: str, brain=None, event_bus=None, config: dict | None = None):
        """Load a plugin by name with manifest and sandbox support."""
        with self._lock:
            if name in self._plugins:
                return self._plugins[name]

        # Ensure plugin directory is in path for imports
        if str(self.plugin_dir) not in sys.path:
            sys.path.insert(0, str(self.plugin_dir))

        try:
            # First try to load from installed plugins (with manifest)
            plugin_path = self.plugin_dir / name
            if plugin_path.is_dir():
                manifest_path = plugin_path / "manifest.json"
                if manifest_path.exists():
                    return self._load_from_manifest(manifest_path, brain, event_bus, config)

            # Fallback to legacy loading
            return self._load_legacy(name, brain, event_bus)

        except Exception as e:
            import traceback
            logger.error("[Plugins] Failed to load %s: %s", name, e)
            logger.debug("[Plugins] Traceback: %s", traceback.format_exc())
            return None

    def _load_from_manifest(self, manifest_path: Path, brain, event_bus, config) -> Plugin | None:
        """Load plugin using manifest.json."""
        # Validate manifest
        is_valid, errors, manifest = PluginManifestValidator.validate_manifest_file(manifest_path)
        if not is_valid:
            logger.error("[Plugins] Invalid manifest for %s: %s", manifest_path.parent.name, errors)
            return None

        # Check API version compatibility
        if manifest.api_version != "1.0":
            logger.warning("[Plugins] Plugin %s uses API version %s, expected 1.0", 
                          manifest.name, manifest.api_version)

        # Check MAI version compatibility
        from app.config_loader import MAI_VERSION
        current = tuple(map(int, MAI_VERSION.split(".")))
        min_ver = tuple(map(int, manifest.min_mai_version.split(".")))
        if current < min_ver:
            logger.warning("[Plugins] Plugin %s requires MAI version >= %s, current is %s",
                          manifest.name, manifest.min_mai_version, MAI_VERSION)
            return None
        if manifest.max_mai_version:
            max_ver = tuple(map(int, manifest.max_mai_version.split(".")))
            if current > max_ver:
                logger.warning("[Plugins] Plugin %s requires MAI version <= %s, current is %s",
                              manifest.name, manifest.max_mai_version, MAI_VERSION)
                return None

        # Create sandbox
        sandbox = create_sandbox_for_plugin(manifest.name, manifest)

        # Load plugin module
        plugin_path = manifest_path.parent
        if str(plugin_path) not in sys.path:
            sys.path.insert(0, str(plugin_path))

        # Clear any cached module to avoid stdlib shadowing
        if manifest.name in sys.modules:
            del sys.modules[manifest.name]

        module = importlib.import_module(manifest.name)
        plugin_cls = None
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
                plugin_cls = attr
                break
        
        if plugin_cls is None:
            # Try to find by convention
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and attr.__name__.endswith("Plugin"):
                    plugin_cls = attr
                    break
        
        if plugin_cls is None:
            logger.warning("[Plugins] No Plugin subclass in %s", manifest.name)
            return None

        # Instantiate plugin
        plugin = plugin_cls()
        plugin.module = None
        plugin._sandbox = None

        # Set sandbox if available
        if hasattr(self, 'sandbox_manager') and self.sandbox_manager:
            sandbox = self.sandbox_manager.create_sandbox(
                plugin_name=manifest.name,
                permissions=manifest.permissions.to_permission_set(),
            )
            plugin._sandbox = sandbox

        # Initialize plugin
        try:
            if hasattr(plugin, "on_load"):
                plugin.on_load(self.hooks, brain, event_bus)
            plugin.initialized = True
        except Exception as e:
            logger.error("[Plugins] on_load failed for %s: %s", manifest.name, e)
            return None

        with self._lock:
            self._plugins[manifest.name] = plugin
        
        logger.info("[Plugins] Loaded: %s v%s", manifest.name, manifest.version)
        return plugin

    def _load_legacy(self, name: str, brain=None, event_bus=None) -> Plugin | None:
        """Legacy plugin loading for plugins without manifest."""
        if self.plugin_dir not in sys.path:
            sys.path.insert(0, str(self.plugin_dir))

        try:
            module = importlib.import_module(name)
            plugin_cls = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, Plugin) and attr is not Plugin:
                    plugin_cls = attr
                    break
            
            if plugin_cls is None:
                logger.warning("[Plugins] No Plugin subclass in %s", name)
                return None

            plugin = plugin_cls()
            plugin.module = module
            
            try:
                plugin.on_load(self.hooks, brain, event_bus)
                plugin.initialized = True
            except Exception as e:
                logger.error("[Plugins] on_load failed for %s: %s", name, e)
                return None

            with self._lock:
                self._plugins[name] = plugin
            
            logger.info("[Plugins] Loaded (legacy): %s", name)
            return plugin

        except Exception as e:
            logger.error("[Plugins] Failed to load %s: %s", name, e)
            return None

    def install_package(self, package_path: Path, force: bool = False) -> bool:
        """Install a plugin from a .mpkg package file."""
        from plugins.plugin_manifest import PluginManifestValidator

        is_valid, errors, manifest = PluginManifestValidator.validate_package(package_path)
        if not is_valid:
            logger.error("[Plugins] Invalid package %s: %s", package_path, errors)
            return False

        name = manifest.name
        install_path = self.plugin_dir / name

        if install_path.exists():
            if not force:
                logger.warning("[Plugins] Plugin %s already installed", name)
                return False
            shutil.rmtree(install_path)

        install_path.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(package_path, "r") as zf:
                zf.extractall(install_path)
        except zipfile.BadZipFile as e:
            logger.error("[Plugins] Failed to extract package: %s", e)
            return False

        # Validate extracted structure
        if not (install_path / "manifest.json").exists():
            shutil.rmtree(install_path)
            logger.error("[Plugins] manifest.json not found in package")
            return False

        # Install dependencies
        self._install_dependencies(install_path)

        logger.info("[Plugins] Installed: %s v%s", manifest.name, manifest.version)
        return True

    def _install_dependencies(self, install_path: Path) -> None:
        """Install Python dependencies from requirements.txt if present."""
        req_file = install_path / "requirements.txt"
        if req_file.exists():
            import subprocess
            try:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
                    check=True,
                    capture_output=True,
                    timeout=120,
                )
                logger.info("[Plugins] Installed dependencies for %s", install_path.name)
            except subprocess.CalledProcessError as e:
                logger.error("[Plugins] Failed to install dependencies: %s", e.stderr.decode())

    def unload(self, name: str) -> bool:
        """Unload a plugin."""
        with self._lock:
            plugin = self._plugins.pop(name, None)
            if plugin:
                try:
                    plugin.on_unload()
                except Exception as e:
                    logger.debug("[Plugins] unload error %s: %s", name, e)
                return True
            return False

    def list(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {n: {"name": p.name, "version": p.version, "initialized": p.initialized} 
                    for n, p in self._plugins.items()}

    def get_plugin_metadata(self, name: str) -> dict[str, Any] | None:
        """Get full plugin metadata from plugins.json manifest."""
        manifest_path = self.plugin_dir / "plugins.json"
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)
            
            for plugin_info in data.get("plugins", []):
                if plugin_info.get("name") == name:
                    return plugin_info
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("[Plugins] Failed to read plugins.json: %s", e)
        
        return None

    def get_all_plugin_metadata(self) -> builtins.list[dict[str, Any]]:
        """Get all plugin metadata from plugins.json manifest."""
        manifest_path = self.plugin_dir / "plugins.json"
        if not manifest_path.exists():
            return []
        
        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)
            return data.get("plugins", [])
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("[Plugins] Failed to read plugins.json: %s", e)
            return []

    def load_all(self, brain=None, event_bus=None, config: dict | None = None):
        """Load all discovered plugins."""
        names = self.discover()
        results = []
        for name in names:
            plugin = self.load(name, brain, event_bus, config.get(name) if config else None)
            results.append({"name": name, "success": plugin is not None})
        return results


def create_plugin_loader(hooks, plugin_dir="plugins", sandbox_manager=None) -> PluginLoader:
    """Factory function to create a configured PluginLoader."""
    return PluginLoader(hooks, plugin_dir, sandbox_manager)