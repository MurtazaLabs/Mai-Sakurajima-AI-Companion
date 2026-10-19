"""
Plugin Sandbox
Provides isolated execution environment with permission enforcement for plugins.
"""
import socket
import json
import re
import pathlib
import random
import time
import datetime
import math
import os
import sys
import subprocess
import threading
import tempfile
from pathlib import Path
from typing import Set, Optional, List, Any, Dict
from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    resource = None
    HAS_RESOURCE = False


class Permission(str, Enum):
    """Granular permissions for plugin sandbox."""
    # Filesystem
    FS_READ = "fs:read"
    FS_WRITE = "fs:write"
    
    # Network
    NET_OUTBOUND = "net:outbound"
    NET_INBOUND = "net:inbound"
    
    # Execution
    EXEC_SUBPROCESS = "exec:subprocess"
    EXEC_EVAL = "exec:eval"
    
    # API Access
    API_WEATHER = "api:weather"
    API_MEMORY = "api:memory"
    API_CALENDAR = "api:calendar"
    API_SYSTEM = "api:system"
    
    # Configuration
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"


@dataclass
class ResourceLimits:
    """Resource limits for plugin execution."""
    max_cpu_time: int = 30  # seconds
    max_memory: int = 256 * 1024 * 1024  # 256 MB
    max_processes: int = 10
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    max_open_files: int = 100


