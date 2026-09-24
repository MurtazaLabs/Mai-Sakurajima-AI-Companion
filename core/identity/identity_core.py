# core/identity/identity_core.py
# Identity Core (MaiCore) — consultative facade, NOT the execution path.
#
# Every subsystem can ask "what would Mai do?" — but the core only answers
# queries. It never executes actions, never mutates state, and delegates rule
# production to owning engines (personality_state, relationship engine, etc.).
#
# God-object guardrail: any method that grows >10 lines of actual logic must be
# split — delegate to the engine that owns that knowledge, keep the facade thin.
#
# ⚠️ Seam: additive changes only. All query APIs are read-only projections.

import json
import logging
import threading

from core.identity import (
    IDENTITY,
    PERSONALITY,
    VALUES,
    SPEECH,
    PREFERENCES,
    BOUNDARIES,
)
from core.identity.canonical import CANON_KEYS, check_drift

logger = logging.getLogger("Mai.IdentityCore")

# PersonalityState trait names (numeric modulation axes). Ordering is stable.
_TRAIT_KEYS = (
    "warmth", "teasing", "directness", "playfulness", "affection",
    "patience", "confidence",
)


class IdentityCore:
    """Consultative identity facade — query API, zero side effects.

    Delegation map (read-only):
      - personality_state  → numeric trait modulation (injected later by app)
      - relationship_engine → live relationship scores (if injected by app)
      - static identity modules → canonical canon (identity.py, etc.)
    """

    def __init__(self, personality_state=None, relationship_engine=None):
        self._personality_state = personality_state
        self._relationship_engine = relationship_engine
        self._preference_overlay = {}
        self._lock = threading.RLock()

    # ==================================================
    # 🏗️ INJECTION (app wiring — allowed, still read-only use)
    # ==================================================

    def bind(self, personality_state=None, relationship_engine=None):
        """Attach owning engines. IdentityCore never mutates them."""
        with self._lock:
            if personality_state is not None:
                self._personality_state = personality_state
            if relationship_engine is not None:
                self._relationship_engine = relationship_engine

    # ==================================================
    # 🧠 QUERY APIs
    # ==================================================

    def get_identity(self) -> dict:
        return self._deepcopy(IDENTITY)

    def get_personality(self) -> dict:
        """Character-level traits: prose canon + numeric modulation state."""
        traits = self._deepcopy(PERSONALITY)
        numeric = self._safe_numeric()
        if numeric:
            traits["state"] = numeric
        return traits

    def get_values(self) -> dict:
        return self._deepcopy(VALUES)

    def get_boundaries(self) -> dict:
        return self._deepcopy(BOUNDARIES)

    def get_preferences(self) -> dict:
        prefs = self._deepcopy(PREFERENCES)
        with self._lock:
            overlay = self._deepcopy(self._preference_overlay)
        if overlay:
            for topic, entry in overlay.items():
                target = (entry or {}).get("list")
                if target not in ("likes", "dislikes"):
                    continue
                prefs["likes"] = [p for p in prefs.get("likes", []) if p != topic]
                prefs["dislikes"] = [p for p in prefs.get("dislikes", []) if p != topic]
                prefs[target].append(topic)
        return prefs

    def attach_preference_overlay(self, overlay: dict) -> None:
        """Snapshot the evidence-based preference overlay (read-only use).

        The overlay comes from PreferenceEvolution — a dict of
        {topic: {"list": "likes"|"dislikes", ...}}. IdentityCore never
        mutates the source; it only projects the snapshot into queries.
        """
        with self._lock:
            self._preference_overlay = self._deepcopy(overlay or {})

    def get_speech_rules(self) -> dict:
        """Effective speech rules: canon style + personality style modifiers."""
        rules = self._deepcopy(SPEECH)
        modifiers = []
        ps = self._personality_state
        if ps is not None:
            try:
                if hasattr(ps, "get_style_modifiers"):
                    modifiers = ps.get_style_modifiers()
                elif hasattr(ps, "state"):
                    rules_list = rules.setdefault("rules", [])
                    if ps.state.get("warmth", 0.5) > 0.7:
                        rules_list.append("Speak in a softer and emotionally warmer tone.")
                    if ps.state.get("directness", 0.5) > 0.7:
                        rules_list.append("Keep responses concise and direct.")
            except Exception as exc:
                logger.debug("IdentityCore personality style modifiers failed: %s", exc)
        if modifiers:
            rules["dynamic"] = modifiers
        return rules

    def get_relationship_rules(self) -> dict:
        """Canonical relationship rules; overlays live scores when engine present."""
        rules = {
            "closeness_stages": [
                {"stage": "stranger", "range": "0.0-0.25",
                 "behavior": "polite, guarded, formal but functional warmth"},
                {"stage": "acquaintance", "range": "0.25-0.5",
                 "behavior": "warm tone, small talk, still reserved"},
                {"stage": "friend", "range": "0.5-0.75",
                 "behavior": "playfulness, teasing begins, more honesty"},
                {"stage": "close", "range": "0.75-1.0",
                 "behavior": "comfort, teasing, direct affection"},
            ],
            "trust_mechanics": [
                "Trust climbs slowly with repeated behavior, never one event",
                "Trust falls fast on clear violation",
                "Respect is a baseline; trust is earned",
            ],
            "affection_display": "affection in actions and consistency",
            "security": "independent judgment at every closeness stage",
        }
        engine = self._relationship_engine
        if engine is not None:
            live = None
            try:
                if callable(getattr(engine, "get_scores", None)):
                    live = engine.get_scores()
                else:
                    engine_state = getattr(engine, "state", None)
                    rel_state = getattr(engine_state, "relationship_scores", None) \
                        if engine_state is not None else None
                    if rel_state is not None:
                        if hasattr(rel_state, "model_dump"):
                            live = rel_state.model_dump()
                        elif isinstance(rel_state, dict):
                            live = dict(rel_state)
            except Exception as exc:
                logger.debug("IdentityCore relationship scores: %s", exc)
            if live:
                rules["live"] = self._deepcopy(live)
        return rules

    def get_social_rules(self) -> dict:
        canon_social = CANON_KEYS.get("social_rules.teasing", "") or (
            "teasing emerges from familiarity; never wounds;"
            " retreats at negative reaction"
        )
        return {
            "teasing": canon_social,
            "indirectness": CANON_KEYS.get("social_rules.indirectness"),
            "restraint": CANON_KEYS.get("social_rules.restraint"),
        }

    def get_emotional_rules(self) -> dict:
        return {
            "jealousy": CANON_KEYS.get("emotional_rules.jealousy"),
            "warmth": CANON_KEYS.get("emotional_rules.warmth"),
            "absence": CANON_KEYS.get("emotional_rules.absence"),
        }

    def get_conflict_resolution(self) -> dict:
        """Canonical rule-resolution policy (Volume IV) — read-only projection.

        Returns the 7-tier priority order and resolution principles as canon
        policy only. This is NOT wired into prompts or decision paths; it is
        the explicit precedence artifact for validation (M13)."""
        return {
            "priority_order": CANON_KEYS.get("conflict_resolution.priority_order"),
            "resolution_principles": CANON_KEYS.get("conflict_resolution.resolution_principles"),
        }

    # ==================================================
    # 🧠 COMPOSITE
    # ==================================================

    def get_current_identity(self) -> dict:
        """Full character snapshot — how the character answers the platform."""
        with self._lock:
            return {
                "identity": self.get_identity(),
                "personality": self.get_personality(),
                "values": self.get_values(),
                "boundaries": self.get_boundaries(),
                "preferences": self.get_preferences(),
                "speech": self.get_speech_rules(),
                "relationship": self.get_relationship_rules(),
                "social": self.get_social_rules(),
                "emotional": self.get_emotional_rules(),
            }

    def get_snapshot(self) -> dict:
        """Bounded JSON-safe snapshot (dashboard/observability-friendly)."""
        with self._lock:
            try:
                return json.loads(json.dumps(self.get_current_identity()))
            except Exception as exc:
                logger.warning("IdentityCore snapshot failed: %s", exc)
                return {}

    # ==================================================
    # 🧹 DRIFT CHECK (book ↔ code)
    # ==================================================

    def drift_issues(self) -> list:
        """List of book↔code mismatches. Empty = canon aligned."""
        with self._lock:
            return check_drift()

    # ==================================================
    # 🔧 INTERNAL — read-only one-off projections
    # ==================================================

    def _safe_numeric(self) -> dict:
        ps = self._personality_state
        if ps is None:
            return {}
        try:
            if hasattr(ps, "get"):
                return dict(ps.get() or {})
            if hasattr(ps, "state"):
                return {k: v for k, v in ps.state.items() if k in _TRAIT_KEYS}
        except Exception as exc:
            logger.debug("IdentityCore numeric traits failed: %s", exc)
        return {}

    def _deepcopy(self, obj):
        import copy
        return copy.deepcopy(obj)