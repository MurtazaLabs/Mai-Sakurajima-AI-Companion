"""Analyze boot profile, print top 40 cumulative time callers."""

import pstats
import sys

path = sys.argv[1] if len(sys.argv) > 1 else "profiling/boot_profile.prof"

p = pstats.Stats(path)
p.sort_stats("cumulative")

print("=" * 80)
print("TOP 40 BY CUMULATIVE TIME (boot sequence)")
print("=" * 80)
p.print_stats(40)

print("\n" + "=" * 80)
print("TOP 20 BY TOTAL TIME (self-time, no children)")
print("=" * 80)
p.sort_stats("time")
p.print_stats(20)

print("\n" + "=" * 80)
print("TOP 20 BY CALL COUNT")
print("=" * 80)
p.sort_stats("calls")
p.print_stats(20)
