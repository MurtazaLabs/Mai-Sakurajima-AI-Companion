# core/state/database.py
"""PostgreSQL/SQLite database layer with SQLAlchemy and Alembic support."""
import os
import threading
from contextlib import contextmanager
from typing import Optional, Generator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.engine import Engine

from core.state.models import Base
from core.state.models import (
    EvidenceModel,
    ProfileModel,
    SessionModel,
    MemoryNodeModel,
    RelationshipEvidenceModel,
    SharedStateModel,
)

from app.config_loader import (
    POSTGRES_DSN,
    DATABASE_URL,
    DB_POOL_SIZE,
    DB_MAX_OVERFLOW,
    DB_POOL_TIMEOUT,
)

logger = __import__("logging").getLogger(__name__)

# Global engine and session factory
_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None
_init_lock = threading.Lock()


def get_database_url() -> str:
    """Get database URL from environment or fallback to SQLite."""
    # Try PostgreSQL first
    if POSTGRES_DSN:
        return POSTGRES_DSN
    # Fallback to DATABASE_URL (could be postgres or sqlite)
    if DATABASE_URL:
        return DATABASE_URL
    # Fallback to local SQLite
    from config.paths import MEMORY_DIR
    db_path = Path(MEMORY_DIR) / "mai.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


def create_engine_instance() -> Engine:
    """Create SQLAlchemy engine with appropriate configuration."""
    url = get_database_url()
    is_postgres = url.startswith("postgresql") or url.startswith("postgres")
    
    if is_postgres:
        # PostgreSQL with connection pooling
        engine = create_engine(
            url,
            poolclass=QueuePool,
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW,
            pool_timeout=DB_POOL_TIMEOUT,
            pool_pre_ping=True,
            echo=False,
        )
    else:
        # SQLite with no pooling (file-based)
        engine = create_engine(
            url,
            poolclass=NullPool,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    
    # Enable foreign keys for SQLite
    if not is_postgres:
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    
    return engine


def get_engine() -> Engine:
    """Get or create the global engine instance."""
    global _engine
    if _engine is None:
        with _init_lock:
            if _engine is None:
                _engine = create_engine_instance()
    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the global session factory."""
    global _session_factory
    if _session_factory is None:
        with _init_lock:
            if _session_factory is None:
                _session_factory = sessionmaker(
                    bind=get_engine(),
                    expire_on_commit=False,
                    autoflush=False,
                )
    return _session_factory


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(drop_existing: bool = False) -> None:
    """Initialize database tables. Creates tables if they don't exist."""
    engine = get_engine()
    if drop_existing:
        Base.metadata.drop_all(engine)
    
    # Check if tables already exist to avoid index creation errors
    from sqlalchemy import inspect
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if existing_tables:
        # Tables already exist, skip creation to avoid index conflicts
        logger.info("Database tables already exist, skipping creation")
    else:
        Base.metadata.create_all(engine)
        logger.info("Database tables created")
    
    logger.info("Database initialized")


def close_db() -> None:
    """Close database connections."""
    global _engine, _session_factory
    with _init_lock:
        if _engine:
            _engine.dispose()
            _engine = None
        _session_factory = None


# Convenience functions for common operations
def get_session() -> Session:
    """Get a new database session."""
    return get_session_factory()()


def create_tables() -> None:
    """Create all tables."""
    Base.metadata.create_all(get_engine())


def drop_tables() -> None:
    """Drop all tables."""
    Base.metadata.drop_all(get_engine())