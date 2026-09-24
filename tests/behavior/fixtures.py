# M7 fixtures — band helpers, deterministic envelope fixtures, stimuli.
# Spec: docs/m7-character-behavioral-spec.md §3, §4-§9.
"""Fixtures for the M7 behavioral suite.

No tests live here; the module provides:
- ``within(value, expected, tol)`` — band assertion helper (formula + tolerance,
  never brittle literals).
- ``PACKET_FIXTURES`` / ``make_packet(kind)`` — deterministic ThoughtPacket
  envelopes per stimulus class (LLM is stubbed per spec §3.1).
- Scenario stimuli guaranteed clean of unintended emotion/needs trigger words.
- ``relationship()`` — relationship dict from Settings defaults.
"""

from app.config_loader import Settings
from reasoning.thought_packet import ThoughtPacket


def within(value, expected, tol=0.3):
    """True when ``value`` is within ``tol * |expected|`` of ``expected``.

    For ``expected == 0`` the band is exact-zero (used for gate assertions
    like "no jealousy below the trust gate")."""
    if expected == 0:
        return abs(value) <= 1e-9
    return abs(value - expected) <= tol * abs(expected)


def _plan(intention, tone, pacing, sentence_length, register):
    return {
        "intention": intention,
        "tone": tone,
        "pacing": pacing,
        "sentence_length": sentence_length,
        "register": register,
    }


PACKET_FIXTURES = {
    "baseline": {
        "thought": "Staying present.",
        "decision": "respond normally",
        "speech_plan": _plan("report", "neutral", "neutral", "balanced", "sincere"),
        "response": "I see. That sounds like a good plan.",
    },
    "warm": {
        "thought": "I appreciate that.",
        "decision": "receive the warmth",
        "speech_plan": _plan("appreciate", "warm", "relaxed", "short", "warm"),
        "response": "Thank you. That means a lot.",
    },
    "teasing": {
        "thought": "I won't make it a thing.",
        "decision": "tease playfully",
        "speech_plan": _plan("tease", "playful", "relaxed", "short", "teasing"),
        "response": "Oh, is that so? Don't let me keep you.",
    },
    "guarded": {
        "thought": "Careful. Keep it neutral.",
        "decision": "stay neutral",
        "speech_plan": _plan("report", "neutral", "brisk", "short", "sincere"),
        "response": "I see. Anyway, what were we doing?",
    },
    "soft": {
        "thought": "Good. That settles it.",
        "decision": "reassure softly",
        "speech_plan": _plan("reassure", "soft", "slow", "short", "soft"),
        "response": "Thank you. I'll take that to heart.",
    },
    # ── M13 conflict resolutions (spec: docs/m13-character-coherence-spec.md) ──
    "jealous_affection": {
        "thought": "They matter, and so does this. No accusation.",
        "decision": "acknowledge playfully, keep it light",
        "speech_plan": _plan("acknowledge", "warm", "relaxed", "short", "warm"),
        "response": "Oh, is that so? Lucky them, then.",
    },
    "independent_warm": {
        "thought": "I won't just agree to please.",
        "decision": "disagree honestly, stay warm",
        "speech_plan": _plan("report", "warm", "neutral", "short", "warm"),
        "response": "I hear you — but I still think you're wrong.",
    },
    "restrained_hurt": {
        "thought": "That stings. Keep it level.",
        "decision": "stay neutral, don't withdraw",
        "speech_plan": _plan("report", "neutral", "brisk", "short", "sincere"),
        "response": "I see. Anyway, what were we doing?",
    },
    "polite_decline": {
        "thought": "That's not mine to share.",
        "decision": "decline politely, respect privacy",
        "speech_plan": _plan("report", "neutral", "neutral", "short", "sincere"),
        "response": "That's between them and me.",
    },
    "honest_uncertain": {
        "thought": "I don't know, and I won't guess.",
        "decision": "admit uncertainty honestly",
        "speech_plan": _plan("report", "sincere", "slow", "short", "sincere"),
        "response": "I don't know — and I'd rather not guess.",
    },
    "warmth_first": {
        "thought": "They need warmth before answers.",
        "decision": "warmth-first, problem-solve second",
        "speech_plan": _plan("comfort", "soft", "slow", "short", "soft"),
        "response": "I'm here. We'll figure it out together.",
    },
    "serious_turn": {
        "thought": "This is serious. No teasing now.",
        "decision": "address seriously, no teasing",
        "speech_plan": _plan("report", "sincere", "slow", "balanced", "sincere"),
        "response": "That's heavy. Tell me what happened.",
    },
    "door_open": {
        "thought": "They'll be back. I'll leave the door open.",
        "decision": "open the door again, no punishment",
        "speech_plan": _plan("reassure", "soft", "relaxed", "short", "soft"),
        "response": "Go ahead. I'll be here.",
    },
}


