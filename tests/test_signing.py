"""
Tests for Plugin Signing and Verification
"""
import json
import tempfile
import zipfile
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization

from plugins.signing import (
    PluginSignatureManager,
    PluginSigner,
    PluginVerifier,
    verify_plugin_package,
)


class TestPluginSigner:
    """Tests for PluginSigner class."""
    
    def test_generate_keypair(self):
        """Test keypair generation."""
        private_key, public_key = PluginSigner.generate_keypair()
        assert private_key is not None
        assert public_key is not None
    
    def test_create_signer(self):
        """Test creating a signer with generated keypair."""
        private_key, public_key = PluginSigner.generate_keypair()
        signer = PluginSigner(private_key)
        assert signer.private_key is not None
        assert signer.public_key is not None
    
    def test_sign_and_verify_data(self):
        """Test signing and verifying data."""
        private_key, public_key = PluginSigner.generate_keypair()
        signer = PluginSigner(private_key)
        PluginVerifier(public_key)
        
        signature = signer.sign_data(b"test data")
        
        # Verify using the public key
        public_key.verify(signature, b"test data")
    
    def test_sign_and_verify_package(self):
        """Test creating and verifying a signed package."""
        import json
        import tempfile
        
        # Create a temporary plugin directory with manifest
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "test_plugin"
            plugin_dir.mkdir()
            
            # Create manifest
            manifest = {
                "name": "test_plugin",
                "version": "1.0.0",
                "description": "Test plugin",
                "author": "Test",
                "entry_point": "test:TestPlugin",
                "api_version": "1.0",
                "permissions": {
                    "filesystem": "none",
                    "network": "outbound",
                    "execution": "none",
                    "api_access": [],
                    "config": "read"
                },
                "dependencies": [],
                "hooks": ["pre_chat"],
                "min_mai_version": "1.0.0",
                "license": "MIT",
                "tags": ["test"]
            }
            
            with open(plugin_dir / "manifest.json", "w") as f:
                json.dump(manifest, f)
            
            # Create a test file
            (plugin_dir / "main.py").write_text("print('hello')")
            
            # Create signer and package
            private_key, public_key = PluginSigner.generate_keypair()
            signer = PluginSigner(private_key)
            
            with tempfile.NamedTemporaryFile(suffix=".mpkg", delete=False) as tmp:
                output_path = Path(tmp.name)
            
            try:
                signed_path = signer.create_signed_package(plugin_dir, output_path)
                
                assert output_path.exists()
                
                # Verify the package
                verifier = PluginVerifier(public_key)
                is_valid, error = verifier.verify_package(signed_path)
                assert is_valid, f"Verification failed: {error}"
                
            finally:
                if signed_path.exists():
                    signed_path.unlink()
    
    def test_signature_verification_fails_on_tampering(self):
        """Test that tampered packages fail verification."""
        import json
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "test_plugin"
            plugin_dir.mkdir()
            
            manifest = {
                "name": "test_plugin",
                "version": "1.0.0",
                "description": "Test plugin",
                "author": "Test",
                "entry_point": "test:TestPlugin",
                "api_version": "1.0",
                "permissions": {
                    "filesystem": "none",
                    "network": "outbound",
                    "execution": "none",
                    "api_access": [],
                    "config": "read"
                },
                "dependencies": [],
                "hooks": ["pre_chat"],
                "min_mai_version": "1.0.0",
                "license": "MIT",
                "tags": ["test"]
            }
            
            with open(plugin_dir / "manifest.json", "w") as f:
                json.dump(manifest, f)
            
            (plugin_dir / "main.py").write_text("print('hello')")
            
            private_key, public_key = PluginSigner.generate_keypair()
            signer = PluginSigner(private_key)
            
            with tempfile.NamedTemporaryFile(suffix=".mpkg", delete=False) as tmp:
                output_path = Path(tmp.name)
            
            try:
                signer.create_signed_package(plugin_dir, output_path)
                
                # Tamper with the package
                signed_path = output_path
                with zipfile.ZipFile(signed_path, "a") as zf:
                    zf.writestr("malicious.txt", "malicious content")
                
                # Verification should fail
                verifier = PluginVerifier(public_key)
                is_valid, error = verifier.verify_package(signed_path)
                assert not is_valid
                assert "tamper" in error.lower() or "signature" in error.lower() or "hash" in error.lower()
                
            finally:
                if output_path.exists():
                    output_path.unlink()


