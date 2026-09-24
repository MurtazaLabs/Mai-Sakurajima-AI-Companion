"""
Auto-Rollback Management for Mai AI.
Monitors model health and automatically rolls back on anomalies.
"""
import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class RollbackReason(Enum):
    """Reasons for automatic rollback."""
    HIGH_ERROR_RATE = "high_error_rate"
    HIGH_LATENCY = "high_latency"
    LOW_THROUGHPUT = "low_throughput"
    HEALTH_CHECK_FAILURE = "health_check_failure"
    CUSTOM_METRIC_VIOLATION = "custom_metric_violation"
    MANUAL_TRIGGER = "manual_trigger"
    DEPENDENCY_FAILURE = "dependency_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class RollbackTrigger(Enum):
    """Trigger types for rollback evaluation."""
    IMMEDIATE = "immediate"          # Single violation triggers rollback
    WINDOWED = "windowed"            # Violations over time window
    TREND = "trend"                  # Degrading trend detected
    STATISTICAL = "statistical"      # Statistical anomaly detection


@dataclass
class RollbackRule:
    """A single rollback rule."""
    name: str
    trigger: RollbackTrigger
    reason: RollbackReason
    metric_name: str
    threshold: float
    comparison: str  # "gt", "lt", "gte", "lte", "eq", "neq"
    window_seconds: int = 60
    min_samples: int = 10
    cooldown_seconds: int = 300
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackEvent:
    """Record of a rollback event."""
    model_id: str
    version: str
    reason: RollbackReason
    trigger: RollbackTrigger
    rule_name: str
    metric_value: float
    threshold: float
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    resolved: bool = False
    resolved_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricWindow:
    """Sliding window for metric values."""
    
    def __init__(self, window_seconds: int):
        self.window_seconds = window_seconds
        self.values: deque = deque()
    
    def add(self, value: float, timestamp: float = None):
        """Add a value to the window."""
        ts = timestamp or time.time()
        self.values.append((ts, value))
        self._prune(ts)
    
    def _prune(self, current_time: float):
        """Remove old values outside window."""
        cutoff = current_time - self.window_seconds
        while self.values and self.values[0][0] < cutoff:
            self.values.popleft()
    
    def get_values(self) -> List[float]:
        """Get all values in window."""
        return [v for _, v in self.values]
    
    def get_timestamps(self) -> List[float]:
        """Get all timestamps in window."""
        return [ts for ts, _ in self.values]
    
    def count(self) -> int:
        """Get count of values in window."""
        return len(self.values)
    
    def average(self) -> Optional[float]:
        """Get average of values in window."""
        values = self.get_values()
        return sum(values) / len(values) if values else None
    
    def percentile(self, p: float) -> Optional[float]:
        """Get percentile of values in window."""
        values = sorted(self.get_values())
        if not values:
            return None
        idx = int(len(values) * p / 100)
        return values[min(idx, len(values) - 1)]
    
    def trend(self) -> Optional[float]:
        """Calculate linear trend (slope) of values."""
        values = self.get_values()
        timestamps = self.get_timestamps()
        if len(values) < 2:
            return None
        
        n = len(values)
        sum_x = sum(timestamps)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(timestamps, values))
        sum_x2 = sum(x * x for x in timestamps)
        
        if n * sum_x2 == sum_x * sum_x:
            return 0.0
        
        return (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)


