"""CI gate: enforce the single-writer vault invariant.

The State-First architecture (docs/cognitive-architecture-state-first.md) mandates
that the ONLY modules permitted to write Obsidian vault markdown are:

    knowledge/vault_compiler.py   (the canonical facade)
    knowledge/obsidian_writer.py  (the underlying implementation)

Any other module that writes directly to a vault folder (e.g. via `.write_text`,
`open(..., "w")`, `.mkdir` + write) is a violation of the invariant and will cause
the folder-drift bugs this architecture was built to prevent.

Usage:
    python scripts/check_vault_writers.py
Exit code 0 = clean, 1 = violation found.
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent

# Modules permitted to perform vault writes.
ALLOWED_MODULES = {
    "knowledge/vault_compiler.py",
    "knowledge/obsidian_writer.py",
    "knowledge/vault_migrator.py",   # boot-time migration (read + safe move), not runtime
}

# Patterns that indicate a direct vault write.
WRITE_PATTERNS = (
    ".write_text(",
    'open(',                       # open(...) may be a write
    ".write(",
)

# Tokens that, when present, mean the file is clearly NOT a vault writer
# (e.g. it is reading, or writing to a non-vault path). Used to prune false hits.
NON_VAULT_HINTS = (
    "read_text",
    "def read_",
    "ObsidianReader",
)

# Files to skip entirely.
SKIP_DIRS = {"scripts", "tests", "mai_env", ".venv", "venv", "__pycache__",
             ".git", "node_modules", "docs"}
SKIP_FILES = {"check_vault_writers.py"}


def scan_file(path: Path) -> list:
    violations = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        logger.warning("[CheckVaultWriters] Failed to read file %s: %s", path, e)
        return violations
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    if rel in ALLOWED_MODULES or rel in SKIP_FILES:
        return violations
    for i, line in enumerate(lines, 1):
        if any(p in line for p in WRITE_PATTERNS):
            # Prune obvious non-writes.
            if "w" not in line and "a" not in line and ".write_text" not in line:
                continue
            if any(h in line for h in NON_VAULT_HINTS):
                continue
            # Heuristic: a vault writer touches `vault_root` / `OBSIDIAN_VAULT`
            # or one of the canonical folder names.
            if ("vault" in line.lower() or "OBSIDIAN" in line
                    or any(f'"{f}"' in line or f"'{f}'" in line
                           for f in ("conversation", "identity", "relationship",
                                     "knowledge", "graph", "people", "places",
                                     "projects", "preferences", "reflections",
                                     "dreams", "statistics",
                                     "maintenance", "archive", "important"))):
                violations.append((rel, i, line.strip()))
    return violations


def main() -> int:
    all_violations = []
    for p in ROOT.rglob("*.py"):
        parts = set(p.parts)
        if parts & SKIP_DIRS:
            continue
        all_violations.extend(scan_file(p))
    if all_violations:
        print("VAULT WRITE INVARIANT VIOLATIONS — only vault_compiler.py / "
              "obsidian_writer.py may write the vault:")
        for rel, i, line in all_violations:
            print(f"  {rel}:{i}: {line}")
        return 1
    print("OK: no direct vault writes outside the allowed writer modules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
