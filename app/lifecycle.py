import logging
import os
import signal
import sys
import tempfile

from app.boot import BOOT_ORDER

logger = logging.getLogger("Mai")


def initialize(app):
    """Load persisted state, warm caches, prepare databases."""
    if app.shared_state:
        app.shared_state.load_state_from_disk()
        logger.info("[Lifecycle] SharedState loaded")


def start(app):
    """Start active services — VoiceManager, Scheduler, background workers."""
    _setup_signals(app)

    if app.voice_manager:
        app.voice_manager.start()
        logger.info("[Lifecycle] VoiceManager started")

    if app.kernel and hasattr(app.kernel, 'background_tick'):
        logger.info("[Lifecycle] Kernel background tasks active")

    if hasattr(app, 'directory_watcher') and app.directory_watcher:
        app.directory_watcher.start()
        logger.info("[Lifecycle] DirectoryWatcher started")


def wait(app):
    """Block on main loop."""
    app.kernel.run()


def shutdown(app):
    """Reverse of BOOT_ORDER — Runtime → Voice → Cognition → ... → Infrastructure."""
    logger.info("[Shutdown]")
    for layer_name, _ in reversed(BOOT_ORDER):
        _shutdown_layer(app, layer_name)
    _cleanup()
    logger.info("[Shutdown] Complete")


def _shutdown_layer(app, layer_name):
    try:
        if layer_name == "Runtime":
            if app.model_lifecycle:
                from core.model_lifecycle import shutdown_coordinator
                shutdown_coordinator()
                logger.info("  ✓ ModelLifecycleCoordinator stopped")
            if app.kernel:
                app.kernel.shutdown()
                logger.info("  ✓ Kernel stopped")
            if app.directory_watcher:
                app.directory_watcher.stop()
                logger.info("  ✓ DirectoryWatcher stopped")
        elif layer_name == "Voice":
            if app.voice:
                app.voice.stop()
                logger.info("  ✓ Voice stopped")
            if app.voice_manager:
                app.voice_manager.stop()
                logger.info("  ✓ VoiceManager stopped")
        elif layer_name == "Cognition":
            if app.brain:
                app.brain.shutdown(timeout=3.0)
                logger.info("  ✓ Brain shutdown")
        elif layer_name == "Agency":
            if app.goal_manager:
                logger.info("  ✓ Goals persisted")
        elif layer_name == "Memory":
            if app.memory:
                logger.info("  ✓ Memory persisted")
            if app.vector_store:
                logger.info("  ✓ Vector store saved")
        elif layer_name == "Infrastructure":
            if app.event_inspector:
                app.event_inspector.shutdown()
                logger.info("  ✓ EventInspector stopped")
            if app.event_bus:
                app.event_bus.shutdown(timeout=3.0)
                logger.info("  ✓ EventBus workers stopped")
            if app.write_journal:
                app.write_journal.drain()
                app.write_journal.stop(timeout=5.0)
                logger.info("  ✓ WriteJournal drained & stopped")
            if app.shared_state:
                app.shared_state.save()
                logger.info("  ✓ State saved")
    except Exception as e:
        logger.warning("  Shutdown warning (%s): %s", layer_name, e)


def _setup_signals(app):
    def _handler(sig, frame):
        try:
            app.shutdown()  # routes through the System Orchestrator (state machine)
        finally:
            sys.exit(0)

    signal.signal(signal.SIGINT, _handler)
    try:
        signal.signal(signal.SIGTERM, _handler)
    except ValueError:
        logger.warning("[Lifecycle] SIGTERM not supported on this platform — skipping")


def _cleanup():
    logger.info("[Shutdown] Cleaning up temp audio files...")
    temp_dir = tempfile.gettempdir()
    for file in os.listdir(temp_dir):
        if file.startswith("tmp_mai_") and file.endswith(".wav"):
            try:
                os.remove(os.path.join(temp_dir, file))
            except Exception as e:
                logger.debug("  Could not remove temp file: %s", e)