class AutoRollbackManager:
    """Monitors models and automatically rolls back on anomalies."""
    
    def __init__(
        self,
        registry,
        rollout_manager,
        rules: List[RollbackRule] = None,
        check_interval: int = 30,
        notifier: Callable = None
    ):
        self.registry = registry
        self.rollout_manager = rollout_manager
        self.rules = rules or self._default_rules()
        self.check_interval = check_interval
        self.notifier = notifier
        
        self._monitored_models: Dict[str, Dict[str, MetricWindow]] = {}
        self._rollback_history: List[RollbackEvent] = []
        self._last_rollback: Dict[str, float] = {}  # model_id -> timestamp
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
    
    def _default_rules(self) -> List[RollbackRule]:
        """Create default rollback rules."""
        return [
            RollbackRule(
                name="high_error_rate",
                trigger=RollbackTrigger.WINDOWED,
                reason=RollbackReason.HIGH_ERROR_RATE,
                metric_name="error_rate",
                threshold=0.05,  # 5% error rate
                comparison="gt",
                window_seconds=60,
                min_samples=20,
                cooldown_seconds=300
            ),
            RollbackRule(
                name="critical_error_rate",
                trigger=RollbackTrigger.IMMEDIATE,
                reason=RollbackReason.HIGH_ERROR_RATE,
                metric_name="error_rate",
                threshold=0.20,  # 20% error rate = immediate
                comparison="gt",
                window_seconds=10,
                min_samples=5,
                cooldown_seconds=60
            ),
            RollbackRule(
                name="high_latency_p99",
                trigger=RollbackTrigger.WINDOWED,
                reason=RollbackReason.HIGH_LATENCY,
                metric_name="latency_p99",
                threshold=5.0,  # 5 seconds
                comparison="gt",
                window_seconds=120,
                min_samples=20,
                cooldown_seconds=300
            ),
            RollbackRule(
                name="critical_latency",
                trigger=RollbackTrigger.IMMEDIATE,
                reason=RollbackReason.HIGH_LATENCY,
                metric_name="latency_p99",
                threshold=30.0,  # 30 seconds = immediate
                comparison="gt",
                window_seconds=10,
                min_samples=3,
                cooldown_seconds=60
            ),
            RollbackRule(
                name="degrading_trend",
                trigger=RollbackTrigger.TREND,
                reason=RollbackReason.HIGH_LATENCY,
                metric_name="latency_p99",
                threshold=0.1,  # Positive slope = degrading
                comparison="gt",
                window_seconds=300,
                min_samples=30,
                cooldown_seconds=600
            ),
            RollbackRule(
                name="low_throughput",
                trigger=RollbackTrigger.WINDOWED,
                reason=RollbackReason.LOW_THROUGHPUT,
                metric_name="request_count",
                threshold=1,  # Less than 1 req/min
                comparison="lt",
                window_seconds=120,
                min_samples=5,
                cooldown_seconds=300
            ),
        ]
    
    def start_monitoring(self):
        """Start the monitoring thread."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning("Monitoring already running")
            return
        
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True
        )
        self._monitor_thread.start()
        logger.info("Auto-rollback monitoring started")
    
    def stop_monitoring(self):
        """Stop the monitoring thread."""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
        logger.info("Auto-rollback monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while not self._stop_event.is_set():
            try:
                self._check_all_models()
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            self._stop_event.wait(self.check_interval)
    
    def _check_all_models(self):
        """Check all monitored models for rollback conditions."""
        with self._lock:
            # Get all models in canary or progressive rollout
            for model_id in list(self._monitored_models.keys()):
                self._check_model(model_id)
    
    def _check_model(self, model_id: str):
        """Check a single model for rollback conditions."""
        # Get active rollout
        rollout_key = None
        for key, state in self.rollout_manager._rollouts.items():
            if key.startswith(f"{model_id}:"):
                rollout_key = key
                break
        
        if not rollout_key:
            return
        
        state = self.rollout_manager.get_rollout_state(
            model_id, rollout_key.split(":")[1]
        )
        if not state or state.phase in (RolloutPhase.COMPLETED, RolloutPhase.ROLLED_BACK, RolloutPhase.FAILED):
            return
        
        # Get current metrics
        metrics = self._collect_metrics(model_id, state.plan.version)
        if not metrics:
            return
        
        # Update metric windows
        self._update_windows(model_id, metrics)
        
        # Evaluate rules
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if self._evaluate_rule(model_id, state, rule, metrics):
                self._trigger_rollback(model_id, state, rule, metrics)
                break  # Only one rollback at a time
    
    def _collect_metrics(self, model_id: str, version: str) -> Optional[Dict[str, float]]:
        """Collect current metrics for a model."""
        # Try to get from registry
        mv = self.registry.get(model_id, version)
        if not mv:
            return None
        
        metrics = {
            "error_rate": mv.error_rate,
            "latency_p99": mv.latency_p99,
            "request_count": mv.request_count,
        }
        
        # Add custom metrics
        metrics.update(mv.metadata.metrics)
        
        return metrics
    
    def _update_windows(self, model_id: str, metrics: Dict[str, float]):
        """Update metric windows for a model."""
        if model_id not in self._monitored_models:
            self._monitored_models[model_id] = {}
        
        for metric_name, value in metrics.items():
            if metric_name not in self._monitored_models[model_id]:
                # Find window size from rules
                window_size = 300  # default
                for rule in self.rules:
                    if rule.metric_name == metric_name:
                        window_size = rule.window_seconds
                        break
                self._monitored_models[model_id][metric_name] = MetricWindow(window_size)
            
            self._monitored_models[model_id][metric_name].add(value)
    
    def _evaluate_rule(
        self,
        model_id: str,
        state: 'RolloutState',
        rule: RollbackRule,
        metrics: Dict[str, float]
    ) -> bool:
        """Evaluate a single rollback rule."""
        # Check cooldown
        last_rollback = self._last_rollback.get(f"{model_id}:{rule.name}", 0)
        if time.time() - last_rollback < rule.cooldown_seconds:
            return False
        
        # Get metric window
        window = self._monitored_models.get(model_id, {}).get(rule.metric_name)
        if not window or window.count() < rule.min_samples:
            return False
        
        # Evaluate based on trigger type
        if rule.trigger == RollbackTrigger.IMMEDIATE:
            return self._evaluate_immediate(window, rule, metrics)
        elif rule.trigger == RollbackTrigger.WINDOWED:
            return self._evaluate_windowed(window, rule)
        elif rule.trigger == RollbackTrigger.TREND:
            return self._evaluate_trend(window, rule)
        elif rule.trigger == RollbackTrigger.STATISTICAL:
            return self._evaluate_statistical(window, rule)
        
        return False
    
    def _evaluate_immediate(self, window: MetricWindow, rule: RollbackRule, metrics: Dict) -> bool:
        """Evaluate immediate trigger (latest value)."""
        current_value = metrics.get(rule.metric_name)
        if current_value is None:
            return False
        return self._compare(current_value, rule.threshold, rule.comparison)
    
    def _evaluate_windowed(self, window: MetricWindow, rule: RollbackRule) -> bool:
        """Evaluate windowed trigger (aggregated over window)."""
        avg_value = window.average()
        if avg_value is None:
            return False
        return self._compare(avg_value, rule.threshold, rule.comparison)
    
    def _evaluate_trend(self, window: MetricWindow, rule: RollbackRule) -> bool:
        """Evaluate trend trigger (degrading trend)."""
        trend = window.trend()
        if trend is None:
            return False
        return self._compare(trend, rule.threshold, rule.comparison)
    
    def _evaluate_statistical(self, window: MetricWindow, rule: RollbackRule) -> bool:
        """Evaluate statistical anomaly (using z-score)."""
        values = window.get_values()
        if len(values) < rule.min_samples:
            return False
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return False
        
        # Check if latest value is anomaly
        latest = values[-1]
        z_score = abs(latest - mean) / std_dev
        
        # Anomaly if z-score > 3 (3 sigma)
        return z_score > 3.0
    
    def _compare(self, value: float, threshold: float, comparison: str) -> bool:
        """Compare value against threshold."""
        if comparison == "gt":
            return value > threshold
        elif comparison == "gte":
            return value >= threshold
        elif comparison == "lt":
            return value < threshold
        elif comparison == "lte":
            return value <= threshold
        elif comparison == "eq":
            return abs(value - threshold) < 1e-9
        elif comparison == "neq":
            return abs(value - threshold) >= 1e-9
        return False
    
    def _trigger_rollback(self, model_id: str, state: 'RolloutState', rule: RollbackRule, metrics: Dict):
        """Trigger automatic rollback."""
        version = state.plan.version
        metric_value = metrics.get(rule.metric_name, 0)
        
        event = RollbackEvent(
            model_id=model_id,
            version=version,
            reason=rule.reason,
            trigger=rule.trigger,
            rule_name=rule.name,
            metric_value=metric_value,
            threshold=rule.threshold,
            metadata={
                "phase": state.phase.value,
                "step": state.current_step,
                "metrics": metrics
            }
        )
        
        with self._lock:
            self._rollback_history.append(event)
            self._last_rollback[f"{model_id}:{rule.name}"] = time.time()
        
        # Execute rollback
        reason_str = f"Auto-rollback: {rule.reason.value} ({rule.name}) - {rule.metric_name}={metric_value:.4f} {rule.comparison} {rule.threshold}"
        self.rollout_manager.abort_rollout(model_id, version, reason_str)
        
        # Also rollback in registry
        self.registry.update_status(model_id, version, RolloutPhase.ROLLED_BACK)
        self.registry.update_rollout(model_id, version, 0.0)
        
        self._notify(f"🚨 AUTO-ROLLBACK: {reason_str}", "error")
        logger.error(f"Auto-rollback triggered: {reason_str}")
    
    def _notify(self, message: str, level: str = "info"):
        """Send notification."""
        if self.notifier:
            try:
                self.notifier(message, level)
            except Exception as e:
                logger.warning(f"Notification failed: {e}")
    
    def add_rule(self, rule: RollbackRule):
        """Add a rollback rule."""
        with self._lock:
            self.rules.append(rule)
    
    def remove_rule(self, rule_name: str):
        """Remove a rollback rule."""
        with self._lock:
            self.rules = [r for r in self.rules if r.name != rule_name]
    
    def enable_rule(self, rule_name: str):
        """Enable a rollback rule."""
        with self._lock:
            for rule in self.rules:
                if rule.name == rule_name:
                    rule.enabled = True
                    break
    
    def disable_rule(self, rule_name: str):
        """Disable a rollback rule."""
        with self._lock:
            for rule in self.rules:
                if rule.name == rule_name:
                    rule.enabled = False
                    break
    
    def get_rollback_history(self, model_id: str = None, limit: int = 100) -> List[RollbackEvent]:
        """Get rollback history."""
        with self._lock:
            history = self._rollback_history
            if model_id:
                history = [e for e in history if e.model_id == model_id]
            return history[-limit:]
    
    def get_model_status(self, model_id: str) -> Dict[str, Any]:
        """Get monitoring status for a model."""
        with self._lock:
            windows = self._monitored_models.get(model_id, {})
            return {
                "model_id": model_id,
                "monitored_metrics": list(windows.keys()),
                "metric_windows": {
                    name: {
                        "count": w.count(),
                        "average": w.average(),
                        "latest": w.get_values()[-1] if w.get_values() else None,
                        "trend": w.trend()
                    }
                    for name, w in windows.items()
                },
                "recent_rollbacks": len([
                    e for e in self._rollback_history 
                    if e.model_id == model_id and 
                    (datetime.utcnow() - datetime.fromisoformat(e.timestamp)).total_seconds() < 86400
                ])
            }
    
    def manual_rollback(self, model_id: str, version: str, reason: str = "Manual trigger"):
        """Manually trigger rollback."""
        rollout_key = f"{model_id}:{version}"
        state = self.rollout_manager.get_rollout_state(model_id, version)
        
        if state:
            event = RollbackEvent(
                model_id=model_id,
                version=version,
                reason=RollbackReason.MANUAL_TRIGGER,
                trigger=RollbackTrigger.IMMEDIATE,
                rule_name="manual",
                metric_value=0,
                threshold=0,
                metadata={"reason": reason}
            )
            
            with self._lock:
                self._rollback_history.append(event)
            
            self.rollout_manager.abort_rollout(model_id, version, reason)
            self.registry.update_status(model_id, version, RolloutPhase.ROLLED_BACK)
            self.registry.update_rollout(model_id, version, 0.0)
            
            self._notify(f"🔴 MANUAL ROLLBACK: {model_id}:{version} - {reason}", "warning")
            logger.warning(f"Manual rollback: {model_id}:{version} - {reason}")


def create_default_rollback_manager(registry, rollout_manager) -> AutoRollbackManager:
    """Create auto-rollback manager with default configuration."""
    
    def default_notifier(message: str, level: str):
        logger.log(
            logging.INFO if level == "info" else 
            logging.WARNING if level == "warning" else 
            logging.ERROR,
            message
        )
    
    return AutoRollbackManager(
        registry=registry,
        rollout_manager=rollout_manager,
        notifier=default_notifier
    )