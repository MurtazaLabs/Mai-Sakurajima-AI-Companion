"""VaultLogger — append-only operational log for the Obsidian vault.

Part of the State-First architecture (docs/cognitive-architecture-state-first.md,
audit Step 10). `log.md` is the single append-only ledger of major vault
operations: conversations processed, reflections created, dreams completed,
maintenance runs, knowledge merged, migrations executed, statistics rebuilt.

The log is a compiler output owned by `VaultCompiler`. It is append-only — never
rewritten — so the vault carries a complete, inspectable history of cognition.
"""

import threading
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class VaultLogger:
    def __init__(self, vault_root):
        self.vault_root = Path(vault_root) if vault_root else None
        self._lock = threading.RLock()

    def _log(self, event: str, detail: str = ""):
        if not self.vault_root:
            return
        try:
            path = self.vault_root / "log.md"
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"- [{ts}] {event}"
            if detail:
                line += f" — {detail}"
            with self._lock:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
        except Exception as e:
            logger.warning("[VaultLogger] write failed: %s", e)

    # ── Event helpers (audit Step 10 vocabulary) ──

    def conversation_processed(self, detail: str = ""):
        self._log("conversation_processed", detail)

    def reflection_created(self, detail: str = ""):
        self._log("reflection_created", detail)

    def dream_completed(self, level=None, detail: str = ""):
        d = f"level={level}" if level is not None else ""
        if detail:
            d = (d + " " + detail).strip()
        self._log("dream_completed", d)

    def maintenance_run(self, detail: str = ""):
        self._log("maintenance_run", detail)

    def knowledge_merged(self, detail: str = ""):
        self._log("knowledge_merged", detail)

    def migration_executed(self, detail: str = ""):
        self._log("migration_executed", detail)

    def statistics_rebuilt(self, detail: str = ""):
        self._log("statistics_rebuilt", detail)

    def compile(self, detail: str = ""):
        self._log("vault_compiled", detail)

    def maintenance_log(self, entry: str):
        """Write a detailed entry to `maintenance/maintenance_log.md` (audit Step 8)."""
        if not self.vault_root:
            return
        try:
            from datetime import datetime
            path = self.vault_root / "maintenance" / "maintenance_log.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with self._lock:
                with open(path, "a", encoding="utf-8") as f:
                    f.write(f"- [{ts}] {entry}\n")
        except Exception as e:
            logger.warning("[VaultLogger] maintenance_log failed: %s", e)
