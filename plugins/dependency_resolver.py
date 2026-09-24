"""
Plugin Dependency Resolution with Semantic Versioning
Provides full semantic version resolution with conflict detection.
"""
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from packaging.version import Version, parse
from packaging.specifiers import SpecifierSet
from packaging.requirements import Requirement
import re


class DependencyResolutionError(Exception):
    """Raised when dependency resolution fails."""
    pass


class VersionConflictError(DependencyResolutionError):
    """Raised when version conflicts are detected."""
    pass


class CircularDependencyError(DependencyResolutionError):
    """Raised when circular dependencies are detected."""
    pass


@dataclass
class ResolvedDependency:
    """A resolved dependency with version information."""
    name: str
    required_version: str  # The version constraint (e.g., ">=1.0.0 <2.0.0")
    resolved_version: str  # The actual version that satisfies the constraint
    optional: bool = False


@dataclass
class DependencyNode:
    """Node in the dependency graph."""
    manifest: "PluginManifest"
    dependencies: List["DependencyNode"] = field(default_factory=list)
    dependents: List["DependencyNode"] = field(default_factory=list)
    resolved_version: Optional[str] = None
    state: str = "pending"  # pending, resolved, failed


class DependencyResolver:
    """
    Resolves plugin dependencies with full semantic versioning support.
    Implements a SAT-solver-like approach for dependency resolution.
    """
    
    def __init__(self, registry: Optional["PluginRegistry"] = None):
        self.registry = registry
        self._version_cache: Dict[str, Version] = {}
    
    def parse_version(self, version_str: str) -> Version:
        """Parse version string with caching."""
        if version_str not in self._version_cache:
            self._version_cache[version_str] = parse(version_str)
        return self._version_cache[version_str]
    
    def _parse_specifier(self, specifier: str) -> SpecifierSet:
        """Parse specifier string, handling comma-separated format."""
        # Convert comma-separated to proper format for SpecifierSet
        # e.g., ">=1.0.0 <2.0.0" -> ">=1.0.0,<2.0.0"
        normalized = specifier.replace(" ", ",")
        # Fix double commas
        while ",," in normalized:
            normalized = normalized.replace(",,", ",")
        return SpecifierSet(normalized)
    
    def satisfies(self, version: str, specifier: str) -> bool:
        """Check if a version satisfies a specifier."""
        try:
            spec = self._parse_specifier(specifier)
            return self.parse_version(version) in spec
        except Exception:
            return False
    
    def get_best_version(self, available_versions: List[str], specifier: str) -> Optional[str]:
        """Find the best matching version from available versions."""
        spec = self._parse_specifier(specifier)
        matching = []
        for v in available_versions:
            try:
                if self.parse_version(v) in spec:
                    matching.append((self.parse_version(v), v))
            except Exception:
                continue
        
        if not matching:
            return None
        
        # Return highest matching version
        return max(matching, key=lambda x: x[0])[1]
    
    def resolve_dependencies(
        self, 
        manifest: "PluginManifest",
        installed_plugins: Dict[str, "PluginManifest"],
        available_packages: Dict[str, List[str]] = None
    ) -> List[ResolvedDependency]:
        """
        Resolve all dependencies for a plugin manifest.
        
        Args:
            manifest: The plugin manifest to resolve dependencies for
            installed_plugins: Map of installed plugin name -> manifest
            available_packages: Optional map of package name -> available versions
            
        Returns:
            List of resolved dependencies
            
        Raises:
            VersionConflictError: If version conflicts exist
            CircularDependencyError: If circular dependencies detected
        """
        resolved = []
        visited = set()
        path = set()
        
        def resolve(dep_name: str, constraint: str, path: Set[str]) -> ResolvedDependency:
            if dep_name in path:
                raise CircularDependencyError(f"Circular dependency detected: {' -> '.join(path)} -> {dep_name}")
            
            new_path = path | {dep_name}
            
            # Check if already installed
            if dep_name in self.registry._registry if self.registry else {}:
                installed_data = self.registry.get(dep_name) if self.registry else None
                if installed_data:
                    installed_manifest = PluginManifest.from_dict(installed_data["manifest"])
                    # Check if installed version satisfies constraint
                    if self.satisfies(installed_manifest.version, constraint):
                        return ResolvedDependency(
                            name=dep_name,
                            required_version=constraint,
                            resolved_version=installed_manifest.version,
                            optional=False
                        )
            
            # Find best available version
            available_versions = []
            if dep_name in available_packages:
                available_versions = available_packages[dep_name]
            else:
                # Check installed plugins
                for name, manifest in available_packages.items():
                    if name == dep_name:
                        available_versions.append(manifest.version)
            
            best_version = self.get_best_version(available_versions, constraint)
            if best_version:
                return ResolvedDependency(
                    name=dep_name,
                    required_version=constraint,
                    resolved_version=best_version,
                    optional=False
                )
            
            # Check installed plugins
            for name, manifest in available_packages.items():
                if name == dep_name:
                    if self.satisfies(manifest.version, constraint):
                        return ResolvedDependency(
                            name=dep_name,
                            required_version=constraint,
                            resolved_version=manifest.version,
                            optional=False
                        )
            
            # Not found
            raise VersionConflictError(
                f"Dependency '{dep_name}' with constraint '{constraint}' could not be satisfied. "
                f"Available versions: {available_versions if available_versions else 'none'}"
            )
        
        # Resolve all dependencies
        results = []
        for dep in manifest.dependencies:
            try:
                resolved = resolve(dep.name, dep.version, set())
                results.append(resolved)
            except (VersionConflictError, CircularDependencyError) as e:
                raise
            except Exception as e:
                if not dep.optional:
                    raise VersionConflictError(
                        f"Failed to resolve dependency '{dep.name}': {e}"
                    )
        
        return results


