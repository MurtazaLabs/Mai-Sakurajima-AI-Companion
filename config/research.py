# config/research.py
"""T4 silent research configuration."""
import os
from pathlib import Path

from config.paths import OBSIDIAN_VAULT, ROOT_DIR

RESEARCH_ENABLED = True

RESEARCH_STORE_DIR = ROOT_DIR / "data" / "research"
RESEARCH_ARTIFACT_DIR = Path(os.environ.get(
    "MAI_RESEARCH_ARTIFACTS", str(OBSIDIAN_VAULT / "research")
))

# Sources fetched per job. Depths are budgets, not promises.
RESEARCH_DEPTHS = {"quick": 2, "standard": 4, "deep": 6}
RESEARCH_DEFAULT_DEPTH = "standard"
RESEARCH_MAX_SOURCES = int(os.environ.get("MAI_RESEARCH_MAX_SOURCES", "6") or 6)
RESEARCH_MAX_CHARS = int(os.environ.get("MAI_RESEARCH_MAX_CHARS", "8000") or 8000)
RESEARCH_FETCH_TIMEOUT = float(os.environ.get("MAI_RESEARCH_TIMEOUT", "15") or 15)
RESEARCH_MAX_QUEUE = int(os.environ.get("MAI_RESEARCH_MAX_QUEUE", "8") or 8)
RESEARCH_HISTORY_LIMIT = int(os.environ.get("MAI_RESEARCH_HISTORY", "100") or 100)

# Best-effort HTML search endpoint (no API key). Disable to force URL-seeded
# jobs only; a query-only job then fails honestly.
RESEARCH_SEARCH_ENABLED = os.environ.get(
    "MAI_RESEARCH_SEARCH", "true"
).strip().lower() in ("1", "true", "yes")
RESEARCH_SEARCH_URL = os.environ.get(
    "MAI_RESEARCH_SEARCH_URL", "https://html.duckduckgo.com/html/"
)
RESEARCH_SEARCH_RESULTS = int(os.environ.get("MAI_RESEARCH_SEARCH_RESULTS", "5") or 5)

# Autonomous starts (idle cycles) obey quiet mode and the presence activity.
RESEARCH_AUTONOMOUS = os.environ.get(
    "MAI_RESEARCH_AUTONOMOUS", "true"
).strip().lower() in ("1", "true", "yes")
RESEARCH_TICK_INTERVAL = float(os.environ.get("MAI_RESEARCH_TICK", "300") or 300)

# Playwright is optional; when absent the urllib fetch path is used.
RESEARCH_BROWSER = os.environ.get("MAI_RESEARCH_BROWSER", "auto").strip().lower()
