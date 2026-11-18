import logging

from app.metadata import tag_service
from config.paths import ROOT_DIR
from partner.calendar import IcsCalendar
from partner.engine import PartnerEngine
from partner.mail import ImapMailbox, NullMailbox
from partner.tools import register_partner_tools

logger = logging.getLogger("Mai")


def _build_mailbox(cfg):
    """Build the read-only mailbox, or a NullMailbox when unconfigured."""
    if not (cfg.PARTNER_MAIL_HOST and cfg.PARTNER_MAIL_USER and cfg.PARTNER_MAIL_PASSWORD):
        return NullMailbox("no IMAP credentials configured")
    return ImapMailbox(
        host=cfg.PARTNER_MAIL_HOST,
        username=cfg.PARTNER_MAIL_USER,
        password=cfg.PARTNER_MAIL_PASSWORD,
        port=cfg.PARTNER_MAIL_PORT,
        folder=cfg.PARTNER_MAIL_FOLDER,
        use_ssl=cfg.PARTNER_MAIL_USE_SSL,
        timeout=cfg.PARTNER_MAIL_TIMEOUT,
    )


def build(app):
    """M23 Partner — presence, verified actions, mail, calendar, idle cycles.

    Built after Continuity (idle cycles read its backlog) and after Cognition
    (activity detection reads CognitiveState)."""
    logger.info("    Building PartnerEngine...")
    data_dir = ROOT_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    try:
        import config.partner as cfg
    except Exception as e:
        logger.warning("    Partner config unavailable: %s", e)
        cfg = None

    mail = _build_mailbox(cfg) if cfg is not None else NullMailbox("partner config unavailable")
    calendar = IcsCalendar(
        cfg.PARTNER_CALENDAR_ICS if cfg is not None else data_dir / "calendar.ics"
    )

    app.partner = PartnerEngine(
        store_path=str(data_dir / "partner.json"),
        audit_path=str(data_dir / "partner_actions.jsonl"),
        event_bus=app.event_bus,
        continuity=getattr(app, "continuity", None),
        cognitive_state=getattr(app.brain, "cognitive", None),
        shared_state=app.shared_state,
        mail=mail,
        calendar=calendar,
        quiet_mode=cfg.PARTNER_QUIET_MODE if cfg is not None else False,
        min_trust=cfg.PARTNER_INITIATIVE_MIN_TRUST if cfg is not None else 0.6,
        initiative_cooldown=cfg.PARTNER_INITIATIVE_COOLDOWN if cfg is not None else 3600.0,
        cycle_interval=cfg.PARTNER_IDLE_CYCLE_INTERVAL if cfg is not None else 3600.0,
        max_backlog_items=cfg.PARTNER_MAX_BACKLOG_ITEMS if cfg is not None else 3,
        upcoming_hours=cfg.PARTNER_UPCOMING_HOURS if cfg is not None else 24.0,
    )
    tag_service(app, "partner", "PartnerEngine", "Cognition")

    # The brain exposes partner state to prompts/tools; the scheduler reads
    # tick() for ritual briefings and idle cycles.
    app.brain.partner = app.partner

    from agency.tools import register_file_tools

    file_tools_registered = register_file_tools(
        app.tool_registry, getattr(app, "file_tools", None), app.partner
    )
    logger.info("    ✓ Partner file tools (tools=%s)", file_tools_registered)


    registered = register_partner_tools(app.tool_registry, app.partner)
    logger.info("    ✓ PartnerEngine (tools=%s, mail=%s)", registered, getattr(mail, "name", "?"))

    try:
        app.health_registry.register("partner", component=app.partner)
        app.health_registry.heartbeat("partner")
    except Exception as e:
        logger.warning("    Partner health registration skipped: %s", e)

    app.partner.publish()

    assert app.partner is not None
