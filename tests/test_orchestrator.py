"""Tests for the System Orchestrator (app/orchestrator.py).

Covers the lifecycle state machine, the service registry, crash detection via
the watchdog, restart policies with backoff + max-attempt limits, and the
AIApplication integration.
"""
import json
import threading
import time

import pytest

from app.orchestrator import (
    IllegalStateTransition,
    LifecycleState,
    LifecycleStateMachine,
    ManagedService,
    RestartPolicy,
    ServiceRegistry,
    SystemOrchestrator,
    TransitionJournal,
)
from core.write_journal import WriteJournal


class TestStateMachine:

    def test_initial_state(self):
        fsm = LifecycleStateMachine()
        assert fsm.state == LifecycleState.CREATED

    def test_happy_path_transitions(self):
        fsm = LifecycleStateMachine()
        assert fsm.transition(LifecycleState.INITIALIZING, "init")
        assert fsm.transition(LifecycleState.STARTING, "start")
        assert fsm.transition(LifecycleState.RUNNING, "ready")
        assert fsm.state == LifecycleState.RUNNING

    def test_recovery_round_trip(self):
        fsm = LifecycleStateMachine()
        for t in (LifecycleState.INITIALIZING, LifecycleState.STARTING,
                  LifecycleState.RUNNING):
            fsm.transition(t)
        fsm.transition(LifecycleState.RECOVERING, "crash")
        assert fsm.state == LifecycleState.RECOVERING
        fsm.transition(LifecycleState.RESTARTING, "restart worker")
        fsm.transition(LifecycleState.RUNNING, "recovered")
        fsm.transition(LifecycleState.SHUTTING_DOWN, "bye")
        fsm.transition(LifecycleState.STOPPED, "done")
        assert fsm.state == LifecycleState.STOPPED

    def test_illegal_transition_raises(self):
        fsm = LifecycleStateMachine()
        with pytest.raises(IllegalStateTransition):
            fsm.transition(LifecycleState.STOPPED, "skip-ahead")
        assert fsm.state == LifecycleState.CREATED

    def test_terminal_states_are_dead_ends(self):
        fsm = LifecycleStateMachine()
        for t in (LifecycleState.INITIALIZING, LifecycleState.STARTING,
                  LifecycleState.RUNNING, LifecycleState.SHUTTING_DOWN):
            fsm.transition(t)
        with pytest.raises(IllegalStateTransition):
            fsm.transition(LifecycleState.RUNNING, "must not leave stopped")
        fsm2 = LifecycleStateMachine()
        for t in (LifecycleState.INITIALIZING, LifecycleState.STARTING,
                  LifecycleState.RUNNING):
            fsm2.transition(t)
        fsm2.transition(LifecycleState.ERROR, "fatal")
        with pytest.raises(IllegalStateTransition):
            fsm2.transition(LifecycleState.RUNNING, "no revival")

    def test_same_state_noop_returns_false(self):
        fsm = LifecycleStateMachine()
        assert fsm.transition(LifecycleState.INITIALIZING)
        assert fsm.transition(LifecycleState.INITIALIZING) is False
        assert fsm.state == LifecycleState.INITIALIZING

    def test_history_recorded(self):
        fsm = LifecycleStateMachine()
        fsm.transition(LifecycleState.INITIALIZING, "reason-a")
        history = fsm.history()
        assert len(history) == 1
        assert history[0]["from"] == "created"
        assert history[0]["to"] == "initializing"
        assert history[0]["reason"] == "reason-a"

    def test_listeners_fire_on_change(self):
        fsm = LifecycleStateMachine()
        observed = []
        fsm.on("test", lambda prev, cur, reason: observed.append((prev, cur, reason)))
        fsm.transition(LifecycleState.INITIALIZING, "go")
        assert observed == [(LifecycleState.CREATED, LifecycleState.INITIALIZING, "go")]
        fsm.off("test")
        fsm.transition(LifecycleState.STARTING, "again")
        assert len(observed) == 1


