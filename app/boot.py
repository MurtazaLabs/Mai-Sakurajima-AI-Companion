from app.builders import (
    agency,
    cognition,
    continuity,
    infrastructure,
    knowledge,
    memory,
    partner,
    reasoning,
    runtime,
    self_awareness,
    voice,
)

BOOT_ORDER = [
    ("Infrastructure", infrastructure.build),
    ("Knowledge",       knowledge.build),
    ("Memory",          memory.build),
    ("Reasoning",       reasoning.build),
    ("Agency",          agency.build),
    ("Cognition",       cognition.build),
    ("Continuity",      continuity.build),
    ("Partner",         partner.build),
    ("SelfAwareness",   self_awareness.build),
    ("Voice",           voice.build),
    ("Runtime",         runtime.build),
]