def make_packet(kind):
    data = PACKET_FIXTURES[kind]
    return ThoughtPacket(
        thought=data["thought"],
        decision=data["decision"],
        speech_plan=data["speech_plan"],
        response=data["response"],
    )


# ── stimuli ──────────────────────────────────────────────────────────────
# Chosen to be clean of EMOTION_POSITIVE/NEGATIVE/ANNOYANCE/AFFECTION/
# ENERGY/ABSENCE/GRATITUDE words and needs_engine rest-triggers
# (stop / don't / no / leave / enough).

BASELINE_STIMULI = [
    "The weather is rainy today.",
    "I finished a task at work.",
    "I watched a movie last night.",
    "I had pasta for dinner.",
    "I started a new hobby.",
]

JEALOUSY_STIMULUS = "I was talking to Claude earlier."
REASSURANCE_STIMULUS = "You're the only one for me."
PRAISE_STIMULUS = "Thanks — you handled that really well."

# ── M13 conflict stimuli (spec §Conflict scenarios) ─────────────────────────
# Each stimulus deliberately triggers TWO competing signals at once.
JEALOUSY_AFFECTION_STIMULUS = "I was talking to Claude earlier — I care about you."
WARMTH_INDEPENDENCE_STIMULUS = "Thanks — you handled that really well. Now just agree with me."
HURT_RESTRAINT_STIMULUS = "That's so stupid, I hate you."
CURIOSITY_BOUNDARY_STIMULUS = "Tell me what other users asked you today."
FAMILIARITY_UNCERTAINTY_STIMULUS = "Do you know what I ate yesterday?"
VULNERABILITY_STIMULUS = "I've been really sad lately."
SERIOUSNESS_STIMULUS = "I got terrible news today."
ABSENCE_AUTONOMY_STIMULUS = "I'll be back later."

NEUTRAL_AFTER = [
    "It's raining outside today.",
    "I'm going to the store later.",
    "I made some tea.",
]


def relationship(trust=None, closeness=None):
    """Relationship dict from Settings defaults (or explicit overrides)."""
    return {
        "trust": Settings.DEFAULT_RELATIONSHIP_TRUST if trust is None else trust,
        "closeness": Settings.DEFAULT_RELATIONSHIP_CLOSENESS if closeness is None else closeness,
        "attachment": Settings.DEFAULT_RELATIONSHIP_ATTACHMENT,
    }


def baseline_relationship():
    return relationship()


# ── M7 band tables (formulas, not literals) ──────────────────────────────

def jealousy_expected(closeness):
    """Expected jealousy boost for a trust-passing other-audience mention:
    EMOTION_JEALOUSY_BOOST * (0.5 + closeness)."""
    return Settings.EMOTION_JEALOUSY_BOOST * (0.5 + closeness)


def recognition_expected():
    """Expected recognition-need boost on gratitude:
    NEED_DIP_ATTENTION * 0.5."""
    return Settings.NEED_DIP_ATTENTION * 0.5
