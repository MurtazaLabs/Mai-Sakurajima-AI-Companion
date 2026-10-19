# app/orchestrator.py
"""System Orchestrator — lifecycle states, crash recovery, restart policy,
and the background service registry.

Previously ``app/lifecycle.py`` was a bare boot/shutdown sequence with no
state machine and no supervision: any subsystem that died could never be
detected or restarted. The orchestrator layers a supervisor on top of the
existing lifecycle steps without changing their behavior:

- :class:`LifecycleStateMachine` — guarded, thread-safe application FSM
  (created → initializing → starting → running → recovering/restarting →
  shutting_down → stopped, with error sinks).
- :class:`ServiceRegistry` — live background-service register with per-service
  runtime metadata.
- :class:`SystemOrchestrator` — owns the FSM + registry, drives the lifecycle
  steps in ``app/lifecycle.py``, runs a background watchdog, detects crashed or
  unresponsive services via :class:`HealthRegistry`/probe callables, and applies
  a per-service :class:`RestartPolicy` with exponential backoff.

Design rules
~~~~~~~~~~~~
- The orchestrator never rewrites what builders construct; it supervises it.
- Restart policy defaults to ``NEVER`` — enabling restart for a service is an
  explicit decision requiring a ``factory`` (reconstruction callable), so
  existing boot behavior is identical unless an operator opts in.
- Recovery is graceful: a failed non-restartable service degrades the app
  (logged + flagged) instead of taking the whole process down.

See AGENTS.md → "Phase 3 — System Orchestrator".
"""
from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("Mai")


# ── Lifecycle states ────────────────────────────────────────────────

class LifecycleState(str, Enum):
    """Application-level lifecycle states (finite state machine)."""

    CREATED = "created"
    INITIALIZING = "initializing"
    STARTING = "starting"
    RUNNING = "running"
    RECOVERING = "recovering"
    RESTARTING = "restarting"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    ERROR = "error"


TERMINAL_STATES: set[LifecycleState] = {LifecycleState.STOPPED, LifecycleState.ERROR}

VALID_TRANSITIONS: dict[LifecycleState, set[LifecycleState]] = {
    LifecycleState.CREATED: {LifecycleState.INITIALIZING, LifecycleState.ERROR},
    LifecycleState.INITIALIZING: {LifecycleState.STARTING, LifecycleState.ERROR,
                                  LifecycleState.SHUTTING_DOWN},
    LifecycleState.STARTING: {LifecycleState.RUNNING, LifecycleState.ERROR,
                              LifecycleState.SHUTTING_DOWN},
    LifecycleState.RUNNING: {LifecycleState.RECOVERING, LifecycleState.RESTARTING,
                             LifecycleState.SHUTTING_DOWN, LifecycleState.ERROR},
    LifecycleState.RECOVERING: {LifecycleState.RUNNING, LifecycleState.RESTARTING,
                                LifecycleState.SHUTTING_DOWN, LifecycleState.ERROR},
    LifecycleState.RESTARTING: {LifecycleState.RUNNING, LifecycleState.RECOVERING,
                                LifecycleState.SHUTTING_DOWN, LifecycleState.ERROR},
    LifecycleState.SHUTTING_DOWN: {LifecycleState.STOPPED, LifecycleState.ERROR},
    LifecycleState.STOPPED: set(),
    LifecycleState.ERROR: set(),
}


class IllegalStateTransition(Exception):
    """Raised when a lifecycle transition is not valid for the current state."""

    def __init__(self, current, target, reason=""):
        self.current = current
        self.target = target
        super().__init__(
            f"Illegal lifecycle transition: {current.value} -> {target.value}"
            + (f" ({reason})" if reason else "")
        )


