"""
Plugin Manifest Schema and Validation
Defines the structure and validation for plugin manifests.
"""
import json
import jsonschema
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Literal, Any
from pathlib import Path
from enum import Enum


class PermissionType(str, Enum):
    FS_READ = "fs:read"
    FS_WRITE = "fs:write"
    NET_OUTBOUND = "net:outbound"
    NET_INBOUND = "net:inbound"
    EXEC_SUBPROCESS = "exec:subprocess"
    EXEC_EVAL = "exec:eval"
    API_WEATHER = "api:weather"
    API_MEMORY = "api:memory"
    API_CALENDAR = "api:calendar"
    CONFIG_READ = "config:read"
    CONFIG_WRITE = "config:write"


@dataclass
class PluginPermission:
    """Permission set for a plugin."""
    filesystem: Literal["none", "read", "write", "full"] = "none"
    network: Literal["none", "outbound", "inbound", "full"] = "none"
    execution: Literal["none", "subprocess", "eval", "full"] = "none"
    api_access: List[str] = field(default_factory=list)
    config: Literal["none", "read", "write"] = "none"

    def to_permission_set(self) -> set:
        """Convert to PermissionType set for sandbox enforcement."""
        perms = set()
        if self.filesystem == "read":
            perms.add("fs:read")
        elif self.filesystem == "write":
            perms.add("fs:write")
        elif self.filesystem == "full":
            perms.add("fs:read")
            perms.add("fs:write")

        if self.network == "outbound":
            perms.add("net:outbound")
        elif self.network == "inbound":
            perms.add("net:inbound")
        elif self.network == "full":
            perms.add("net:outbound")
            perms.add("net:inbound")

        if self.execution == "subprocess":
            perms.add("exec:subprocess")
        elif self.execution == "eval":
            perms.add("exec:eval")
        elif self.execution == "full":
            perms.add("exec:subprocess")
            perms.add("exec:eval")

        for api in self.api_access:
            perms.add(f"api:{api}")

        if self.config == "read":
            perms.add("config:read")
        elif self.config == "write":
            perms.add("config:write")

        return perms


@dataclass
class PluginDependency:
    """Plugin dependency specification."""
    name: str
    version: str  # semver range: ">=1.0.0 <2.0.0"
    optional: bool = False


