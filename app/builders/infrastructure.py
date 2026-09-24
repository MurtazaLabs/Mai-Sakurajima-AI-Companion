import logging
from pathlib import Path

import app.config_loader as cfg
from app.metadata import tag_service
from core.event_bus import EventBus
from core.state.shared_state import SharedState
from core.state.relationship import RelationshipEngineV2
from core.write_journal import WriteJournal
from core.session_manager import create_session_manager
from observability.health import HealthRegistry
from llm.manager import LLMManager

logger = logging.getLogger("Mai")


def build(app):
    logger.info("    Building EventBus...")
    app.event_bus = EventBus()
    from core.event_specs import register_event_specs
    register_event_specs(app.event_bus)
    tag_service(app, "event_bus", "EventBus", "Infrastructure")
    logger.info("    ✓ EventBus")

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
    app.shared_state = SharedState(persistence_dir=persistence_path)
    tag_service(app, "shared_state", "SharedState", "Infrastructure")
    logger.info("    ✓ SharedState")

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