@dataclass
class PluginSandbox:
    """
    Sandbox environment for plugin execution with permission enforcement.
    
    Provides isolated execution environment with:
    - Filesystem isolation (chroot-like)
    - Network access control
    - Execution control (subprocess, eval)
    - Resource limits (CPU, memory, processes)
    - API access control
    """
    plugin_name: str
    permissions: set
    fs_root: Path
    network_allowlist: Set[str] = field(default_factory=set)
    resource_limits: "ResourceLimits" = field(default_factory=ResourceLimits)
    
    # Internal state
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False)
    _original_env: Dict[str, str] = field(default_factory=dict, init=False)
    _restricted_env: Dict[str, str] = field(default_factory=dict, init=False)
    _active: bool = field(default=False, init=False)

    def __post_init__(self):
        """Initialize sandbox environment."""
        self.fs_root = self.fs_root.resolve()
        self.fs_root.mkdir(parents=True, exist_ok=True)
        
        # Prepare restricted environment
        self._restricted_env = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(self.fs_root),
            "TMPDIR": str(self.fs_root / "tmp"),
            "TEMP": str(self.fs_root / "tmp"),
            "PYTHONPATH": "",
        }
        (self.fs_root / "tmp").mkdir(parents=True, exist_ok=True)

    def enter(self) -> "PluginSandbox":
        """Enter sandbox context. Call before executing plugin code."""
        with self._lock:
            if self._active:
                raise RuntimeError("Sandbox already active")
            self._active = True
            self._original_env = dict(os.environ)
            os.environ.update(self._restricted_env)
        return self

    def exit(self) -> None:
        """Exit sandbox context. Restore original environment."""
        with self._lock:
            if not self._active:
                return
            os.environ.clear()
            os.environ.update(self._original_env)
            self._active = False

    def __enter__(self):
        return self.enter()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exit()
        return False

    # Permission checks
    def check_permission(self, perm: Permission) -> bool:
        """Check if plugin has a specific permission."""
        return perm in self.permissions

    def require_permission(self, perm: Permission) -> None:
        """Require a permission, raise if not granted."""
        if not self.check_permission(perm):
            raise PermissionError(
                f"Plugin '{self.plugin_name}' lacks required permission: {perm.value}"
            )

    # Filesystem operations
    def resolve_path(self, path: str) -> Path:
        """Resolve path within sandbox root, prevent traversal.

        Uses structural containment (relative_to) instead of a string prefix
        check, so sibling directories like ``<root>_backup/`` cannot be reached,
        and resolved symlinks that escape the root are rejected.
        """
        requested = (self.fs_root / path).resolve()
        try:
            requested.relative_to(self.fs_root)
        except ValueError:
            raise PermissionError(f"Path traversal attempt: {path}")
        return requested

    def read_file(self, path: str) -> str:
        """Read file within sandbox."""
        self.require_permission(Permission.FS_READ)
        path = self.resolve_path(path)
        return path.read_text(encoding="utf-8")

    def write_file(self, path: str, content: str, encoding: str = "utf-8") -> None:
        """Write file within sandbox."""
        self.require_permission(Permission.FS_WRITE)
        path = self.resolve_path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding=encoding)

    def list_dir(self, path: str = ".") -> List[str]:
        """List directory contents within sandbox."""
        self.require_permission(Permission.FS_READ)
        path = self.resolve_path(path)
        return [f.name for f in path.iterdir()]

    def make_dir(self, path: str, exist_ok: bool = True) -> None:
        """Create directory within sandbox."""
        self.require_permission(Permission.FS_WRITE)
        path = self.resolve_path(path)
        path.mkdir(parents=True, exist_ok=exist_ok)

    def remove(self, path: str) -> None:
        """Remove file or directory within sandbox."""
        self.require_permission(Permission.FS_WRITE)
        path = self.resolve_path(path)
        if path.is_dir():
            import shutil
            shutil.rmtree(path)
        else:
            path.unlink()

    # Network operations
    def check_network_allowlist(self, url: str) -> bool:
        """Check if URL domain is in allowlist."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            return any(
                domain == allowed or domain.endswith("." + allowed)
                for allowed in self.network_allowlist
            )
        except Exception:
            return False

    def require_network_permission(self, url: str) -> None:
        """Require network permission and check allowlist."""
        self.require_permission(Permission.NET_OUTBOUND)
        if self.network_allowlist and not self.check_network_allowlist(url):
            raise PermissionError(f"Domain not in allowlist: {urlparse(url).netloc}")

    def http_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[bytes] = None,
        json_data: Optional[Any] = None,
        timeout: int = 30,
    ) -> Any:
        """Make HTTP request within sandbox."""
        import urllib.request
        import urllib.error
        import json

        self.require_network_permission(url)
        
        req = urllib.request.Request(url, method=method)
        if headers:
            for k, v in headers.items():
                req.add_header(k, v)
        if json_data is not None:
            data = json.dumps(json_data).encode()
            req.add_header("Content-Type", "application/json")
        elif data:
            req.add_header("Content-Type", "application/octet-stream")
        
        try:
            with urllib.request.urlopen(req, data=data, timeout=timeout) as resp:
                # Cap the response so a remote host cannot exhaust memory via
                # an unbounded body (e.g. multi-GB stream).
                max_bytes = self.resource_limits.max_file_size
                payload = resp.read(max_bytes + 1)
            if len(payload) > max_bytes:
                raise RuntimeError(
                    f"Response body exceeds sandbox limit ({max_bytes} bytes)"
                )
            return payload
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Network error: {e.reason}")

    # Subprocess execution
    def run_subprocess(
        self,
        cmd: List[str],
        cwd: Optional[str] = None,
        timeout: int = 30,
        capture_output: bool = True,
        env: Optional[Dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        """Run subprocess within sandbox."""
        self.require_permission(Permission.EXEC_SUBPROCESS)
        
        if cwd is None:
            cwd = str(self.fs_root)
        else:
            cwd = str(self.resolve_path(cwd))
        
        env = env or self._restricted_env.copy()
        
        try:
            return subprocess.run(
                cmd,
                cwd=cwd,
                timeout=timeout,
                capture_output=capture_output,
                env=env,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Subprocess timed out after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"Subprocess failed: {e}")

    # Eval execution
    @staticmethod
    def _eval_allowed() -> bool:
        """Eval is a trusted-first-party opt-in (MAI_PLUGIN_ALLOW_EVAL=1).

        exec() can never be a real security boundary — a sufficiently clever
        payload escapes any restricted-globals setup. Third-party plugins must
        use run_subprocess() instead.
        """
        return os.environ.get("MAI_PLUGIN_ALLOW_EVAL", "").strip().lower() in (
            "1", "true", "yes"
        )

    def eval_code(self, code: str, globals_dict: Optional[Dict] = None) -> Any:
        """Evaluate trusted first-party Python code within sandbox.

        NOT a security boundary. Requires both the EXEC_EVAL permission and the
        MAI_PLUGIN_ALLOW_EVAL opt-in; untrusted code must go through
        run_subprocess() instead.
        """
        self.require_permission(Permission.EXEC_EVAL)
        if not self._eval_allowed():
            raise PermissionError(
                "Sandbox eval is disabled by default; set MAI_PLUGIN_ALLOW_EVAL=1 "
                "to opt in (trusted first-party plugins only)"
            )

        # Create restricted globals — os/pathlib are deliberately omitted and
        # reflective escape hatches (getattr/setattr/type) are excluded.
        safe_globals = {
            "__builtins__": {
                "print": print,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "range": range,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs,
                "round": round,
                "sorted": sorted,
                "reversed": reversed,
                "any": any,
                "all": all,
                "isinstance": isinstance,
                "hasattr": hasattr,
                "Exception": Exception,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "KeyError": KeyError,
                "IndexError": IndexError,
            },
            "json": json,
            "datetime": datetime,
            "time": time,
            "math": math,
            "random": random,
            "re": re,
        }
        
        if globals_dict:
            safe_globals.update(globals_dict)
        
        try:
            # Use exec instead of eval for statements, with restricted globals
            exec(code, safe_globals, {})
            return None
        except Exception as e:
            raise RuntimeError(f"Eval failed: {e}")

    # Resource management
    def apply_resource_limits(self) -> None:
        """Apply resource limits to the CURRENT process.

        Trusted-first-party only: these are process-wide, not per-plugin, and
        are only enforced on POSIX (the `resource` module is absent on
        Windows). For any third-party or untrusted code, run it in a separate
        process via run_subprocess() instead.
        """
        if not HAS_RESOURCE:
            return
        try:
            resource.setrlimit(resource.RLIMIT_CPU, (self.resource_limits.max_cpu_time, self.resource_limits.max_cpu_time))
            resource.setrlimit(resource.RLIMIT_AS, (self.resource_limits.max_memory, self.resource_limits.max_memory))
            resource.setrlimit(resource.RLIMIT_NPROC, (self.resource_limits.max_processes, self.resource_limits.max_processes))
            resource.setrlimit(resource.RLIMIT_FSIZE, (self.resource_limits.max_file_size, self.resource_limits.max_file_size))
            resource.setrlimit(resource.RLIMIT_NOFILE, (self.resource_limits.max_open_files, self.resource_limits.max_open_files))
        except (ValueError, OSError):
            # Some limits may not be adjustable on all platforms
            pass

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage."""
        if not HAS_RESOURCE:
            return {}
        try:
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return {
                "cpu_time": usage.ru_utime + usage.ru_stime,
                "memory": usage.ru_maxrss * 1024,  # Convert to bytes on Linux
            }
        except Exception:
            return {}

    # Configuration management
    def read_config(self, key: str, default: Any = None) -> Any:
        """Read plugin configuration."""
        self.require_permission("config:read")
        # Implementation would read from plugin config store
        return default

    def write_config(self, key: str, value: Any) -> None:
        """Write plugin configuration."""
        self.require_permission("config:write")
        # Implementation would write to plugin config store
        pass

    # API access helpers
    def call_weather_api(self, city: str) -> Dict:
        """Call weather API (requires api:weather permission)."""
        self.require_permission(Permission.API_WEATHER)
        # Implementation would call weather API
        return {}

    def call_memory_api(self, query: str) -> List[Dict]:
        """Call memory API (requires api:memory permission)."""
        self.require_permission(Permission.API_MEMORY)
        return []

    def call_calendar_api(self, action: str, **kwargs) -> Any:
        """Call calendar API (requires api:calendar permission)."""
        self.require_permission(Permission.API_CALENDAR)
        return None

    # Context manager for plugin execution
    def execute_plugin(self, func, *args, **kwargs):
        """Execute a trusted first-party plugin function within sandbox context.

        Swaps os.environ and applies process-wide resource limits — affect the
        WHOLE process while running. Never use for third-party/untrusted
        plugins; run them via run_subprocess() in their own process.
        """
        self.enter()
        self.apply_resource_limits()
        try:
            return func(*args, **kwargs)
        finally:
            self.exit()

    def __repr__(self):
        return f"PluginSandbox(plugin={self.plugin_name}, permissions={len(self.permissions)})"