class LifecycleStateMachine:
    """Thread-safe finite state machine guarding the app lifecycle.

    Transition history is stored (bounded) for observability. Listeners can be
    registered to observe state changes (fired outside the lock).
    """

    def __init__(self, initial=LifecycleState.CREATED, history_capacity: int = 200):
        self._lock = threading.RLock()
        self._state = initial
        self._history: deque = deque(maxlen=max(1, int(history_capacity)))
        self._listeners: dict[str, Callable] = {}

    @property
    def state(self) -> LifecycleState:
        with self._lock:
            return self._state

    def can_transition(self, target: LifecycleState) -> bool:
        with self._lock:
            if target == self._state:
                return True  # idempotent re-entry is a no-op, not an error
            return target in VALID_TRANSITIONS.get(self._state, set())

    def transition(self, target: LifecycleState, reason: str = "") -> bool:
        with self._lock:
            current = self._state
            if current == target:
                logger.debug("[Orchestrator] No-op transition %s (already there)", target.value)
                return False
            allowed = VALID_TRANSITIONS.get(current, set())
            if target not in allowed:
                raise IllegalStateTransition(current, target, reason)
            self._state = target
            self._history.append({
                "from": current.value,
                "to": target.value,
                "reason": reason,
                "ts": time.time(),
            })
        self._notify(current, target, reason)
        logger.info("[Orchestrator] state: %s -> %s%s",
                    current.value, target.value,
                    f" ({reason})" if reason else "")
        return True

    def on(self, name: str, fn: Callable[[LifecycleState, LifecycleState, str], None]) -> None:
        with self._lock:
            self._listeners[name] = fn

    def off(self, name: str) -> None:
        with self._lock:
            self._listeners.pop(name, None)

    def _notify(self, previous, current, reason) -> None:
        with self._lock:
            listeners = list(self._listeners.values())
        for fn in listeners:
            try:
                fn(previous, current, reason)
            except Exception as e:
                logger.warning("[Orchestrator] transition listener failed: %s", e)

    def history(self, limit: int = 50) -> list[dict]:
        with self._lock:
            items = list(self._history)
        return list(items[-max(1, int(limit)):])


# ── Restart policy ─────────────────────────────────────────────────

class RestartPolicy(str, Enum):
    """Per-service restart policy (Docker-style semantics)."""

    NEVER = "never"           # no automatic restart — degraded but live
    ON_FAILURE = "on_failure" # restart only when the service becomes unhealthy
    ALWAYS = "always"         # restart whenever the state machine allows


# ── Transition journal (post-mortem persistence) ───────────────────

class TransitionJournal:
    """Appends lifecycle transitions to a JSONL file for post-mortem analysis.

    Thread-safe, append-only, never blocks the FSM: write failures degrade to a
    warning instead of breaking the lifecycle.
    """

    def __init__(self, path: Path | None = None, enabled: bool = True):
        self.enabled = enabled
        self._lock = threading.RLock()
        self._path = Path(path) if path else None
        self._file = None
        self._count = 0
        if enabled and self._path is not None:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._file = self._path.open("a", encoding="utf-8")
            except Exception as e:
                logger.warning("[Orchestrator] journal disabled: %s", e)
                self.enabled = False

    @property
    def path(self):
        return str(self._path) if self._path else None

    @property
    def count(self) -> int:
        with self._lock:
            return self._count

    def record(self, previous: LifecycleState, current: LifecycleState, reason: str) -> None:
        if not self.enabled or self._file is None:
            return
        with self._lock:
            try:
                self._file.write(json.dumps({
                    "from": previous.value,
                    "to": current.value,
                    "reason": reason,
                    "ts": time.time(),
                }) + "\n")
                self._file.flush()
                self._count += 1
            except Exception as e:
                logger.warning("[Orchestrator] journal write failed: %s", e)

    def close(self) -> None:
        with self._lock:
            if self._file is not None:
                try:
                    self._file.close()
                except Exception:
                    pass
                self._file = None


# ── Service registry ───────────────────────────────────────────────

