from app.builders import (
    agency,
    cognition,
    continuity,
    infrastructure,
    knowledge,
    memory,
    reasoning,
    runtime,
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
    ("Voice",           voice.build),
    ("Runtime",         runtime.build),
]