class SandboxManager:
    """Manages sandbox instances for multiple plugins."""
    
    def __init__(self, base_sandbox_dir: Path):
        self.base_sandbox_dir = base_sandbox_dir
        self.base_sandbox_dir.mkdir(parents=True, exist_ok=True)
        self._sandboxes: Dict[str, PluginSandbox] = {}
        self._lock = threading.RLock()

    def create_sandbox(
        self,
        plugin_name: str,
        permissions: set,
        network_allowlist: Optional[Set[str]] = None,
        resource_limits: Optional["ResourceLimits"] = None,
    ) -> PluginSandbox:
        """Create a new sandbox for a plugin."""
        with self._lock:
            if plugin_name in self._sandboxes:
                return self._sandboxes[plugin_name]
            
            sandbox = PluginSandbox(
                plugin_name=plugin_name,
                permissions=permissions,
                fs_root=self.base_sandbox_dir / plugin_name,
                network_allowlist=network_allowlist or set(),
            )
            self._sandboxes[plugin_name] = sandbox
            return sandbox

    def get_sandbox(self, plugin_name: str) -> Optional[PluginSandbox]:
        with self._lock:
            return self._sandboxes.get(plugin_name)

    def remove_sandbox(self, plugin_name: str) -> bool:
        with self._lock:
            if plugin_name in self._sandboxes:
                del self._sandboxes[plugin_name]
                return True
            return False

    def cleanup_all(self) -> None:
        with self._lock:
            for sandbox in self._sandboxes.values():
                sandbox.exit()
            self._sandboxes.clear()


# Default permission sets for common plugin types
DEFAULT_PERMISSIONS = {
    "weather": {Permission.NET_OUTBOUND, "api:weather"},
    "calendar": {Permission.FS_READ, Permission.FS_WRITE, "api:calendar"},
    "news": {Permission.NET_OUTBOUND, "api:news"},
    "system_monitor": {Permission.FS_READ, "api:system"},
    "web_scraper": {Permission.NET_OUTBOUND, Permission.FS_READ},
    "example": set(),
}


def create_sandbox_for_plugin(plugin_name: str, manifest: "PluginManifest") -> PluginSandbox:
    """Create a sandbox with permissions from manifest."""
    permissions = manifest.permissions.to_permission_set()
    sandbox = PluginSandbox(
        plugin_name=plugin_name,
        permissions=permissions,
        fs_root=Path.home() / ".config" / "mai" / "sandbox" / plugin_name,
    )
    return sandbox