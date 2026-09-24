"""
Model Lifecycle Coordinator for Mai AI.
Integrates registry, rollout, and rollback into a unified interface.
"""
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import logging

from .model_registry import ModelRegistry, ModelMetadata, ModelVersion, ModelStatus, ModelType, get_registry
from .rollout import RolloutManager, RolloutPlan, RolloutStrategy, RolloutPhase, create_default_rollout_manager
from .rollback import AutoRollbackManager, RollbackRule, RollbackReason, RollbackTrigger, create_default_rollback_manager
from .fingerprinting import compute_model_fingerprint, verify_fingerprint

logger = logging.getLogger(__name__)


class ModelLifecycleCoordinator:
    """Unified coordinator for model lifecycle management."""
    
    def __init__(
        self,
        registry: ModelRegistry = None,
        rollout_manager: RolloutManager = None,
        rollback_manager: AutoRollbackManager = None,
        db_path: str = "data/models.db"
    ):
        self.registry = registry or get_registry(db_path)
        self.rollout_manager = rollout_manager or create_default_rollout_manager(self.registry)
        self.rollback_manager = rollback_manager or create_default_rollback_manager(
            self.registry, self.rollout_manager
        )
        self._lock = threading.RLock()
        self._initialized = False
    
    def initialize(self):
        """Initialize all components."""
        with self._lock:
            if self._initialized:
                return
            
            # Start monitoring
            self.rollback_manager.start_monitoring()
            
            self._initialized = True
            logger.info("Model lifecycle coordinator initialized")
    
    def shutdown(self):
        """Shutdown all components."""
        with self._lock:
            if not self._initialized:
                return
            
            self.rollback_manager.stop_monitoring()
            
            # Abort any active rollouts
            for state in self.rollout_manager.list_active_rollouts():
                self.rollout_manager.abort_rollout(
                    state.plan.model_id, state.plan.version, "Shutdown"
                )
            
            self._initialized = False
            logger.info("Model lifecycle coordinator shutdown")
    
    # ==================== Registry Operations ====================
    
    def register_model(
        self,
        model_id: str,
        version: str,
        model_type: ModelType,
        name: str,
        description: str,
        file_path: str,
        source_url: str = "",
        framework: str = "unknown",
        framework_version: str = "unknown",
        input_schema: Dict[str, Any] = None,
        output_schema: Dict[str, Any] = None,
        tags: List[str] = None,
        config: Dict[str, Any] = None,
    ) -> ModelVersion:
        """Register a new model version."""
        return self.registry.register(
            model_id=model_id,
            version=version,
            model_type=model_type,
            name=name,
            description=description,
            file_path=file_path,
            source_url=source_url,
            framework=framework,
            framework_version=framework_version,
            input_schema=input_schema,
            output_schema=output_schema,
            tags=tags,
            config=config,
        )
    
    def get_model(self, model_id: str, version: str) -> Optional[ModelVersion]:
        """Get a specific model version."""
        return self.registry.get(model_id, version)
    
    def get_production_model(self, model_id: str) -> Optional[ModelVersion]:
        """Get current production model."""
        return self.registry.get_production(model_id)
    
    def get_staging_model(self, model_id: str) -> Optional[ModelVersion]:
        """Get current staging model."""
        return self.registry.get_staging(model_id)
    
    def list_model_versions(self, model_id: str) -> List[ModelVersion]:
        """List all versions of a model."""
        return self.registry.list_versions(model_id)
    
    def verify_model(self, model_id: str, version: str) -> bool:
        """Verify model file matches registered fingerprint."""
        mv = self.registry.get(model_id, version)
        if not mv:
            return False
        return verify_fingerprint(mv.metadata.file_path, mv.metadata.fingerprint)
    
    # ==================== Rollout Operations ====================
    
    def start_canary_rollout(
        self,
        model_id: str,
        version: str,
        canary_percentage: float = 5.0,
        canary_duration: int = 300,
        progressive_steps: List[float] = None,
        step_duration: int = 300,
        error_threshold: float = 0.01,
        latency_threshold: float = 2.0
    ) -> RolloutPlan:
        """Start a canary rollout."""
        plan = self.rollout_manager.create_canary_plan(
            model_id=model_id,
            version=version,
            canary_percentage=canary_percentage,
            canary_duration=canary_duration,
            progressive_steps=progressive_steps,
            step_duration=step_duration,
            error_threshold=error_threshold,
            latency_threshold=latency_threshold
        )
        
        # Update registry to staging
        self.registry.update_status(model_id, version, ModelStatus.STAGING)
        
        return self.rollout_manager.start_rollout(plan)
    
    def start_blue_green_rollout(
        self,
        model_id: str,
        version: str,
        validation_duration: int = 300,
        error_threshold: float = 0.01,
        latency_threshold: float = 2.0
    ) -> RolloutPlan:
        """Start a blue-green rollout."""
        plan = self.rollout_manager.create_blue_green_plan(
            model_id=model_id,
            version=version,
            validation_duration=validation_duration,
            error_threshold=error_threshold,
            latency_threshold=latency_threshold
        )
        
        self.registry.update_status(model_id, version, ModelStatus.STAGING)
        return self.rollout_manager.start_rollout(plan)
    
    def start_progressive_rollout(
        self,
        model_id: str,
        version: str,
        steps: List[float] = None,
        step_duration: int = 300,
        error_threshold: float = 0.01,
        latency_threshold: float = 2.0
    ) -> RolloutPlan:
        """Start a progressive rollout."""
        plan = self.rollout_manager.create_progressive_plan(
            model_id=model_id,
            version=version,
            steps=steps,
            step_duration=step_duration,
            error_threshold=error_threshold,
            latency_threshold=latency_threshold
        )
        
        self.registry.update_status(model_id, version, ModelStatus.STAGING)
        return self.rollout_manager.start_rollout(plan)
    
    def get_rollout_status(self, model_id: str, version: str) -> Optional[Any]:
        """Get rollout status."""
        return self.rollout_manager.get_rollout_state(model_id, version)
    
    def pause_rollout(self, model_id: str, version: str):
        """Pause rollout."""
        self.rollout_manager.pause_rollout(model_id, version)
    
    def resume_rollout(self, model_id: str, version: str):
        """Resume rollout."""
        self.rollout_manager.resume_rollout(model_id, version)
    
    def abort_rollout(self, model_id: str, version: str, reason: str = "Manual abort"):
        """Abort rollout."""
        self.rollout_manager.abort_rollout(model_id, version, reason)
    
    def list_active_rollouts(self) -> List[Any]:
        """List all active rollouts."""
        return self.rollout_manager.list_active_rollouts()
    
    # ==================== Rollback Operations ====================
    
    def add_rollback_rule(self, rule: RollbackRule):
        """Add a rollback rule."""
        self.rollback_manager.add_rule(rule)
    
    def remove_rollback_rule(self, rule_name: str):
        """Remove a rollback rule."""
        self.rollback_manager.remove_rule(rule_name)
    
    def enable_rollback_rule(self, rule_name: str):
        """Enable a rollback rule."""
        self.rollback_manager.enable_rule(rule_name)
    
    def disable_rollback_rule(self, rule_name: str):
        """Disable a rollback rule."""
        self.rollback_manager.disable_rule(rule_name)
    
    def manual_rollback(self, model_id: str, version: str, reason: str = "Manual trigger"):
        """Manually trigger rollback."""
        self.rollback_manager.manual_rollback(model_id, version, reason)
    
    def get_rollback_history(self, model_id: str = None, limit: int = 100) -> List[Any]:
        """Get rollback history."""
        return self.rollback_manager.get_rollback_history(model_id, limit)
    
    def get_model_monitoring_status(self, model_id: str) -> Dict[str, Any]:
        """Get monitoring status for a model."""
        return self.rollback_manager.get_model_status(model_id)
    
    # ==================== Metrics & Observability ====================
    
    def record_model_metrics(
        self,
        model_id: str,
        version: str,
        error_rate: float = None,
        latency_p99: float = None,
        request_count: int = None,
        custom_metrics: Dict[str, float] = None
    ):
        """Record model metrics for monitoring."""
        self.registry.update_metrics(
            model_id, version,
            error_rate=error_rate,
            latency_p99=latency_p99,
            request_count=request_count,
            custom_metrics=custom_metrics
        )
    
    def promote_to_production(self, model_id: str, version: str):
        """Promote a model version to production."""
        # Deprecate current production
        current_prod = self.registry.get_production(model_id)
        if current_prod and current_prod.metadata.version != version:
            self.registry.deprecate(model_id, current_prod.metadata.version)
        
        # Promote new version
        self.registry.update_status(model_id, version, ModelStatus.PRODUCTION)
        self.registry.update_rollout(model_id, version, 100.0)
        
        logger.info(f"Promoted {model_id}:{version} to production")
    
    def deprecate_model(self, model_id: str, version: str):
        """Deprecate a model version."""
        self.registry.deprecate(model_id, version)
    
    def archive_model(self, model_id: str, version: str):
        """Archive a model version."""
        self.registry.archive(model_id, version)
    
    def get_model_summary(self, model_id: str) -> Dict[str, Any]:
        """Get comprehensive model summary."""
        versions = self.list_model_versions(model_id)
        production = self.get_production_model(model_id)
        staging = self.get_staging_model(model_id)
        
        active_rollout = None
        for state in self.list_active_rollouts():
            if state.plan.model_id == model_id:
                active_rollout = {
                    "version": state.plan.version,
                    "phase": state.phase.value,
                    "step": state.current_step,
                    "total_steps": len(state.plan.steps),
                    "rollout_percentage": state.plan.steps[state.current_step].percentage if state.current_step < len(state.plan.steps) else 100
                }
                break
        
        return {
            "model_id": model_id,
            "total_versions": len(versions),
            "production_version": production.metadata.version if production else None,
            "staging_version": staging.metadata.version if staging else None,
            "active_rollout": active_rollout,
            "versions": [
                {
                    "version": v.metadata.version,
                    "status": v.metadata.status.value,
                    "fingerprint": v.metadata.fingerprint[:16] + "...",
                    "created_at": v.metadata.created_at,
                    "deployed_at": v.metadata.deployed_at,
                    "error_rate": v.error_rate,
                    "latency_p99": v.latency_p99,
                    "request_count": v.request_count,
                    "rollout_percentage": v.rollout_percentage
                }
                for v in versions
            ]
        }
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Get system-wide model lifecycle summary."""
        # This would need a way to list all model_ids
        # For now, return active rollouts and recent rollbacks
        active_rollouts = self.list_active_rollouts()
        recent_rollbacks = self.rollback_manager.get_rollback_history(limit=50)
        
        return {
            "active_rollouts": len(active_rollouts),
            "rollout_details": [
                {
                    "model_id": s.plan.model_id,
                    "version": s.plan.version,
                    "strategy": s.plan.strategy.value,
                    "phase": s.phase.value,
                    "step": s.current_step,
                    "started_at": s.started_at
                }
                for s in active_rollouts
            ],
            "recent_rollbacks": len(recent_rollbacks),
            "rollback_details": [
                {
                    "model_id": e.model_id,
                    "version": e.version,
                    "reason": e.reason.value,
                    "timestamp": e.timestamp,
                    "resolved": e.resolved
                }
                for e in recent_rollbacks[:10]
            ]
        }


# Global coordinator instance
_coordinator: Optional[ModelLifecycleCoordinator] = None
_coordinator_lock = threading.Lock()


def get_coordinator(db_path: str = "data/models.db") -> ModelLifecycleCoordinator:
    """Get global model lifecycle coordinator."""
    global _coordinator
    with _coordinator_lock:
        if _coordinator is None:
            _coordinator = ModelLifecycleCoordinator(db_path=db_path)
        return _coordinator


def init_coordinator(db_path: str = "data/models.db") -> ModelLifecycleCoordinator:
    """Initialize global model lifecycle coordinator."""
    global _coordinator
    with _coordinator_lock:
        _coordinator = ModelLifecycleCoordinator(db_path=db_path)
        _coordinator.initialize()
    return _coordinator


def shutdown_coordinator():
    """Shutdown global coordinator."""
    global _coordinator
    with _coordinator_lock:
        if _coordinator:
            _coordinator.shutdown()
            _coordinator = None