class DependencyGraph:
    """Manages the dependency graph for installed plugins."""
    
    def __init__(self):
        self.nodes: Dict[str, DependencyNode] = {}
        self._lock = threading.RLock()
    
    def add_plugin(self, manifest: "PluginManifest") -> DependencyNode:
        """Add a plugin to the graph."""
        with self._lock:
            if manifest.name in self.nodes:
                node = self.nodes[manifest.name]
                node.manifest = manifest
                return node
            
            node = DependencyNode(manifest=manifest)
            self.nodes[manifest.name] = node
            return node
    
    def remove_plugin(self, name: str) -> None:
        """Remove a plugin from the graph."""
        with self._lock:
            if name in self.nodes:
                node = self.nodes[name]
                # Remove from dependents
                for dep in node.dependencies:
                    if node in dep.dependents:
                        dep.dependents.remove(node)
                # Remove from dependencies
                for dep in node.dependents:
                    if node in dep.dependencies:
                        dep.dependencies.remove(node)
                del self.nodes[name]
    
    def add_dependency(self, from_name: str, to_name: str) -> None:
        """Add a dependency edge."""
        with self._lock:
            if from_name in self.nodes and to_name in self.nodes:
                from_node = self.nodes[from_name]
                to_node = self.nodes[to_name]
                if to_node not in from_node.dependencies:
                    from_node.dependencies.append(to_node)
                if from_node not in to_node.dependents:
                    to_node.dependents.append(from_node)
    
    def check_circular(self, start: str, target: str, visited: Set[str] = None) -> bool:
        """Check if adding an edge would create a cycle."""
        if visited is None:
            visited = set()
        
        if start == target:
            return True
        
        if start in visited:
            return False
        
        visited.add(start)
        
        if start in self.nodes:
            node = self.nodes[start]
            for dep in node.dependencies:
                if self.check_circular(dep.manifest.name, target, visited):
                    return True
        
        return False
    
    def get_install_order(self) -> List[str]:
        """Get topological sort for installation order (dependencies first)."""
        with self._lock:
            # Kahn's algorithm for topological sort
            in_degree = {}
            for name, node in self.nodes.items():
                in_degree[name] = len(node.dependents)
            
            queue = [name for name, degree in in_degree.items() if degree == 0]
            result = []
            
            while queue:
                name = queue.pop(0)
                result.append(name)
                if name in self.nodes:
                    node = self.nodes[name]
                    for dep in node.dependencies:
                        in_degree[dep.manifest.name] -= 1
                        if in_degree[dep.manifest.name] == 0:
                            queue.append(dep.manifest.name)
            
            if len(result) != len(self.nodes):
                # Cycle detected
                raise CircularDependencyError("Circular dependency detected in plugin graph")
            
            return result
    
    def get_affected_plugins(self, name: str) -> Set[str]:
        """Get all plugins that depend on the given plugin (transitively)."""
        affected = set()
        
        def collect_dependents(name: str):
            if name in self.nodes:
                node = self.nodes[name]
                for dependent in node.dependents:
                    if dependent.manifest.name not in affected:
                        affected.add(dependent.manifest.name)
                        collect_dependents(dependent.manifest.name)
        
        collect_dependents(name)
        return affected
    
    def check_conflicts(self, new_manifest: "PluginManifest", 
                       installed_plugins: Dict[str, "PluginManifest"]) -> List[str]:
        """Check for conflicts when installing a new plugin."""
        conflicts = []
        
        # Check direct conflicts
        for dep in new_manifest.dependencies:
            if dep.name in installed_plugins:
                installed = installed_plugins[dep.name]
                try:
                    spec = SpecifierSet(dep.version)
                    if parse(installed.version) not in spec:
                        conflicts.append(
                            f"Plugin requires {dep.name}{dep.version} but "
                            f"{installed.version} is installed"
                        )
                except Exception:
                    pass
        
        # Check if this plugin conflicts with any installed plugin
        for name, manifest in installed_plugins.items():
            for dep in manifest.dependencies:
                if dep.name == new_manifest.name:
                    try:
                        spec = SpecifierSet(dep.version)
                        if parse(new_manifest.version) not in spec:
                            conflicts.append(
                                f"Plugin '{name}' requires {new_manifest.name}{dep.version} "
                                f"but {new_manifest.version} would be installed"
                            )
                    except Exception:
                        pass
        
        return conflicts


# Import threading at module level
import threading