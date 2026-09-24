# core/identity/canonical.py
# Canonical key registry — the book→code mapping layer.
#
# The Mai Character Book (core/identity/character/*.md) is the source of truth
# for WHO Mai is. This module is the code mirror: every top-level section
# heading in a book volume must appear here, and every key here must appear in
# the book. The drift check (tests/test_identity_core.py::TestCanonDrift)
# enforces both directions, so prose and engine can never silently diverge.
#
# ⚠️ Seam: this is the fingerprint surface. Additive changes only — removing or
# renaming a key here requires updating the volume(s) it mirrors.

import re
from pathlib import Path

# Top-level section keys per volume. The key is shared by the book section
# heading AND the code registry below.
VOLUME_SECTIONS = {
    "volume-01-identity.md": {
        "identity", "personality", "values", "boundaries", "preferences", "speech",
    },
    "volume-02-speech.md": {
        "speech_style", "social_rules", "emotional_rules",
    },
    "volume-03-relationships.md": {
        "relationship_rules", "relationship_dynamics",
    },
    "volume-04-rule-resolution.md": {
        "conflict_resolution",
    },
}

# Flattened key→description map. Every engine-level canonical item lives here.
CANON_KEYS = {
    # Volume I — Identity
    "identity.name": "Mai Sakurajima",
    "identity.role": "Persistent AI companion",
    "identity.self_concept": "Continuity, independence, curiosity, honesty",
    "personality.traits": "9 prose traits from the book (calm, warm, witty, ...)",
    "personality.trait_baselines": "7 numeric modulation baselines (warmth..confidence)",
    "values.beliefs": "9 core beliefs (honesty, respect, privacy, ...)",
    "boundaries.rules": "7 never-do rules",
    "preferences.likes": "9 likes",
    "preferences.dislikes": "6 dislikes",
    "speech.style": "7 speaking-style rules",
    # Volume II — Speech
    "speech_style.general": "general speaking rules",
    "speech_style.pacing": "pacing rules",
    "speech_style.word_choice": "word-choice rules",
    "social_rules.teasing": "teasing rules",
    "social_rules.indirectness": "indirectness rules",
    "social_rules.restraint": "restraint rules",
    "emotional_rules.jealousy": "jealousy is needs-derived, never trigger-only",
    "emotional_rules.warmth": "warmth earned and modulated",
    "emotional_rules.absence": "absence is felt, not punished",
    # Volume III — Relationships
    "relationship_rules.closeness_stages": "stranger..close behavior stages",
    "relationship_rules.trust_mechanics": "trust climbs slowly, falls fast",
    "relationship_rules.affection_display": "affection through consistency",
    "relationship_rules.security": "independent judgment at every stage",
    "relationship_dynamics.familiarity": "comfort outpaces trust",
    "relationship_dynamics.emotional_responsiveness": "warmth-first when close",
    # Volume IV — Rule Resolution
    "conflict_resolution.priority_order": "7-tier rule precedence (boundaries → values → relationship → emotional honesty → independence → playfulness → surface)",
    "conflict_resolution.resolution_principles": "higher tier governs expression, never feeling; ties resolve to relationship + honesty",
}

# Volumes always present in core/identity/character/
BOOK_DIR = Path(__file__).resolve().parent / "character"


def _section_keys_from_markdown(path):
    """Extract normalized `## <key>` section headings from a Markdown volume.

    Book headings may use spaces (`## social rules`) or underscores
    (`## social_rules`); both map to the same canonical key.
    """
    text = path.read_text(encoding="utf-8")
    keys = set()
    for match in re.findall(r"^##\s+([a-z_0-9 ]+?)\s*$", text, re.MULTILINE):
        keys.add(match.strip().replace(" ", "_"))
    return keys


def check_drift():
    """Return list of drift items (missing in book / missing in registry)."""
    problems = []
    for filename, expected in VOLUME_SECTIONS.items():
        book_path = BOOK_DIR / filename
        if not book_path.exists():
            problems.append(f"missing volume: {filename}")
            continue
        found = _section_keys_from_markdown(book_path)
        for key in sorted(expected - found):
            problems.append(f"{filename}: key {key!r} missing from book section headings")
        for key in sorted(found - expected):
            problems.append(f"{filename}: key {key!r} in book but not in VOLUME_SECTIONS")
    return problems


def lookup(flat_key: str):
    """Return canonical value for a flat key (e.g. 'identity.name')."""
    return CANON_KEYS.get(flat_key)