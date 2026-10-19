# core/state/redis_state.py
"""
Redis-backed SharedState implementation.

Provides distributed, fault-tolerant state management with Redis backend.
Falls back to in-memory if Redis unavailable.
"""
import json
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import redis
from redis.connection import ConnectionPool

from core.state.db import EvidenceDB
from core.state.models import (
    AttentionState,
    EmotionState,
    GoalState,
    RelationshipValues,
    RuntimeStateFields,
)

logger = logging.getLogger(__name__)


@dataclass
class RedisConfig:
    """Redis connection configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str | None = None
    ssl: bool = False
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    decode_responses: bool = True


class RedisSharedState:
    """
    Redis-backed SharedState with in-memory fallback.
    
    Provides distributed state management with automatic failover
    to in-memory storage when Redis is unavailable.
    """
    
    KEY_PREFIX = "mai:state"
    LOCK_TTL = 10  # seconds
    HEARTBEAT_TTL = 30
    
    def __init__(
        self,
        persistence_dir: Path,
        redis_config: RedisConfig | None = None,
        redis_client: redis.Redis | None = None,
    ):
        self.persistence_dir = persistence_dir
        self.redis_config = redis_config or RedisConfig()
        self._redis_client = redis_client
        self._pool = None
        self._lock = threading.RLock()
        self._available = False
        self._fallback = InMemoryState()

        # Interface parity with core.state.shared_state.SharedState:
        # RelationshipEngineV2, Brain and OsKernel access `state.lock`,
        # `state.db` (SQLite evidence store) and `state.state_dir`.
        self.lock = self._lock
        self.state_dir = Path(persistence_dir) / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.db = EvidenceDB(self.state_dir)
        
        # Local state cache
        self.emotion = EmotionState()
        self.relationship_scores = RelationshipValues()
        self.goals = GoalState()
        self.attention = AttentionState()
        self.runtime = RuntimeStateFields()
        
        # Try to initialize Redis connection
        self._init_redis()
        
        # Load persisted state
        self.load_state_from_disk()

    def _init_redis(self):
        """Initialize Redis connection pool."""
        if self._redis_client is not None:
            self._pool = None
            self._available = True
            return
            
        try:
            cfg = self.redis_config
            connection_kwargs = {
                "host": cfg.host,
                "port": cfg.port,
                "db": cfg.db,
                "password": cfg.password,
                "max_connections": cfg.max_connections,
                "socket_timeout": cfg.socket_timeout,
                "socket_connect_timeout": cfg.socket_connect_timeout,
                "decode_responses": cfg.decode_responses,
            }
            # SSL configuration for redis-py 4.2+
            if cfg.ssl:
                import ssl
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connection_kwargs["ssl_cert_reqs"] = ssl.CERT_NONE
            
            self._pool = ConnectionPool(
                **connection_kwargs
            )
            self._redis_client = redis.Redis(connection_pool=self._pool)
            # Test connection
            self._redis_client.ping()
            self._available = True
            logger.info("[RedisSharedState] Connected to Redis")
        except Exception as e:
            logger.warning("[RedisSharedState] Redis unavailable, using fallback: %s", e)
            self._available = False
            self._pool = None
            self._redis_client = None

    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._available

    def _get_redis(self) -> redis.Redis | None:
        """Get Redis client, returning None if unavailable."""
        if not self._available:
            return None
        try:
            self._redis_client.ping()
            return self._redis_client
        except Exception as e:
            logger.warning("[RedisSharedState] Redis connection lost: %s", e)
            self._available = False
            return None

    def _make_key(self, *parts: str) -> str:
        """Create prefixed Redis key."""
        return ":".join([self.KEY_PREFIX] + list(parts))

    def _serialize(self, data: Any) -> str:
        """Serialize data to JSON."""
        return json.dumps(data, default=str)

    def _deserialize(self, data: str) -> Any:
        """Deserialize JSON data."""
        try:
            return json.loads(data)
        except Exception:
            return data

    # ==================================================
    # 🔒 LOCKING
    # ==================================================

    def acquire_lock(self, name: str, ttl: int = None) -> bool:
        """Acquire distributed lock."""
        if not self._available:
            return self._fallback.acquire_lock(name, ttl)
        
        redis = self._get_redis()
        if not redis:
            return self._fallback.acquire_lock(name, ttl)
        
        lock_key = self._make_key("locks", name)
        ttl = ttl or self.LOCK_TTL
        return redis.set(lock_key, "1", nx=True, ex=ttl)

    def release_lock(self, name: str) -> bool:
        """Release distributed lock."""
        if not self._available:
            return self._fallback.release_lock(name)
        
        redis = self._get_redis()
        if not redis:
            return self._fallback.release_lock(name)
        
        lock_key = self._make_key("locks", name)
        return redis.delete(lock_key) > 0

    # ==================================================
    # 💾 PERSISTENCE
    # ==================================================

    def save_state_to_disk(self):
        """Save state to both Redis and local file."""
        data = self.serialize()
        
        # Save to local file (backup)
        state_dir = Path(self.persistence_dir) / "state"
        state_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(state_dir / "master_state.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error("State Saving Failure: %s", str(e))

        # Save to Redis
        if self._available:
            redis = self._get_redis()
            if redis:
                try:
                    key = self._make_key("master")
                    redis.set(key, self._serialize(data))
                    redis.expire(key, 86400)  # 24h TTL
                except Exception as e:
                    logger.warning("[RedisSharedState] Redis save failed: %s", e)

    def load_state_from_disk(self):
        """Load state from Redis (preferred) or local file."""
        # Try Redis first
        if self._available:
            redis = self._get_redis()
            if redis:
                try:
                    key = self._make_key("master")
                    data = redis.get(key)
                    if data:
                        parsed = json.loads(data)
                        self._load_from_dict(parsed)
                        logger.info("[RedisSharedState] Loaded state from Redis")
                        return
                except Exception as e:
                    # Corrupt/unparsable Redis value — the connection itself is
                    # fine (_get_redis() already flips _available on connection
                    # loss). Keep Redis enabled; fall back to the local file.
                    logger.warning("[RedisSharedState] Redis load failed: %s", e)

        # Fallback to local file
        target_path = Path(self.persistence_dir) / "state" / "master_state.json"
        if not target_path.exists():
            return
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._load_from_dict(data)
            logger.info("[RedisSharedState] Loaded state from local file")
        except Exception as e:
            logger.error("Failed to recover state: %s", str(e))

    def _load_from_dict(self, data: dict):
        """Load state from dictionary."""
        if "emotion" in data:
            self.emotion = EmotionState(**data["emotion"])
        if "relationship_scores" in data:
            self.relationship_scores = RelationshipValues(**data["relationship_scores"])
        if "goals" in data:
            self.goals = GoalState(**data["goals"])
        if "attention" in data:
            self.attention = AttentionState(**data["attention"])
        if "runtime" in data:
            self.runtime = RuntimeStateFields(**data["runtime"])

    # ==================================================
    # 🧠 STATE ACCESS (with Redis sync)
    # ==================================================

    def serialize(self) -> dict:
        """Serialize all state to dictionary."""
        with self._lock:
            return {
                "emotion": self.emotion.model_dump(),
                "relationship_scores": self.relationship_scores.model_dump(),
                "goals": self.goals.model_dump(),
                "attention": self.attention.model_dump(),
                "runtime": self.runtime.model_dump(),
            }

    def save(self):
        self.save_state_to_disk()

    def get_emotion(self) -> EmotionState:
        with self._lock:
            return self.emotion

    def set_emotion(self, emotion: EmotionState):
        with self._lock:
            self.emotion = emotion
            self._sync_to_redis("emotion", self.emotion.model_dump())

    def get_relationship_scores(self) -> RelationshipValues:
        with self._lock:
            return self.relationship_scores

    def set_relationship_scores(self, scores: RelationshipValues):
        with self._lock:
            self.relationship_scores = scores
            self._sync_to_redis("relationship_scores", scores.model_dump())

    def get_goals(self) -> GoalState:
        with self._lock:
            return self.goals

    def set_goals(self, goals: GoalState):
        with self._lock:
            self.goals = goals
            self._sync_to_redis("goals", goals.model_dump())

    def _sync_to_redis(self, key: str, value: dict):
        """Sync a single state component to Redis."""
        if not self._available:
            return
        redis = self._get_redis()
        if not redis:
            return
        try:
            key = self._make_key(key)
            redis.set(key, self._serialize(value))
            redis.expire(key, 3600)  # 1h TTL
        except Exception as e:
            logger.debug("[RedisSharedState] Sync failed: %s", e)

    # ==================================================
    # 🔄 HEARTBEAT / HEALTH
    # ==================================================

    def heartbeat(self, component: str = "brain"):
        """Record component heartbeat."""
        if not self._available:
            return
        redis = self._get_redis()
        if not redis:
            return
        try:
            key = self._make_key("heartbeat", component)
            redis.set(key, time.time(), ex=self.HEARTBEAT_TTL)
        except Exception as e:
            logger.debug("[RedisSharedState] Heartbeat failed: %s", e)

    def is_healthy(self) -> bool:
        """Check if Redis is available."""
        if not self._available:
            return False
        redis = self._get_redis()
        if not redis:
            return False
        try:
            redis.ping()
            return True
        except Exception:
            self._available = False
            return False

    def close(self):
        """Close connections."""
        with self._lock:
            if self._redis_client:
                try:
                    self._redis_client.close()
                except Exception:
                    pass
                self._redis_client = None
            if self._pool:
                try:
                    self._pool.disconnect()
                except Exception:
                    pass
                self._pool = None


class InMemoryState:
    """In-memory fallback when Redis unavailable."""
    
    def __init__(self):
        self._locks: dict[str, float] = {}
        self._lock = threading.RLock()

    def acquire_lock(self, name: str, ttl: int = 10) -> bool:
        with self._lock:
            now = time.time()
            if name in self._locks:
                if self._locks[name] > now:
                    return False
            self._locks[name] = time.time() + ttl
            return True

    def release_lock(self, name: str) -> bool:
        with self._lock:
            if name in self._locks:
                del self._locks[name]
                return True
            return False
