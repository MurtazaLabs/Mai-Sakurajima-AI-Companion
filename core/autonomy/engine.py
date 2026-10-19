# core/autonomy/engine.py
import logging
import random
import threading
import time

logger = logging.getLogger("Mai.Autonomy")


class Autonomy:

    def __init__(
        self,
        brain,
        executor,
        memory,
        emotion=None,
        state=None
    ):
        """
        Autonomous Decision Engine for proactive agent behavior.
        
        :param state: Optional centralized thread-safe system state infrastructure.
        """
        self.brain = brain
        self.executor = executor
        self.memory = memory
        self.emotion = emotion
        
        # 🔒 Centralized Thread-Safe State Infrastructure Alignment
        self.sys_state = state

        self.enabled = True

        # 🧠 Internal reentrant thread safety lock
        self.lock = threading.RLock()

        # ⏱️ Cooldown tracking system
        self.last_action_time = 0.0
        self.current_cooldown = self._generate_cooldown()

        # 🧠 Anti-spam repeat suppression thresholds
        self.last_intent = None
        self.last_intent_time = 0.0
        self.intent_repeat_cooldown = 180

        # 📊 Renamed to avoid shadowing/conflicting with the central 'state' object
        self.runtime_stats = {
            "actions_taken": 0,
            "last_action": None,
            "started_at": time.time()
        }

    # ==================================================
    # 🎲 DYNAMIC COOLDOWN
    # ==================================================
    def _generate_cooldown(self):
        """Generates a random cooldown window in seconds between checks."""
        return random.randint(30, 90)

    # ==================================================
    # ⏱️ MAIN UPDATE LOOP
    # ==================================================
    def tick(self, context=None):
        """
        Evaluates system context and emotional parameters to determine 
        if a proactive autonomous action should be fired.
        """
        with self.lock:
            try:
                if not self.enabled:
                    return None

                # Defensive type normalization for incoming context dicts
                if context is None or not isinstance(context, dict):
                    context = {}

                now = time.time()

                # ⏱️ Core cooldown guard block
                elapsed = now - self.last_action_time
                if elapsed < self.current_cooldown:
                    return None

                # 🧠 Evaluate rules engine
                action = self._decide(context)
                if not action:
                    return None

                # 🚫 Repetition and spam mitigation block
                intent = action.get("intent")
                if (
                    intent == self.last_intent
                    and now - self.last_intent_time < self.intent_repeat_cooldown
                ):
                    return None

                # ✅ Commit updates to the localized metric state
                self.last_action_time = now
                self.current_cooldown = self._generate_cooldown()
                self.last_intent = intent
                self.last_intent_time = now

                self.runtime_stats["actions_taken"] += 1
                self.runtime_stats["last_action"] = action

                return action

            except Exception as e:
                logger.exception("Autonomy tick failed: %s", e)
                return None

    # ==================================================
    # 🧠 DECISION ENGINE
    # ==================================================
    def _decide(self, context):
        """Evaluates relationship parameters and moods to generate intents."""
        relationship = self._get_relationship_state()
        emotion = self._get_emotion_state()

        # Safely extract contextual cross-thread values with reliable fallbacks
        user_active = bool(context.get("user_active", True))
        time_of_day = str(context.get("time_of_day", "day")).lower()
        conversation_length = int(context.get("conversation_length", 0))

        # ==================================================
        # PRIORITY 1 — LONELINESS
        # ==================================================
        if emotion["lonely"] > 0.75 and not user_active:
            return self._build_action(
                intent="seek_attention",
                emotion="lonely",
                priority=10
            )

        # ==================================================
        # PRIORITY 2 — RELATIONSHIP CHECK-IN
        # ==================================================
        if relationship["closeness"] > 0.8 and conversation_length > 3:
            if random.random() < 0.35:
                return self._build_action(
                    intent="gentle_checkin",
                    emotion="warm",
                    priority=7
                )

        # ==================================================
        # PRIORITY 3 — NIGHT PRESENCE
        # ==================================================
        if time_of_day == "night":
            if random.random() < 0.25:
                return self._build_action(
                    intent="soft_presence",
                    emotion="calm",
                    priority=5
                )

        # ==================================================
        # PRIORITY 4 — PLAYFULNESS
        # ==================================================
        if relationship["attachment"] > 0.65 and emotion["happy"] > 0.5:
            if random.random() < 0.15:
                return self._build_action(
                    intent="playful_tease",
                    emotion="playful",
                    priority=4
                )

        return None

    # ==================================================
    # 🏗️ ACTION BUILDER
    # ==================================================
    def _build_action(self, intent, emotion, priority):
        """Constructs standardized schema payloads for execution loops."""
        return {
            "type": "autonomous_action",
            "intent": str(intent),
            "emotion": str(emotion),
            "priority": int(priority),
            "timestamp": time.time()
        }

    # ==================================================
    # ❤️ RELATIONSHIP STATE
    # ==================================================
    def _get_relationship_state(self):
        """Extracts relationship data from standard or fallback storage frameworks."""
        try:
            structured = {}

            # ✅ Memory Wrapper API branch
            if hasattr(self.memory, "get_structured"):
                structured = self.memory.get_structured()
            
            # ✅ Structural Fallback Reader interface branch
            elif hasattr(self.memory, "reader"):
                reader = getattr(self.memory, "reader", None)
                if reader and hasattr(reader, "get_all"):
                    structured = reader.get_all()

            if not isinstance(structured, dict):
                structured = {}

            relationship = structured.get("relationship", {})
            if not isinstance(relationship, dict):
                relationship = {}

            # Safe float conversion utility
            def safe_float(val, default=0.0):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            return {
                "closeness": safe_float(relationship.get("closeness"), 0.0),
                "trust": safe_float(relationship.get("trust"), 0.0),
                "attachment": safe_float(relationship.get("attachment"), 0.0)
            }

        except Exception as e:
            logger.exception("Autonomy relationship state error: %s", e)
            return {"closeness": 0.0, "trust": 0.0, "attachment": 0.0}

    # ==================================================
    # 😊 EMOTIONAL STATE
    # ==================================================
    def _get_emotion_state(self):
        """Extracts runtime mood metrics safely across class/dictionary models."""
        try:
            if not self.emotion:
                return self._default_emotion()

            def safe_float(val, default=0.5):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return default

            # ✅ Active System Class Engine branch
            if hasattr(self.emotion, "get"):
                exported = self.emotion.get()

                if isinstance(exported, dict) and "state" in exported:
                    state = exported["state"]
                    if isinstance(state, dict):
                        return {
                            "lonely": safe_float(state.get("lonely"), 0.0),
                            "happy": safe_float(state.get("happy"), 0.5),
                            "energy": safe_float(state.get("energy"), 0.5)
                        }

            # ✅ Standalone dictionary configuration branch
            if isinstance(self.emotion, dict):
                return {
                    "lonely": safe_float(self.emotion.get("lonely"), 0.0),
                    "happy": safe_float(self.emotion.get("happy"), 0.5),
                    "energy": safe_float(self.emotion.get("energy"), 0.5)
                }

            return self._default_emotion()

        except Exception as e:
            logger.exception("Autonomy emotion state error: %s", e)
            return self._default_emotion()

    # ==================================================
    # 🛡️ DEFAULT EMOTION
    # ==================================================
    def _default_emotion(self):
        return {"lonely": 0.0, "happy": 0.5, "energy": 0.5}

    # ==================================================
    # ⚙️ ENABLE / DISABLE
    # ==================================================
    def enable(self):
        with self.lock:
            self.enabled = True

    def disable(self):
        with self.lock:
            self.enabled = False

    # ==================================================
    # 📊 DEBUG STATS
    # ==================================================
    def stats(self):
        """Gathers system operations metrics safely."""
        with self.lock:
            uptime = round(
                time.time() - self.runtime_stats["started_at"], 
                2
            )
            return {
                "enabled": self.enabled,
                "actions_taken": self.runtime_stats["actions_taken"],
                "last_action": self.runtime_stats["last_action"],
                "cooldown": self.current_cooldown,
                "uptime_seconds": uptime
            }