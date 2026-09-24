"""Profile the ApplicationBuilder boot sequence.

Usage:
    python profiling/profile_boot.py
    python -m cProfile -o profiling/boot_profile.prof profiling/profile_boot.py
    python -m pstats profiling/boot_profile.prof
"""

import cProfile
import logging
import warnings
import time

logging.basicConfig(level=logging.WARNING)
warnings.filterwarnings("ignore")

from app.builder import ApplicationBuilder

t0 = time.time()
app = ApplicationBuilder().build()
t1 = time.time()

print(f"\nBoot completed in {t1 - t0:.2f}s")
print(f"Subsystems built: {len([a for a in dir(app) if not a.startswith('_')])}")
