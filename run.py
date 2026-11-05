#!/usr/bin/env python3
"""
Unified entry point for Mai AI.

Modes:
  --mode cli     (default)  Foreground CLI with interactive kernel FSM
  --mode daemon            Background daemon with tray, hotkeys, uvicorn API
  --mode api               API server only (no kernel FSM)

Usage:
  python run.py --mode cli
  python run.py --mode daemon
  python run.py --mode api
"""
import argparse
import logging
import os
import signal
import sys
import threading
import warnings
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ==================================================
# 🧠 LOGGING
# ==================================================
from app.config_loader import LOG_LEVEL

# Configure root logger with both console and rotating file handler
log_dir = Path(__file__).resolve().parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

file_handler = RotatingFileHandler(
    log_dir / "mai.log",
    maxBytes=10_000_000,  # 10 MB
    backupCount=5,
    encoding="utf-8",
)
file_handler.setLevel(LOG_LEVEL)
file_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))

console_handler = logging.StreamHandler()
console_handler.setLevel(LOG_LEVEL)
console_handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))

logging.basicConfig(
    level=LOG_LEVEL,
    handlers=[file_handler, console_handler],
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("Mai")

# ==================================================
# 🧠 SUPPRESS KNOWN HARMLESS THIRD-PARTY WARNINGS
# ==================================================
warnings.filterwarnings("ignore", message="dropout option adds dropout after all but last recurrent layer")
warnings.filterwarnings("ignore", message="torch.nn.utils.weight_norm is deprecated")
warnings.filterwarnings("ignore", message="TypedStorage is deprecated")
warnings.filterwarnings("ignore", message="Defaulting repo_id to hexgrad/Kokoro-82M")

# ==================================================
# 🚀 CONFIG VALIDATION
# ==================================================
def validate_config():
    """Validate that all required Settings attributes are present. Fail fast if missing."""
    from app.config_loader import Settings
    settings = Settings()
    required_attrs = [
        # Paths
        "ROOT_DIR", "MEMORY_DIR", "VECTOR_DB_DIR", "TEMP_AUDIO_DIR",
        "LOG_DIR", "CACHE_DIR", "OBSIDIAN_VAULT",
        # AI Identity
        "AI_NAME", "WAKE_WORD", "WAKE_WORDS", "AI_PERSONALITY",
        # LLM
        "LLM_MODEL", "LLM_TEMPERATURE", "LLM_TOP_P", "LLM_STREAM",
        "LLM_MAX_CONTEXT", "LLM_TIMEOUT", "LLM_RETRY_COUNT", "LLM_STOP_TOKENS",
        "OPENROUTER_API_KEY",
        # Memory
        "EMBEDDING_MODEL", "MEMORY_RECALL_LIMIT", "MEMORY_SIMILARITY",
        "MAX_MEMORY_RESULTS", "MEMORY_MAX_NODES", "MEMORY_MAX_LINKS",
        "MEMORY_SAVE_INTERVAL", "MEMORY_AUTOSAVE",
        # Voice
        "WHISPER_MODEL", "VOICE_SAMPLE_RATE", "SILENCE_THRESHOLD", "SILENCE_DURATION",
        "MAX_RECORDING_SECONDS", "KOKORO_VOICE", "KOKORO_LANG_CODE", "USE_CUSTOM_VOICE",
        "VOICE_COOLDOWN", "WAKE_COOLDOWN", "VOICE_RENDERER",
        # API
        "API_HOST", "API_PORT", "API_AUTH_TOKEN", "API_REQUIRE_AUTH",
        "API_RATE_LIMIT_PER_MINUTE", "API_SSL_CERTFILE", "API_SSL_KEYFILE",
        "API_JWT_SECRET", "API_JWT_ACCESS_EXPIRE_MINUTES", "API_JWT_REFRESH_EXPIRE_DAYS",
        "API_RATE_LIMIT_CHAT", "API_RATE_LIMIT_AUTH", "API_RATE_LIMIT_HEALTH",
        "API_RATE_LIMIT_INGEST", "API_RATE_LIMIT_GENERAL",
        "API_CORS_ORIGINS", "API_TRUSTED_HOSTS",
        # Logging
        "LOG_LEVEL",
    ]
    missing = []
    for attr in required_attrs:
        if not hasattr(settings, attr):
            missing.append(attr)
    if missing:
        raise RuntimeError(f"Missing required Settings attributes: {missing}")
    logger.info("Config validation passed")

# ==================================================
# 🚀 BOOTSTRAP (for API / external use)
# ==================================================
def bootstrap_system():
    logger.info("Bootstrapping Mai system...")
    validate_config()
    from app.builder import ApplicationBuilder
    app = ApplicationBuilder().build()
    return {
        "brain": app.brain, "llm": app.llm, "event_bus": app.event_bus,
        "health_registry": app.health_registry, "knowledge_graph": app.knowledge_graph,
        "brain_graph": app.brain_graph, "belief_engine": app.belief_engine,
        "vector_store": app.vector_store, "graph_manager": app.graph_manager,
        "cognitive_graph": app.cognitive_graph, "graph_reflection": app.graph_reflection,
        "graph_reasoning": app.graph_reasoning,
        "tool_registry": app.tool_registry, "agent": app.agent,
        "thought_journal": app.thought_journal, "reasoning_engine": app.reasoning_engine,
        "reflection_engine": app.reflection_engine, "learning_engine": app.learning_engine,
        "goal_manager": app.goal_manager, "procedural_memory": app.procedural_memory,
        "world_model": app.world_model, "dream_engine": app.dream_engine,
        "memory": app.memory, "memory_hierarchy": app.memory_hierarchy,
        "knowledge_builder": app.knowledge_builder,
        "voice": app.voice, "voice_manager": app.voice_manager,
        "wake": app.wake, "plugin_loader": app.plugin_loader,
        "hook_registry": app.hook_registry,
        "safe_executor": app.safe_executor,
        "event_inspector": app.event_inspector,
        "orchestrator": app.orchestrator,
        "directory_watcher": app.directory_watcher,
        "app": app,
        "lifecycle_manager": getattr(app, "lifecycle_manager", None),
        "model_lifecycle": getattr(app, "model_lifecycle", None),
    }

# ==================================================
# 🚀 MODE HANDLERS
# ==================================================
def _daemon_quit(app):
    """Tray Quit — graceful: stop subsystems (drains the WriteJournal batch
    queue, ordered teardown) before the process exits (audit Oct 25 2026)."""
    try:
        app.shutdown()
    except Exception as e:
        logger.warning("[Daemon] Graceful shutdown failed: %s", e)
    os._exit(0)


def run_cli_mode():
    """Foreground CLI with interactive kernel FSM."""
    logger.info("Starting Mai AI in CLI mode...")
    from app.builder import ApplicationBuilder
    app = ApplicationBuilder().build()
    try:
        app.initialize()
        app.start()
        app.wait()
    finally:
        app.shutdown()


def run_daemon_mode(window=True):
    """Background daemon: tray, hotkeys, kernel FSM, uvicorn API, desktop window.

    Bootstraps the system exactly once (via MaiAPI.bootstrap). The previous
    implementation built the whole application twice (two brains, two voice
    managers fighting over the mic) and never started the kernel, because
    bootstrap_system() does not return it.
    """
    logger.info("[Daemon] Starting Mai AI daemon...")

    from api.server import MaiAPI, app
    mai = MaiAPI()
    if not mai.bootstrap():
        logger.error("[Daemon] Bootstrap failed — aborting")
        sys.exit(1)

    from execution.handlers import ClipboardActions, FileSystemActions, _configure_sandbox
    mai.clipboard_actions = ClipboardActions()
    mai.filesystem_actions = FileSystemActions()
    from config.paths import OBSIDIAN_VAULT, ROOT_DIR
    _configure_sandbox(str(ROOT_DIR), str(OBSIDIAN_VAULT))

    from app.config_loader import API_HOST, API_PORT
    host = API_HOST if API_HOST in ("127.0.0.1", "localhost") else "127.0.0.1"
    port = int(API_PORT or 8000)

    # Desktop window (pywebview); degrades to tray+browser if unavailable
    app_window = None
    try:
        from native.app_window import AppWindow
        app_window = AppWindow(host=host, port=port)
    except Exception as e:
        logger.warning("[Daemon] App window unavailable: %s", e)

    # System tray — "Open Mai" focuses the desktop window when present
    try:
        from native.tray import TrayDaemon
        tray = TrayDaemon(
            host=host, port=port,
            voice_manager=mai.voice_manager, brain=mai.brain,
            on_open=app_window.show if app_window else None,
            on_quit=lambda: _daemon_quit(mai.app),
        )
        tray.start()
        logger.info("[Daemon] System tray started")
    except Exception as e:
        logger.warning("[Daemon] Tray init failed: %s", e)

    # Global hotkeys
    try:
        from native.hotkeys import HotkeyManager
        hotkeys = HotkeyManager(voice_manager=mai.voice_manager)
        hotkeys.start()
        logger.info("[Daemon] Global hotkeys started")
    except Exception as e:
        logger.warning("[Daemon] Hotkeys init failed: %s", e)

    # Kernel wake/greeting FSM in background tick mode
    if mai.kernel:
        try:
            mai.kernel.background_start(tick_interval=0.5)
            logger.info("[Daemon] Kernel background FSM started")
        except Exception as e:
            logger.warning("[Daemon] Kernel start failed: %s", e)
    else:
        logger.warning("[Daemon] No kernel attached — wake/greeting FSM disabled")

    # Health monitor (logs failures/recovery)
    try:
        from native.watchdog import HealthMonitor
        monitor = HealthMonitor(host="127.0.0.1", port=port)
        monitor.start()
    except Exception as e:
        logger.warning("[Daemon] Health monitor init failed: %s", e)

    logger.info("[Daemon] Serving on %s:%s", host, port)

    def _serve():
        import uvicorn
        try:
            uvicorn.run(app, host=host, port=port)
        except Exception as e:
            logger.error("[Daemon] Uvicorn crashed: %s", e)

    server_thread = threading.Thread(target=_serve, daemon=True, name="api-server")
    server_thread.start()

    if window and app_window is not None:
        import time as _time
        import urllib.request as _urlrequest
        for _ in range(240):  # up to ~120s — first boot loads models slowly
            try:
                _urlrequest.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=2)
                break
            except Exception:
                _time.sleep(0.5)
        logger.info("[Daemon] Opening desktop window")
        app_window.start()  # blocks in the GUI loop; close hides to tray
        return

    # No window (or pywebview missing): stay alive until tray quit
    import time
    while True:
        time.sleep(3600)


