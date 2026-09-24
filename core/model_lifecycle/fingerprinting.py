"""
Model Fingerprinting for Mai AI.
Computes deterministic fingerprints for model files and configurations.
"""
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class ModelFingerprinter:
    """Computes deterministic fingerprints for models."""
    
    def __init__(self, algorithm: str = "sha256"):
        self.algorithm = algorithm
        self._hasher = hashlib.new(algorithm)
    
    def fingerprint_file(self, file_path: Union[str, Path]) -> str:
        """Compute fingerprint of a model file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        hasher = hashlib.new(self.algorithm)
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    def fingerprint_config(self, config: Dict[str, Any]) -> str:
        """Compute fingerprint of model configuration."""
        # Sort keys for deterministic output
        config_str = json.dumps(config, sort_keys=True, separators=(',', ':'))
        hasher = hashlib.new(self.algorithm)
        hasher.update(config_str.encode('utf-8'))
        return hasher.hexdigest()
    
    def fingerprint_combined(self, file_path: Union[str, Path], config: Dict[str, Any]) -> str:
        """Compute combined fingerprint of file and config."""
        file_fp = self.fingerprint_file(file_path)
        config_fp = self.fingerprint_config(config)
        
        hasher = hashlib.new(self.algorithm)
        hasher.update(file_fp.encode('utf-8'))
        hasher.update(config_fp.encode('utf-8'))
        return hasher.hexdigest()
    
    def fingerprint_model_artifacts(self, artifacts_dir: Union[str, Path]) -> str:
        """Compute fingerprint of all model artifacts in a directory."""
        path = Path(artifacts_dir)
        if not path.exists() or not path.is_dir():
            raise ValueError(f"Not a directory: {artifacts_dir}")
        
        hasher = hashlib.new(self.algorithm)
        
        # Sort files for deterministic order
        files = sorted(path.rglob('*'))
        for file_path in files:
            if file_path.is_file():
                # Include relative path in hash
                rel_path = file_path.relative_to(path)
                hasher.update(str(rel_path).encode('utf-8'))
                hasher.update(b'\x00')
                
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(8192), b''):
                        hasher.update(chunk)
        
        return hasher.hexdigest()


def compute_model_fingerprint(
    file_path: Union[str, Path],
    config: Optional[Dict[str, Any]] = None,
    algorithm: str = "sha256"
) -> str:
    """Compute model fingerprint (file + optional config)."""
    fingerprinter = ModelFingerprinter(algorithm)
    
    if config:
        return fingerprinter.fingerprint_combined(file_path, config)
    else:
        return fingerprinter.fingerprint_file(file_path)


def compute_config_fingerprint(config: Dict[str, Any], algorithm: str = "sha256") -> str:
    """Compute configuration fingerprint."""
    fingerprinter = ModelFingerprinter(algorithm)
    return fingerprinter.fingerprint_config(config)


def verify_fingerprint(
    file_path: Union[str, Path],
    expected_fingerprint: str,
    config: Optional[Dict[str, Any]] = None,
    algorithm: str = "sha256"
) -> bool:
    """Verify model fingerprint matches expected value."""
    actual = compute_model_fingerprint(file_path, config, algorithm)
    return actual == expected_fingerprint


class FingerprintCache:
    """Cache for model fingerprints to avoid recomputation."""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, str] = {}
        self._access_order: list = []
    
    def get(self, file_path: Union[str, Path], config: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get cached fingerprint."""
        key = self._make_key(file_path, config)
        if key in self._cache:
            # Update access order
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None
    
    def set(self, file_path: Union[str, Path], fingerprint: str, config: Optional[Dict[str, Any]] = None):
        """Cache fingerprint."""
        key = self._make_key(file_path, config)
        
        if key in self._cache:
            self._access_order.remove(key)
        elif len(self._cache) >= self.max_size:
            # Evict LRU
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
        
        self._cache[key] = fingerprint
        self._access_order.append(key)
    
    def _make_key(self, file_path: Union[str, Path], config: Optional[Dict[str, Any]]) -> str:
        """Create cache key."""
        path_str = str(Path(file_path).absolute())
        if config:
            config_str = json.dumps(config, sort_keys=True)
            return f"{path_str}:{hashlib.sha256(config_str.encode()).hexdigest()[:16]}"
        return path_str
    
    def clear(self):
        """Clear cache."""
        self._cache.clear()
        self._access_order.clear()


# Global fingerprint cache
_fingerprint_cache = FingerprintCache()


def get_fingerprint_cached(
    file_path: Union[str, Path],
    config: Optional[Dict[str, Any]] = None,
    algorithm: str = "sha256"
) -> str:
    """Get fingerprint with caching."""
    cached = _fingerprint_cache.get(file_path, config)
    if cached:
        return cached
    
    fingerprint = compute_model_fingerprint(file_path, config, algorithm)
    _fingerprint_cache.set(file_path, fingerprint, config)
    return fingerprint