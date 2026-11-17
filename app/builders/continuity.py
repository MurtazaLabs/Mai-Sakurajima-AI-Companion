import logging

from app.metadata import tag_service
from config.paths import ROOT_DIR
from continuity.engine import ContinuityEngine
from continuity.tools import register_continuity_tools

logger = logging.getLogger("Mai")


def build(app):
    """Continuity Engine — built after Cognition because it reconciles over
    GoalManager, CognitiveState and SharedState rather than owning them."""
    logger.info("    Building ContinuityEngine...")
    data_dir = ROOT_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    app.continuity = ContinuityEngine(
        store_path=str(data_dir / "continuity.json"),
        event_bus=app.event_bus,
        goal_manager=app.goal_manager,
        cognitive_state=getattr(app.brain, "cognitive", None),
        shared_state=app.shared_state,
    )
    tag_service(app, "continuity", "ContinuityEngine", "Cognition")

    # The brain reads the continuity brief at prompt time; the scheduler reads
    # check_commitments(); the tool registry exposes the continuity tools.
    app.brain.continuity = app.continuity
    registered = register_continuity_tools(app.tool_registry, app.continuity)
    logger.info("    ✓ ContinuityEngine (tools=%s)", registered)

    try:
        app.health_registry.register("continuity", component=app.continuity)
        app.health_registry.heartbeat("continuity")
    except Exception as e:
        logger.warning("    Continuity health registration skipped: %s", e)

    app.continuity.publish()

    assert app.continuity is not None
