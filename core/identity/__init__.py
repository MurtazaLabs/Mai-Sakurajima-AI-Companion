# core/identity/__init__.py

from core.identity.identity import IDENTITY
from core.identity.personality import PERSONALITY
from core.identity.values import VALUES
from core.identity.speech import SPEECH
from core.identity.preferences import PREFERENCES
from core.identity.boundaries import BOUNDARIES
from core.identity.canonical import CANON_KEYS, check_drift
from core.identity.identity_core import IdentityCore


def get_identity():
    return {
        "identity": IDENTITY,
        "personality": PERSONALITY,
        "values": VALUES,
        "speech": SPEECH,
        "preferences": PREFERENCES,
        "boundaries": BOUNDARIES,
    }
