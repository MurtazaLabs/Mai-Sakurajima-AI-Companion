from app.builders import (
    infrastructure,
    knowledge,
    memory,
    reasoning,
    agency,
    cognition,
    voice,
    runtime,
)

BOOT_ORDER = [
    ("Infrastructure", infrastructure.build),
    ("Knowledge",       knowledge.build),
    ("Memory",          memory.build),
    ("Reasoning",       reasoning.build),
    ("Agency",          agency.build),
    ("Cognition",       cognition.build),
    ("Voice",           voice.build),
    ("Runtime",         runtime.build),
]
