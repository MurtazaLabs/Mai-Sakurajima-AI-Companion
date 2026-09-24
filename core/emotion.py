# core/emotion.py
import time
import threading
import logging

from app.config_loader import Settings
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class Emotion:

    def __init__(self, shared_state=None, event_bus=None, brain_graph=None):

        self._shared_state = shared_state
        self.event_bus = event_bus or EventBus()
        self.brain_graph = brain_graph
        self._snapshot_counter = 0

        # ==================================================
        # 🧠 THREAD SAFETY
        # ==================================================

        self.lock = threading.RLock()
        self._dirty = False

        # ==================================================
        # 🧠 CURRENT EMOTIONAL STATE
        # ==================================================

        defaults = {
            "happy":   Settings.EMOTION_DEFAULT_HAPPY,
            "lonely":  Settings.EMOTION_DEFAULT_LONELY,
            "annoyed": Settings.EMOTION_DEFAULT_ANNOYED,
            "affection": Settings.EMOTION_DEFAULT_AFFECTION,
            "energy":  Settings.EMOTION_DEFAULT_ENERGY,
            "stress":  Settings.EMOTION_DEFAULT_STRESS,
            "jealousy": Settings.EMOTION_DEFAULT_JEALOUSY,
        }

        # Load from persisted SharedState if available
        if shared_state is not None:
            loaded_jealousy = getattr(shared_state.emotion, "jealousy", Settings.EMOTION_DEFAULT_JEALOUSY)
            if not isinstance(loaded_jealousy, (int, float)):
                loaded_jealousy = Settings.EMOTION_DEFAULT_JEALOUSY
            self.state = {
                "happy":     shared_state.emotion.happy,
                "lonely":    shared_state.emotion.lonely,
                "annoyed":   shared_state.emotion.annoyed,
                "affection": shared_state.emotion.affection,
                "energy":    shared_state.emotion.energy,
                "stress":    shared_state.emotion.stress,
                "jealousy":  loaded_jealousy,
            }
        else:
            self.state = dict(defaults)

        # ==================================================
        # 🧠 BASELINE EMOTIONS
        # ==================================================

        self.baseline = dict(defaults)

        # ==================================================
        # 🧠 DECAY SETTINGS
        # ==================================================

        self.decay_speed = (
            Settings.EMOTION_DECAY_SPEED
        )

        self.max_decay_elapsed = (
            Settings.EMOTION_MAX_DECAY_ELAPSED
        )

        self.last_update = time.time()

        # ==================================================
        # 🧠 EMOTION PROFILES
        # ==================================================

        from core.emotion_system import EmotionHistory, EmotionTriggerLog, find_closest_profile, EMOTION_PROFILES
        self.history = EmotionHistory()
        self.triggers = EmotionTriggerLog()
        self._find_closest_profile = find_closest_profile
        self._profiles = EMOTION_PROFILES
        self.current_profile = find_closest_profile(self.state)

    # ==================================================
    # 🧠 MAIN UPDATE
    # ==================================================

    def update(self, text, relationship=None):
        with self.lock:
            if not text:
                return
            text = str(text).lower()

            self._decay()

            if not isinstance(relationship, dict):
                relationship = {}
            closeness = relationship.get("closeness", Settings.DEFAULT_RELATIONSHIP_CLOSENESS)
            attachment = relationship.get("attachment", Settings.DEFAULT_RELATIONSHIP_ATTACHMENT)
            trust = relationship.get("trust", Settings.DEFAULT_RELATIONSHIP_TRUST)

            self._handle_gratitude(text)
            self._handle_annoyance(text, closeness)
            self._handle_affection(text, attachment)
            self._handle_absence(text)
            self._handle_positive(text)
            self._handle_negative(text)
            self._handle_energy(text)
            self._handle_trust(trust)
            self._handle_jealousy(text, closeness, trust)

            self._clamp()
            self._publish_update()

    def _handle_gratitude(self, text):
        if any(word in text for word in Settings.EMOTION_GRATITUDE_WORDS):
            self.modify("happy", Settings.EMOTION_GRATITUDE_HAPPY_BOOST)
            self.modify("affection", Settings.EMOTION_GRATITUDE_AFFECTION_BOOST)

    def _handle_annoyance(self, text, closeness):
        if any(word in text for word in Settings.EMOTION_ANNOYANCE_WORDS):
            boost = Settings.EMOTION_ANNOYANCE_BOOST * (1 - closeness)
            self.modify("annoyed", boost)
            self.modify("happy", Settings.EMOTION_ANNOYANCE_HAPPY_PENALTY)
            self.modify("stress", Settings.EMOTION_ANNOYANCE_STRESS_BOOST)

    def _handle_affection(self, text, attachment):
        if any(word in text for word in Settings.EMOTION_AFFECTION_WORDS):
            boost = Settings.EMOTION_AFFECTION_BASE + (attachment * Settings.EMOTION_ATTACHMENT_MULTIPLIER)
            self.modify("affection", boost)
            self.modify("happy", Settings.EMOTION_AFFECTION_HAPPY_BOOST)
            self.modify("lonely", Settings.EMOTION_AFFECTION_LONELY_REDUCTION)

    def _handle_absence(self, text):
        if any(word in text for word in Settings.EMOTION_ABSENCE_WORDS):
            self.modify("lonely", Settings.EMOTION_LONELY_BOOST)

    def _handle_positive(self, text):
        if any(word in text for word in Settings.EMOTION_POSITIVE_WORDS):
            self.modify("happy", Settings.EMOTION_POSITIVE_HAPPY_BOOST)
            self.modify("energy", Settings.EMOTION_POSITIVE_ENERGY_BOOST)

    def _handle_negative(self, text):
        if any(word in text for word in Settings.EMOTION_NEGATIVE_WORDS):
            self.modify("happy", Settings.EMOTION_NEGATIVE_HAPPY_PENALTY)
            self.modify("annoyed", Settings.EMOTION_NEGATIVE_ANNOYED_BOOST)
            self.modify("stress", Settings.EMOTION_NEGATIVE_STRESS_BOOST)

    def _handle_energy(self, text):
        if any(word in text for word in Settings.EMOTION_ENERGY_WORDS):
            self.modify("energy", Settings.EMOTION_ENERGY_BOOST)
            self.modify("happy", Settings.EMOTION_ENERGY_HAPPY_BOOST)

    def _handle_trust(self, trust):
        if trust > Settings.EMOTION_TRUST_THRESHOLD:
            self.modify("stress", Settings.EMOTION_TRUST_STRESS_REDUCTION)

    def _handle_jealousy(self, text, closeness, trust):
        if not any(word in text for word in Settings.EMOTION_OTHER_AUDIENCE_WORDS):
            return
        if trust < Settings.EMOTION_JEALOUSY_TRUST_GATE:
            return
        boost = Settings.EMOTION_JEALOUSY_BOOST * (0.5 + closeness)
        self.modify("jealousy", boost)
        self.modify("happy", Settings.EMOTION_JEALOUSY_HAPPY_PENALTY)
        self.modify("stress", Settings.EMOTION_JEALOUSY_STRESS_BOOST)

    def _publish_update(self):
        self.current_profile = self._find_closest_profile(self.state)
        self.history.record(self.state.copy())

        if self.brain_graph:
            try:
                self._snapshot_counter += 1
                self.brain_graph.add_emotion_snapshot(
                    str(self._snapshot_counter),
                    self.state,
                    self.current_profile,
                    self.dominant(),
                )
            except Exception as e:
                logger.debug("[Emotion] BrainGraph snapshot: %s", e)

        if not self.event_bus:
            return
        from core.event_specs import EMOTION_CHANGED, STATE_EMOTION_CHANGED
        from core.mai_message import MaiMessage, Priority
        state_payload = {
            "dominant": self.dominant(),
            "profile": self.current_profile,
            "state": self.state.copy(),
        }
        # Async publish to avoid lock ordering deadlock (Emotion.lock -> SharedState.lock)
        # publish_event uses wait=True (sync); we use async dispatch instead.
        for event_type, payload in [
            (EMOTION_CHANGED, {"state": self.state.copy(), "dominant": self.dominant(), "profile": self.current_profile}),
            (STATE_EMOTION_CHANGED, state_payload),
        ]:
            msg = MaiMessage(
                type=event_type,
                payload=payload,
                source="cognition",
                priority=Priority.NORMAL,
            )
            self.event_bus.publish_message(msg, wait=False)

    # ==================================================
    # 📋 CURRENT PROFILE NAME
    # ==================================================

    def profile_name(self):

        with self.lock:

            return self.current_profile

    # ==================================================
    # 📋 ALL AVAILABLE PROFILES
    # ==================================================

    def available_profiles(self):

        return dict(self._profiles)

    # ==================================================
    # 🎯 PUSH TO A NAMED PROFILE
    # ==================================================

    def push_profile(self, name):

        with self.lock:

            if name not in self._profiles:
                return False

            old_state = dict(self.state)

            self.state = dict(self._profiles[name])

            self.last_update = time.time()

            self._clamp()

            self.current_profile = name

            self.history.record(self.state.copy())

            self.triggers.record("profile_push", f"pushed to {name}",
                                 self._delta(old_state), self.state)

            if self.event_bus:
                from core.event_specs import EMOTION_PROFILE_PUSHED, STATE_EMOTION_CHANGED
                from core.mai_message import publish_event
                publish_event(self.event_bus, EMOTION_PROFILE_PUSHED, {
                    "profile": name,
                    "state": self.state.copy(),
                }, source="cognition")
                publish_event(self.event_bus, STATE_EMOTION_CHANGED, {
                    "dominant": self.dominant(),
                    "profile": name,
                    "state": self.state.copy(),
                }, source="cognition")

            return True

    # ==================================================
    # 📊 EMOTION HISTORY
    # ==================================================

    def get_history(self, limit=10):
        return self.history.recent(limit)

    # ==================================================
    # 📊 EMOTION TRIGGERS
    # ==================================================

    def get_triggers(self, limit=20):
        return self.triggers.recent(limit)

    # ==================================================
    # 🔍 DELTA BETWEEN TWO STATES
    # ==================================================

    def _delta(self, old_state):
        delta = {}
        for k in self.state:
            diff = round(self.state[k] - old_state.get(k, 0), 4)
            if abs(diff) > 0.001:
                delta[k] = diff
        return delta

    # ==================================================
    # ➕ SAFE EMOTION MODIFICATION
    # ==================================================

    def modify(
        self,
        emotion,
        amount
    ):

        with self.lock:

            if emotion not in self.state:
                return

            try:

                amount = float(amount)

            except Exception as e:
                logger.warning("Emotion modify amount conversion failed: %s", e)
                return

            old_val = self.state[emotion]

            self.state[emotion] += amount

            self.triggers.record("modify", f"{emotion} += {amount}",
                                 {emotion: round(amount, 4)}, self.state)

    # ==================================================
    # 🌊 EMOTIONAL DECAY
    # ==================================================

    def _decay(self):

        with self.lock:

            now = time.time()

            elapsed = now - self.last_update

            # ==================================================
            # 🧠 PREVENT MASSIVE JUMPS
            # ==================================================

            elapsed = min(
                elapsed,
                self.max_decay_elapsed
            )

            decay_rate = min(

                elapsed
                /
                Settings.EMOTION_DECAY_INTERVAL,

                1.0
            )

            for emotion in self.state:

                baseline = self.baseline.get(

                    emotion,

                    Settings.EMOTION_MIN_VALUE
                )

                current = self.state.get(
                    emotion,
                    baseline
                )

                self.state[emotion] += (

                    (
                        baseline - current
                    )

                    *

                    self.decay_speed

                    *

                    decay_rate
                )

            self.last_update = now

            self._clamp()

    # ==================================================
    # 🔒 CLAMP VALUES
    # ==================================================

    def _clamp(self):

        with self.lock:

            for emotion in self.state:

                self.state[emotion] = max(

                    Settings.EMOTION_MIN_VALUE,

                    min(

                        Settings.EMOTION_MAX_VALUE,

                        self.state[emotion]
                    )
                )

            self._sync()

    # ==================================================
    # 🔄 SYNC TO SHARED STATE
    # ==================================================

    def _sync(self):
        """
        Mark emotion state as dirty. Does NOT acquire SharedState.lock.
        Brain._sync_emotion() is the single writer to SharedState — it pulls
        from Emotion (acquiring Emotion.lock) then writes to SharedState
        (acquiring SharedState.lock). This lock ordering (Emotion → SharedState)
        prevents deadlock with any code that acquires SharedState.lock first.
        """
        self._dirty = True

    # ==================================================
    # 🧠 DOMINANT EMOTION
    # ==================================================

    def dominant(self):
     with self.lock:
        return max(
            self.state,
            key=lambda k: self.state[k]
        )

    # ==================================================
    # 📦 EXPORT EMOTIONAL STATE
    # ==================================================

    def get(self):

        with self.lock:

            return {

                "dominant_emotion":
                    self.dominant(),

                "state":
                    self.state.copy()
            }

    # ==================================================
    # 📤 FULL EXPORT
    # ==================================================

    def export(self):

        with self.lock:

            return self.state.copy()

    # ==================================================
    # 🧠 EMOTION INFLUENCE (multipliers for subsystems)
    # ==================================================

    def influence(self, dimension):
        with self.lock:
            h = self.state.get("happy", 0.5)
            s = self.state.get("stress", 0.2)
            e = self.state.get("energy", 0.5)
            a = self.state.get("annoyed", 0.1)
            l = self.state.get("lonely", 0.3)
            af = self.state.get("affection", 0.3)

            if dimension == "retrieval":
                base = 1.0 + (h - 0.5) * 0.4 - s * 0.3 + e * 0.2
                return max(0.3, min(1.8, base))

            elif dimension == "speech_speed":
                base = 1.0 + (e - 0.5) * 0.5 - s * 0.3 - a * 0.2
                return max(0.5, min(1.5, base))

            elif dimension == "goal_priority":
                base = 1.0 + (l - 0.3) * 0.6 + (af - 0.3) * 0.4 - a * 0.3
                return max(0.5, min(2.0, base))

            elif dimension == "interrupt_tolerance":
                base = 1.0 - s * 0.4 - a * 0.3 + h * 0.2
                return max(0.2, min(1.5, base))

            elif dimension == "word_choice":
                if h > 0.6:
                    return "positive"
                elif a > 0.5 or s > 0.6:
                    return "cautious"
                elif l > 0.6:
                    return "warm"
                return "neutral"

            return 1.0

    # ==================================================
    # 🧹 RESET TO BASELINE
    # ==================================================

    def reset(self):

        with self.lock:

            self.state = (
                self.baseline.copy()
            )

            self.last_update = time.time()

            self._sync()

    # ==================================================
    # 📊 DEBUG STATS
    # ==================================================

    def stats(self):

        with self.lock:

            return {

                "dominant":
                    self.dominant(),

                "state":
                    self.state.copy(),

                "last_update":
                    self.last_update,

                "decay_speed":
                    self.decay_speed
            }