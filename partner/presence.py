# partner/presence.py
"""Presence policy — when Mai may approach, interrupt, or start something.

Ambient presence, not a notification machine. Everything is a deterministic
policy decision over observable state:

- the current **activity class** (coding, working, focus, idle, conversation, away)
- **quiet mode** ("sees everything, initiates nothing")
- **interruption class** per activity (coding → urgent/commitment only)
- **time-of-day rituals** (morning / midday / evening / night, once per day)
- **initiative** (may she start a conversation?) and **disagreement**
  (may she say no?) — both gated by trust, so she earns the privilege.

Activity detection reads ``CognitiveState`` signals and, when T3 lands, a
window-title provider. Absent signals mean "idle", never "active".
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

ACTIVITY_CLASSES = ("coding", "working", "focus", "idle", "conversation", "away")

INTERRUPTION_KINDS = (
    "urgent",
    "commitment_missed",
    "commitment_due",
    "goal_update",
    "small_talk",
    "ritual",
)

# Per-activity interruption policy: which interruption classes may reach the
# user, and how long to wait between two of them.
INTERRUPTION_POLICY: dict[str, dict[str, Any]] = {
    "coding": {"allowed": {"urgent", "commitment_missed"}, "cooldown": 900.0},
    "focus": {"allowed": {"urgent"}, "cooldown": 1800.0},
    "working": {"allowed": {"urgent", "commitment_missed", "commitment_due"}, "cooldown": 600.0},
    "idle": {"allowed": set(INTERRUPTION_KINDS), "cooldown": 60.0},
    "conversation": {"allowed": {"urgent"}, "cooldown": 300.0},
    "away": {"allowed": {"urgent", "commitment_missed", "commitment_due", "ritual"}, "cooldown": 1200.0},
}

# Ritual windows (local time, hour bands). Outside every band there is no ritual.
RITUAL_WINDOWS = {
    "morning": (5, 11),
    "midday": (11, 15),
    "evening": (17, 22),
    "night": (22, 5),
}

_CODING_TOKENS = (
    "visual studio", "vscode", "vs code", "pycharm", "intellij", "sublime",
    "android studio", "terminal", "powershell", "git bash", "cmd.exe", "notepad++",
)
_WORK_TOKENS = ("word", "excel", "powerpoint", "docs", "sheets", "figma", "slack", "teams")
_FOCUS_TOKENS = ("zoom", "meet", "webex", "obs ", "presentation")


@dataclass
class Decision:
    """One presence decision, with the reason it was made."""

    allowed: bool
    reason: str
    activity: str
    kind: str = ""
    deferred_until: float = 0.0
    detail: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "activity": self.activity,
            "kind": self.kind,
            "deferred_until": self.deferred_until,
            "detail": dict(self.detail),
        }


class PresencePolicy:

    def __init__(self, store=None, quiet_mode: bool = False,
                 min_trust: float = 0.6, initiative_cooldown: float = 3600.0):
        self._store = store
        self._lock = threading.RLock()
        self._activity = "idle"
        self._last_interrupt = 0.0
        self._last_initiative = 0.0
        self.min_trust = float(min_trust)
        self.initiative_cooldown = float(initiative_cooldown)
        self._quiet_mode = self._load_quiet(quiet_mode)

    # -- persistence -------------------------------------------------

    def _load_quiet(self, fallback: bool) -> bool:
        if self._store is None:
            return bool(fallback)
        try:
            presence = self._store.read().get("presence") or {}
            value = presence.get("quiet_mode")
            return bool(value) if isinstance(value, bool) else bool(fallback)
        except Exception as exc:
            logger.debug("[Presence] quiet_mode load failed: %s", exc)
            return bool(fallback)

    def _save_quiet(self, value: bool) -> None:
        if self._store is None:
            return
        with self._store.transaction() as document:
            presence = document.setdefault("presence", {})
            presence["quiet_mode"] = bool(value)
            presence["updated_at"] = time.time()

    # -- quiet mode / activity ---------------------------------------

    @property
    def quiet_mode(self) -> bool:
        with self._lock:
            return self._quiet_mode

    def set_quiet(self, flag: bool) -> bool:
        with self._lock:
            self._quiet_mode = bool(flag)
        self._save_quiet(self._quiet_mode)
        logger.info("[Presence] quiet mode %s", "on" if self._quiet_mode else "off")
        return self._quiet_mode

    @property
    def activity(self) -> str:
        with self._lock:
            return self._activity

    def set_activity(self, activity: str) -> bool:
        if activity not in ACTIVITY_CLASSES:
            return False
        with self._lock:
            changed = self._activity != activity
            self._activity = activity
        if changed:
            logger.info("[Presence] activity -> %s", activity)
        return True

    def detect_activity(self, cognitive_state=None, window_title: str = "",
                        idle_seconds: float | None = None) -> str:
        """Infer the activity class from available signals; never guesses busy."""
        title = str(window_title or "").lower()
        if title:
            if any(token in title for token in _CODING_TOKENS):
                return "coding"
            if any(token in title for token in _FOCUS_TOKENS):
                return "focus"
            if any(token in title for token in _WORK_TOKENS):
                return "working"
        if idle_seconds is not None and idle_seconds >= 900:
            return "away"
        if cognitive_state is not None and hasattr(cognitive_state, "get"):
            try:
                state = cognitive_state.get() or {}
            except Exception as exc:
                logger.debug("[Presence] cognitive read failed: %s", exc)
                state = {}
            task = str(state.get("active_task") or "").lower()
            intent = str(state.get("conversation_intent") or "").lower()
            if any(token in task for token in ("code", "debug", "implement", "refactor", "test")):
                return "coding"
            if intent in ("engineering", "coding"):
                return "coding"
            if intent:
                return "conversation"
        return "idle"

    # -- interruption ------------------------------------------------

    def decide(self, kind: str, now: float | None = None) -> Decision:
        """May an interruption of ``kind`` reach the user right now?"""
        now = time.time() if now is None else float(now)
        with self._lock:
            activity = self._activity
            quiet = self._quiet_mode
            last = self._last_interrupt
        if kind not in INTERRUPTION_KINDS:
            return Decision(False, f"unknown interruption kind: {kind}", activity, kind)
        if quiet:
            return Decision(False, "quiet_mode", activity, kind)
        policy = INTERRUPTION_POLICY.get(activity, INTERRUPTION_POLICY["idle"])
        if kind not in policy["allowed"]:
            return Decision(
                False, f"{activity}_suppresses_{kind}", activity, kind,
                detail={"allowed": sorted(policy["allowed"])},
            )
        cooldown = float(policy["cooldown"])
        elapsed = now - last
        if last and elapsed < cooldown:
            return Decision(
                False, "cooldown", activity, kind,
                deferred_until=last + cooldown,
                detail={"remaining": round(cooldown - elapsed, 1)},
            )
        with self._lock:
            self._last_interrupt = now
        return Decision(True, "allowed", activity, kind)

    # -- initiative + disagreement -----------------------------------

    def should_initiate(self, trust: float, now: float | None = None) -> Decision:
        """May she start a conversation on her own?"""
        now = time.time() if now is None else float(now)
        with self._lock:
            activity = self._activity
            quiet = self._quiet_mode
            last = self._last_initiative
        if quiet:
            return Decision(False, "quiet_mode", activity)
        if activity in ("focus", "conversation", "away"):
            return Decision(False, f"{activity}_no_initiative", activity)
        if float(trust or 0.0) < self.min_trust:
            return Decision(
                False, "trust_too_low", activity,
                detail={"trust": round(float(trust or 0.0), 3), "min_trust": self.min_trust},
            )
        if last and (now - last) < self.initiative_cooldown:
            return Decision(
                False, "initiative_cooldown", activity,
                deferred_until=last + self.initiative_cooldown,
            )
        with self._lock:
            self._last_initiative = now
        return Decision(True, "allowed", activity)

    def may_disagree(self, trust: float) -> Decision:
        """High trust is what buys her the right to say no."""
        trust = float(trust or 0.0)
        allowed = trust >= self.min_trust
        return Decision(
            allowed,
            "allowed" if allowed else "trust_too_low",
            self.activity,
            detail={"trust": round(trust, 3), "min_trust": self.min_trust},
        )

    # -- rituals -----------------------------------------------------

    def ritual_for(self, now: float | None = None) -> str | None:
        hour = datetime.fromtimestamp(time.time() if now is None else float(now)).hour
        for name, (start, end) in RITUAL_WINDOWS.items():
            if start <= end:
                if start <= hour < end:
                    return name
            elif hour >= start or hour < end:  # window wraps midnight
                return name
        return None

    def ritual_due(self, name: str, now: float | None = None) -> bool:
        """True when ``name`` is the current ritual and it has not run today."""
        if name not in RITUAL_WINDOWS:
            return False
        now = time.time() if now is None else float(now)
        if self.ritual_for(now) != name:
            return False
        if self._store is None:
            return True
        try:
            rituals = self._store.read().get("rituals") or {}
        except Exception as exc:
            logger.debug("[Presence] ritual read failed: %s", exc)
            return False
        today = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
        return rituals.get(name) != today

    def mark_ritual(self, name: str, now: float | None = None) -> None:
        if self._store is None:
            return
        now = time.time() if now is None else float(now)
        today = datetime.fromtimestamp(now).strftime("%Y-%m-%d")
        with self._store.transaction() as document:
            document.setdefault("rituals", {})[name] = today

    # -- introspection -----------------------------------------------

    def status(self) -> dict:
        with self._lock:
            return {
                "activity": self._activity,
                "quiet_mode": self._quiet_mode,
                "min_trust": self.min_trust,
                "ritual_now": self.ritual_for(),
                "policy": {
                    name: {"allowed": sorted(policy["allowed"]), "cooldown": policy["cooldown"]}
                    for name, policy in INTERRUPTION_POLICY.items()
                },
            }