@dataclass
class PluginManifest:
    """Plugin manifest containing metadata and configuration."""
    name: str
    version: str
    description: str
    author: str
    entry_point: str
    api_version: str = "1.0"
    permissions: PluginPermission = field(default_factory=PluginPermission)
    dependencies: List[PluginDependency] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    min_mai_version: str = "1.0.0"
    max_mai_version: Optional[str] = None
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: str = "MIT"
    tags: List[str] = field(default_factory=list)

    # JSON Schema for validation
    JSON_SCHEMA = {
        "type": "object",
        "required": ["name", "version", "description", "author", "entry_point"],
        "properties": {
            "name": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
            "version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+(-[a-zA-Z0-9.-]+)?$"},
            "description": {"type": "string", "minLength": 1},
            "author": {"type": "string", "minLength": 1},
            "entry_point": {"type": "string", "minLength": 1},
            "api_version": {"type": "string", "pattern": "^\\d+\\.\\d+$"},
            "permissions": {
                "type": "object",
                "properties": {
                    "filesystem": {"type": "string", "enum": ["none", "read", "write", "full"]},
                    "network": {"type": "string", "enum": ["none", "outbound", "inbound", "full"]},
                    "execution": {"type": "string", "enum": ["none", "subprocess", "eval", "full"]},
                    "api_access": {"type": "array", "items": {"type": "string"}},
                    "config": {"type": "string", "enum": ["none", "read", "write"]},
                },
                "additionalProperties": False,
            },
            "dependencies": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["name", "version"],
                    "properties": {
                        "name": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
                        "version": {"type": "string"},
                        "optional": {"type": "boolean"},
                    },
                    "additionalProperties": False,
                },
            },
            "hooks": {"type": "array", "items": {"type": "string"}},
            "min_mai_version": {"type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$"},
            "max_mai_version": {"type": ["string", "null"], "pattern": "^\\d+\\.\\d+\\.\\d+$"},
            "homepage": {"type": ["string", "null"], "format": "uri"},
            "repository": {"type": ["string", "null"], "format": "uri"},
            "license": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "entry_point": self.entry_point,
            "api_version": self.api_version,
            "permissions": {
                "filesystem": self.permissions.filesystem,
                "network": self.permissions.network,
                "execution": self.permissions.execution,
                "api_access": self.permissions.api_access,
                "config": self.permissions.config,
            },
            "dependencies": [
                {"name": d.name, "version": d.version, "optional": d.optional}
                for d in self.dependencies
            ],
            "hooks": self.hooks,
            "min_mai_version": self.min_mai_version,
            "max_mai_version": self.max_mai_version,
            "homepage": self.homepage,
            "repository": self.repository,
            "license": self.license,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginManifest":
        """Create manifest from dictionary."""
        permissions_data = data.get("permissions", {})
        permissions = PluginPermission(
            filesystem=permissions_data.get("filesystem", "none"),
            network=permissions_data.get("network", "none"),
            execution=permissions_data.get("execution", "none"),
            api_access=permissions_data.get("api_access", []),
            config=permissions_data.get("config", "none"),
        )
        dependencies = [
            PluginDependency(name=d["name"], version=d["version"], optional=d.get("optional", False))
            for d in data.get("dependencies", [])
        ]
        return cls(
            name=data["name"],
            version=data["version"],
            description=data["description"],
            author=data["author"],
            entry_point=data["entry_point"],
            api_version=data.get("api_version", "1.0"),
            permissions=permissions,
            dependencies=dependencies,
            hooks=data.get("hooks", []),
            min_mai_version=data.get("min_mai_version", "1.0.0"),
            max_mai_version=data.get("max_mai_version"),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
            license=data.get("license", "MIT"),
            tags=data.get("tags", []),
        )

    def validate(self) -> List[str]:
        """Validate manifest against schema. Returns list of errors."""
        try:
            jsonschema.validate(instance=self.to_dict(), schema=self.JSON_SCHEMA)
            return []
        except jsonschema.ValidationError as e:
            return [str(e)]

    def save(self, path: Path) -> None:
        """Save manifest to JSON file."""
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "PluginManifest":
        """Load manifest from JSON file."""
        data = json.loads(path.read_text())
        return cls.from_dict(data)


class PluginManifestValidator:
    """Validator for plugin manifests."""

    @staticmethod
    def validate_manifest_file(path: Path) -> tuple[bool, List[str], Optional[PluginManifest]]:
        """Validate a manifest file. Returns (is_valid, errors, manifest)."""
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"], None
        except Exception as e:
            return False, [f"Failed to read file: {e}"], None

        manifest = PluginManifest.from_dict(data)
        errors = manifest.validate()
        return len(errors) == 0, errors, manifest

    @staticmethod
    def validate_package(package_path: Path) -> tuple[bool, List[str], Optional[PluginManifest]]:
        """Validate a plugin package (.mpkg zip file)."""
        import zipfile
        import tempfile

        if not package_path.exists():
            return False, ["Package file not found"], None

        if not zipfile.is_zipfile(package_path):
            return False, ["Not a valid zip file"], None

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            try:
                with zipfile.ZipFile(package_path, "r") as zf:
                    zf.extractall(tmpdir)
            except zipfile.BadZipFile as e:
                return False, [f"Invalid zip file: {e}"], None

            manifest_path = tmpdir / "manifest.json"
            if not manifest_path.exists():
                return False, ["manifest.json not found in package"], None

            return PluginManifestValidator.validate_manifest_file(manifest_path)


# Example manifest for reference
EXAMPLE_MANIFEST = PluginManifest(
    name="weather",
    version="1.0.0",
    description="Fetches current weather via OpenWeatherMap API",
    author="Mai AI Team",
    entry_point="weather:WeatherPlugin",
    api_version="1.0",
    permissions=PluginPermission(
        filesystem="none",
        network="outbound",
        execution="none",
        api_access=["weather"],
        config="read",
    ),
    dependencies=[],
    hooks=["pre_chat"],
    min_mai_version="1.0.0",
    homepage="https://github.com/mai-ai/plugins",
    repository="https://github.com/mai-ai/plugins",
    license="MIT",
    tags=["weather", "utility"],
)

if __name__ == "__main__":
    # Test validation
    errors = EXAMPLE_MANIFEST.validate()
    print(f"Example manifest errors: {errors}")
    print(json.dumps(EXAMPLE_MANIFEST.to_dict(), indent=2))