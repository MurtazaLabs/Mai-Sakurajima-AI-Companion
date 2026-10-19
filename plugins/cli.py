"""
Plugin CLI Commands
Provides command-line interface for plugin management: install, enable, disable, uninstall, list, search.
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from core.plugin_system import HookRegistry
from plugins.lifecycle import PluginLifecycleManager, create_plugin_lifecycle_manager
from plugins.marketplace_client import create_marketplace_client

logger = logging.getLogger(__name__)


class PluginCLI:
    """Command-line interface for plugin management."""
    
    def __init__(self, plugin_dir: Path | None = None, registry_url: str | None = None):
        self.plugin_dir = plugin_dir or (Path.home() / ".config" / "mai" / "plugins")
        self.registry_url = registry_url
        self.client = create_marketplace_client(registry_url)
        # Force refresh registry for local file URLs
        if registry_url and registry_url.startswith("file://"):
            self.client.fetch_registry(force_refresh=True)
        self._lifecycle_manager: PluginLifecycleManager | None = None
    
    def _get_lifecycle_manager(self) -> PluginLifecycleManager:
        if self._lifecycle_manager is None:
            self._lifecycle_manager = create_plugin_lifecycle_manager(
                plugin_dir=self.plugin_dir,
                hook_registry=HookRegistry(),
            )
        return self._lifecycle_manager
    
    def install(self, name: str, version: str = "latest", force: bool = False,
                trusted_keys: list[str] | None = None) -> int:
        """Install a plugin from the marketplace."""
        logger.info("Searching for plugin: %s", name)
        
        # Convert trusted key paths to bytes
        key_bytes = []
        if trusted_keys:
            for key_path in trusted_keys:
                with open(key_path, "rb") as f:
                    key_bytes.append(f.read())
        
        success, message, package_path = self.client.install_plugin(
            name=name,
            version=version,
            force=force,
            trusted_keys=key_bytes if key_bytes else None,
            lifecycle_manager=self._get_lifecycle_manager()
        )
        
        if success:
            logger.info("[OK] %s", message)
            if package_path:
                logger.info("   Package: %s", package_path)
            return 0
        else:
            logger.error("[FAIL] %s", message)
            return 1
    
    def search(self, query: str = "", tags: list[str] | None = None,
               category: str | None = None, json_output: bool = False) -> int:
        """Search the marketplace for plugins."""
        plugins = self.client.search(query=query, tags=tags, category=category)
        
        if json_output:
            logger.info(json.dumps([{
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "author": p.author,
                "tags": p.tags,
                "downloads": p.downloads,
                "rating": p.rating,
            } for p in plugins], indent=2))
        else:
            if not plugins:
                logger.info("No plugins found.")
                return 0
            
            logger.info("Found %d plugin(s):", len(plugins))
            for p in plugins:
                stars = "*" * int(p.rating) + "-" * (5 - int(p.rating))
                logger.info("  %s v%s", p.name, p.version)
                logger.info("    %s", p.description)
                logger.info("    Author: %s | %s (%.1f) | %d downloads",
                            p.author, stars, p.rating, p.downloads)
                logger.info("    Tags: %s", ", ".join(p.tags))
                logger.info("")
        
        return 0
    
    def list_installed(self, json_output: bool = False) -> int:
        """List installed plugins."""
        manager = self._get_lifecycle_manager()
        plugins = manager.list_plugins()
        
        if not plugins:
            logger.info("No plugins installed.")
            return 0
        
        if json_output:
            logger.info(json.dumps([{
                "name": p.manifest.name,
                "version": p.manifest.version,
                "state": p.state.value,
                "enabled": p.state.value == "activated",
                "description": p.manifest.description,
            } for p in plugins], indent=2))
        else:
            logger.info("Installed plugins (%d):", len(plugins))
            for p in plugins:
                if p.state.value == "activated":
                    status = "[ON]"
                elif p.state.value == "deactivated":
                    status = "[OFF]"
                else:
                    status = "[...]"
                logger.info("  %s %s v%s [%s]", status, p.manifest.name, p.manifest.version, p.state.value)
                logger.info("    %s", p.manifest.description)
                if p.error:
                    logger.info("    Error: %s", p.error)
                logger.info("")
        
        return 0
    
    def enable(self, name: str) -> int:
        """Enable an installed plugin."""
        manager = self._get_lifecycle_manager()
        try:
            success = manager.enable(name)
            if success:
                logger.info("[OK] Plugin '%s' enabled", name)
                return 0
            else:
                logger.error("[FAIL] Failed to enable plugin '%s'", name)
                return 1
        except Exception as e:
            logger.error("[ERROR] %s", e)
            return 1
    
    def disable(self, name: str) -> int:
        """Disable an enabled plugin."""
        manager = self._get_lifecycle_manager()
        try:
            success = manager.disable(name)
            if success:
                logger.info("[OK] Plugin '%s' disabled", name)
                return 0
            else:
                logger.error("[FAIL] Failed to disable plugin '%s'", name)
                return 1
        except Exception as e:
            logger.error("[ERROR] %s", e)
            return 1
    
    def uninstall(self, name: str, purge: bool = False) -> int:
        """Uninstall a plugin."""
        manager = self._get_lifecycle_manager()
        try:
            success = manager.uninstall(name, purge_config=purge)
            if success:
                logger.info("[OK] Plugin '%s' uninstalled", name)
                return 0
            else:
                logger.error("[FAIL] Failed to uninstall plugin '%s'", name)
                return 1
        except Exception as e:
            logger.error("[ERROR] %s", e)
            return 1
    
    def info(self, name: str, json_output: bool = False) -> int:
        """Get detailed info about a plugin (installed or marketplace)."""
        # Check installed first
        manager = self._get_lifecycle_manager()
        record = manager.get_plugin(name)
        
        if record:
            data = {
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
                "enabled": record.state.value == "activated",
                "installed_at": record.installed_at,
                "updated_at": record.updated_at,
                "config": record.config,
                "error": record.error,
                "install_path": str(record.install_path),
            }
        else:
            # Check marketplace
            plugin = self.client.get_plugin(name)
            if plugin:
                data = {
                    "name": plugin.name,
                    "version": plugin.version,
                    "description": plugin.description,
                    "author": plugin.author,
                    "entry_point": plugin.entry_point,
                    "api_version": plugin.api_version,
                    "permissions": plugin.permissions,
                    "dependencies": plugin.dependencies,
                    "hooks": plugin.hooks,
                    "min_mai_version": plugin.min_mai_version,
                    "max_mai_version": plugin.max_mai_version,
                    "homepage": plugin.homepage,
                    "repository": plugin.repository,
                    "license": plugin.license,
                    "tags": plugin.tags,
                    "downloads": plugin.downloads,
                    "rating": plugin.rating,
                    "updated_at": plugin.updated_at,
                    "package_url": plugin.package_url,
                    "source": "marketplace",
                }
            else:
                logger.error("Plugin '%s' not found", name)
                return 1
        
        if json_output:
            logger.info(json.dumps(data, indent=2))
        else:
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    logger.info("  %s: %s", key, json.dumps(value))
                else:
                    logger.info("  %s: %s", key, value)
        
        return 0
    
    def update(self, name: str) -> int:
        """Update a plugin to latest version."""
        logger.warning("Update not yet implemented")
        return 1


def main():
    # CLI output goes through logger.info/error — without a handler, Python
    # drops INFO lines and the tool appears silent.
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(
        prog="mai plugin",
        description="Mai AI Plugin Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  mai plugin install weather              # Install latest weather plugin
  mai plugin install weather --version 1.0.0  # Install specific version
  mai plugin search weather               # Search for weather plugins
  mai plugin search --tag utility         # Filter by tag
  mai plugin list                         # List installed plugins
  mai plugin enable weather               # Enable weather plugin
  mai plugin disable weather              # Disable weather plugin
  mai plugin uninstall weather            # Uninstall plugin
  mai plugin info weather                 # Show plugin details
        """
    )
    
    parser.add_argument(
        "--plugin-dir",
        type=Path,
        help="Plugin installation directory",
        default=Path.home() / ".config" / "mai" / "plugins"
    )
    parser.add_argument(
        "--registry",
        type=str,
        help="Marketplace registry URL",
        default=None
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # install
    install_parser = subparsers.add_parser("install", help="Install a plugin")
    install_parser.add_argument("name", help="Plugin name")
    install_parser.add_argument("--version", default="latest", help="Version to install")
    install_parser.add_argument("--force", action="store_true", help="Force reinstall")
    install_parser.add_argument("--trusted-key", action="append", help="Trusted public key file")
    
    # search
    search_parser = subparsers.add_parser("search", help="Search marketplace")
    search_parser.add_argument("query", nargs="?", default="", help="Search query")
    search_parser.add_argument("--tag", action="append", help="Filter by tag")
    search_parser.add_argument("--category", help="Filter by category")
    
    # list
    subparsers.add_parser("list", help="List installed plugins")
    
    # enable
    enable_parser = subparsers.add_parser("enable", help="Enable a plugin")
    enable_parser.add_argument("name", help="Plugin name")
    
    # disable
    disable_parser = subparsers.add_parser("disable", help="Disable a plugin")
    disable_parser.add_argument("name", help="Plugin name")
    
    # uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help="Uninstall a plugin")
    uninstall_parser.add_argument("name", help="Plugin name")
    uninstall_parser.add_argument("--purge", action="store_true", help="Purge config")
    
    # info
    info_parser = subparsers.add_parser("info", help="Show plugin info")
    info_parser.add_argument("name", help="Plugin name")
    
    # update
    update_parser = subparsers.add_parser("update", help="Update a plugin")
    update_parser.add_argument("name", help="Plugin name")
    
    args = parser.parse_args()
    
    cli = PluginCLI(plugin_dir=args.plugin_dir, registry_url=args.registry)
    
    try:
        if args.command == "install":
            return cli.install(args.name, args.version, args.force, args.trusted_key)
        elif args.command == "search":
            return cli.search(args.query, args.tag, args.category, args.json)
        elif args.command == "list":
            return cli.list_installed(args.json)
        elif args.command == "enable":
            return cli.enable(args.name)
        elif args.command == "disable":
            return cli.disable(args.name)
        elif args.command == "uninstall":
            return cli.uninstall(args.name, args.purge)
        elif args.command == "info":
            return cli.info(args.name, args.json)
        elif args.command == "update":
            return cli.update(args.name)
    except KeyboardInterrupt:
        logger.info("\nInterrupted")
        return 130
    except Exception as e:
        logger.error("[ERROR] %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())