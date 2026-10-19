"""
Tests for the Dependency Resolver
"""
import pytest

from plugins.dependency_resolver import (
    CircularDependencyError,
    DependencyGraph,
    DependencyResolver,
    VersionConflictError,
)
from plugins.plugin_manifest import PluginDependency, PluginManifest


class TestDependencyResolver:
    """Tests for the DependencyResolver class."""
    
    def test_resolve_simple_dependency(self):
        """Test resolving a simple dependency."""
        
        resolver = DependencyResolver(None)
        
        manifest = PluginManifest(
            name="test_plugin",
            version="1.0.0",
            description="Test plugin",
            author="Test",
            entry_point="test:TestPlugin",
            dependencies=[
                PluginDependency(name="dep1", version=">=1.0.0 <2.0.0")
            ]
        )
        
        available = {
            "dep1": ["1.0.0", "1.1.0", "1.2.0", "2.0.0"]
        }
        
        resolved = resolver.resolve_dependencies(
            manifest,
            {},  # No installed plugins
            available
        )
        
        assert len(resolved) == 1
        assert resolved[0].name == "dep1"
        assert resolved[0].resolved_version == "1.2.0"  # Highest matching <2.0.0
    
    def test_resolve_with_installed_dependency(self):
        """Test resolving when dependency is already installed."""
        
        resolver = DependencyResolver(None)
        
        manifest = PluginManifest(
            name="test_plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            entry_point="test:TestPlugin",
            dependencies=[
                PluginDependency(name="dep1", version=">=1.0.0 <2.0.0")
            ]
        )
        
        installed = {
            "dep1": PluginManifest(
                name="dep1",
                version="1.5.0",
                description="Dep",
                author="Test",
                entry_point="dep:Dep",
            )
        }
        
        available = {
            "dep1": ["1.0.0", "1.1.0", "1.5.0", "2.0.0"]
        }
        
        resolved = resolver.resolve_dependencies(
            manifest,
            {"dep1": installed["dep1"]},
            available
        )
        
        assert len(resolved) == 1
        assert resolved[0].resolved_version == "1.5.0"
    
    def test_version_conflict_raises(self):
        """Test that version conflicts raise an error."""
        
        resolver = DependencyResolver(None)
        
        PluginManifest(
            name="test",
            version="1.0.0",
            description="test",
            author="test",
            entry_point="t:t",
            dependencies=[PluginDependency(name="dep1", version=">=2.0.0 <3.0.0")]
        )
        
        available = {"dep1": ["1.0.0", "1.5.0"]}  # No version >=2.0.0
        
        with pytest.raises(VersionConflictError):
            resolver.resolve_dependencies(
                PluginManifest(
                    name="test", version="1.0.0", description="test",
                    author="test", entry_point="t:t",
                    dependencies=[PluginDependency(name="dep1", version=">=2.0.0 <3.0.0")]
                ),
                {},
                available
            )
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        from plugins.dependency_resolver import DependencyGraph
        
        graph = DependencyGraph()
        
        # Create plugins A -> B -> A (circular)
        manifest_a = PluginManifest(name="a", version="1.0.0", description="", author="", entry_point="")
        manifest_b = PluginManifest(name="b", version="1.0.0", description="", author="", entry_point="")
        
        graph.add_plugin(manifest_a)
        graph.add_plugin(manifest_b)
        
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "a")
        
        with pytest.raises(CircularDependencyError):
            graph.get_install_order()


class TestDependencyGraph:
    """Tests for the DependencyGraph class."""
    
    def test_get_install_order(self):
        """Test topological sort for installation order."""
        
        graph = DependencyGraph()
        
        # A depends on B and C
        # B depends on C
        a = PluginManifest(name="a", version="1.0", description="", author="", entry_point="")
        b = PluginManifest(name="b", version="1.0", description="", author="", entry_point="")
        c = PluginManifest(name="c", version="1.0", description="", author="", entry_point="")
        
        graph.add_plugin(a)
        graph.add_plugin(b)
        graph.add_plugin(c)
        
        graph.add_dependency("a", "b")
        graph.add_dependency("a", "c")
        graph.add_dependency("b", "c")
        
        order = graph.get_install_order()
        # a should come first, then b, then c (dependents first)
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")
    
    def test_circular_dependency_raises(self):
        """Test that circular dependencies raise an error."""
        
        graph = DependencyGraph()
        
        a = PluginManifest(name="a", version="1.0", description="", author="", entry_point="")
        b = PluginManifest(name="b", version="1.0", description="", author="", entry_point="")
        
        graph.add_plugin(a)
        graph.add_plugin(b)
        graph.add_dependency("a", "b")
        graph.add_dependency("b", "a")
        
        with pytest.raises(CircularDependencyError):
            graph.get_install_order()
    
    def test_get_affected_plugins(self):
        """Test getting affected plugins when one changes."""
        
        graph = DependencyGraph()
        
        a = PluginManifest(name="a", version="1.0", description="", author="", entry_point="")
        b = PluginManifest(name="b", version="1.0", description="", author="", entry_point="")
        c = PluginManifest(name="c", version="1.0", description="", author="", entry_point="")
        
        graph.add_plugin(a)
        graph.add_plugin(b)
        graph.add_plugin(c)
        graph.add_dependency("b", "a")
        graph.add_dependency("c", "b")
        
        affected = graph.get_affected_plugins("a")
        assert "b" in affected
        assert "c" in affected
    
    def test_conflict_detection(self):
        """Test conflict detection between plugins."""
        
        graph = DependencyGraph()
        
        installed = PluginManifest(name="lib", version="1.0", description="", author="", entry_point="")
        graph.add_plugin(installed)
        
        # New plugin requires lib>=2.0
        new = PluginManifest(
            name="app", version="1.0", description="", author="", entry_point="",
            dependencies=[PluginDependency(name="lib", version=">=2.0", optional=False)]
        )
        
        conflicts = graph.check_conflicts(new, {"lib": PluginManifest(name="lib", version="1.0", description="", author="", entry_point="")})
        assert len(conflicts) > 0
        assert ">=2.0" in conflicts[0]


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])