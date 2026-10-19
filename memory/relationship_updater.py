# Mai_ai/memory/relationship_updater.py
"""RelationshipUpdater — state-first relationship tracking.

Phase 2 of docs/cognitive-architecture-state-first.md. The relationship values
(closeness, trust, interactions, ...) are now the runtime source of truth held
in memory. The markdown file `relationship/relationship.md` is a *compile output*
produced by the VaultCompiler, not the live store. On update, the in-memory
state is mutated and then compiled through the VaultCompiler.

The emitted markdown format is preserved exactly (Closeness / Trust /
Interactions / LastInteraction / LastInteractionUnix) so that ObsidianReader and
the autonomy engine keep parsing it unchanged.
"""
import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class RelationshipState:
    closeness: float = 0.5
    trust: float = 0.5
    interactions: int = 0
    last_interaction_unix: float = 0.0
    attachment: float = 0.0


class RelationshipUpdater:
    def __init__(self, path, compiler=None):
        self.path = Path(path) if not isinstance(path, Path) else path
        self.compiler = compiler

        # 🧠 relationship decay settings
        self.decay_rate = 0.002

        # 🧠 emotional amplification
        self.strong_emotion_bonus = 0.05

        # 🔒 Thread safety lock
        self.lock = threading.RLock()

        # 🧠 runtime source of truth
        self.state = RelationshipState()

        # 🛡️ bootstrap from existing file (read-only); file is a compile output
        self._load_from_file()

    # ── public API ──

    def update(self, text, emotion=None):
        with self.lock:
            self._ensure_defaults()
            s = self.state

            closeness = s.closeness
            trust = s.trust

            t = (text or "").lower()

            # 🧠 TIME DECAY
            closeness, trust = self._apply_decay(closeness, trust, s.last_interaction_unix)

            # 🧠 POSITIVE SOCIAL SIGNALS
            if any(word in t for word in ["thank", "thanks", "appreciate"]):
                closeness += 0.02

            # 🧠 TRUST SIGNALS
            if any(word in t for word in ["trust", "help", "rely", "need you"]):
                trust += 0.02

            # 🧠 EMOTIONAL OPENNESS
            if any(phrase in t for phrase in ["miss you", "sad", "lonely", "worried", "i feel"]):
                closeness += 0.03

            # 🧠 NEGATIVE SIGNALS
            if any(phrase in t for phrase in ["shut up", "annoying", "leave me alone", "hate you"]):
                closeness -= 0.04
                trust -= 0.03

            # 🧠 STRONG EMOTION BONUS
            if emotion and isinstance(emotion, dict):
                intensity = emotion.get("intensity", 0.5)
                if intensity > 0.8:
                    closeness += self.strong_emotion_bonus * 0.5

            # 🧠 INTERACTION MOMENTUM
            interactions = s.interactions + 1
            if interactions > 50:
                closeness += 0.01

            # 🧠 CLAMP VALUES
            closeness = max(0.0, min(closeness, 1.0))
            trust = max(0.0, min(trust, 1.0))

            s.closeness = closeness
            s.trust = trust
            s.interactions = interactions
            s.last_interaction_unix = time.time()

            self._compile()

    # 📊 DEBUG INFO
    def stats(self):
        with self.lock:
            now = int(self.state.last_interaction_unix) or int(time.time())
            now_str = __import__("datetime").datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
            return (
                f"Closeness: {self.state.closeness:.2f}\n"
                f"Trust: {self.state.trust:.2f}\n"
                f"Interactions: {self.state.interactions}\n"
                f"LastInteraction: {now_str}\n"
                f"LastInteractionUnix: {now}\n"
            )

    # ── internals ──

    def _compile(self):
        """Write the in-memory state to relationship.md via the VaultCompiler."""
        if self.compiler is not None:
            try:
                self.compiler.compile_relationship(self.state)
                return
            except Exception as e:
                logger.error("[RelationshipUpdater] compiler failed, falling back: %s", e)
        # fallback: write directly (preserves boot behavior when no compiler wired)
        self._write_file()

    def _write_file(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        now = int(self.state.last_interaction_unix) or int(time.time())
        now_str = __import__("datetime").datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        content = f"""
Closeness: {self.state.closeness:.2f}
Trust: {self.state.trust:.2f}
Interactions: {self.state.interactions}
LastInteraction: {now_str}
LastInteractionUnix: {now}
"""
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(content.strip())

    def _ensure_defaults(self):
        if not self.path.exists():
            self._write_file()

    def _load_from_file(self):
        if not self.path.exists():
            return
        try:
            content = self.path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning("[RelationshipUpdater] Failed to read relationship file: %s", e)
            return
        s = self.state
        s.closeness = self._get(content, "Closeness")
        s.trust = self._get(content, "Trust")
        s.interactions = int(self._get(content, "Interactions"))
        s.last_interaction_unix = self._get_timestamp(content)

        # 🧠 Integrity guard: an empty/fresh relationship file (no interactions
        # recorded) must not zero out closeness/trust.  Boot-time compilers can
        # emit a blank file which would otherwise pin Trust=0 forever.
        if s.interactions == 0 and s.closeness == 0.0 and s.trust == 0.0:
            logger.info("[RelationshipUpdater] fresh/empty state detected — "
                        "defaulting closeness/trust to their baselines")
            s.closeness = 0.5
            s.trust = 0.5

    def _get(self, text, key):
        match = re.search(rf"{key}:\s*([0-9.]+)", text)
        if match:
            return float(match.group(1))
        return 0.5

    def _get_timestamp(self, text):
        unix_match = re.search(r"LastInteractionUnix:\s*(\d+)", text)
        if unix_match:
            return int(unix_match.group(1))
        match = re.search(r"LastInteraction:\s*(\d+)", text)
        if match:
            return int(match.group(1))
        return int(time.time())

    def _apply_decay(self, closeness, trust, last_interaction):
        now = time.time()
        days = (now - last_interaction) / 86400
        closeness -= days * self.decay_rate
        trust -= days * (self.decay_rate * 0.5)
        return closeness, trust

    def _relationship_stage(self, closeness, trust):
        avg = (closeness + trust) / 2
        if avg < 0.3:
            return "distant"
        if avg < 0.5:
            return "familiar"
        if avg < 0.7:
            return "trusted"
        if avg < 0.9:
            return "close"
        return "deeply_attached"
