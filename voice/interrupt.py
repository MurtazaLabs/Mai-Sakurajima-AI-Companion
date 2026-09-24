# Mai_ai/voice/interrupt.py
import threading
import time


class InterruptManager:

    def __init__(self):

        # 🧠 thread-safe interrupt signal
        self._event = threading.Event()

        # 🧠 metadata
        self.reason = None

        self.source = None

        self.priority = 0

        self.timestamp = None

        self.history = []

        self._lock = threading.RLock()

    # 🛑 TRIGGER INTERRUPT
    def trigger(

        self,

        reason="unknown",

        source="system",

        priority=1
    ):

        with self._lock:

            self._event.set()

            self.reason = reason

            self.source = source

            self.priority = priority

            self.timestamp = time.time()

            # 🧠 history log
            self.history.append({

                "reason":
                    reason,

                "source":
                    source,

                "priority":
                    priority,

                "timestamp":
                    self.timestamp
            })

            # 🧠 prevent infinite history growth
            self.history = self.history[-50:]

    # 🔄 RESET INTERRUPT
    def reset(self):

        with self._lock:

            self._event.clear()

            self.reason = None

            self.source = None

            self.priority = 0

            self.timestamp = None

    # ❓ CHECK INTERRUPT STATE
    def is_interrupted(self):

        with self._lock:
            return self._event.is_set()

    # 📊 DEBUG INFO
    def get_state(self):

        return {

            "interrupted":
                self.is_interrupted(),

            "reason":
                self.reason,

            "source":
                self.source,

            "priority":
                self.priority,

            "timestamp":
                self.timestamp
        }

    # 📜 RECENT INTERRUPTS
    def recent_history(
        self,
        limit=10
    ):

        return self.history[-limit:]

    # ⏳ TIME SINCE INTERRUPT
    def seconds_since_interrupt(self):
        with self._lock:
            if self.timestamp is None:
                return float("inf")
            return time.time() - self.timestamp