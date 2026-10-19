from config import voice as voice_config
from config.paths import ROOT_DIR
from config.settings import *  # re-export everything

EMBEDDING_MODEL = "Embedding_models/all-MiniLM-L6-v2"

__all__ = [
    "ROOT_DIR",
    "models/all-MiniLM-L6-v2",
    "voice_config"
]