class TestServiceRegistry:

    def test_register_get_snapshot(self):
        reg = ServiceRegistry()
        svc = ManagedService(name="a", layer="Runtime")
        reg.register(svc)
        assert reg.has("a")
        assert reg.get("a") is svc
        assert reg.names() == ["a"]
        snap = reg.snapshot()
        assert snap[0]["name"] == "a"
        assert snap[0]["state"] == "created"

    def test_duplicate_register_raises_unless_replace(self):
        reg = ServiceRegistry()
        reg.register(ManagedService(name="a"))
        with pytest.raises(ValueError):
            reg.register(ManagedService(name="a"))
        reg.register(ManagedService(name="a", layer="Other"), replace=True)
        assert reg.get("a").layer == "Other"

    def test_type_check(self):
        reg = ServiceRegistry()
        with pytest.raises(TypeError):
            reg.register("not-a-service")

    def test_unregister_and_clear(self):
        reg = ServiceRegistry()
        reg.register(ManagedService(name="a"))
        reg.register(ManagedService(name="b"))
        reg.unregister("a")
        assert not reg.has("a")
        assert reg.names() == ["b"]
        reg.clear()
        assert reg.names() == []

    def test_snapshot_is_a_copy_live_refs_mutate(self):
        reg = ServiceRegistry()
        reg.register(ManagedService(name="a"))
        snap = reg.snapshot()
        snap[0]["state"] = "mutated"
        assert reg.get("a").state == "created"
        reg.get("a").state = "failed"
        assert reg.snapshot()[0]["state"] == "failed"

    def test_managed_service_snapshot_flags_restartable(self):
        plain = ManagedService(name="p", restart_policy=RestartPolicy.NEVER)
        assert plain.snapshot()["restartable"] is False
        managed = ManagedService(name="m", restart_policy=RestartPolicy.ON_FAILURE,
                                 factory=lambda: object())
        assert managed.snapshot()["restartable"] is True


class _FakeService:
    """Deterministic fake background service for restart tests."""

    def __init__(self):
        self.started = 0
        self.stopped = 0

    def start(self):
        self.started += 1

    def stop(self):
        self.stopped += 1


class _Tracker:
    """Records which lifecycle methods the app components get called with."""

    def __init__(self, background_tick=False):
        self.calls = []
        self.background_tick = background_tick

    def __getattr__(self, name):
        def _record(*args, **kwargs):
            self.calls.append(name)
        return _record

    def has(self, *names):
        return all(n in self.calls for n in names)


class _FakeApp:
    """Deterministic fake application: inherits the subsystem attribute skeleton
    (all component slots = None) and fills the ones lifecycle actually drives."""

    def __init__(self):
        from app.application import AIApplication

        AIApplication.__init__(self)
        self.shared_state = _Tracker()
        self.voice_manager = _Tracker()
        self.kernel = _Tracker(background_tick=True)
        self.event_inspector = _Tracker()
        self.event_bus = _Tracker()
        self.write_journal = _Tracker()


class TestOrchestratorLifecycle:

    def test_initialize_start_shutdown_drives_fsm(self):
        app = _FakeApp()
        orch = SystemOrchestrator(app=app)
        orch.initialize()
        assert app.shared_state.has("load_state_from_disk")
        assert orch.states.state == LifecycleState.STARTING
        orch.start()
        assert app.voice_manager.has("start")
        assert orch.states.state == LifecycleState.RUNNING
        orch.shutdown()
        assert orch.states.state == LifecycleState.STOPPED
        assert app.event_bus.has("shutdown")
        assert app.voice_manager.has("stop")
        assert app.shared_state.has("save")
        assert app.write_journal.has("drain", "stop")

    def test_shutdown_is_idempotent(self):
        app = _FakeApp()
        orch = SystemOrchestrator(app=app)
        orch.initialize()
        orch.start()
        orch.shutdown()
        orch.shutdown()
        assert orch.states.state == LifecycleState.STOPPED

    def test_start_before_initialize_is_defensive(self):
        app = _FakeApp()
        orch = SystemOrchestrator(app=app)
        orch.start()
        assert orch.states.state == LifecycleState.RUNNING

    def test_initialize_failure_transitions_to_error(self):
        class FailingSharedState(_Tracker):
            def load_state_from_disk(self):
                raise RuntimeError("boom")

        app = _FakeApp()
        app.shared_state = FailingSharedState()
        orch = SystemOrchestrator(app=app)
        with pytest.raises(RuntimeError):
            orch.initialize()
        assert orch.states.state == LifecycleState.ERROR

    def test_summary_shape(self):
        app = _FakeApp()
        orch = SystemOrchestrator(app=app)
        orch.initialize()
        orch.start()
        s = orch.summary()
        assert s["state"] == "running"
        assert s["watchdog"]["running"] is True
        assert isinstance(s["services"], list)
        orch.shutdown()
        orch.stop_watchdog()


