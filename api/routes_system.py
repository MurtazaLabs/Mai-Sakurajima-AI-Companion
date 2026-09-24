"""System domain logic for the Mai API (health, plugins, about, config,
clipboard, file system bridge).

Kept as a mixin so ``MaiAPI`` can inherit these methods without changing any
call sites. See ``api.server`` for how this is composed.
"""
import logging
import re
from typing import Any, Optional
from api.errors import safe_error

logger = logging.getLogger("api.server")


class SystemMixin:
    """Health registry, plugin registry, about/configuration handlers."""

    # Set by MaiAPI at runtime — declared here for type checker
    health_registry: Any = None
    plugin_loader: Any = None
    hook_registry: Any = None
    brain: Any = None
    event_bus: Any = None
    config_manager: Any = None
    clipboard_actions: Any = None
    filesystem_actions: Any = None
    orchestrator: Any = None

    def system_orchestrator(self):
        orch = self.orchestrator
        if orch and hasattr(orch, "summary"):
            try:
                return orch.summary()
            except Exception as e:
                logger.exception("[routes_system] orchestrator summary: %s", e)
                return {"error": "orchestrator_summary_failed", "detail": safe_error(e)}
        return {"status": "unavailable"}

    def system_health(self):
        hr = self.health_registry
        if hr and hasattr(hr, "stats"):
            return hr.stats()
        return {"status": "unavailable", "components": {}, "summary": {"total": 0, "ok": 0, "warn": 0, "error": 0, "stalled": 0}}

    def system_plugins(self):
        pl = self.plugin_loader
        hr = self.hook_registry
        if pl:
            plugins = pl.list()
            hooks = hr.list_hooks() if hr and hasattr(hr, "list_hooks") else {}
            return {"plugins": plugins, "hooks": hooks}
        return {"plugins": {}, "hooks": {}}

    def system_plugin_load(self, name: str):
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            return {"error": "invalid_plugin_name"}
        if not self.plugin_loader:
            return {"error": "plugin_loader_unavailable"}
        plugin = self.plugin_loader.load(name, self.brain, self.event_bus)
        if plugin:
            return {"name": name, "status": "loaded", "initialized": plugin.initialized}
        return {"error": f"failed_to_load_{name}"}

    def system_plugin_unload(self, name: str):
        if not self.plugin_loader:
            return {"error": "plugin_loader_unavailable"}
        ok = self.plugin_loader.unload(name)
        return {"name": name, "status": "unloaded" if ok else "not_found"}

    def system_about(self):
        info = {}
        try:
            from app.config_loader import AI_NAME, AI_PERSONALITY
            info["name"] = AI_NAME
            info["personality"] = AI_PERSONALITY
        except Exception as e:
            logger.warning("[routes_system] Failed to load AI_NAME/AI_PERSONALITY: %s", e)
            info["name"] = "Mai"
            info["personality"] = "Mai Sakurajima"
        try:
            from config.settings import Settings
            s = Settings()
            keys = ["WHISPER_MODEL", "VOICE_SAMPLE_RATE", "SILENCE_THRESHOLD",
                    "KOKORO_VOICE", "KOKORO_LANG_CODE", "PORCUPINE_ENABLED", "EMBEDDING_MODEL",
                    "LLM_MODEL", "LLM_TEMPERATURE", "MEMORY_RECALL_LIMIT", "SCHEDULER_ENABLED",
                    "DEBUG_MODE", "LOG_LEVEL"]
            cfg = {}
            for k in keys:
                if hasattr(s, k):
                    cfg[k] = getattr(s, k)
            info["config"] = cfg
        except Exception as e:
            logger.exception("[System] config: %s", e)
        try:
            if self.brain and hasattr(self.brain, "state") and hasattr(self.brain.state, "runtime"):
                info["runtime"] = self.brain.state.runtime.model_dump() if hasattr(self.brain.state.runtime, "model_dump") else {}
        except Exception as e:
            logger.exception("[System] runtime: %s", e)
        return info

    def system_config_all(self):
        result = {}
        try:
            from config.settings import Settings
            s = Settings()
            cm = getattr(self, "config_manager", None)
            overrides = cm.get_all() if cm else {}

            keys = [a for a in dir(s) if not a.startswith("_")]
            for k in sorted(keys):
                v = getattr(s, k)
                if isinstance(v, (str, int, float, bool)):
                    result[k] = {"default": v, "value": overrides.get(k, v), "meta": cm.get_meta(k) if cm else {}}
        except Exception as e:
            logger.exception("[System] config_all: %s", e)
        return result

    def system_config_update(self, updates: dict):
        cm = getattr(self, "config_manager", None)
        if not cm:
            return {"error": "config_manager_unavailable"}
        updated = cm.set_many(updates)
        return {"updated": list(updated.keys()), "values": updated}

    # ── Clipboard Bridge ────────────────────────────────────────────────

    def system_clipboard_read(self):
        cb = getattr(self, "clipboard_actions", None)
        if not cb:
            return {"error": "clipboard_unavailable"}
        return cb.read()

    def system_clipboard_write(self, text: str):
        cb = getattr(self, "clipboard_actions", None)
        if not cb:
            return {"error": "clipboard_unavailable"}
        return cb.write(text)

    # ── File System Bridge ──────────────────────────────────────────────

    def system_fs_list(self, path: str):
        fs = getattr(self, "filesystem_actions", None)
        if not fs:
            return {"error": "fs_unavailable"}
        return fs.list_dir(path)

    def system_fs_read(self, path: str):
        fs = getattr(self, "filesystem_actions", None)
        if not fs:
            return {"error": "fs_unavailable"}
        return fs.read_file(path)

    def system_fs_write(self, path: str, content: str):
        fs = getattr(self, "filesystem_actions", None)
        if not fs:
            return {"error": "fs_unavailable"}
        return fs.write_file(path, content)

    # ── Model Lifecycle ───────────────────────────────────────────────────

    def model_lifecycle_summary(self):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        return ml.get_system_summary()

    def model_lifecycle_models(self):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        # This would need a way to list all model_ids from registry
        return {"models": [], "message": "Use /api/model/{model_id} for specific model"}

    def model_lifecycle_model(self, model_id: str):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        return ml.get_model_summary(model_id)

    def model_lifecycle_register(self, model_id: str, version: str, model_type: str, name: str,
                                 description: str, file_path: str, source_url: str = "",
                                 framework: str = "unknown", framework_version: str = "unknown",
                                 input_schema: dict = None, output_schema: dict = None,
                                 tags: list = None, config: dict = None):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        try:
            from core.model_lifecycle import ModelType
            mv = ml.register_model(
                model_id=model_id,
                version=version,
                model_type=ModelType(model_type),
                name=name,
                description=description,
                file_path=file_path,
                source_url=source_url,
                framework=framework,
                framework_version=framework_version,
                input_schema=input_schema or {},
                output_schema=output_schema or {},
                tags=tags or [],
                config=config or {},
            )
            return {"model_id": mv.metadata.model_id, "version": mv.metadata.version, "status": "registered"}
        except Exception as e:
            logger.exception("[model_lifecycle] register: %s", e)
            return {"error": str(e)}

    def model_lifecycle_rollout_start(self, model_id: str, version: str, strategy: str = "canary",
                                      canary_percentage: float = 5.0, canary_duration: int = 300,
                                      progressive_steps: list = None, step_duration: int = 300,
                                      error_threshold: float = 0.01, latency_threshold: float = 2.0):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        try:
            from core.model_lifecycle import RolloutStrategy
            if strategy == "canary":
                state = ml.start_canary_rollout(
                    model_id=model_id,
                    version=version,
                    canary_percentage=canary_percentage,
                    canary_duration=canary_duration,
                    progressive_steps=progressive_steps,
                    step_duration=step_duration,
                    error_threshold=error_threshold,
                    latency_threshold=latency_threshold,
                )
            elif strategy == "blue_green":
                state = ml.start_blue_green_rollout(
                    model_id=model_id,
                    version=version,
                    validation_duration=canary_duration,
                    error_threshold=error_threshold,
                    latency_threshold=latency_threshold,
                )
            elif strategy == "progressive":
                state = ml.start_progressive_rollout(
                    model_id=model_id,
                    version=version,
                    steps=progressive_steps,
                    step_duration=step_duration,
                    error_threshold=error_threshold,
                    latency_threshold=latency_threshold,
                )
            else:
                return {"error": f"unknown_strategy: {strategy}"}
            return {"model_id": model_id, "version": version, "status": "started", "phase": state.phase.value}
        except Exception as e:
            logger.exception("[model_lifecycle] rollout: %s", e)
            return {"error": str(e)}

    def model_lifecycle_rollout_status(self, model_id: str, version: str):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        state = ml.get_rollout_status(model_id, version)
        if not state:
            return {"error": "no_active_rollout"}
        return {
            "model_id": state.plan.model_id,
            "version": state.plan.version,
            "strategy": state.plan.strategy.value,
            "phase": state.phase.value,
            "current_step": state.current_step,
            "total_steps": len(state.plan.steps),
            "started_at": state.started_at,
            "updated_at": state.updated_at,
            "completed_at": state.completed_at,
            "error": state.error,
        }

    def model_lifecycle_rollout_pause(self, model_id: str, version: str):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        ml.pause_rollout(model_id, version)
        return {"status": "paused"}

    def model_lifecycle_rollout_resume(self, model_id: str, version: str):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        ml.resume_rollout(model_id, version)
        return {"status": "resumed"}

    def model_lifecycle_rollout_abort(self, model_id: str, version: str, reason: str = "Manual abort"):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        ml.abort_rollout(model_id, version, reason)
        return {"status": "aborted"}

    def model_lifecycle_rollback(self, model_id: str, version: str, reason: str = "Manual trigger"):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        ml.manual_rollback(model_id, version, reason)
        return {"status": "rolled_back"}

    def model_lifecycle_rollback_history(self, model_id: str = None, limit: int = 100):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        history = ml.get_rollback_history(model_id, limit)
        return {"events": [
            {
                "model_id": e.model_id,
                "version": e.version,
                "reason": e.reason.value,
                "trigger": e.trigger.value,
                "rule_name": e.rule_name,
                "metric_value": e.metric_value,
                "threshold": e.threshold,
                "timestamp": e.timestamp,
                "resolved": e.resolved,
            }
            for e in history
        ]}

    def model_lifecycle_promote(self, model_id: str, version: str):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        ml.promote_to_production(model_id, version)
        return {"status": "promoted", "model_id": model_id, "version": version}

    def model_lifecycle_deprecate(self, model_id: str, version: str):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        ml.deprecate_model(model_id, version)
        return {"status": "deprecated"}

    def model_lifecycle_archive(self, model_id: str, version: str):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        ml.archive_model(model_id, version)
        return {"status": "archived"}

    def model_lifecycle_metrics(self, model_id: str, version: str):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        return ml.get_model_monitoring_status(model_id)

    def model_lifecycle_verify(self, model_id: str, version: str):
        ml = getattr(self, "model_lifecycle", None)
        if not ml:
            return {"error": "model_lifecycle_unavailable"}
        verified = ml.verify_model(model_id, version)
        return {"model_id": model_id, "version": version, "verified": verified}