@dataclass
class ManagedService:
    """A supervised background service (or supervised component)."""

    name: str
    layer: str = "Infrastructure"
    start: Callable[[], Any] | None = None
    stop: Callable[[], Any] | None = None
    health: Callable[[], bool] | None = None
    factory: Callable[[], Any] | None = None
    restart_policy: RestartPolicy = RestartPolicy.NEVER
    max_restarts: int = 3
    backoff: float = 1.0
    # runtime (mutated by the watchdog under the recovery lock)
    obj: Any = None
    state: str = "created"    # created|running|failed|restarting|stopped|terminated
    restarts: int = 0
    healthy: bool = True
    last_error: str | None = None
    window_start: float = 0.0
    started_at: float = 0.0

    def snapshot(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "layer": self.layer,
            "state": self.state,
            "restart_policy": self.restart_policy.value,
            "restarts": self.restarts,
            "max_restarts": self.max_restarts,
            "backoff": self.backoff,
            "healthy": self.healthy,
            "last_error": self.last_error,
            "started_at": self.started_at,
            "has_start": self.start is not None,
            "has_stop": self.stop is not None,
            "has_health": self.health is not None,
            "restartable": self.restart_policy != RestartPolicy.NEVER and
                           (self.factory is not None or self.start is not None),
        }


