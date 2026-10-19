# core/identity/__init__.py

from core.identity.boundaries import BOUNDARIES
from core.identity.canonical import CANON_KEYS, check_drift
from core.identity.identity import IDENTITY
from core.identity.identity_core import IdentityCore
from core.identity.personality import PERSONALITY
from core.identity.preferences import PREFERENCES
from core.identity.speech import SPEECH
from core.identity.values import VALUES

# Test/tool patch and import surface for this package (keeps re-exports lint-quiet).
__all__ = [
    "BOUNDARIES",
    "CANON_KEYS",
    "IDENTITY",
    "PERSONALITY",
    "PREFERENCES",
    "SPEECH",
    "VALUES",
    "IdentityCore",
    "check_drift",
    "get_identity",
]


def get_identity():
    return {
        "identity": IDENTITY,
        "personality": PERSONALITY,
        "values": VALUES,
        "speech": SPEECH,
        "preferences": PREFERENCES,
        "boundaries": BOUNDARIES,
    }
