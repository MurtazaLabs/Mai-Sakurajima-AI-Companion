"""
Model Lifecycle Management for Mai AI.
Provides versioning, fingerprinting, gradual rollout, and auto-rollback capabilities.
"""
from .model_registry import ModelRegistry, ModelMetadata, ModelVersion, ModelStatus, ModelType, get_registry, init_registry
from .fingerprinting import ModelFingerprinter, compute_model_fingerprint, verify_fingerprint, get_fingerprint_cached
from .rollout import RolloutManager, RolloutStrategy, RolloutPhase, RolloutPlan, RolloutState, create_default_rollout_manager
from .rollback import AutoRollbackManager, RollbackTrigger, RollbackReason, RollbackRule, RollbackEvent, create_default_rollback_manager
from .coordinator import ModelLifecycleCoordinator, get_coordinator, init_coordinator, shutdown_coordinator

__all__ = [
    # Registry
    "ModelRegistry",
    "ModelMetadata", 
    "ModelVersion",
    "ModelStatus",
    "ModelType",
    "get_registry",
    "init_registry",
    
    # Fingerprinting
    "ModelFingerprinter",
    "compute_model_fingerprint",
    "verify_fingerprint",
    "get_fingerprint_cached",
    
    # Rollout
    "RolloutManager",
    "RolloutStrategy",
    "RolloutPhase",
    "RolloutPlan",
    "RolloutState",
    "create_default_rollout_manager",
    
    # Rollback
    "AutoRollbackManager",
    "RollbackTrigger",
    "RollbackReason",
    "RollbackRule",
    "RollbackEvent",
    "create_default_rollback_manager",
    
    # Coordinator
    "ModelLifecycleCoordinator",
    "get_coordinator",
    "init_coordinator",
    "shutdown_coordinator",
]