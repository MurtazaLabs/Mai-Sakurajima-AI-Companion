"""
Gradual Rollout Management for Mai AI.
Implements canary, blue-green, and progressive rollout strategies.
"""
import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RolloutStrategy(Enum):
    """Rollout strategy types."""
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    PROGRESSIVE = "progressive"
    RING = "ring"


class RolloutPhase(Enum):
    """Rollout phases."""
    PENDING = "pending"
    CANARY = "canary"
    PROGRESSIVE = "progressive"
    FULL = "full"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class RolloutStep:
    """A single step in the rollout plan."""
    phase: RolloutPhase
    percentage: float
    duration_seconds: int
    success_criteria: Dict[str, Any]
    description: str


@dataclass
class RolloutPlan:
    """Complete rollout plan."""
    model_id: str
    version: str
    strategy: RolloutStrategy
    steps: List[RolloutStep]
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RolloutState:
    """Current state of a rollout."""
    plan: RolloutPlan
    current_step: int = 0
    phase: RolloutPhase = RolloutPhase.PENDING
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class RolloutManager:
    """Manages gradual model rollouts."""
    
    def __init__(
        self,
        registry,
        metrics_collector: Callable = None,
        health_checker: Callable = None,
        notifier: Callable = None
    ):
        self.registry = registry
        self.metrics_collector = metrics_collector
        self.health_checker = health_checker
        self.notifier = notifier
        self._rollouts: Dict[str, RolloutState] = {}
        self._lock = threading.RLock()
        self._monitor_threads: Dict[str, threading.Thread] = {}
        self._stop_events: Dict[str, threading.Event] = {}
    
    def create_canary_plan(
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
        """Create a canary rollout plan."""
        if progressive_steps is None:
            progressive_steps = [10, 25, 50, 75, 100]
        
        steps = [
            RolloutStep(
                phase=RolloutPhase.CANARY,
                percentage=canary_percentage,
                duration_seconds=canary_duration,
                success_criteria={
                    "max_error_rate": error_threshold,
                    "max_latency_p99": latency_threshold,
                    "min_requests": 100
                },
                description=f"Canary deployment at {canary_percentage}%"
            )
        ]
        
        for i, pct in enumerate(progressive_steps):
            steps.append(RolloutStep(
                phase=RolloutPhase.PROGRESSIVE,
                percentage=pct,
                duration_seconds=step_duration,
                success_criteria={
                    "max_error_rate": error_threshold,
                    "max_latency_p99": latency_threshold,
                    "min_requests": 100
                },
                description=f"Progressive rollout to {pct}%"
            ))
        
        steps.append(RolloutStep(
            phase=RolloutPhase.FULL,
            percentage=100.0,
            duration_seconds=60,
            success_criteria={
                "max_error_rate": error_threshold,
                "max_latency_p99": latency_threshold
            },
            description="Full rollout complete"
        ))
        
        return RolloutPlan(
            model_id=model_id,
            version=version,
            strategy=RolloutStrategy.CANARY,
            steps=steps
        )
    
    def create_blue_green_plan(
        self,
        model_id: str,
        version: str,
        validation_duration: int = 300,
        error_threshold: float = 0.01,
        latency_threshold: float = 2.0
    ) -> RolloutPlan:
        """Create a blue-green rollout plan."""
        steps = [
            RolloutStep(
                phase=RolloutPhase.CANARY,
                percentage=0.0,
                duration_seconds=validation_duration,
                success_criteria={
                    "max_error_rate": error_threshold,
                    "max_latency_p99": latency_threshold,
                    "min_requests": 50
                },
                description="Validate green environment (0% traffic)"
            ),
            RolloutStep(
                phase=RolloutPhase.FULL,
                percentage=100.0,
                duration_seconds=60,
                success_criteria={
                    "max_error_rate": error_threshold,
                    "max_latency_p99": latency_threshold
                },
                description="Switch 100% traffic to green"
            )
        ]
        
        return RolloutPlan(
            model_id=model_id,
            version=version,
            strategy=RolloutStrategy.BLUE_GREEN,
            steps=steps
        )
    
    def create_progressive_plan(
        self,
        model_id: str,
        version: str,
        steps: List[float] = None,
        step_duration: int = 300,
        error_threshold: float = 0.01,
        latency_threshold: float = 2.0
    ) -> RolloutPlan:
        """Create a progressive rollout plan."""
        if steps is None:
            steps = [5, 10, 25, 50, 75, 100]
        
        rollout_steps = []
        for i, pct in enumerate(steps):
            phase = RolloutPhase.CANARY if i == 0 else (
                RolloutPhase.FULL if pct >= 100 else RolloutPhase.PROGRESSIVE
            )
            rollout_steps.append(RolloutStep(
                phase=phase,
                percentage=pct,
                duration_seconds=step_duration,
                success_criteria={
                    "max_error_rate": error_threshold,
                    "max_latency_p99": latency_threshold,
                    "min_requests": 100
                },
                description=f"Rollout to {pct}%"
            ))
        
        return RolloutPlan(
            model_id=model_id,
            version=version,
            strategy=RolloutStrategy.PROGRESSIVE,
            steps=rollout_steps
        )
    
    def start_rollout(self, plan: RolloutPlan) -> RolloutState:
        """Start a new rollout."""
        rollout_key = f"{plan.model_id}:{plan.version}"
        
        with self._lock:
            if rollout_key in self._rollouts:
                raise ValueError(f"Rollout already in progress for {rollout_key}")
            
            # Update registry status
            self.registry.update_status(
                plan.model_id, plan.version, 
                RolloutPhase.CANARY if plan.steps[0].phase == RolloutPhase.CANARY else RolloutPhase.PENDING
            )
            
            state = RolloutState(
                plan=plan,
                phase=RolloutPhase.PENDING,
                started_at=datetime.utcnow().isoformat(),
                updated_at=datetime.utcnow().isoformat()
            )
            
            self._rollouts[rollout_key] = state
            self._stop_events[rollout_key] = threading.Event()
            
            # Start monitoring thread
            thread = threading.Thread(
                target=self._monitor_rollout,
                args=(rollout_key,),
                daemon=True
            )
            self._monitor_threads[rollout_key] = thread
            thread.start()
            
            self._notify(f"Rollout started for {rollout_key}", "info")
            logger.info(f"Started rollout: {rollout_key}")
            
            return state
    
    def _monitor_rollout(self, rollout_key: str):
        """Monitor rollout progress."""
        stop_event = self._stop_events[rollout_key]
        
        while not stop_event.is_set():
            with self._lock:
                state = self._rollouts.get(rollout_key)
                if not state:
                    break
                
                if state.phase in (RolloutPhase.COMPLETED, RolloutPhase.ROLLED_BACK, RolloutPhase.FAILED):
                    break
                
                # Check current step
                if state.current_step >= len(state.plan.steps):
                    self._complete_rollout(rollout_key)
                    break
                
                step = state.plan.steps[state.current_step]
                
                # Update rollout percentage in registry
                self.registry.update_rollout(
                    state.plan.model_id, state.plan.version, step.percentage
                )
                
                # Collect metrics
                if self.metrics_collector:
                    try:
                        metrics = self.metrics_collector(state.plan.model_id, state.plan.version)
                        state.metrics = metrics
                    except Exception as e:
                        logger.warning(f"Failed to collect metrics: {e}")
                
                # Check success criteria
                if self._check_success_criteria(state, step):
                    # Move to next step
                    state.current_step += 1
                    state.phase = step.phase
                    state.updated_at = datetime.utcnow().isoformat()
                    
                    if state.current_step >= len(state.plan.steps):
                        self._complete_rollout(rollout_key)
                    else:
                        self._notify(
                            f"Rollout {rollout_key} advanced to step {state.current_step}: "
                            f"{state.plan.steps[state.current_step].description}",
                            "info"
                        )
                else:
                    # Check if step duration exceeded
                    step_start = self._get_step_start_time(state)
                    if step_start and (time.time() - step_start) > step.duration_seconds:
                        # Step timed out - check if we should rollback
                        if self._should_rollback(state, step):
                            self._rollback(rollout_key, "Step timeout with failed criteria")
                        else:
                            # Extend step
                            logger.warning(f"Step timeout for {rollout_key}, extending...")
            
            # Sleep before next check
            stop_event.wait(30)
    
    def _check_success_criteria(self, state: RolloutState, step: RolloutStep) -> bool:
        """Check if step success criteria are met."""
        criteria = step.success_criteria
        metrics = state.metrics
        
        # Check error rate
        if "max_error_rate" in criteria:
            error_rate = metrics.get("error_rate", 1.0)
            if error_rate > criteria["max_error_rate"]:
                logger.warning(f"Error rate {error_rate} exceeds threshold {criteria['max_error_rate']}")
                return False
        
        # Check latency
        if "max_latency_p99" in criteria:
            latency = metrics.get("latency_p99", float('inf'))
            if latency > criteria["max_latency_p99"]:
                logger.warning(f"Latency P99 {latency} exceeds threshold {criteria['max_latency_p99']}")
                return False
        
        # Check minimum requests
        if "min_requests" in criteria:
            requests = metrics.get("request_count", 0)
            if requests < criteria["min_requests"]:
                logger.info(f"Insufficient requests: {requests} < {criteria['min_requests']}")
                return False
        
        # Custom health check
        if self.health_checker:
            try:
                if not self.health_checker(state.plan.model_id, state.plan.version):
                    logger.warning("Health check failed")
                    return False
            except Exception as e:
                logger.warning(f"Health check error: {e}")
                return False
        
        return True
    
    def _should_rollback(self, state: RolloutState, step: RolloutStep) -> bool:
        """Determine if rollback should be triggered."""
        criteria = step.success_criteria
        metrics = state.metrics
        
        # Rollback on critical error rate
        if "max_error_rate" in criteria:
            error_rate = metrics.get("error_rate", 0)
            if error_rate > criteria["max_error_rate"] * 2:  # 2x threshold = critical
                return True
        
        # Rollback on critical latency
        if "max_latency_p99" in criteria:
            latency = metrics.get("latency_p99", 0)
            if latency > criteria["max_latency_p99"] * 3:  # 3x threshold = critical
                return True
        
        return False
    
    def _get_step_start_time(self, state: RolloutState) -> Optional[float]:
        """Get start time of current step."""
        # Simplified - in production would track per-step timing
        if state.started_at:
            return datetime.fromisoformat(state.started_at).timestamp()
        return None
    
    def _complete_rollout(self, rollout_key: str):
        """Mark rollout as completed."""
        with self._lock:
            state = self._rollouts.get(rollout_key)
            if not state:
                return
            
            state.phase = RolloutPhase.COMPLETED
            state.completed_at = datetime.utcnow().isoformat()
            state.updated_at = datetime.utcnow().isoformat()
            
            # Update registry to production
            self.registry.update_status(
                state.plan.model_id, state.plan.version, RolloutPhase.FULL
            )
            
            self._notify(f"Rollout completed for {rollout_key}", "success")
            logger.info(f"Rollout completed: {rollout_key}")
            
            self._cleanup_rollout(rollout_key)
    
    def _rollback(self, rollout_key: str, reason: str):
        """Rollback a rollout."""
        with self._lock:
            state = self._rollouts.get(rollout_key)
            if not state:
                return
            
            state.phase = RolloutPhase.ROLLED_BACK
            state.error = reason
            state.completed_at = datetime.utcnow().isoformat()
            state.updated_at = datetime.utcnow().isoformat()
            
            # Revert registry to previous production version
            self.registry.update_status(
                state.plan.model_id, state.plan.version, RolloutPhase.ROLLED_BACK
            )
            
            # Set rollout to 0%
            self.registry.update_rollout(state.plan.model_id, state.plan.version, 0.0)
            
            self._notify(f"Rollback triggered for {rollout_key}: {reason}", "error")
            logger.error(f"Rollback: {rollout_key} - {reason}")
            
            self._cleanup_rollout(rollout_key)
    
    def _cleanup_rollout(self, rollout_key: str):
        """Clean up rollout resources."""
        self._stop_events.pop(rollout_key, None)
        self._monitor_threads.pop(rollout_key, None)
    
    def _notify(self, message: str, level: str = "info"):
        """Send notification."""
        if self.notifier:
            try:
                self.notifier(message, level)
            except Exception as e:
                logger.warning(f"Notification failed: {e}")
    
    def get_rollout_state(self, model_id: str, version: str) -> Optional[RolloutState]:
        """Get current rollout state."""
        with self._lock:
            return self._rollouts.get(f"{model_id}:{version}")
    
    def pause_rollout(self, model_id: str, version: str):
        """Pause an in-progress rollout."""
        rollout_key = f"{model_id}:{version}"
        with self._lock:
            state = self._rollouts.get(rollout_key)
            if state and state.phase not in (RolloutPhase.COMPLETED, RolloutPhase.ROLLED_BACK, RolloutPhase.FAILED):
                # Signal monitor to pause
                self._stop_events[rollout_key].set()
                logger.info(f"Paused rollout: {rollout_key}")
    
    def resume_rollout(self, model_id: str, version: str):
        """Resume a paused rollout."""
        rollout_key = f"{model_id}:{version}"
        with self._lock:
            state = self._rollouts.get(rollout_key)
            if state and state.phase not in (RolloutPhase.COMPLETED, RolloutPhase.ROLLED_BACK, RolloutPhase.FAILED):
                self._stop_events[rollout_key].clear()
                # Restart monitoring thread
                thread = threading.Thread(
                    target=self._monitor_rollout,
                    args=(rollout_key,),
                    daemon=True
                )
                self._monitor_threads[rollout_key] = thread
                thread.start()
                logger.info(f"Resumed rollout: {rollout_key}")
    
    def abort_rollout(self, model_id: str, version: str, reason: str = "Manual abort"):
        """Abort a rollout."""
        rollout_key = f"{model_id}:{version}"
        with self._lock:
            state = self._rollouts.get(rollout_key)
            if state:
                state.phase = RolloutPhase.FAILED
                state.error = reason
                state.completed_at = datetime.utcnow().isoformat()
                self._notify(f"Rollout aborted for {rollout_key}: {reason}", "warning")
                logger.warning(f"Rollout aborted: {rollout_key} - {reason}")
                self._cleanup_rollout(rollout_key)
    
    def list_active_rollouts(self) -> List[RolloutState]:
        """List all active rollouts."""
        with self._lock:
            return [
                s for s in self._rollouts.values()
                if s.phase not in (RolloutPhase.COMPLETED, RolloutPhase.ROLLED_BACK, RolloutPhase.FAILED)
            ]


def create_default_rollout_manager(registry) -> RolloutManager:
    """Create rollout manager with default callbacks."""
    
    def default_metrics_collector(model_id: str, version: str) -> Dict[str, Any]:
        # In production, collect from Prometheus
        mv = registry.get(model_id, version)
        if mv:
            return {
                "error_rate": mv.error_rate,
                "latency_p99": mv.latency_p99,
                "request_count": mv.request_count,
            }
        return {}
    
    def default_health_checker(model_id: str, version: str) -> bool:
        # In production, check health endpoint
        return True
    
    def default_notifier(message: str, level: str):
        logger.log(
            logging.INFO if level == "info" else 
            logging.WARNING if level == "warning" else 
            logging.ERROR,
            message
        )
    
    return RolloutManager(
        registry=registry,
        metrics_collector=default_metrics_collector,
        health_checker=default_health_checker,
        notifier=default_notifier
    )