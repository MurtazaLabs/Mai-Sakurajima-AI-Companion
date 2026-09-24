import os
from pathlib import Path

# Load .env file if present (before reading env vars)
try:
    from dotenv import load_dotenv
    # Use project root based on __file__ location
    _project_root = Path(__file__).resolve().parent.parent
    load_dotenv(_project_root / ".env")
except Exception:
    pass

ROOT_DIR = Path(os.environ.get("ROOT_DIR", str(Path(__file__).resolve().parent.parent)))
MEMORY_DIR = ROOT_DIR / "memory"
VECTOR_DB_DIR = ROOT_DIR / "vector_memory"
TEMP_AUDIO_DIR = ROOT_DIR / "temp"
LOG_DIR = ROOT_DIR / "logs"
CACHE_DIR = ROOT_DIR / "cache"
OBSIDIAN_VAULT = Path(os.environ.get("MAI_OBSIDIAN_VAULT", str(Path.home() / "MaiMemory")))
OBSIDIAN_ENABLED = True
OBSIDIAN_DAILY_NOTES = True
OBSIDIAN_AUTO_LINKS = True
OBSIDIAN_TAGS_ENABLED = True
OBSIDIAN_MAX_FILE_SIZE = 5_000_000
OBSIDIAN_FOLDERS = [
    "conversation", "relationship", "people", "places", "projects",
    "knowledge", "dreams", "identity", "preferences", "reflections",
    "statistics", "archive", "important",
    "graph", "maintenance",
]

for _dir in [MEMORY_DIR, VECTOR_DB_DIR, TEMP_AUDIO_DIR, LOG_DIR, CACHE_DIR, OBSIDIAN_VAULT]:
    _dir.mkdir(parents=True, exist_ok=True)