class ServiceRegistry:
    """Thread-safe register of supervised/managed services.

    Services are referenced by identity (live objects) so the watchdog can
    mutate runtime state in place; ``snapshot()`` returns immutable copies for
    observability.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._services: dict[str, ManagedService] = {}
        self._order: list[str] = []

    def register(self, svc: ManagedService, replace: bool = False) -> ManagedService:
        if not isinstance(svc, ManagedService):
            raise TypeError("Only ManagedService instances can be registered")
        with self._lock:
            if svc.name in self._services and not replace:
                raise ValueError(
                    f"Service '{svc.name}' already registered — pass replace=True"
                )
            self._services[svc.name] = svc
            if svc.name not in self._order:
                self._order.append(svc.name)
        return svc

    def unregister(self, name: str) -> None:
        with self._lock:
            self._services.pop(name, None)
            if name in self._order:
                self._order.remove(name)

    def clear(self) -> None:
        with self._lock:
            self._services.clear()
            self._order.clear()

    def has(self, name: str) -> bool:
        with self._lock:
            return name in self._services

    def get(self, name: str) -> ManagedService | None:
        with self._lock:
            return self._services.get(name)

    def names(self) -> list[str]:
        with self._lock:
            return list(self._order)

    def all(self) -> list[ManagedService]:
        """Live references to every registered service (registry-lock snapshot)."""
        with self._lock:
            return list(self._services.values())

    def snapshot(self) -> list[dict]:
        with self._lock:
            return [svc.snapshot() for svc in self._services.values()]


# ── Layer map (mirrors BOOT_ORDER / SERVICE_ATTRS) ──────────────────

APP_LAYER_MAP: list[tuple[str, str]] = [
    # Infrastructure
    ("event_bus", "Infrastructure"),
    ("shared_state", "Infrastructure"),
    ("llm", "Infrastructure"),
    ("write_journal", "Infrastructure"),
    ("event_inspector", "Infrastructure"),
    # Knowledge
    ("knowledge_graph", "Knowledge"),
    ("brain_graph", "Knowledge"),
    ("belief_engine", "Knowledge"),
    ("attention_system", "Knowledge"),
    ("graph_manager", "Knowledge"),
    ("cognitive_graph", "Knowledge"),
    ("graph_reflection", "Knowledge"),
    ("graph_reasoning", "Knowledge"),
    ("knowledge_builder", "Knowledge"),
    # Memory
    ("memory_hierarchy", "Memory"),
    ("raw_memory", "Memory"),
    ("memory_pipeline", "Memory"),
    ("memory", "Memory"),
    ("vector_store", "Memory"),
    ("retriever", "Memory"),
    # Reasoning
    ("thought_journal", "Reasoning"),
    ("reasoning_engine", "Reasoning"),
    ("reflection_engine", "Reasoning"),
    ("learning_engine", "Reasoning"),
    # Agency
    ("tool_registry", "Agency"),
    ("agent", "Agency"),
    ("goal_manager", "Agency"),
    ("procedural_memory", "Agency"),
    ("world_model", "Agency"),
    ("dream_engine", "Agency"),
    ("executor", "Agency"),
    ("safe_executor", "Agency"),
    ("personality_evolution", "Agency"),
    # Cognition
    ("brain", "Cognition"),
    ("relationship_engine", "Cognition"),
    # Voice
    ("tts", "Voice"),
    ("voice", "Voice"),
    ("stt", "Voice"),
    ("adaptive_noise", "Voice"),
    ("full_aec", "Voice"),
    ("emotion_detector", "Voice"),
    ("diarization", "Voice"),
    ("voice_manager", "Voice"),
    ("wake", "Voice"),
    ("speaker_manager", "Voice"),
    ("per_person_relationship", "Voice"),
    # Runtime
    ("kernel", "Runtime"),
    ("plugin_loader", "Runtime"),
    ("hook_registry", "Runtime"),
    ("directory_watcher", "Runtime"),
]


# ── Orchestrator ───────────────────────────────────────────────────

class SystemOrchestrator:
    """Supervisor for the whole application lifecycle.

    Drives the existing ``app/lifecycle.py`` steps while maintaining an explicit
    state machine, a background-service registry, and a watchdog that performs
    crash detection + policy-driven restart with exponential backoff.
    """

    def __init__(self, app=None, watchdog_interval: float = 5.0,
                 restart_backoff: float = 1.0, restart_max_attempts: int = 3,
                 journal_dir=None, journal_enabled: bool = True):
        self.app = app
        self.states = LifecycleStateMachine()
        self.services = ServiceRegistry()
        self.watchdog_interval = max(0.1, float(watchdog_interval))
        self.restart_backoff = max(0.1, float(restart_backoff))
        self.restart_max_attempts = max(1, int(restart_max_attempts))

        self._lock = threading.RLock()
        self._recovery_lock = threading.RLock()
        self._watchdog: threading.Thread | None = None
        self._watchdog_stop = threading.Event()
        self._watchdog_active = threading.Event()
        self._lifecycle_module = None

        self.crash_count = 0
        self.recovery_count = 0

        journal_path = Path(journal_dir) / "transitions.jsonl" if journal_dir else None
        self.journal = TransitionJournal(path=journal_path, enabled=journal_enabled)
        self.states.on("journal", self.journal.record)

    # ── Lifecycle driver ─────────────────────────────────────────

    def _lifecycle(self):
        if self._lifecycle_module is None:
            import app.lifecycle as lc
            self._lifecycle_module = lc
        return self._lifecycle_module

    def initialize(self) -> None:
        if self.states.state == LifecycleState.CREATED:
            self.states.transition(LifecycleState.INITIALIZING, "initialize()")
        try:
            self._lifecycle().initialize(self.app)
        except Exception:
            self.states.transition(LifecycleState.ERROR, "initialize() failed")
            raise
        self.states.transition(LifecycleState.STARTING, "initialize() completed")

    def start(self) -> None:
        if self.states.state == LifecycleState.CREATED:
            # Defensive: start() called without initialize() → treat as initialized
            self.states.transition(LifecycleState.INITIALIZING,
                                   "implicit init before start()")
        if self.states.state != LifecycleState.STARTING:
            self.states.transition(LifecycleState.STARTING, "start()")
        try:
            self._lifecycle().start(self.app)
        except Exception:
            self.states.transition(LifecycleState.ERROR, "start() failed")
            raise
        self.states.transition(LifecycleState.RUNNING, "start() completed")
        self.start_watchdog()

    def wait(self) -> None:
        self._lifecycle().wait(self.app)
        # Only reached when the main loop returns by itself.
        if self.states.state == LifecycleState.RUNNING:
            logger.critical(
                "[Orchestrator] Main loop exited unexpectedly (kernel stopped) — "
                "no supervisor restart; transitioning to ERROR"
            )
            self.crash_count += 1
            self.states.transition(LifecycleState.ERROR,
                                   "main loop exited without shutdown")

    def shutdown(self) -> None:
        self.stop_watchdog()
        if self.states.state in TERMINAL_STATES:
            return
        self.states.transition(LifecycleState.SHUTTING_DOWN, "shutdown()")
        try:
            self._lifecycle().shutdown(self.app)
        except Exception:
            self.states.transition(LifecycleState.ERROR, "shutdown() failed")
            raise
        self.states.transition(LifecycleState.STOPPED, "stopped")

    # ── Service registration ─────────────────────────────────────

    def register_service(self, name: str, *, layer: str = "Infrastructure",
                         start=None, stop=None, health=None, factory=None,
                         restart_policy: RestartPolicy = RestartPolicy.NEVER,
                         max_restarts: int | None = None,
                         backoff: float | None = None,
                         obj: Any = None, replace: bool = False) -> ManagedService:
        svc = ManagedService(
            name=name,
            layer=layer,
            start=start,
            stop=stop,
            health=health,
            factory=factory,
            restart_policy=restart_policy,
            max_restarts=self.restart_max_attempts if max_restarts is None else int(max_restarts),
            backoff=self.restart_backoff if backoff is None else float(backoff),
            obj=obj,
        )
        self.services.register(svc, replace=replace)
        return svc

    def register_app_services(self) -> None:
        """Auto-register the app's components as supervised services.

        Restart policy defaults to ``NEVER`` for every auto-registered service:
        this only *observes* whatever the builders already constructed. Restart
        is enabled via :meth:`configure_restart` for services with factories.
        """
        if self.app is None:
            return
        health = getattr(self.app, "health_registry", None)
        for attr_name, layer in APP_LAYER_MAP:
            obj = getattr(self.app, attr_name, None)
            if obj is None:
                continue
            svc = ManagedService(
                name=attr_name,
                layer=layer,
                obj=obj,
                start=getattr(obj, "start", None) if callable(getattr(obj, "start", None)) else None,
                stop=getattr(obj, "stop", None) if callable(getattr(obj, "stop", None)) else None,
                health=self._health_probe(health, attr_name),
            )
            self.services.register(svc)
        self._configure_restartable()

    def _service_alive(self, obj):
        probe = getattr(obj, "is_alive", None)
        return probe if callable(probe) else None

    def _configure_restartable(self) -> None:
        """Opt restartable services into ``ON_FAILURE``.

        Explicit opt-in required by design (restart never happens without a
        factory). Factories return the same live instance: ``stop()`` halts its
        thread, ``start()`` spawns a fresh one, so backends/state survive.
        """
        wj = getattr(self.app, "write_journal", None)
        if wj is not None:
            self.services.register(ManagedService(
                name="write_journal",
                layer="Infrastructure",
                obj=wj,
                start=wj.start if callable(getattr(wj, "start", None)) else None,
                stop=wj.stop if callable(getattr(wj, "stop", None)) else None,
                health=self._service_alive(wj),
                factory=lambda: wj,
                restart_policy=RestartPolicy.ON_FAILURE,
                max_restarts=self.restart_max_attempts,
                backoff=self.restart_backoff,
            ), replace=True)
        watcher = getattr(self.app, "directory_watcher", None)
        if watcher is not None:
            self.services.register(ManagedService(
                name="directory_watcher",
                layer="Runtime",
                obj=watcher,
                start=watcher.start if callable(getattr(watcher, "start", None)) else None,
                stop=watcher.stop if callable(getattr(watcher, "stop", None)) else None,
                health=self._service_alive(watcher),
                factory=lambda: watcher,
                restart_policy=RestartPolicy.ON_FAILURE,
                max_restarts=self.restart_max_attempts,
                backoff=self.restart_backoff,
            ), replace=True)

    def configure_restart(self, name: str, *, factory=None, restart_policy=RestartPolicy.ON_FAILURE,
                          max_restarts=None, backoff=None) -> ManagedService:
        """Opt a registered service into supervised restarts."""
        svc = self.services.get(name)
        if svc is None:
            raise KeyError(f"No registered service named '{name}'")
        if factory is not None:
            svc.factory = factory
        svc.restart_policy = restart_policy
        if max_restarts is not None:
            svc.max_restarts = int(max_restarts)
        if backoff is not None:
            svc.backoff = float(backoff)
        return svc

    def _health_probe(self, health, name):
        if health is None:
            return None

        def probe() -> bool:
            try:
                status = health.status(name).get("status", "unknown")
            except Exception:
                return True  # supervisor cannot reach health data → don't guess
            if status in ("ok", "warn"):
                return True
            if status in ("error", "stalled"):
                return False
            return True  # unregistered components are not supervised
        return probe

    # ── Watchdog (crash detection) ───────────────────────────────

    @property
    def watchdog_running(self) -> bool:
        return bool(self._watchdog is not None and self._watchdog.is_alive())

    def start_watchdog(self) -> None:
        with self._lock:
            if self._watchdog is not None and self._watchdog.is_alive():
                return
            self._watchdog_stop.clear()
            self._watchdog = threading.Thread(
                name="orchestrator-watchdog",
                target=self._watchdog_loop,
                daemon=True,
            )
            self._watchdog.start()
        logger.debug("[Orchestrator] watchdog started (interval %.1fs)", self.watchdog_interval)

    def stop_watchdog(self, timeout: float = 2.0) -> None:
        self._watchdog_stop.set()
        watcher = self._watchdog
        if watcher is not None and watcher is not threading.current_thread():
            watcher.join(timeout=timeout)
        with self._lock:
            self._watchdog = None

    def _watchdog_loop(self) -> None:
        self._watchdog_active.set()
        try:
            while not self._watchdog_stop.wait(self.watchdog_interval):
                try:
                    self._check()
                except Exception as e:
                    logger.warning("[Orchestrator] watchdog cycle failed: %s", e)
        finally:
            self._watchdog_active.clear()

    def _check(self) -> None:
        if self.states.state != LifecycleState.RUNNING:
            return
        health = getattr(self.app, "health_registry", None)
        if health is not None and hasattr(health, "check_stalled"):
            try:
                health.check_stalled()
            except Exception:
                pass
        restartable_failures: list[ManagedService] = []
        for svc in self.services.all():
            if svc.health is None:
                continue
            try:
                ok = bool(svc.health())
            except Exception:
                ok = False
            if not ok and svc.state != "failed":
                svc.state = "failed"
                svc.healthy = False
                svc.last_error = "health probe failed"
                logger.warning("[Orchestrator] service '%s' unhealthy", svc.name)
                if svc.restart_policy != RestartPolicy.NEVER:
                    restartable_failures.append(svc)
            elif ok and svc.state in ("failed", "terminated"):
                svc.state = "running"
                svc.healthy = True
                svc.last_error = None
        if restartable_failures:
            self.recover(services=restartable_failures,
                         reason=f"{len(restartable_failures)} service(s) unhealthy")

    # ── Recovery + restart ───────────────────────────────────────

    def recover(self, services: list[ManagedService] | None = None,
                reason: str = "crash recovery") -> dict[str, Any]:
        """Attempt policy-based recovery of failed services.

        Runs under an exclusive recovery lock. Returns ``{"recovered", "failed",
        "services"}``. Never raises; failures are recorded on the service.
        """
        with self._recovery_lock:
            if self.states.state in TERMINAL_STATES:
                return {"recovered": 0, "failed": 0, "services": [], "skipped": "terminal"}
            if self.states.can_transition(LifecycleState.RECOVERING):
                self.states.transition(LifecycleState.RECOVERING, reason)
            issues = services if services is not None else self._collect_failures()
            self.crash_count += 1
            restarted = 0
            failed = 0
            for svc in issues:
                if self._restart(svc):
                    restarted += 1
                else:
                    failed += 1
            self.recovery_count += 1
            if self.states.can_transition(LifecycleState.RUNNING):
                self.states.transition(
                    LifecycleState.RUNNING,
                    f"recovery complete (restarted={restarted}, failed={failed})",
                )
            return {
                "recovered": restarted,
                "failed": failed,
                "services": [s.name for s in issues],
            }

    def restart(self, name: str) -> bool:
        """Manually restart a single managed service. Returns success."""
        with self._recovery_lock:
            svc = self.services.get(name)
            if svc is None:
                raise KeyError(f"No registered service named '{name}'")
            return self._restart(svc)

    def _restart(self, svc: ManagedService) -> bool:
        if svc.restart_policy == RestartPolicy.NEVER:
            svc.last_error = "restart policy is NEVER"
            return False
        if svc.restarts >= svc.max_restarts:
            svc.state = "terminated"
            svc.healthy = False
            svc.last_error = f"max restarts ({svc.max_restarts}) exceeded"
            logger.error("[Orchestrator] service '%s' terminated: %s", svc.name, svc.last_error)
            return False
        if self.states.can_transition(LifecycleState.RESTARTING):
            self.states.transition(LifecycleState.RESTARTING, f"restart {svc.name}")
        attempt = svc.restarts + 1
        delay = min(30.0, svc.backoff * (2 ** (attempt - 1)))
        try:
            if svc.stop is not None:
                svc.stop()
            obj = svc.factory() if svc.factory is not None else svc.obj
            if obj is not None and obj is not svc.obj:
                # Fresh instance from factory → rebind lifecycle hooks so future
                # restarts drive the new object, not a stale reference.
                svc.obj = obj
                new_start = getattr(obj, "start", None)
                new_stop = getattr(obj, "stop", None)
                if callable(new_start):
                    svc.start = new_start
                if callable(new_stop):
                    svc.stop = new_stop
            if svc.start is not None:
                svc.start()
            svc.obj = obj if obj is not None else svc.obj
            svc.restarts += 1
            svc.healthy = True
            svc.state = "running"
            svc.last_error = None
            svc.window_start = time.time()
            svc.started_at = time.time()
            logger.info("[Orchestrator] service '%s' restarted (attempt %d/%d)",
                        svc.name, attempt, svc.max_restarts)
            return True
        except Exception as e:
            svc.restarts += 1
            svc.state = "failed"
            svc.healthy = False
            svc.last_error = str(e)
            logger.exception("[Orchestrator] restart of '%s' failed (attempt %d/%d)",
                             svc.name, attempt, svc.max_restarts)
            if attempt < svc.max_restarts:
                time.sleep(delay)
                return self._restart(svc)
            svc.state = "terminated"
            svc.last_error = f"max restarts ({svc.max_restarts}) exceeded: {e}"
            return False

    # ── Observability ────────────────────────────────────────────

    def summary(self) -> dict[str, Any]:
        health = None
        if self.app is not None and getattr(self.app, "health_registry", None) is not None:
            try:
                health = self.app.health_registry.stats()
            except Exception:
                health = None
        return {
            "state": self.states.state.value,
            "transitions": len(self.states.history(1000)),
            "crash_count": self.crash_count,
            "recovery_count": self.recovery_count,
            "watchdog": {
                "running": self.watchdog_running,
                "interval": self.watchdog_interval,
            },
            "service_count": len(self.services.names()),
            "services": self.services.snapshot(),
            "health": health,
            "journal": {
                "enabled": self.journal.enabled,
                "path": self.journal.path,
                "entries": self.journal.count,
            },
        }

    def __repr__(self):
        return f"<SystemOrchestrator state={self.states.state.value} services={len(self.services.names())}>"