def run_api_mode():
    """API server only, no kernel FSM."""
    logger.info("[API] Starting Mai AI API server only...")
    import uvicorn

    from api.server import MaiAPI, app
    from app.config_loader import API_HOST, API_PORT

    mai = MaiAPI()
    mai.bootstrap()

    logger.info("[API] Serving on %s:%s", API_HOST or "127.0.0.1", API_PORT or 8000)
    uvicorn.run(
        app,
        host=API_HOST or "127.0.0.1",
        port=int(API_PORT or 8000),
    )

# ==================================================
# 🚀 ENTRY
# ==================================================
def main():
    parser = argparse.ArgumentParser(description="Mai AI unified entry point")
    parser.add_argument(
        "--mode",
        choices=["cli", "daemon", "api"],
        default="cli",
        help="Run mode: cli (foreground), daemon (background with tray), api (server only)"
    )
    args = parser.parse_args()

    # Graceful shutdown handler
    def _signal_handler(signum, frame):
        logger.info("Received signal %s, initiating graceful shutdown...", signum)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    if args.mode == "cli":
        run_cli_mode()
    elif args.mode == "daemon":
        run_daemon_mode()
    elif args.mode == "api":
        run_api_mode()
    else:
        logger.error("Unknown mode: %s", args.mode)
        sys.exit(1)


if __name__ == "__main__":
    main()