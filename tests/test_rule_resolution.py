# Volume IV — Rule Resolution canon artifact tests (M13 precursor).
# Spec: docs/m13-character-coherence-spec.md
"""The Volume IV gate: the priority order is explicit, grounded in Volumes
I–III, and exposed as a read-only projection — no engine, no prompt wiring."""

import re
from pathlib import Path

from core.identity.canonical import (
    BOOK_DIR,
    CANON_KEYS,
    VOLUME_SECTIONS,
    check_drift,
    _section_keys_from_markdown,
)
from core.identity.identity_core import IdentityCore

VOLUME_IV = BOOK_DIR / "volume-04-rule-resolution.md"

EXPECTED_PRIORITY = [
    "boundaries_safety",
    "core_values",
    "relationship_preservation",
    "emotional_honesty",
    "independence_self_respect",
    "playfulness_humor",
    "surface_expression",
]

# Each tier must be grounded in a real `##` section of Volumes I–III.
TIER_SOURCES = {
    "boundaries_safety": ("volume-01-identity.md", "boundaries"),
    "core_values": ("volume-01-identity.md", "values"),
    "relationship_preservation": ("volume-03-relationships.md", "relationship_rules"),
    "emotional_honesty": ("volume-02-speech.md", "emotional_rules"),
    "independence_self_respect": ("volume-03-relationships.md", "relationship_rules"),
    "playfulness_humor": ("volume-02-speech.md", "social_rules"),
    "surface_expression": ("volume-02-speech.md", "speech_style"),
}

_PRIORITY_LINE = re.compile(r"^- (\d+)\. ([a-z_]+) —", re.MULTILINE)


def _parse_priority_order():
    text = VOLUME_IV.read_text(encoding="utf-8")
    return [
        m.group(2)
        for m in _PRIORITY_LINE.finditer(text)
    ]


class TestVolumeIVCanon:

    def test_volume_exists_and_registered(self):
        assert VOLUME_IV.exists()
        assert "volume-04-rule-resolution.md" in VOLUME_SECTIONS
        assert "conflict_resolution" in VOLUME_SECTIONS["volume-04-rule-resolution.md"]

    def test_no_canon_drift_with_volume_iv(self):
        assert check_drift() == []

    def test_priority_order_is_exact_and_ordered(self):
        parsed = _parse_priority_order()
        assert parsed == EXPECTED_PRIORITY, (
            f"priority order drift: {parsed}"
        )

    def test_priority_grounded_in_earlier_volumes(self):
        for tier, (filename, section) in TIER_SOURCES.items():
            volume = BOOK_DIR / filename
            assert volume.exists(), f"tier {tier} references missing {filename}"
            sections = _section_keys_from_markdown(volume)
            assert section in sections, (
                f"tier {tier} references {filename}#{section} which does not exist"
            )

    def test_registry_keys_for_volume_iv(self):
        assert any(
            k.startswith("conflict_resolution.")
            for k in CANON_KEYS
        )


class TestResolutionPrinciples:

    def test_expression_not_feeling_stated(self):
        text = VOLUME_IV.read_text(encoding="utf-8")
        assert "never *feeling*" in text or "never feeling" in text

    def test_principles_exist_and_nonempty(self):
        core = IdentityCore()
        policy = core.get_conflict_resolution()
        assert policy["priority_order"]
        assert policy["resolution_principles"]
        assert "boundaries" in policy["priority_order"]
        assert "expression" in policy["resolution_principles"]

    def test_projection_is_readonly(self):
        core = IdentityCore()
        before = core.get_conflict_resolution()
        core.get_conflict_resolution()
        assert core.get_conflict_resolution() == before


class TestVolumeIVTierSemantics:

    def test_higher_tier_mentions_boundaries_absolute(self):
        text = VOLUME_IV.read_text(encoding="utf-8")
        assert "No emotion, need, or relationship state overrides" in text

    def test_teasing_steps_back_at_negative_reaction(self):
        text = VOLUME_IV.read_text(encoding="utf-8")
        assert "steps back immediately" in text
