# self_awareness/__init__.py
"""T7 Self — own-code index, health/error feeds, proactive self-diagnosis.

Read and diagnose only. Nothing in this package edits source, restarts a
component, or applies a fix: findings carry proposals and the user approves.
"""
from self_awareness.code_index import OwnCodeIndex
from self_awareness.diagnosis import SelfDiagnosis
from self_awareness.engine import SelfAwarenessEngine
from self_awareness.feeds import HealthErrorFeeds

__all__ = [
    "HealthErrorFeeds",
    "OwnCodeIndex",
    "SelfAwarenessEngine",
    "SelfDiagnosis",
]
