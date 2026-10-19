"""
Model Lifecycle Management for Mai AI.
Provides versioning, fingerprinting, gradual rollout, and auto-rollback capabilities.
"""
from .coordinator import (
    ModelLifecycleCoordinator,
    get_coordinator,
    init_coordinator,
    shutdown_coordinator,
)
from .fingerprinting import (
    ModelFingerprinter,
    compute_model_fingerprint,
    get_fingerprint_cached,
    verify_fingerprint,
)
from .model_registry import (
    ModelMetadata,
    ModelRegistry,
    ModelStatus,
    ModelType,
    ModelVersion,
    get_registry,
    init_registry,
)
from .rollback import (
    AutoRollbackManager,
    RollbackEvent,
    RollbackReason,
    RollbackRule,
    RollbackTrigger,
    create_default_rollback_manager,
)
from .rollout import (
    RolloutManager,
    RolloutPhase,
    RolloutPlan,
    RolloutState,
    RolloutStrategy,
    create_default_rollout_manager,
)

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