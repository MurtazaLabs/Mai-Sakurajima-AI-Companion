"""Analyze chat profile — top 30 cumulative + self time."""

import pstats
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "profiling/chat_profile.prof"

p = pstats.Stats(path)

print("=" * 80)
print("TOP 30 BY CUMULATIVE TIME (chat hot path)")
print("=" * 80)
p.sort_stats("cumulative")
p.print_stats(30)

print("\n" + "=" * 80)
print("TOP 15 BY TOTAL / SELF TIME")
print("=" * 80)
p.sort_stats("time")
p.print_stats(15)
