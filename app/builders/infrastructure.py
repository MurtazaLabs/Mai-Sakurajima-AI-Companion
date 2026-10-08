import logging
import os
from pathlib import Path

import app.config_loader as cfg
from app.metadata import tag_service
from core.event_bus import EventBus
from core.event_bus_redis import RedisEventBus
from core.state.shared_state import SharedState
from core.state.redis_state import RedisSharedState
from core.state.relationship import RelationshipEngineV2
from core.write_journal import WriteJournal
from core.session_manager import create_session_manager
from observability.health import HealthRegistry
from llm.manager import LLMManager

logger = logging.getLogger("Mai")

# Phase 2a — distributed backends are opt-in via MAI_REDIS_URL (e.g.
# "redis://localhost:6379/0"). Unset/unreachable → the historical in-process
# EventBus + file-backed SharedState, so the default boot path never changes.
REDIS_URL_ENV = "MAI_REDIS_URL"


def _redis_url() -> str:
    """Return the opt-in Redis URL, or "" when the variable is unset/blank."""
    return (os.getenv(REDIS_URL_ENV) or "").strip()


def _resolve_redis_client():
    """Build and ping a Redis client when MAI_REDIS_URL is set.

    Returns the client, or None when the variable is unset or Redis is
    unreachable — the caller then falls back to the in-process backends.
    Never raises.
    """
    url = _redis_url()
    if not url:
        return None
    try:
        import redis as redis_lib
        client = redis_lib.Redis.from_url(
            url,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
        client.ping()
        logger.info(
            "[Infrastructure] Redis reachable — distributed backends active"
        )
        return client
    except Exception as e:
        logger.warning(
            "[Infrastructure] %s is set but Redis is unreachable (%s) — "
            "falling back to in-process backends",
            REDIS_URL_ENV,
            e,
        )
        return None


def _build_event_bus(redis_client):
    """Select the EventBus backend. Returns (bus, backend_name)."""
    if redis_client is not None:
        return RedisEventBus(redis_client=redis_client), "redis"
    return EventBus(), "in-process"


def _build_shared_state(persistence_path, redis_client):
    """Select the SharedState backend. Returns (state, backend_name)."""
    if redis_client is not None:
        state = RedisSharedState(
            persistence_dir=persistence_path,
            redis_client=redis_client,
        )
        return state, "redis"
    return SharedState(persistence_dir=persistence_path), "in-process"


def _mask_url(url: str) -> str:
    """Scrub credentials from a database URL before logging it."""
    import re
    return re.sub(r"://[^@/\s]+@", "://***@", str(url))


def _build_database():
    """Build the SQLAlchemy engine (Phase 2c). Returns (engine, url).

    URL: POSTGRES_DSN -> DATABASE_URL -> sqlite:///{MEMORY_DIR}/mai.db.
    Engine construction is lazy (no connection until first use), so an
    unreachable PostgreSQL degrades to an error at first use, never at boot.
    """
    from core.state.database import get_database_url, get_engine
    url = get_database_url()
    engine = get_engine()
    return engine, url


def _maybe_run_migrations() -> bool:
    """Run ``alembic upgrade head`` when MAI_DB_AUTO_MIGRATE is truthy
    (1/true/yes/on). Default is OFF — migrations stay a deliberate, manual
    step (``alembic upgrade head``) unless explicitly enabled.
    """
    if os.getenv("MAI_DB_AUTO_MIGRATE", "").strip().lower() not in ("1", "true", "yes", "on"):
        return False
    try:
        from alembic import command
        from alembic.config import Config

        ini_path = Path(__file__).resolve().parents[2] / "alembic.ini"
        if not ini_path.exists():
            logger.warning(
                "[Infrastructure] MAI_DB_AUTO_MIGRATE set but %s not found",
                ini_path,
            )
            return False
        cfg = Config(str(ini_path))
        # Anchor script_location to the repo root so boot works from any cwd.
        # Forward slashes: backslashes break ConfigParser interpolation.
        cfg.set_main_option(
            "script_location",
            str(ini_path.parent / "core/state/alembic").replace("\\", "/"),
        )
        command.upgrade(cfg, "head")
        return True
    except Exception as exc:
        logger.warning("[Infrastructure] Database auto-migration failed: %s", exc)
        return False


def build(app):
    redis_client = _resolve_redis_client()

    logger.info("    Building EventBus...")
    app.event_bus, app.event_bus_backend = _build_event_bus(redis_client)
    from core.event_specs import register_event_specs
    register_event_specs(app.event_bus)
    tag_service(app, "event_bus", "EventBus", "Infrastructure")
    logger.info("    ✓ EventBus (%s)", app.event_bus_backend)

    logger.info("    Building ConfigManager...")
    from core.config_manager import ConfigManager
    app.config_manager = ConfigManager()
    tag_service(app, "config_manager", "ConfigManager", "Infrastructure")
    logger.info("    ✓ ConfigManager")

    logger.info("    Building HealthRegistry...")
    app.health_registry = HealthRegistry(event_bus=app.event_bus)
    tag_service(app, "health_registry", "HealthRegistry", "Infrastructure")
    logger.info("    ✓ HealthRegistry")

    logger.info("    Building EventInspector...")
    from observability.event_inspector import EventInspector
    app.event_inspector = EventInspector(
        event_bus=app.event_bus,
        health_registry=app.health_registry,
    )
    tag_service(app, "event_inspector", "EventInspector", "Infrastructure")
    logger.info("    ✓ EventInspector")

    logger.info("    Building SharedState...")
    persistence_path = Path(cfg.OBSIDIAN_VAULT).parent / "mai_runtime_data"
    (
        app.shared_state,
        app.shared_state_backend,
    ) = _build_shared_state(persistence_path, redis_client)
    tag_service(app, "shared_state", "SharedState", "Infrastructure")
    logger.info("    ✓ SharedState (%s)", app.shared_state_backend)

    logger.info("    Building SQL engine...")
    app.database, app.database_url = _build_database()
    app.database_migrations_applied = _maybe_run_migrations()
    tag_service(app, "database", "SQLAlchemy Engine", "Infrastructure")
    logger.info(
        "    ✓ SQL engine (%s, migrations=%s)",
        _mask_url(app.database_url),
        app.database_migrations_applied,
    )

    logger.info("    Building LLMManager...")
    app.llm = LLMManager()
    tag_service(app, "llm", "LLMManager", "Infrastructure")
    logger.info("    ✓ LLMManager")

    logger.info("    Building RelationshipEngine...")
    app.relationship_engine = RelationshipEngineV2(state=app.shared_state, llm=app.llm)
    tag_service(app, "relationship_engine", "RelationshipEngine", "Infrastructure")
    logger.info("    ✓ RelationshipEngine")

    logger.info("    Building WriteJournal...")
    app.write_journal = WriteJournal()
    app.write_journal.start()
    tag_service(app, "write_journal", "WriteJournal", "Infrastructure")
    logger.info("    ✓ WriteJournal")

    logger.info("    Building SessionManager...")
    app.session_manager = create_session_manager()
    app.session_manager.start()
    tag_service(app, "session_manager", "SessionManager", "Infrastructure")
    logger.info("    ✓ SessionManager")

    logger.info("    Building IdentityCore...")
    from core.identity.identity_core import IdentityCore
    app.identity = IdentityCore()
    tag_service(app, "identity", "IdentityCore", "Infrastructure")
    logger.info("    ✓ IdentityCore")

    assert app.event_bus is not None
    assert app.health_registry is not None
    assert app.event_inspector is not None
    assert app.shared_state is not None
    assert app.llm is not None
    assert app.relationship_engine is not None
    assert app.identity is not None
