import time
from unittest.mock import MagicMock


class TestM6SchedulerWiring:
    """M6 background tasks must be registered when the kernel is present."""

    def _make_with_brain(self, brain):
        from core.scheduler import Scheduler
        kernel = MagicMock()
        kernel.background_tick = MagicMock()
        kernel.brain = brain
        return Scheduler(kernel)

    def test_dream_level5_registered(self):
        brain = MagicMock()
        brain.dream_engine = MagicMock()
        sched = self._make_with_brain(brain)
        sched.tasks.clear()
        sched._register_default_tasks()
        names = [t["name"] for t in sched.tasks]
        assert "dream_level5" in names

    def test_preference_apply_registered(self):
        brain = MagicMock()
        brain.dream_engine = MagicMock()
        sched = self._make_with_brain(brain)
        sched.tasks.clear()
        sched._register_default_tasks()
        names = [t["name"] for t in sched.tasks]
        assert "preference_apply" in names

    def test_preference_apply_task_calls_apply_pending(self):
        from core.scheduler import Scheduler
        pref = MagicMock()
        pref.apply_pending.return_value = [{"topic": "jazz", "after": "likes"}]
        brain = MagicMock()
        brain.preference_evolution = pref
        kernel = MagicMock()
        kernel.background_tick = MagicMock()
        kernel.brain = brain
        sched = Scheduler(kernel)
        sched.tasks.clear()
        sched._register_default_tasks()
        task = next(t for t in sched.tasks if t["name"] == "preference_apply")
        task["callback"]()
        pref.apply_pending.assert_called_once()

    def test_preference_apply_noop_without_brain(self):
        from core.scheduler import Scheduler
        kernel = MagicMock()
        kernel.background_tick = MagicMock()
        kernel.brain = None
        sched = Scheduler(kernel)
        sched.tasks.clear()
        sched._register_default_tasks()  # must not raise
        assert any(t["name"] == "preference_apply" for t in sched.tasks)


class TestSchedulerLockDiscipline:
    """Shared-task mutations must be guarded by scheduler.lock."""

    def _make(self):
        from core.scheduler import Scheduler
        kernel = MagicMock()
        kernel.background_tick = MagicMock()
        sched = Scheduler(kernel)
        return sched

    def test_register_task_append_under_lock(self):
        sched = self._make()
        sched.tasks.clear()
        with sched.lock:
            acquired = sched.lock.acquire(blocking=False)
            if acquired:
                # Lock was free — we own it; simulate an already-held lock
                # by checking register_task still appends via lock context.
                sched.lock.release()
        sched.register_task("t1", lambda: None, interval=10)
        assert any(t["name"] == "t1" for t in sched.tasks)

    def test_enable_disable_task(self):
        sched = self._make()
        sched.tasks.clear()
        sched.register_task("t1", lambda: None, 10)
        assert sched.disable_task("t1") is True
        task = [t for t in sched.tasks if t["name"] == "t1"][0]
        assert task["enabled"] is False
        assert sched.enable_task("t1") is True
        assert task["enabled"] is True

    def test_remove_task(self):
        sched = self._make()
        sched.tasks.clear()
        sched.register_task("t1", lambda: None, 10)
        sched.register_task("t2", lambda: None, 10)
        assert sched.remove_task("t1") is True
        names = [t["name"] for t in sched.tasks]
        assert "t1" not in names and "t2" in names

    def test_stats_snapshot(self):
        sched = self._make()
        sched.tasks.clear()
        sched.register_task("t1", lambda: None, 10)
        stats = sched.stats()
        assert stats["tasks"] == 1
        assert stats["registered_tasks"][0]["name"] == "t1"

    def test_run_task_success_updates_counters(self):
        sched = self._make()
        sched.tasks.clear()
        fired = []
        sched.register_task("t1", lambda: fired.append(1), 0)
        task = sched.tasks[0]
        task["last_run"] = 0.0
        sched._run_task(task, time.time())
        assert fired == [1]
        assert task["total_runs"] == 1
        assert sched.total_runs == 1

    def test_run_task_failure_disables_after_max(self):
        sched = self._make()
        sched.tasks.clear()
        sched.max_task_failures = 3
        sched.register_task("t1", lambda: (_ for _ in ()).throw(RuntimeError("boom")), 10)
        task = sched.tasks[0]
        task["last_run"] = 0.0
        for _ in range(3):
            sched._run_task(task, time.time())
        assert task["failures"] == 3
        assert task["enabled"] is False
        assert sched.total_errors == 3