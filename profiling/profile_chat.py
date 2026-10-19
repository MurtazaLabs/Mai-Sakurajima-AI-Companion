"""Profile the Brain.think() hot path.

Usage:
    python profiling/profile_chat.py
    python -m cProfile -o profiling/chat_profile.prof profiling/profile_chat.py
"""

import logging
import time
import warnings

logging.basicConfig(level=logging.WARNING)
warnings.filterwarnings("ignore")

from app.builder import ApplicationBuilder

print("Building system...")
t0 = time.time()
app = ApplicationBuilder().build()
t1 = time.time()
print(f"Build: {t1 - t0:.2f}s")

brain = app.brain
messages: list[str] = [
]

print(f"\nChat hot path: {len(messages)} calls")
total = 0.0
for i, msg in enumerate(messages, 1):
    t0 = time.time()
    resp = brain.think(msg)
    t1 = time.time()
    duration = t1 - t0
    total += duration
    resp_str = str(resp)[:60]
    print(f"  [{i}] {msg:30s} -> {t1-t0:.2f}s  ({resp_str}...)")

print(f"\nAverage: {total / len(messages):.2f}s per call")
print(f"Total:   {total:.2f}s for {len(messages)} calls")