class TestRestartPolicy:

    def test_on_failure_restarts_with_backoff(self):
        orch = SystemOrchestrator(app=_FakeApp(), restart_backoff=0.01)
        svc = _FakeService()
        orch.register_service(
            "svc", obj=svc, start=svc.start, stop=svc.stop,
            restart_policy=RestartPolicy.ON_FAILURE,
        )
        assert orch.restart("svc") is True
        assert svc.started == 1
        assert svc.stopped == 1
        entry = orch.services.get("svc")
        assert entry.state == "running"
        assert entry.restarts == 1
        assert entry.started_at > 0

    def test_never_policy_does_not_restart(self):
        orch = SystemOrchestrator(app=_FakeApp())
        svc = _FakeService()
        orch.register_service(
            "svc", obj=svc, start=svc.start, stop=svc.stop,
            restart_policy=RestartPolicy.NEVER,
        )
        assert orch.restart("svc") is False
        assert svc.started == 0
        assert orch.services.get("svc").last_error == "restart policy is NEVER"

    def test_max_restarts_reached_terminates(self):
        orch = SystemOrchestrator(app=_FakeApp(), restart_backoff=0.01)
        calls = {"n": 0}

        class Flaky(_FakeService):
            def start(self):
                self.started += 1
                calls["n"] += 1
                raise RuntimeError("flaky always")

        svc = Flaky()
        orch.register_service(
            "flaky", obj=svc, start=svc.start, stop=svc.stop,
            restart_policy=RestartPolicy.ON_FAILURE,
            max_restarts=2,
        )
        assert orch.restart("flaky") is False
        assert calls["n"] == 2
        assert orch.services.get("flaky").state == "terminated"
        assert "exceeded" in orch.services.get("flaky").last_error

    def test_restart_reconstructs_via_factory(self):
        orch = SystemOrchestrator(app=_FakeApp())
        produced = []
        orch.register_service(
            "svc",
            restart_policy=RestartPolicy.ON_FAILURE,
            factory=lambda: produced.append(_FakeService()) or produced[-1],
        )
        assert orch.restart("svc") is True
        svc = orch.services.get("svc")
        assert len(produced) == 1
        assert svc.obj is produced[0]
        assert svc.state == "running"
        assert svc.restarts == 1

    def test_recover_result_counts(self):
        orch = SystemOrchestrator(app=_FakeApp(), restart_backoff=0.01)
        ok = _FakeService()
        dead = _FakeService()
        orch.register_service(
            "ok", obj=ok, start=ok.start, stop=ok.stop,
            restart_policy=RestartPolicy.ON_FAILURE,
        )
        orch.register_service(
            "dead", obj=dead, start=dead.start, stop=dead.stop,
            restart_policy=RestartPolicy.NEVER,
        )
        dead_started = dead.started
        result = orch.recover(services=[orch.services.get("ok"),
                                        orch.services.get("dead")])
        assert result["recovered"] == 1
        assert result["failed"] == 1
        assert dead.started == dead_started
        assert orch.recovery_count == 1


