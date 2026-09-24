# core/attention.py
import random
import threading
import time


class Attention:

    def __init__(self):
        self._lock = threading.RLock()

        # 🎯 current focus
        self.focus = "user"

        # 🔥 focus strength
        self.intensity = 0.8

        # 🕒 last focus switch
        self.last_shift = time.time()

        # ⏳ minimum time before switching
        self.cooldown = 5

        # 🔒 temporary lock
        self.locked_until = 0

    # 🧠 MAIN UPDATE
    def update(

        self,

        emotion=None,

        speaking=False,

        user_active=False,

        thinking=False
    ):
        with self._lock:
            now = time.time()

            # 🔒 attention lock
            if now < self.locked_until:
                return

            # ⏳ prevent jitter switching
            if now - self.last_shift < self.cooldown:
                return

            previous = self.focus

            # 🎤 user speaking
            if user_active:

                self.focus = "user"

                self.intensity = 1.0

            # 🗣️ AI speaking
            elif speaking:

                self.focus = "user"

                self.intensity = 0.9

            # 🧠 deep thinking
            elif thinking:

                self.focus = "self"

                self.intensity = 0.85

            else:

                # 🎭 emotional influence
                mood = "neutral"

                if emotion:
                    mood = emotion.get(
                        "mood",
                        "neutral"
                    )

                # ❤️ warm emotion
                if mood in [

                    "soft",

                    "subtle_warmth"
                ]:

                    bias = 0.75

                # 😠 annoyed emotion
                elif mood == "annoyed":

                    bias = 0.4

                else:

                    bias = 0.6

                # 🎲 weighted drift
                if random.random() < bias:

                    self.focus = "user"

                    self.intensity = round(

                        random.uniform(
                            0.6,
                            1.0
                        ),

                        2
                    )

                else:

                    self.focus = "self"

                    self.intensity = round(

                        random.uniform(
                            0.4,
                            0.9
                        ),

                        2
                    )

            # 🧠 update shift timer
            if self.focus != previous:

                self.last_shift = now

    # 🔒 TEMPORARY ATTENTION LOCK
    def lock(

        self,

        seconds=5,

        focus="user"
    ):
        with self._lock:
            self.focus = focus

            self.locked_until = (
                time.time() + seconds
            )

    # 📊 CURRENT STATE
    def get(self):
        with self._lock:
            return {

                "focus":
                    self.focus,

                "intensity":
                    round(self.intensity, 2)
            }

    # 🧠 DEBUG INFO
    def debug(self):
        with self._lock:
            return (

                f"[Attention] "

                f"focus={self.focus} "

                f"intensity={self.intensity}"
            )

    