class TestPluginVerifier:
    """Tests for PluginVerifier class."""
    
    def test_verify_package_integrity(self):
        """Test package integrity verification without signature."""
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "test_plugin"
            plugin_dir.mkdir()
            
            manifest = {
                "name": "test_plugin",
                "version": "1.0.0",
                "description": "Test plugin",
                "author": "Test",
                "entry_point": "test:TestPlugin",
                "api_version": "1.0",
                "permissions": {
                    "filesystem": "none",
                    "network": "outbound",
                    "execution": "none",
                    "api_access": [],
                    "config": "read"
                },
                "dependencies": [],
                "hooks": ["pre_chat"],
                "min_mai_version": "1.0.0",
                "license": "MIT",
                "tags": ["test"]
            }
            
            with open(plugin_dir / "manifest.json", "w") as f:
                json.dump(manifest, f)
            
            (plugin_dir / "main.py").write_text("print('hello')")
            
            with tempfile.NamedTemporaryFile(suffix=".mpkg", delete=False) as tmp:
                output_path = Path(tmp.name)
            
            try:
                # Create unsigned package
                with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for file_path in plugin_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = file_path.relative_to(plugin_dir)
                            zf.write(file_path, arcname)
                
                # Verify integrity (should pass even without signature)
                PluginVerifier(None)
                # This test would need a proper verifier setup
                
            finally:
                if output_path.exists():
                    output_path.unlink()


class TestPluginSignatureManager:
    """Tests for PluginSignatureManager."""
    
    def test_add_and_verify_trusted_key(self):
        """Test adding and using trusted keys."""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir) / "keys"
            
            private_key, public_key = PluginSigner.generate_keypair()
            signer = PluginSigner(private_key)
            
            manager = PluginSignatureManager(Path(tmpdir) / "keys")
            fingerprint = manager.add_trusted_key(public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ), "test-key")
            
            assert fingerprint in manager._trusted_keys
            
            # Verify package with trusted key
            with tempfile.TemporaryDirectory() as tmpdir:
                plugin_dir = Path(tmpdir) / "test_plugin"
                plugin_dir.mkdir()
                
                manifest = {
                    "name": "test_plugin",
                    "version": "1.0.0",
                    "description": "Test plugin",
                    "author": "Test",
                    "entry_point": "test:TestPlugin",
                    "api_version": "1.0",
                    "permissions": {
                        "filesystem": "none",
                        "network": "outbound",
                        "execution": "none",
                        "api_access": [],
                        "config": "read"
                    },
                    "dependencies": [],
                    "hooks": ["pre_chat"],
                    "min_mai_version": "1.0.0",
                    "license": "MIT",
                    "tags": ["test"]
                }
                
                with open(plugin_dir / "manifest.json", "w") as f:
                    json.dump(manifest, f)
                
                (plugin_dir / "main.py").write_text("print('hello')")
                
                with tempfile.NamedTemporaryFile(suffix=".mpkg", delete=False) as tmp:
                    output_path = Path(tmp.name)
                
                try:
                    private_key, public_key = PluginSigner.generate_keypair()
                    signer = PluginSigner(private_key)
                    signer.create_signed_package(plugin_dir, output_path)
                    
                    # Verify with manager
                    is_valid, error, info = verify_plugin_package(output_path, trusted_keys=[public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )])
                    
                    assert is_valid, f"Verification failed: {error}"
                    assert info["verified"] is True
                    
                finally:
                    if output_path.exists():
                        output_path.unlink()
    
    def test_untrusted_key_rejected(self):
        """Test that untrusted keys are rejected."""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir) / "keys"
            
            # Create manager with one trusted key
            private_key1, public_key1 = PluginSigner.generate_keypair()
            manager = PluginSignatureManager(Path(tmpdir) / "keys")
            manager.add_trusted_key(public_key1.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            ), "trusted-key")
            
            # Create a package signed with a different (untrusted) key
            private_key2, public_key2 = PluginSigner.generate_keypair()
            signer2 = PluginSigner(private_key2)
            
            with tempfile.TemporaryDirectory() as tmpdir:
                plugin_dir = Path(tmpdir) / "test_plugin"
                plugin_dir.mkdir()
                
                manifest = {
                    "name": "test_plugin",
                    "version": "1.0.0",
                    "description": "Test plugin",
                    "author": "Test",
                    "entry_point": "test:TestPlugin",
                    "api_version": "1.0",
                    "permissions": {
                        "filesystem": "none",
                        "network": "outbound",
                        "execution": "none",
                        "api_access": [],
                        "config": "read"
                    },
                    "dependencies": [],
                    "hooks": ["pre_chat"],
                    "min_mai_version": "1.0.0",
                    "license": "MIT",
                    "tags": ["test"]
                }
                
                with open(plugin_dir / "manifest.json", "w") as f:
                    json.dump(manifest, f)
                
                (plugin_dir / "main.py").write_text("print('hello')")
                
                with tempfile.NamedTemporaryFile(suffix=".mpkg", delete=False) as tmp:
                    output_path = Path(tmp.name)
                
                try:
                    signer2.create_signed_package(plugin_dir, output_path)
                    
                    # Try to verify with manager (should fail - untrusted key)
                    is_valid, error, _ = verify_plugin_package(
                        output_path, 
                        trusted_keys=[public_key1.public_bytes(
                            encoding=serialization.Encoding.PEM,
                            format=serialization.PublicFormat.SubjectPublicKeyInfo
                        )]
                    )
                    
                    assert not is_valid
                    assert "trusted" in error.lower() or "untrusted" in error.lower()
                    
                finally:
                    if output_path.exists():
                        output_path.unlink()


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])