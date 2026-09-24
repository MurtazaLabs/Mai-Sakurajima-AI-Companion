# core/cognition.py
import random
import time
import logging

logger = logging.getLogger("Mai.Cognition")

class Cognition:
    def __init__(self, brain, memory, state, emotion=None):
        self.brain = brain
        self.memory = memory
        self.state = state  # ✅ Connected to Centralized Cognitive Operating State
        self.emotion = emotion

        self.last_thought_time = 0
        self.current_focus = None
        self.last_thought = None

        self.cooldown = (60, 180)

    # 🧠 Main cognition loop
    def think(self, context=None):
        if context is None:
            context = {}

        if not self._can_think():
            return None

        # Memory retrieval can be thread-heavy; handled safely
        memories = self.memory.get_context()

        if not memories:
            return None

        seed = self._select_memory(memories)

        thought = self._generate_thought(seed, context)

        if not thought:
            return None

        cognition = self._build_cognition(
            thought=thought,
            memory=seed
        )

        # Apply subconscious updates atomically to global state
        self._apply_cognition_effects(cognition)

        self.last_thought = cognition
        self.last_thought_time = time.time()

        return cognition

    # ⏱️ cooldown system
    def _can_think(self):
        now = time.time()

        required = random.randint(
            self.cooldown[0],
            self.cooldown[1]
        )

        return now - self.last_thought_time > required

    # 🎯 smarter memory selection
    def _select_memory(self, memories):
        weighted = []

        for memory in memories:
            importance = memory.get("importance", 0.5)
            recency = memory.get("recency", 0.5)

            weight = importance + recency
            weighted.append((memory, weight))

        total = sum(w for _, w in weighted)

        if total <= 0:
            return random.choice(memories)

        r = random.uniform(0, total)

        upto = 0

        for memory, weight in weighted:
            if upto + weight >= r:
                return memory

            upto += weight

        return random.choice(memories)

    # 🧠 generate internal thought
    def _generate_thought(self, memory, context):
        emotion_state = self._emotion_state()

        prompt = f"""
You are generating an INTERNAL thought.

Rules:
- This is NEVER spoken to the user.
- Keep it short.
- Be introspective and emotionally grounded.
- Avoid roleplay formatting.
- Avoid dialogue quotes.
- Sound natural and subtle.

Current emotion:
{emotion_state}

Context:
{context}

Memory:
{memory}

Generate one short internal thought.
"""

        try:
            if not self.brain.llm:
                return None
            thought = self.brain.llm.generate(
                system=prompt,
                user=""
            )

            return thought.strip()

        except Exception as e:
            logger.error("[COGNITION ERROR] %s", e)
            return None

    # 🧱 structured cognition object
    def _build_cognition(self, thought, memory):
        return {
            "thought": thought,
            "focus": memory.get("topic", "general"),
            "emotion": memory.get("emotion", "neutral"),
            "importance": memory.get("importance", 0.5),
            "timestamp": time.time()
        }

    # ❤️ cognition influences emotion/memory
    def _apply_cognition_effects(self, cognition):
        emotion = cognition.get("emotion", "neutral")

        # ==================================================
        # 🔒 ATOMIC STATE MUTATION TRANSACTION
        # ==================================================
        with self.state.lock:
            updated = False
            
            if emotion == "lonely":
                if hasattr(self.state.emotion, "lonely"):
                    # Boundary protection (0.0 - 1.0)
                    self.state.emotion.lonely = max(0.0, min(1.0, self.state.emotion.lonely + 0.05))
                    updated = True
                if self.emotion and hasattr(self.emotion, "modify"):
                    self.emotion.modify("lonely", 0.05)

            elif emotion == "happy":
                if hasattr(self.state.emotion, "happy"):
                    # Boundary protection (0.0 - 1.0)
                    self.state.emotion.happy = max(0.0, min(1.0, self.state.emotion.happy + 0.03))
                    updated = True
                if self.emotion and hasattr(self.emotion, "modify"):
                    self.emotion.modify("happy", 0.03)
            
            if updated:
                logger.info("Subconscious thought shifted emotional vector. Persisting state changes.")
                self.state.save_state_to_disk()

    # 😊 emotion state helper
    def _emotion_state(self):
        # Read directly from the thread-safe shared system state 
        with self.state.lock:
            return self.state.emotion.model_dump()