class TestWatchdog:

    def test_watchdog_starts_and_stops(self):
        app = _FakeApp()
        orch = SystemOrchestrator(app=app)
        orch.initialize()
        orch.start()
        assert orch.watchdog_running
        orch.stop_watchdog()
        assert not orch.watchdog_running

    def test_watchdog_detects_and_recovers(self):
        app = _FakeApp()
        orch = SystemOrchestrator(app=app, watchdog_interval=0.1)
        svc = _FakeService()
        health_flag = {"ok": False}
        orch.register_service(
            "svc", obj=svc, start=svc.start, stop=svc.stop,
            restart_policy=RestartPolicy.ON_FAILURE,
            health=lambda: health_flag["ok"], max_restarts=5,
        )
        orch.initialize()
        orch.start()
        deadline = time.time() + 5
        while time.time() < deadline and svc.started < 1:
            time.sleep(0.05)
        assert svc.started >= 1
        assert orch.crash_count >= 1
        health_flag["ok"] = True
        deadline = time.time() + 5
        while time.time() < deadline and orch.services.get("svc").state != "running":
            time.sleep(0.05)
        assert orch.services.get("svc").state == "running"
        orch.shutdown()
        orch.stop_watchdog()

    def test_watchdog_never_policy_only_degrades(self):
        app = _FakeApp()
        orch = SystemOrchestrator(app=app, watchdog_interval=0.1)
        svc = _FakeService()
        orch.register_service(
            "svc", obj=svc, start=svc.start, stop=svc.stop,
            restart_policy=RestartPolicy.NEVER,
            health=lambda: False,
        )
        orch.initialize()
        orch.start()
        deadline = time.time() + 3
        while time.time() < deadline and svc.started == 0:
            if orch.services.get("svc").state == "failed":
                break
            time.sleep(0.05)
        assert svc.started == 0
        assert orch.services.get("svc").state == "failed"
        assert orch.recovery_count == 0
        orch.shutdown()
        orch.stop_watchdog()


def test_app_registers_services_from_attributes():
    from app.application import AIApplication

    app = AIApplication()
    app.kernel = _FakeService()
    app.voice_manager = _FakeService()
    app.event_bus = object()
    orch = SystemOrchestrator(app=app)
    orch.register_app_services()
    names = orch.services.names()
    assert "kernel" in names
    assert "voice_manager" in names
    assert orch.services.get("kernel").layer == "Runtime"
    assert orch.services.get("kernel").snapshot()["restartable"] is False
    assert orch.services.get("voice_manager").layer == "Voice"


def test_ai_application_routes_through_orchestrator():
    from app.application import AIApplication

    app = AIApplication()
    orch = app._get_orchestrator()
    assert orch is app.orchestrator
    # an unbuilt app has no components → no auto-registered services
    assert orch.services.names() == []
    assert orch.states.state == LifecycleState.CREATED
    # lifecycle methods route through the orchestrator state machine
    app.initialize()
    assert orch.states.state == LifecycleState.STARTING
    app.shutdown()
    assert orch.states.state == LifecycleState.STOPPED


class _ThreadedService:
    """Minimal background service exposing ``is_alive`` + start/stop counts."""

    def __init__(self):
        self.started = 0
        self.stopped = 0
        self._alive = False
        self._lock = threading.RLock()

    def start(self):
        with self._lock:
            self.started += 1
            self._alive = True

    def stop(self):
        with self._lock:
            self.stopped += 1
            self._alive = False

    def is_alive(self):
        with self._lock:
            return self._alive


