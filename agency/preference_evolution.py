# Mai_ai/agency/preference_evolution.py
# M6 · Evidence-based preference evolution.
#
# Mai's likes/dislikes are canonical (core/identity/preferences.py) and never
# mutated directly. This module maintains an *overlay* driven strictly by
# evidence windows: a topic only moves between likes and dislikes after N≥3
# approval/disapproval events, at most once per cadence period, and every
# change is written to a decision trail and is revertible.
import time
import json
import logging
import re
import threading
from typing import Optional

logger = logging.getLogger(__name__)

# Topics that must never evolve — Mai's own name and generic pronouns.
_STOP_TOPICS = {
    "mai", "mai sakurajima", "sakurajima", "mai-chan", "senpai",
    "i", "me", "my", "you", "your", "we", "us", "they", "it", "this",
    "that", "the", "a", "an", "and", "or", "but",
}


class PreferenceEvolution:

    SENTIMENTS = ("like", "dislike")

    def __init__(self, threshold=3, cadence_days=7, state_path: Optional[str] = None,
                 trail_path: Optional[str] = None, event_bus=None, on_change=None):
        self.threshold = max(1, int(threshold))
        self.cadence_days = max(1, float(cadence_days))
        self._lock = threading.RLock()
        self.event_bus = event_bus
        self.on_change = on_change
        self._state_path = str(state_path) if state_path else None
        self._trail_path = str(trail_path) if trail_path else None

        # overlay: topic -> {"list": "likes"|"dislikes", "applied_at": float}
        self._overlay = {}
        # evidence: topic -> {"like": n, "dislike": n, "last_seen": float}
        self._evidence = {}
        # decision trail: [{timestamp, topic, before, after, reason}]
        self._trail = []

        self._load_state()
        self._load_trail()

    # ── evidence windows ────────────────────────────────────────────────

    # Sentiment phrase → evidence sentiment. Case-insensitive; the topic is
    # spliced into the pattern so multi-word topics match exactly.
    # Forms: "i love X" / "i don't like X" (first-person) and adjacency
    # "love X" / "hate X". Optional "the/my/your" between verb and topic.
    _LIKE_RE_TMPL = (
        r"\bi\s+(?:really\s+|just\s+|definitely\s+|totally\s+)?"
        r"(?:love|like|enjoy|adore|prefer)\s+(?:the\s+|my\s+|your\s+)?TOPIC\b",
        r"\b(?:love|like|enjoy|adore|prefer)\s+(?:the\s+)?TOPIC\b",
    )
    _DISLIKE_RE_TMPL = (
        r"\bi\s+(?:really\s+|just\s+|definitely\s+|totally\s+)?"
        r"(?:hate|dislike|detest|cannot\s+stand|can't\s+stand|don't\s+like|"
        r"do\s+not\s+like)\s+(?:the\s+|my\s+|your\s+)?TOPIC\b",
        r"\b(?:hate|dislike|detest)\s+(?:the\s+)?TOPIC\b",
    )

    def scan_turn(self, text, topics) -> list:
        """Scan a user turn for approval/disapproval evidence.

        ``topics`` are candidate entity/tag names from the turn (lowercased
        internally). Returns the list of (topic, sentiment) records applied.
        Deterministic regex matching — no LLM, no blocking. Recording only:
        applying happens in the background via :meth:`apply_pending`
        (scheduler task), gated by threshold + cadence."""
        if not text or not topics:
            return []
        text = str(text).strip().lower()
        # Strip negated approval constructions so adjacency patterns cannot
        # fire inside "do not love X" / "don't like X".
        text_like = re.sub(
            r"(?:do\s+not|don't|doesn't|didn't|never)\s+"
            r"(?:really\s+|just\s+|definitely\s+|totally\s+)?"
            r"(?:love|like|enjoy|adore|prefer)",
            " ", text,
        )
        hits = []
        with self._lock:
            for topic in set(str(t).strip().lower() for t in topics if t):
                if not topic or topic in _STOP_TOPICS:
                    continue
                escaped = re.escape(topic)
                # Dislike first — "don't like X" must not classify as like.
                for dislike_re in self._DISLIKE_RE_TMPL:
                    if re.search(dislike_re.replace("TOPIC", escaped), text):
                        hits.append((topic, "dislike"))
                        break
                else:
                    for like_re in self._LIKE_RE_TMPL:
                        if re.search(like_re.replace("TOPIC", escaped), text_like):
                            hits.append((topic, "like"))
                            break
        recorded = []
        for topic, sentiment in hits:
            status = self.record_evidence(topic, sentiment)
            if status.get("ok"):
                recorded.append((topic, sentiment))
        return recorded

    def record_evidence(self, topic: str, sentiment: str) -> dict:
        """Register one approval/disapproval event for a topic.

        Returns a status dict describing whether the topic now qualifies for
        evolution (``candidate=True`` when evidence >= threshold). Applying
        waits for the cadence gate in :meth:`apply_candidates`."""
        topic = str(topic or "").strip().lower()
        sentiment = str(sentiment or "").strip().lower()
        if not topic or sentiment not in self.SENTIMENTS:
            return {"ok": False, "reason": "invalid_topic_or_sentiment"}
        with self._lock:
            window = self._evidence.setdefault(
                topic, {"like": 0, "dislike": 0, "last_seen": time.time()}
            )
            window[sentiment] += 1
            window["last_seen"] = time.time()
            candidate = window[sentiment] >= self.threshold
            self._save_state()
        return {"ok": True, "topic": topic, "candidate": candidate,
                "count": window[sentiment]}

    def evidence_for(self, topic: str) -> dict:
        with self._lock:
            return dict(self._evidence.get(str(topic).strip().lower(), {}))

    # ── applying & gating ───────────────────────────────────────────────

    def apply_pending(self) -> list:
        """Apply candidate evidence against the canonical preference lists.

        Reads the canonical likes/dislikes from
        ``core.identity.preferences.PREFERENCES`` (never mutated) and
        delegates to :meth:`apply_candidates`. Returns applied changes."""
        try:
            from core.identity.preferences import PREFERENCES
            likes = list(PREFERENCES.get("likes") or [])
            dislikes = list(PREFERENCES.get("dislikes") or [])
        except Exception as e:
            logger.debug("[PreferenceEvolution] canonical prefs read failed: %s", e)
            return []
        return self.apply_candidates(likes, dislikes)

    def apply_candidates(self, current_likes, current_dislikes) -> list:
        """Evolve any candidate topics that cleared threshold + cadence.

        ``current_likes`` / ``current_dislikes`` are the canonical lists;
        returns the list of applied change dicts. Applies are logged in the
        decision trail and persisted to the overlay."""
        applied = []
        with self._lock:
            now = time.time()
            eff_likes = set(current_likes)
            eff_dislikes = set(current_dislikes)
            for topic, entry in self._overlay.items():
                if entry.get("list") == "likes":
                    eff_likes.add(topic)
                    eff_dislikes.discard(topic)
                else:
                    eff_dislikes.add(topic)
                    eff_likes.discard(topic)
            for topic, window in self._evidence.items():
                like_n = window.get("like", 0)
                dislike_n = window.get("dislike", 0)
                if max(like_n, dislike_n) < self.threshold:
                    continue
                if topic in self._overlay:
                    # already evolved — a new cadence period must elapse
                    applied_at = self._overlay[topic].get("applied_at", 0)
                    if now - applied_at < self.cadence_days * 86400:
                        continue
                target = "likes" if like_n >= dislike_n else "dislikes"
                if topic in self._overlay:
                    if self._overlay[topic].get("list") == target:
                        continue  # already evolved in this direction
                before = topic in eff_likes
                after = target == "likes"
                if before == after:
                    # effective direction already matches — no actual change;
                    # drop evidence to avoid re-eval noise
                    continue
                self._overlay[topic] = {"list": target, "applied_at": now}
                change = {
                    "timestamp": now,
                    "topic": topic,
                    "before": "likes" if before else "dislikes",
                    "after": target,
                    "reason": f"evidence like={like_n} dislike={dislike_n} "
                              f"(threshold {self.threshold}, cadence {self.cadence_days}d)",
                }
                self._trail.append(change)
                applied.append(change)
            if applied:
                self._save_state()
                self._save_trail()
                if self.event_bus:
                    from core.event_specs import PREFERENCE_EVOLVED
                    from core.mai_message import publish_event
                    publish_event(self.event_bus, PREFERENCE_EVOLVED, {
                        "changes": applied,
                    }, source="agency")
                if self.on_change:
                    try:
                        self.on_change(self.overlay_map())
                    except Exception as e:
                        logger.debug("[PreferenceEvolution] on_change failed: %s", e)
        return applied

    def overlay_map(self) -> dict:
        """Overlay in IdentityCore.attach_preference_overlay shape:
        ``{topic: {"list": "likes"|"dislikes"}}``. The shape consumed by
        identity projection (M7 wiring fix — on_change delivers this)."""
        with self._lock:
            return {
                topic: {"list": entry.get("list")}
                for topic, entry in self._overlay.items()
            }

    def revert(self, topic: str) -> bool:
        """Remove an overlay entry, restoring the canonical preference."""
        topic = str(topic or "").strip().lower()
        with self._lock:
            if topic not in self._overlay:
                return False
            prev = self._overlay.pop(topic)
            self._trail.append({
                "timestamp": time.time(),
                "topic": topic,
                "before": prev.get("list", ""),
                "after": "canonical",
                "reason": "revert",
            })
            self._save_state()
            self._save_trail()
            if self.on_change:
                try:
                    self.on_change(self.overlay_map())
                except Exception as e:
                    logger.debug("[PreferenceEvolution] on_change failed: %s", e)
        return True

    def evolved_preferences(self) -> dict:
        """Overlay as {likes: [...], dislikes: [...]} applied topics."""
        likes, dislikes = [], []
        with self._lock:
            for topic, entry in self._overlay.items():
                if entry.get("list") == "likes":
                    likes.append(topic)
                else:
                    dislikes.append(topic)
        return {"likes": likes, "dislikes": dislikes}

    def decision_trail(self, limit=None) -> list:
        with self._lock:
            trail = list(self._trail)
        if limit is not None:
            trail = trail[-int(limit):]
        return trail

    def stats(self) -> dict:
        with self._lock:
            return {
                "evidence_topics": len(self._evidence),
                "overlay_topics": len(self._overlay),
                "trail_entries": len(self._trail),
                "threshold": self.threshold,
                "cadence_days": self.cadence_days,
            }

    # ── persistence ─────────────────────────────────────────────────────

    def _save_state(self):
        if not self._state_path:
            return
        try:
            with open(self._state_path, "w", encoding="utf-8") as fh:
                json.dump({
                    "overlay": self._overlay,
                    "evidence": self._evidence,
                }, fh, indent=2)
        except Exception as e:
            logger.debug("[PreferenceEvolution] state save failed: %s", e)

    def _load_state(self):
        if not self._state_path:
            return
        try:
            with open(self._state_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._overlay = {str(k): dict(v) for k, v in (data.get("overlay") or {}).items()}
            self._evidence = {
                str(k): dict(v) for k, v in (data.get("evidence") or {}).items()
            }
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug("[PreferenceEvolution] state load failed: %s", e)

    def _save_trail(self):
        if not self._trail_path:
            return
        try:
            with open(self._trail_path, "w", encoding="utf-8") as fh:
                json.dump(self._trail, fh, indent=2)
        except Exception as e:
            logger.debug("[PreferenceEvolution] trail save failed: %s", e)

    def _load_trail(self):
        if not self._trail_path:
            return
        try:
            with open(self._trail_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._trail = list(data or [])
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug("[PreferenceEvolution] trail load failed: %s", e)