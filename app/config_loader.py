from config.settings import *  # re-export everything
from config.paths import ROOT_DIR
from config import voice as voice_config
EMBEDDING_MODEL = "Embedding_models/all-MiniLM-L6-v2"

__all__ = [
    "ROOT_DIR",
    "voice_config",
    "models/all-MiniLM-L6-v2"
]
