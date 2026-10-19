"""
Model Registry for Mai AI.
Manages model versions, metadata, and lifecycle state.
"""
import hashlib
import json
import logging
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from core.model_lifecycle.fingerprinting import compute_model_fingerprint

logger = logging.getLogger(__name__)


class ModelStatus(Enum):
    """Model deployment status."""
    REGISTERED = "registered"
    STAGING = "staging"
    CANARY = "canary"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ModelType(Enum):
    """Types of models managed."""
    LLM = "llm"
    EMBEDDING = "embedding"
    VAD = "vad"
    STT = "stt"
    TTS = "tts"
    SPEAKER_ENCODER = "speaker_encoder"
    CLASSIFIER = "classifier"
    CUSTOM = "custom"


@dataclass
class ModelMetadata:
    """Metadata for a model version."""
    model_id: str
    version: str
    model_type: ModelType
    name: str
    description: str
    fingerprint: str
    source_url: str
    file_path: str
    file_size: int
    file_hash: str
    framework: str
    framework_version: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    tags: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    status: ModelStatus = ModelStatus.REGISTERED
    deployed_at: str | None = None
    deprecated_at: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['model_type'] = self.model_type.value
        data['status'] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'ModelMetadata':
        data = data.copy()
        data['model_type'] = ModelType(data['model_type'])
        data['status'] = ModelStatus(data['status'])
        return cls(**data)


@dataclass
class ModelVersion:
    """A specific version of a model."""
    metadata: ModelMetadata
    is_active: bool = False
    deployment_config: dict[str, Any] = field(default_factory=dict)
    health_checks: dict[str, Any] = field(default_factory=dict)
    rollout_percentage: float = 0.0
    error_rate: float = 0.0
    latency_p99: float = 0.0
    request_count: int = 0


