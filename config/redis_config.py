# config/redis_config.py
"""Redis configuration for distributed state and event bus."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class RedisConfig:
    """Redis connection configuration."""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    max_connections: int = 10
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    decode_responses: bool = True

    @classmethod
    def from_env(cls) -> 'RedisConfig':
        """Create RedisConfig from environment variables."""
        import os
        return cls(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            password=os.getenv("REDIS_PASSWORD") or None,
            ssl=os.getenv("REDIS_SSL", "false").lower() == "true",
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "10")),
            socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT", "5.0")),
            socket_connect_timeout=float(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5.0")),
            decode_responses=os.getenv("REDIS_DECODE_RESPONSES", "true").lower() == "true",
        )