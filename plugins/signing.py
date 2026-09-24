"""
Plugin Signature Verification
Provides Ed25519 signature verification for plugin packages.
"""
import os
import base64
import hashlib
import json
import time
import shutil
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature
import base64
import zipfile


@dataclass
class SignatureInfo:
    """Information about a plugin signature."""
    signature: bytes
    public_key: bytes
    algorithm: str = "Ed25519"
    signed_at: float = 0
    signer: str = ""


class PluginSigner:
    """Handles plugin package signing and verification."""
    
    # Standard algorithm identifier
    ALGORITHM = "Ed25519"
    
    def __init__(self, private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        """
        Initialize the signer.
        
        Args:
            private_key: Optional Ed25519 private key. If not provided, a new one is generated.
        """
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
    
    @classmethod
    def generate_keypair(cls) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
        """Generate a new Ed25519 keypair."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        return private_key, private_key.public_key()
    
    @classmethod
    def from_private_key_pem(cls, pem: bytes) -> "PluginSigner":
        """Create signer from PEM-encoded private key."""
        private_key = serialization.load_pem_private_key(pem, password=None)
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError("Private key must be Ed25519")
        return cls(private_key)
    
    @classmethod
    def from_private_key_file(cls, path: Path) -> "PluginSigner":
        """Load signer from a PEM file."""
        with open(path, "rb") as f:
            pem = f.read()
        return cls.from_private_key_pem(pem)
    
    @classmethod
    def from_public_key_file(cls, path: Path) -> "PluginVerifier":
        """Create a verifier from a public key file."""
        with open(path, "rb") as f:
            pem = f.read()
        public_key = serialization.load_pem_public_key(pem)
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Public key must be Ed25519")
        return PluginVerifier(public_key)
    
    def get_public_key_pem(self) -> bytes:
        """Get the public key in PEM format."""
        return self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def get_private_key_pem(self) -> bytes:
        """Get the private key in PEM format (PKCS8, unencrypted)."""
        return self.private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
    
    def sign_data(self, data: bytes) -> bytes:
        """Sign arbitrary data."""
        return self.private_key.sign(data)
    
    def sign_package(self, package_path: Path) -> bytes:
        """
        Sign a plugin package.
        
        Computes SHA256 of the package contents and signs the hash.
        """
        # Compute hash of package contents
        with open(package_path, "rb") as f:
            content = f.read()
        
        digest = hashlib.sha256(content).digest()
        
        # Create signing data with metadata
        signing_data = {
            "algorithm": "Ed25519",
            "hash_algorithm": "SHA256",
            "content_hash": base64.b64encode(digest).decode(),
            "signed_at": time.time(),
        }
        
        signing_data_json = json.dumps(signing_data, separators=(',', ':')).encode()
        
        # Sign the signing data
        signature = self.private_key.sign(signing_data_json)
        
        return signature
    
    def create_signed_package(self, source_dir: Path, output_path: Path) -> Path:
        """
        Create a signed .mpkg package from a directory.
        
        Args:
            source_dir: Directory containing plugin files (must have manifest.json)
            output_path: Path to write the .mpkg file
            
        Returns:
            Path to the created package
        """
        import zipfile
        import tempfile
        import json
        
        source_dir = Path(source_dir)
        
        # Verify manifest exists
        manifest_path = source_dir / "manifest.json"
        if not manifest_path.exists():
            raise ValueError("manifest.json not found in source directory")
        
        # Compute content hash from source files directly (before creating zip)
        content_hash = hashlib.sha256()
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                with open(file_path, "rb") as f:
                    content_hash.update(f.read())
        content_hash_b64 = base64.b64encode(content_hash.digest()).decode()
        
        # Create package
        with tempfile.NamedTemporaryFile(suffix=".mpkg", delete=False) as tmp:
            temp_path = Path(tmp.name)
        
        try:
            with zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                # Add all files from source directory
                for file_path in source_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(source_dir)
                        zf.write(file_path, arcname)
                
                # Add signature file
                manifest_path = source_dir / "manifest.json"
                with open(manifest_path, "r") as f:
                    manifest_data = json.load(f)
                
                # Sign the package content - use a single timestamp for consistency
                signed_at = time.time()
                signing_data = {
                    "algorithm": "Ed25519",
                    "hash_algorithm": "SHA256",
                    "content_hash": content_hash_b64,
                    "signed_at": signed_at,
                }
                
                signing_data_json = json.dumps(signing_data, separators=(',', ':')).encode()
                signature = self.private_key.sign(signing_data_json)
                
                # Add signature to package - use the SAME timestamp
                sig_data = {
                    "signature": base64.b64encode(signature).decode(),
                    "algorithm": "Ed25519",
                    "public_key": base64.b64encode(self.get_public_key_pem()).decode(),
                    "signed_at": signed_at,
                    "content_hash": content_hash_b64,
                }
                
                # Add signature file to package
                sig_json = json.dumps(sig_data, separators=(',', ':')).encode()
                zf.writestr(".signature.json", sig_json)
        
            # Move to final location
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(temp_path, output_path)
            
            return output_path
        
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise


class PluginVerifier:
    """Verifies plugin package signatures."""
    
    def __init__(self, public_key: ed25519.Ed25519PublicKey):
        self.public_key = public_key
    
    @classmethod
    def from_public_key_pem(cls, pem: bytes) -> "PluginVerifier":
        """Create verifier from PEM-encoded public key."""
        public_key = serialization.load_pem_public_key(pem)
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Public key must be Ed25519")
        return PluginVerifier(public_key)
    
    @classmethod
    def from_public_key_file(cls, path: Path) -> "PluginVerifier":
        """Load verifier from a public key PEM file."""
        with open(path, "rb") as f:
            pem = f.read()
        return cls.from_public_key_pem(pem)
    
    @classmethod
    def from_package(cls, package_path: Path) -> "PluginVerifier":
        """Extract and create verifier from package signature."""
        import zipfile
        import json
        import tempfile
        
        with zipfile.ZipFile(package_path, "r") as zf:
            # Look for signature file
            sig_files = [f for f in zf.namelist() if f.endswith(".signature.json") or f == ".signature.json"]
            if not sig_files:
                raise ValueError("No signature file found in package")
            
            sig_name = sig_files[0]
            sig_data = json.loads(zf.read(sig_name).decode())
            
            public_key_pem = base64.b64decode(sig_data["public_key"])
            public_key = serialization.load_pem_public_key(public_key_pem)
            
            return PluginVerifier(public_key)
    
    def verify_package(self, package_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Verify a plugin package signature.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        import zipfile
        import json
        import tempfile
        
        if not zipfile.is_zipfile(package_path):
            return False, "Not a valid zip file"
        
        try:
            with zipfile.ZipFile(package_path, "r") as zf:
                # Find signature file
                sig_files = [f for f in zf.namelist() if f.endswith(".signature.json") or f == ".signature.json"]
                if not sig_files:
                    return False, "No signature file found in package"
                
                sig_name = sig_files[0]
                sig_data = json.loads(zf.read(sig_name).decode())
                
                # Extract signature
                signature = base64.b64decode(sig_data["signature"])
                signed_at = sig_data.get("signed_at", 0)
                
                # Verify the public key matches
                public_key_pem_verify = base64.b64encode(
                    self.public_key.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    )
                ).decode()
                
                if public_key_pem_verify.strip() != sig_data["public_key"].strip():
                    return False, "Public key in signature does not match verifier"
                
                # Read package content (excluding signature file) to compute content hash
                content_hash = hashlib.sha256()
                
                for file_info in zf.infolist():
                    if file_info.filename != ".signature.json" and not file_info.filename.endswith(".signature.json"):
                        with zf.open(file_info) as f:
                            content_hash.update(f.read())
                
                computed_hash = base64.b64encode(content_hash.digest()).decode()
                
                # Verify the signature
                # The signature was created over signing_data_json which includes:
                # - algorithm
                # - hash_algorithm
                # - content_hash (the computed hash)
                # - signed_at
                # We need to reconstruct the exact same signing_data_json
                if sig_data.get("content_hash") != computed_hash:
                    return False, f"Content hash mismatch: expected {sig_data.get('content_hash')}, got {computed_hash}"
                
                signing_data = {
                    "algorithm": sig_data.get("algorithm", "Ed25519"),
                    "hash_algorithm": sig_data.get("hash_algorithm", "SHA256"),
                    "content_hash": sig_data["content_hash"],
                    "signed_at": sig_data["signed_at"],
                }
                
                signing_data_json = json.dumps(signing_data, separators=(',', ':')).encode()
                
                # Verify the signature
                try:
                    self.public_key.verify(signature, signing_data_json)
                    return True, None
                except InvalidSignature:
                    return False, "Signature verification failed"
                except Exception as e:
                    return False, f"Verification error: {e}"
        
        except Exception as e:
            return False, f"Verification failed: {e}"
    
    def verify_package_integrity(self, package_path: Path) -> Tuple[bool, Optional[str]]:
        """Verify package integrity without checking signature (for unsigned packages)."""
        import zipfile
        import hashlib
        
        if not zipfile.is_zipfile(package_path):
            return False, "Not a valid zip file"
        
        try:
            with zipfile.ZipFile(package_path, "r") as zf:
                # Check for manifest
                if "manifest.json" not in zf.namelist():
                    return False, "No manifest.json found"
                
                # Verify all files can be read
                for file_info in zf.infolist():
                    if file_info.filename.endswith(".signature.json") or file_info.filename == ".signature.json":
                        continue
                    try:
                        with zf.open(file_info) as f:
                            f.read()
                    except Exception as e:
                        return False, f"Failed to read {file_info.filename}: {e}"
                
                return True, None
        except Exception as e:
            return False, f"Integrity check failed: {e}"


def verify_plugin_package(package_path: Path, trusted_keys: Optional[list] = None) -> Tuple[bool, Optional[str], Optional[dict]]:
    """
    Verify a plugin package signature and integrity.
    
    Args:
        package_path: Path to the .mpkg package
        trusted_keys: Optional list of trusted public keys (PEM format)
        
    Returns:
        Tuple of (is_valid, error_message, signature_info)
    """
    import zipfile
    import json
    import base64
    
    try:
        with zipfile.ZipFile(package_path, "r") as zf:
            # Check for signature
            sig_files = [f for f in zf.namelist() 
                        if f == ".signature.json" or f.endswith(".signature.json")]
            
            if not sig_files:
                return False, "No signature found in package", None
            
            sig_name = sig_files[0]
            sig_data = json.loads(zf.read(sig_files[0]).decode())
            
            # Extract signature info
            signature = base64.b64decode(sig_data["signature"])
            public_key_pem = base64.b64decode(sig_data["public_key"])
            signed_at = sig_data.get("signed_at", 0)
            algorithm = sig_data.get("algorithm", "Ed25519")
            
            # Verify against trusted keys if provided
            if trusted_keys:
                trusted = False
                # sig_data["public_key"] is base64 encoded, decode it for comparison
                sig_public_key = base64.b64decode(sig_data["public_key"])
                for key_pem in trusted_keys:
                    if isinstance(key_pem, str):
                        key_pem = key_pem.encode()
                    if key_pem.strip() == sig_public_key.strip():
                        trusted = True
                        break
                if not trusted:
                    return False, "Signature not from trusted key", None
            
            # Verify signature
            public_key = serialization.load_pem_public_key(
                base64.b64decode(sig_data["public_key"])
            )
            
            if not isinstance(public_key, ed25519.Ed25519PublicKey):
                return False, "Public key is not Ed25519", None
            
            # Compute hash of package contents (excluding signature)
            content_hash = hashlib.sha256()
            with zipfile.ZipFile(package_path, "r") as zf:
                for file_info in zf.infolist():
                    if file_info.filename != ".signature.json" and not file_info.filename.endswith(".signature.json"):
                        with zf.open(file_info) as f:
                            content_hash.update(f.read())
            
            # Verify content hash matches what was signed
            computed_hash = base64.b64encode(content_hash.digest()).decode()
            if sig_data.get("content_hash") != computed_hash:
                return False, f"Content hash mismatch: expected {sig_data.get('content_hash')}, got {computed_hash}", None
            
            # Reconstruct the exact signing data that was signed
            signing_data = {
                "algorithm": sig_data.get("algorithm", "Ed25519"),
                "hash_algorithm": sig_data.get("hash_algorithm", "SHA256"),
                "content_hash": sig_data["content_hash"],
                "signed_at": sig_data["signed_at"],
            }
            
            signing_data_json = json.dumps(signing_data, separators=(',', ':')).encode()
            
            # Verify signature
            try:
                public_key.verify(signature, signing_data_json)
                return True, None, {
                    "algorithm": "Ed25519",
                    "public_key": sig_data["public_key"],
                    "signed_at": signed_at,
                    "verified": True
                }
            except InvalidSignature:
                return False, "Invalid signature", None
            
    except InvalidSignature:
        return False, "Invalid signature", None
    except Exception as e:
        return False, f"Verification failed: {e}", None


class PluginSignatureManager:
    """Manages trusted plugin signing keys and package verification."""
    
    def __init__(self, keys_dir: Path):
        """
        Initialize the signature manager.
        
        Args:
            keys_dir: Directory to store trusted public keys
        """
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self._trusted_keys = {}
        self._load_trusted_keys()
    
    def _load_trusted_keys(self):
        """Load trusted keys from the keys directory."""
        import json
        for key_file in self.keys_dir.glob("*.pem"):
            try:
                with open(key_file, "rb") as f:
                    pem = f.read()
                # Compute fingerprint
                public_key = serialization.load_pem_public_key(pem)
                if isinstance(public_key, ed25519.Ed25519PublicKey):
                    fingerprint = self._compute_fingerprint(public_key)
                    self._trusted_keys[fingerprint] = {
                        "pem": pem,
                        "key_id": key_file.stem,
                    }
            except Exception:
                pass  # Skip invalid key files
    
    def _compute_fingerprint(self, public_key: ed25519.Ed25519PublicKey) -> str:
        """Compute a fingerprint for a public key."""
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return hashlib.sha256(pem).hexdigest()[:16]
    
    def add_trusted_key(self, public_key_pem: bytes, key_id: str) -> str:
        """
        Add a trusted public key.
        
        Args:
            public_key_pem: PEM-encoded public key
            key_id: Identifier for the key
            
        Returns:
            Fingerprint of the added key
        """
        public_key = serialization.load_pem_public_key(public_key_pem)
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("Public key must be Ed25519")
        
        fingerprint = self._compute_fingerprint(public_key)
        
        # Save to file
        key_file = self.keys_dir / f"{key_id}.pem"
        with open(key_file, "wb") as f:
            f.write(public_key_pem)
        
        # Store in memory
        self._trusted_keys[fingerprint] = {
            "pem": public_key_pem,
            "key_id": key_id,
        }
        
        return fingerprint
    
    def remove_trusted_key(self, fingerprint: str) -> bool:
        """
        Remove a trusted key.
        
        Args:
            fingerprint: Fingerprint of the key to remove
            
        Returns:
            True if key was removed, False if not found
        """
        if fingerprint in self._trusted_keys:
            key_id = self._trusted_keys[fingerprint]["key_id"]
            key_file = self.keys_dir / f"{key_id}.pem"
            if key_file.exists():
                key_file.unlink()
            del self._trusted_keys[fingerprint]
            return True
        return False
    
    def get_trusted_keys(self) -> list:
        """Get list of trusted key fingerprints."""
        return list(self._trusted_keys.keys())
    
    def verify_package(self, package_path: Path) -> tuple[bool, Optional[str], Optional[dict]]:
        """
        Verify a package against trusted keys.
        
        Returns:
            Tuple of (is_valid, error_message, signature_info)
        """
        trusted_pems = [info["pem"] for info in self._trusted_keys.values()]
        return verify_plugin_package(package_path, trusted_keys=trusted_pems)
    
    def get_trusted_key_pems(self) -> list:
        """Get all trusted public keys in PEM format."""
        return [info["pem"] for info in self._trusted_keys.values()]