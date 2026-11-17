# config/partner.py
"""M23 Partner configuration — presence, action policy, mail, calendar, cycles.

Local-first: mail is read-only IMAP, calendar is a local .ics file, and nothing
here sends anything. Credentials come from the environment, never from source.
"""
import os
from pathlib import Path

from config.paths import ROOT_DIR

PARTNER_ENABLED = True

# Scheduler tick: ritual briefing gate + idle work cycle (the cycle keeps its
# own cooldown, so ticking more often than the cycle interval is harmless).
PARTNER_TICK_INTERVAL = 900

# Presence
PARTNER_QUIET_MODE = os.environ.get("MAI_PARTNER_QUIET", "").strip().lower() in ("1", "true", "yes")
PARTNER_INITIATIVE_MIN_TRUST = 0.6
PARTNER_INITIATIVE_COOLDOWN = 3600.0
PARTNER_UPCOMING_HOURS = 24

# Autonomous cycles — during idle she picks up her backlog; she plans and
# checkpoints work, never acts outside the action policy.
PARTNER_IDLE_CYCLE_INTERVAL = 3600.0
PARTNER_MAX_BACKLOG_ITEMS = 3

# Mail — read-only IMAP. An empty host keeps mail unavailable (NullMailbox);
# boot never half-connects to a mailbox.
PARTNER_MAIL_HOST = os.environ.get("MAI_MAIL_IMAP_HOST", "").strip()
PARTNER_MAIL_PORT = int(os.environ.get("MAI_MAIL_IMAP_PORT", "993") or 993)
PARTNER_MAIL_USER = os.environ.get("MAI_MAIL_IMAP_USER", "").strip()
PARTNER_MAIL_PASSWORD = os.environ.get("MAI_MAIL_IMAP_PASSWORD", "")
PARTNER_MAIL_FOLDER = os.environ.get("MAI_MAIL_IMAP_FOLDER", "INBOX").strip() or "INBOX"
PARTNER_MAIL_USE_SSL = os.environ.get("MAI_MAIL_IMAP_SSL", "1").strip().lower() not in ("0", "false", "no")
PARTNER_MAIL_TIMEOUT = float(os.environ.get("MAI_MAIL_IMAP_TIMEOUT", "15") or 15)
PARTNER_MAIL_LIMIT = 10

# Calendar — a local iCalendar file (a synced .ics export). Missing file means
# an empty calendar, not a failed boot.
PARTNER_CALENDAR_ICS = Path(
    os.environ.get("MAI_CALENDAR_ICS", str(ROOT_DIR / "data" / "calendar.ics"))
)
