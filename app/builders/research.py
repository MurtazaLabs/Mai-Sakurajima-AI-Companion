import logging

from app.metadata import tag_service
from research.artifacts import ResearchArtifacts
from research.engine import ResearchEngine
from research.store import ResearchStore
from research.tools import register_research_tools

logger = logging.getLogger("Mai")


def build(app):
    """T4 Silent Research — built after Partner (idle cycles + presence)."""
    try:
        import config.research as cfg
    except Exception as exc:
        logger.warning("    Research config unavailable: %s", exc)
        app.research = None
        return

    if not cfg.RESEARCH_ENABLED:
        logger.info("    Research disabled")
        app.research = None
        return

    logger.info("    Building ResearchEngine...")
    store_dir = cfg.RESEARCH_STORE_DIR
    store_dir.mkdir(parents=True, exist_ok=True)
    partner = getattr(app, "partner", None)

    app.research = ResearchEngine(
        store=ResearchStore(store_dir / "jobs.json", history_limit=cfg.RESEARCH_HISTORY_LIMIT),
        artifacts=ResearchArtifacts(cfg.RESEARCH_ARTIFACT_DIR),
        event_bus=app.event_bus,
        continuity=getattr(app, "continuity", None),
        presence=getattr(partner, "presence", None),
        max_sources=cfg.RESEARCH_MAX_SOURCES,
        max_chars=cfg.RESEARCH_MAX_CHARS,
        timeout=cfg.RESEARCH_FETCH_TIMEOUT,
        max_queue=cfg.RESEARCH_MAX_QUEUE,
        search_enabled=cfg.RESEARCH_SEARCH_ENABLED,
        search_url=cfg.RESEARCH_SEARCH_URL,
        search_results=cfg.RESEARCH_SEARCH_RESULTS,
        autonomous_allowed=cfg.RESEARCH_AUTONOMOUS,
        browser_mode=cfg.RESEARCH_BROWSER,
    )
    tag_service(app, "research", "ResearchEngine", "Cognition")

    app.brain.research = app.research
    if partner is not None:
        partner.research = app.research
        cycles = getattr(partner, "cycles", None)
        if cycles is not None:
            cycles.research = app.research

    registered = register_research_tools(app.tool_registry, app.research)
    logger.info("    ✓ ResearchEngine (tools=%s, resumed=%s)",
                registered, app.research.resumed)

    try:
        app.health_registry.register("research", component=app.research)
        app.health_registry.heartbeat("research")
    except Exception as exc:
        logger.warning("    Research health registration skipped: %s", exc)

    app.research._publish_state()
    assert app.research is not None
