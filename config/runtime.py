import os

SAFE_MODE = "safe"
DEFAULT_ERROR_MESSAGE = "Sorry… something went wrong."
ENABLE_THREADING = True
ENABLE_CACHE = True
ENABLE_LOGGING = True

EXTRACTOR_USE_LLM = True

# Database configuration
POSTGRES_DSN = os.environ.get("POSTGRES_DSN", "")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "30"))

API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8000"))
API_AUTH_TOKEN = os.environ.get("API_AUTH_TOKEN", "")
API_REQUIRE_AUTH = os.environ.get("API_REQUIRE_AUTH", "False").lower() == "true"
API_RATE_LIMIT_PER_MINUTE = int(os.environ.get("API_RATE_LIMIT_PER_MINUTE", "120"))
API_RATE_LIMIT_CHAT = int(os.environ.get("API_RATE_LIMIT_CHAT", "60"))
API_RATE_LIMIT_AUTH = int(os.environ.get("API_RATE_LIMIT_AUTH", "20"))
API_RATE_LIMIT_HEALTH = int(os.environ.get("API_RATE_LIMIT_HEALTH", "300"))
API_RATE_LIMIT_INGEST = int(os.environ.get("API_RATE_LIMIT_INGEST", "10"))
API_RATE_LIMIT_GENERAL = int(os.environ.get("API_RATE_LIMIT_GENERAL", "120"))
API_CORS_ORIGINS = os.environ.get("API_CORS_ORIGINS", "")
API_TRUSTED_HOSTS = os.environ.get("API_TRUSTED_HOSTS", "127.0.0.1,localhost")
API_SSL_CERTFILE = os.environ.get("API_SSL_CERTFILE", "")
API_SSL_KEYFILE = os.environ.get("API_SSL_KEYFILE", "")
API_JWT_SECRET = os.environ.get("API_JWT_SECRET", "")
API_JWT_ACCESS_EXPIRE_MINUTES = int(os.environ.get("API_JWT_ACCESS_EXPIRE_MINUTES", "15"))
API_JWT_REFRESH_EXPIRE_DAYS = int(os.environ.get("API_JWT_REFRESH_EXPIRE_DAYS", "7"))

# Redis configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
REDIS_SSL = os.environ.get("REDIS_SSL", "False").lower() == "true"
REDIS_MAX_CONNECTIONS = int(os.environ.get("REDIS_MAX_CONNECTIONS", "10"))
REDIS_SOCKET_TIMEOUT = float(os.environ.get("REDIS_SOCKET_TIMEOUT", "5.0"))
REDIS_SOCKET_CONNECT_TIMEOUT = float(os.environ.get("REDIS_SOCKET_CONNECT_TIMEOUT", "5.0"))