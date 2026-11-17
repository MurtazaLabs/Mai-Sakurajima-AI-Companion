import logging

from app.metadata import tag_service
from config.paths import ROOT_DIR
from self_awareness.engine import SelfAwarenessEngine
from self_awareness.tools import register_self_tools

logger = logging.getLogger("Mai")


def build(app):
    """T7 Self — built after Partner: it reads health, logs and its own code.

    Read-only by design. The builder indexes the repository once at boot so the
    tools have data immediately; the scheduler refreshes incrementally and runs
    a proactive diagnosis on its own interval.
    """
    logger.info("    Building SelfAwarenessEngine...")
    store_dir = ROOT_DIR / "data" / "self_awareness"
    store_dir.mkdir(parents=True, exist_ok=True)

    app.self_awareness = SelfAwarenessEngine(
        root=ROOT_DIR,
        store_dir=store_dir,
        event_bus=app.event_bus,
        health_registry=app.health_registry,
    )
    tag_service(app, "self_awareness", "SelfAwarenessEngine", "Cognition")

    # The brain can reason about itself; the partner briefing carries one line.
    app.brain.self_awareness = app.self_awareness
    partner = getattr(app, "partner", None)
    if partner is not None:
        partner.self_awareness = app.self_awareness

    registered = register_self_tools(app.tool_registry, app.self_awareness)
    logger.info("    ✓ SelfAwarenessEngine (tools=%s)", registered)

    try:
        app.health_registry.register("self_awareness", component=app.self_awareness)
        app.health_registry.heartbeat("self_awareness")
    except Exception as e:
        logger.warning("    Self health registration skipped: %s", e)

    app.self_awareness.refresh_index()
    app.self_awareness.publish()

    assert app.self_awareness is not None
