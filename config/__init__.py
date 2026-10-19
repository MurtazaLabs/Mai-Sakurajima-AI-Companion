# Load .env file FIRST, before any config module reads os.environ
try:
    from pathlib import Path

    from dotenv import load_dotenv
    _project_root = Path(__file__).resolve().parent.parent
    load_dotenv(_project_root / ".env")
except Exception:
    pass

# Re-export all config modules for convenience
from config.ai import *
from config.debug import *
from config.emotion import *
from config.llm import *
from config.memory import *
from config.paths import *
from config.redis_config import *
from config.reflection import *
from config.runtime import *
from config.settings import Settings  # noqa: F401  re-exported convenience import
from config.speaker import *