class ModelRegistry:
    """Central registry for all model versions."""
    
    def __init__(self, db_path: str = "data/models.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._init_db()
        self._cache: dict[str, ModelVersion] = {}
    
    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS models (
                    model_id TEXT NOT NULL,
                    version TEXT NOT NULL,
                    model_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    fingerprint TEXT NOT NULL,
                    source_url TEXT,
                    file_path TEXT,
                    file_size INTEGER,
                    file_hash TEXT,
                    framework TEXT,
                    framework_version TEXT,
                    input_schema TEXT,
                    output_schema TEXT,
                    tags TEXT,
                    config TEXT,
                    metrics TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    status TEXT,
                    deployed_at TEXT,
                    deprecated_at TEXT,
                    is_active INTEGER DEFAULT 0,
                    deployment_config TEXT,
                    health_checks TEXT,
                    rollout_percentage REAL DEFAULT 0.0,
                    error_rate REAL DEFAULT 0.0,
                    latency_p99 REAL DEFAULT 0.0,
                    request_count INTEGER DEFAULT 0,
                    PRIMARY KEY (model_id, version)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_status 
                ON models(model_id, status)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_fingerprint 
                ON models(fingerprint)
            """)
            conn.commit()
    
    def register(
        self,
        model_id: str,
        version: str,
        model_type: ModelType,
        name: str,
        description: str,
        file_path: str,
        source_url: str = "",
        framework: str = "unknown",
        framework_version: str = "unknown",
        input_schema: dict[str, Any] = None,
        output_schema: dict[str, Any] = None,
        tags: list[str] = None,
        config: dict[str, Any] = None,
    ) -> ModelVersion:
        """Register a new model version."""
        with self._lock:
            path = Path(file_path)
            if not path.exists():
                raise FileNotFoundError(f"Model file not found: {file_path}")
            
            # Compute fingerprints
            fingerprint = compute_model_fingerprint(file_path)
            file_hash = self._compute_file_hash(file_path)
            file_size = path.stat().st_size
            
            metadata = ModelMetadata(
                model_id=model_id,
                version=version,
                model_type=model_type,
                name=name,
                description=description,
                fingerprint=fingerprint,
                source_url=source_url,
                file_path=str(path.absolute()),
                file_size=file_size,
                file_hash=file_hash,
                framework=framework,
                framework_version=framework_version,
                input_schema=input_schema or {},
                output_schema=output_schema or {},
                tags=tags or [],
                config=config or {},
            )
            
            model_version = ModelVersion(metadata=metadata)
            
            # Save to database
            self._save_to_db(model_version)
            
            # Update cache
            cache_key = f"{model_id}:{version}"
            self._cache[cache_key] = model_version
            
            logger.info(f"Registered model: {model_id}:{version} (fingerprint: {fingerprint[:16]}...)")
            return model_version
    
    def _save_to_db(self, model_version: ModelVersion):
        """Save model version to database."""
        m = model_version.metadata
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO models VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                m.model_id, m.version, m.model_type.value, m.name, m.description,
                m.fingerprint, m.source_url, m.file_path, m.file_size, m.file_hash,
                m.framework, m.framework_version, json.dumps(m.input_schema),
                json.dumps(m.output_schema), json.dumps(m.tags), json.dumps(m.config),
                json.dumps(m.metrics), m.created_at, m.updated_at, m.status.value,
                m.deployed_at, m.deprecated_at,
                1 if model_version.is_active else 0,
                json.dumps(model_version.deployment_config),
                json.dumps(model_version.health_checks),
                model_version.rollout_percentage,
                model_version.error_rate,
                model_version.latency_p99,
                model_version.request_count,
            ))
            conn.commit()
    
    def _load_from_db(self, model_id: str, version: str) -> ModelVersion | None:
        """Load model version from database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM models WHERE model_id = ? AND version = ?",
                (model_id, version)
            ).fetchone()
            
            if not row:
                return None
            
            metadata = ModelMetadata(
                model_id=row['model_id'],
                version=row['version'],
                model_type=ModelType(row['model_type']),
                name=row['name'],
                description=row['description'],
                fingerprint=row['fingerprint'],
                source_url=row['source_url'],
                file_path=row['file_path'],
                file_size=row['file_size'],
                file_hash=row['file_hash'],
                framework=row['framework'],
                framework_version=row['framework_version'],
                input_schema=json.loads(row['input_schema']),
                output_schema=json.loads(row['output_schema']),
                tags=json.loads(row['tags']),
                config=json.loads(row['config']),
                metrics=json.loads(row['metrics']),
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                status=ModelStatus(row['status']),
                deployed_at=row['deployed_at'],
                deprecated_at=row['deprecated_at'],
            )
            
            return ModelVersion(
                metadata=metadata,
                is_active=bool(row['is_active']),
                deployment_config=json.loads(row['deployment_config']),
                health_checks=json.loads(row['health_checks']),
                rollout_percentage=row['rollout_percentage'],
                error_rate=row['error_rate'],
                latency_p99=row['latency_p99'],
                request_count=row['request_count'],
            )
    
    def get(self, model_id: str, version: str) -> ModelVersion | None:
        """Get a specific model version."""
        cache_key = f"{model_id}:{version}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        with self._lock:
            model_version = self._load_from_db(model_id, version)
            if model_version:
                self._cache[cache_key] = model_version
            return model_version
    
    def get_latest(self, model_id: str, status: ModelStatus = None) -> ModelVersion | None:
        """Get latest version of a model."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT version FROM models WHERE model_id = ?"
            params = [model_id]
            if status:
                query += " AND status = ?"
                params.append(status.value)
            query += " ORDER BY created_at DESC LIMIT 1"
            
            row = conn.execute(query, params).fetchone()
            if row:
                return self.get(model_id, row['version'])
            return None
    
    def get_production(self, model_id: str) -> ModelVersion | None:
        """Get production version of a model."""
        return self.get_latest(model_id, ModelStatus.PRODUCTION)
    
    def get_staging(self, model_id: str) -> ModelVersion | None:
        """Get staging version of a model."""
        return self.get_latest(model_id, ModelStatus.STAGING)
    
    def get_canary(self, model_id: str) -> ModelVersion | None:
        """Get canary version of a model."""
        return self.get_latest(model_id, ModelStatus.CANARY)
    
    def list_versions(self, model_id: str) -> list[ModelVersion]:
        """List all versions of a model."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT version FROM models WHERE model_id = ? ORDER BY created_at DESC",
                (model_id,)
            ).fetchall()
            
            versions = []
            for row in rows:
                mv = self.get(model_id, row['version'])
                if mv:
                    versions.append(mv)
            return versions
    
    def update_status(
        self,
        model_id: str,
        version: str,
        status: ModelStatus,
        deployment_config: dict[str, Any] = None
    ) -> ModelVersion:
        """Update model status."""
        with self._lock:
            model_version = self.get(model_id, version)
            if not model_version:
                raise ValueError(f"Model not found: {model_id}:{version}")
            
            model_version.metadata.status = status
            model_version.metadata.updated_at = datetime.utcnow().isoformat()
            
            if status in (ModelStatus.STAGING, ModelStatus.CANARY, ModelStatus.PRODUCTION):
                model_version.metadata.deployed_at = datetime.utcnow().isoformat()
            elif status == ModelStatus.DEPRECATED:
                model_version.metadata.deprecated_at = datetime.utcnow().isoformat()
            
            if deployment_config:
                model_version.deployment_config.update(deployment_config)
            
            self._save_to_db(model_version)
            self._cache[f"{model_id}:{version}"] = model_version
            
            logger.info(f"Updated {model_id}:{version} status to {status.value}")
            return model_version
    
    def update_metrics(
        self,
        model_id: str,
        version: str,
        error_rate: float = None,
        latency_p99: float = None,
        request_count: int = None,
        custom_metrics: dict[str, float] = None
    ) -> ModelVersion:
        """Update model performance metrics."""
        with self._lock:
            model_version = self.get(model_id, version)
            if not model_version:
                raise ValueError(f"Model not found: {model_id}:{version}")
            
            if error_rate is not None:
                model_version.error_rate = error_rate
            if latency_p99 is not None:
                model_version.latency_p99 = latency_p99
            if request_count is not None:
                model_version.request_count = request_count
            if custom_metrics:
                model_version.metadata.metrics.update(custom_metrics)
            
            model_version.metadata.updated_at = datetime.utcnow().isoformat()
            self._save_to_db(model_version)
            self._cache[f"{model_id}:{version}"] = model_version
            
            return model_version
    
    def update_rollout(self, model_id: str, version: str, percentage: float) -> ModelVersion:
        """Update rollout percentage."""
        with self._lock:
            model_version = self.get(model_id, version)
            if not model_version:
                raise ValueError(f"Model not found: {model_id}:{version}")
            
            model_version.rollout_percentage = max(0.0, min(100.0, percentage))
            model_version.metadata.updated_at = datetime.utcnow().isoformat()
            self._save_to_db(model_version)
            self._cache[f"{model_id}:{version}"] = model_version
            
            return model_version
    
    def deprecate(self, model_id: str, version: str) -> ModelVersion:
        """Deprecate a model version."""
        return self.update_status(model_id, version, ModelStatus.DEPRECATED)
    
    def archive(self, model_id: str, version: str) -> ModelVersion:
        """Archive a model version."""
        return self.update_status(model_id, version, ModelStatus.ARCHIVED)
    
    def delete(self, model_id: str, version: str) -> bool:
        """Delete a model version (only if not active)."""
        with self._lock:
            model_version = self.get(model_id, version)
            if not model_version:
                return False
            
            if model_version.is_active or model_version.metadata.status in (
                ModelStatus.PRODUCTION, ModelStatus.CANARY, ModelStatus.STAGING
            ):
                raise ValueError("Cannot delete active or deployed model")
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM models WHERE model_id = ? AND version = ?",
                    (model_id, version)
                )
                conn.commit()
            
            cache_key = f"{model_id}:{version}"
            self._cache.pop(cache_key, None)
            
            # Delete model file if it's local
            try:
                Path(model_version.metadata.file_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Failed to delete model file: {e}")
            
            return True
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA-256 hash of model file."""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    
    def find_by_fingerprint(self, fingerprint: str) -> list[ModelVersion]:
        """Find all model versions with matching fingerprint."""
        with self._lock, sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT model_id, version FROM models WHERE fingerprint = ?",
                (fingerprint,)
            ).fetchall()
            
            versions = []
            for row in rows:
                mv = self.get(row['model_id'], row['version'])
                if mv:
                    versions.append(mv)
            return versions


# Global registry instance
_registry: ModelRegistry | None = None
_registry_lock = threading.Lock()


def get_registry(db_path: str = "data/models.db") -> ModelRegistry:
    """Get global model registry instance."""
    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = ModelRegistry(db_path)
        return _registry


def init_registry(db_path: str = "data/models.db") -> ModelRegistry:
    """Initialize global model registry."""
    global _registry
    with _registry_lock:
        _registry = ModelRegistry(db_path)
    return _registry