class TestTransitionJournal:

    def test_journal_class_appends_jsonl(self, tmp_path):
        j = TransitionJournal(path=tmp_path / "transitions.jsonl")
        j.record(LifecycleState.CREATED, LifecycleState.INITIALIZING, "manual-1")
        j.record(LifecycleState.INITIALIZING, LifecycleState.STARTING, "manual-2")
        j.close()
        lines = (tmp_path / "transitions.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        rec = json.loads(lines[0])
        assert rec["from"] == "created"
        assert rec["to"] == "initializing"
        assert rec["reason"] == "manual-1"
        assert "ts" in rec

    def test_orchestrator_persists_wired_listener(self, tmp_path):
        orch = SystemOrchestrator(app=_FakeApp(), journal_dir=str(tmp_path))
        assert orch.journal.enabled
        assert orch.journal.path == str(tmp_path / "transitions.jsonl")
        orch.states.transition(LifecycleState.INITIALIZING, "manual-1")
        orch.states.transition(LifecycleState.STARTING, "manual-2")
        orch.journal.close()
        lines = (tmp_path / "transitions.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[1])["to"] == "starting"

    def test_journal_no_dir_records_nothing(self):
        orch = SystemOrchestrator(app=_FakeApp())
        orch.states.transition(LifecycleState.INITIALIZING, "x")
        assert orch.summary()["journal"]["entries"] == 0

    def test_summary_reports_journal(self, tmp_path):
        orch = SystemOrchestrator(app=_FakeApp(), journal_dir=str(tmp_path))
        orch.states.transition(LifecycleState.INITIALIZING, "x")
        orch.states.transition(LifecycleState.STARTING, "y")
        summary = orch.summary()
        assert summary["journal"]["enabled"] is True
        assert summary["journal"]["path"] == str(tmp_path / "transitions.jsonl")
        assert summary["journal"]["entries"] == 2
        orch.journal.close()


class TestRestartableOnFailure:

    def _app_with_restartables(self):
        from app.application import AIApplication
        app = AIApplication()
        app.write_journal = _ThreadedService()
        app.directory_watcher = _ThreadedService()
        return app

    def test_auto_opts_write_journal_and_watcher(self):
        orch = SystemOrchestrator(app=self._app_with_restartables())
        orch.register_app_services()
        wj = orch.services.get("write_journal")
        assert wj is not None
        assert wj.restart_policy == RestartPolicy.ON_FAILURE
        assert wj.factory is not None
        assert wj.health is not None
        assert wj.layer == "Infrastructure"
        assert wj.snapshot()["restartable"] is True
        watcher = orch.services.get("directory_watcher")
        assert watcher is not None
        assert watcher.restart_policy == RestartPolicy.ON_FAILURE
        assert watcher.factory is not None
        assert watcher.health is not None
        assert watcher.layer == "Runtime"
        assert watcher.snapshot()["restartable"] is True

    def test_restart_recovers_opted_in_service(self):
        orch = SystemOrchestrator(app=self._app_with_restartables())
        orch.register_app_services()
        orch.start_watchdog()
        assert orch.restart("write_journal") is True
        assert orch.restart("directory_watcher") is True
        for name in ("write_journal", "directory_watcher"):
            svc = orch.services.get(name)
            assert svc.state == "running"
            assert svc.restarts == 1
        orch.stop_watchdog()

    def test_restart_real_write_journal_preserves_backends(self, tmp_path):
        from app.application import AIApplication
        app = AIApplication()
        wj = WriteJournal(drain_interval=0.05)
        wj.register("state", lambda batch: None)
        wj.start()
        app.write_journal = wj
        orch = SystemOrchestrator(app=app)
        orch.register_app_services()
        assert orch.restart("write_journal") is True
        entry = orch.services.get("write_journal")
        assert entry.obj is wj
        assert set(wj.backends()) == {"state"}
        assert wj.is_alive()
        wj.stop(timeout=1.0)

    def test_factory_rebind_replaces_lifecycle_hooks(self):
        orch = SystemOrchestrator(app=_FakeApp())
        produced = []

        def factory():
            obj = _FakeService()
            produced.append(obj)
            return obj

        orch.register_service("svc", restart_policy=RestartPolicy.ON_FAILURE,
                              factory=factory)
        assert orch.restart("svc") is True
        entry = orch.services.get("svc")
        assert entry.obj is produced[0]
        assert entry.start.__self__ is produced[0]
        assert entry.stop.__self__ is produced[0]
        assert produced[0].started == 1


def test_system_mixin_orchestrator_summary():
    from api.routes_system import SystemMixin

    class FakeOrch:
        def summary(self):
            return {"state": "running"}

    m = SystemMixin()
    assert m.system_orchestrator() == {"status": "unavailable"}
    m.orchestrator = FakeOrch()
    assert m.system_orchestrator() == {"state": "running"}


def test_directory_watcher_restart_cycle(tmp_path):
    from knowledge.watcher import DirectoryWatcher

    class FakeBuilder:
        def build_from_file(self, path):
            pass

    w = DirectoryWatcher(builder=FakeBuilder(), directories=[str(tmp_path)], interval=0.05)
    w.start()
    assert w.is_alive()
    w.stop()
    time.sleep(0.2)
    assert not w.is_alive()
    w.start()
    assert w.is_alive()
    w.stop()


def test_bootstrap_exposes_orchestrator_and_watcher():
    from app.application import AIApplication
    from app.orchestrator import SystemOrchestrator

    app = AIApplication()
    app.directory_watcher = _ThreadedService()
    app.write_journal = _ThreadedService()
    orch = app._get_orchestrator()
    assert isinstance(orch, SystemOrchestrator)
    assert app.orchestrator is orch
    assert orch.services.get("write_journal").restart_policy == RestartPolicy.ON_FAILURE
    assert orch.services.get("directory_watcher") is not None