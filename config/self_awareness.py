# config/self_awareness.py
"""T7 Self — own-code index, health/error feeds, proactive self-diagnosis.

Read and diagnose only: nothing in this subsystem edits code or restarts a
component on its own. Findings carry proposals; the user approves fixes.
"""
import os
from pathlib import Path

from config.paths import LOG_DIR, ROOT_DIR

SELF_ENABLED = True

# How often the scheduler asks for a proactive diagnosis (the engine gates on
# the same interval, so a manual diagnose is never duplicated).
SELF_DIAGNOSIS_INTERVAL = 6 * 3600.0

# A log signature must repeat this often before it becomes a finding.
SELF_ERROR_THRESHOLD = int(os.environ.get("MAI_SELF_ERROR_THRESHOLD", "3") or 3)
SELF_ERROR_LIMIT = 40
SELF_MAX_LOG_BYTES = 512 * 1024

# The app log written by run.py; read-only, tail-only.
SELF_LOG_PATH = Path(os.environ.get("MAI_SELF_LOG", str(LOG_DIR / "mai.log")))

# Never index virtualenvs, caches, generated data or docs (they are not "her
# code", and a venv would add thousands of files).
SELF_INDEX_EXCLUDES = frozenset({
    "mai_env", "venv", ".venv", "env", ".git", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", "node_modules", "build", "dist", "data",
    "logs", "temp", "cache", "vector_memory", "docs", "important", ".opencode",
    "desktop", "assets",
})
SELF_MAX_MODULES = int(os.environ.get("MAI_SELF_MAX_MODULES", "4000") or 4000)

SELF_STORE_DIR = ROOT_DIR / "data" / "self_awareness"
