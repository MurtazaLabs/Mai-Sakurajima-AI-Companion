import logging
import os
import time

import app.config_loader as cfg
from app.application import AIApplication
from app.boot import BOOT_ORDER
from app.validation import validate

logger = logging.getLogger("Mai")


class ApplicationBuilder:

    def build(self):
        app = AIApplication()
        app.boot_start = time.time()
        logger.info("[BOOT]")

        os.makedirs(str(cfg.OBSIDIAN_VAULT), exist_ok=True)

        for layer_name, build_fn in BOOT_ORDER:
            logger.info("  %s...", layer_name)
            t0 = time.perf_counter()
            build_fn(app)
            elapsed = time.perf_counter() - t0
            logger.info("    ✓ %s  (%.2fs)", layer_name, elapsed)

        if not validate(app):
            raise RuntimeError("Boot validation failed — see errors above")

        # Ensure the orchestrator exists post-build (run.py + API both use it)
        app._get_orchestrator()

        # Fresh heartbeats at boot end: components built >stall_timeout ago
        # would otherwise be falsely flagged STALLED by the supervisor.
        health = getattr(app, "health_registry", None)
        if health is not None and hasattr(health, "heartbeat_all"):
            health.heartbeat_all()

        boot_time = round(time.time() - app.boot_start, 2)
        logger.info("Ready. (%ss)", boot_time)

        return app
