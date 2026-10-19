# core/scheduler.py
import logging
import threading
import time
import traceback

from app.config_loader import Settings
from core.event_bus import EventBus

logger = logging.getLogger(__name__)


class Scheduler:

    def __init__(self, kernel, event_bus=None):

        self.kernel = kernel
        self.event_bus = event_bus or EventBus()

        self.running = False

        self.thread = None

        # ==================================================
        # 🧠 TASK REGISTRY
        # ==================================================

        self.tasks = []

        # ==================================================
        # 🧠 CONFIG SETTINGS
        # ==================================================

        self.loop_delay_active = (
            Settings.SCHEDULER_LOOP_DELAY_ACTIVE
        )

        self.loop_delay_idle = (
            Settings.SCHEDULER_LOOP_DELAY_IDLE
        )

        self.max_task_failures = (
            Settings.SCHEDULER_MAX_TASK_FAILURES
        )

        self.error_sleep = (
            Settings.SCHEDULER_ERROR_SLEEP
        )

        self.background_tick_interval = (
            Settings.SCHEDULER_BACKGROUND_TICK_INTERVAL
        )

        self.emotion_decay_interval = (
            Settings.SCHEDULER_EMOTION_DECAY_INTERVAL
        )

        self.personality_decay_interval = (
            Settings.SCHEDULER_PERSONALITY_DECAY_INTERVAL
        )

        self.memory_decay_interval = (
            Settings.SCHEDULER_MEMORY_DECAY_INTERVAL
        )

        self.dream_level1_interval = (
            Settings.SCHEDULER_DREAM_LEVEL1_INTERVAL
        )

        self.dream_level2_interval = (
            Settings.SCHEDULER_DREAM_LEVEL2_INTERVAL
        )

        self.dream_level3_interval = (
            Settings.SCHEDULER_DREAM_LEVEL3_INTERVAL
        )

        self.dream_level4_interval = (
            Settings.SCHEDULER_DREAM_LEVEL4_INTERVAL
        )

        self.dream_level5_interval = (
            Settings.SCHEDULER_DREAM_LEVEL5_INTERVAL
        )

        self.preference_apply_interval = (
            Settings.SCHEDULER_PREFERENCE_APPLY_INTERVAL
        )

        # ==================================================
        # 🧠 THREAD SAFETY
        # ==================================================

        self.lock = threading.RLock()

        # ==================================================
        # 🧠 RUNTIME METRICS
        # ==================================================

        self.total_runs = 0

        self.total_errors = 0

        self.recovery_interval = 60.0

        self.last_recovery_check = 0.0

        self._register_default_tasks()

    # ==================================================
    # 🚀 START SCHEDULER
    # ==================================================

    def start(self):

        with self.lock:

            if self.running:

                logger.info(
                    "[Scheduler] Already running"
                )

                return False

            self.running = True

            self.thread = threading.Thread(

                target=self.loop,

                daemon=True,

                name="SchedulerThread"
            )

            self.thread.start()

            logger.info("[Scheduler] Started")

            return True

    # ==================================================
    # 🛑 STOP SCHEDULER
    # ==================================================

    def stop(self):

        with self.lock:

            self.running = False

            logger.info("[Scheduler] Stopped")

            return True

    # ==================================================
    # 🧠 REGISTER TASK
    # ==================================================

    def register_task(
        self,
        name,
        callback,
        interval
    ):

        try:

            if not callable(callback):

                raise ValueError(
                    f"Task '{name}' callback is not callable"
                )

            interval = max(
                1,
                float(interval)
            )

            task = {

                "name": name,

                "callback": callback,

                "interval": interval,

                "last_run": 0,

                "enabled": True,

                "failures": 0,

                "total_runs": 0
            }

            with self.lock:
                self.tasks.append(task)

            logger.info(
                f"[Scheduler] Registered task: {name}"
            )

            return True

        except Exception as e:

            logger.error(
                f"[TASK REGISTER ERROR] {e}"
            )

            return False

    # ==================================================
    # 🧠 DEFAULT TASKS
    # ==================================================

    def _register_default_tasks(self):

        # ==================================================
        # 🧠 BACKGROUND TICK
        # ==================================================

        if hasattr(
            self.kernel,
            "background_tick"
        ):

            self.register_task(

                "background_tick",

                self.kernel.background_tick,

                interval=self.background_tick_interval
            )

        # ==================================================
        # ❤️ EMOTION DECAY
        # ==================================================

        emotion = getattr(
            self.kernel,
            "emotion",
            None
        )

        if (
            emotion
            and
            hasattr(emotion, "_decay")
        ):

            self.register_task(

                "emotion_decay",

                emotion._decay,

                interval=self.emotion_decay_interval
            )

        # ==================================================
        # 🧠 PERSONALITY DECAY
        # ==================================================

        brain = getattr(
            self.kernel,
            "brain",
            None
        )

        if brain:

            personality_state = getattr(

                brain,

                "personality_state",

                None
            )

            if (
                personality_state
                and
                hasattr(
                    personality_state,
                    "decay"
                )
            ):

                self.register_task(

                    "personality_decay",

                    personality_state.decay,

                    interval=self.personality_decay_interval
                )

        # ==================================================
        # 🧠 MEMORY DECAY
        # ==================================================

        memory = None

        if brain:
            memory = getattr(
                brain,
                "memory",
                None
            )

        if memory:

            decay = getattr(
                memory,
                "decay",
                None
            )

            graph = getattr(
                memory,
                "graph",
                None
            )

            if (
                decay
                and
                graph
                and
                hasattr(decay, "apply")
            ):

                self.register_task(

                    "memory_decay",

                    lambda: self._safe_memory_decay(
                        decay,
                        graph,
                        memory
                    ),

                    interval=self.memory_decay_interval
                )

        # ==================================================
        # 🧠 DREAM LEVEL 2 (hourly)
        # ==================================================

        dream_engine = None
        brain = getattr(self.kernel, "brain", None)
        if brain:
            dream_engine = getattr(brain, "dream_engine", None)

        if dream_engine and hasattr(dream_engine, "run_cycle"):

            def _dream_wrapper(level):
                # Run dreams off the scheduler thread so a long (LLM-backed)
                # dream cycle never blocks memory/emotion decay tasks (P-05).
                if getattr(dream_engine, "is_dreaming", False):
                    logger.info("[Scheduler] Dream L%d skipped — already dreaming", level)
                    return

                def _dream_thread():
                    try:
                        dream_engine.run_cycle(level=level)
                    except Exception as e:
                        logger.error("[Scheduler] Dream L%d error: %s", level, e)

                t = threading.Thread(
                    target=_dream_thread,
                    daemon=True,
                    name=f"DreamL{level}",
                )
                t.start()

            self.register_task(
                "dream_level2",
                lambda: _dream_wrapper(2),
                interval=self.dream_level2_interval
            )

            self.register_task(
                "dream_level3",
                lambda: _dream_wrapper(3),
                interval=self.dream_level3_interval
            )

            self.register_task(
                "dream_level4",
                lambda: _dream_wrapper(4),
                interval=self.dream_level4_interval
            )

            # M6 · Experience reflection (daily) — lazy growth work over
            # significant unreflected emotional experiences.
            self.register_task(
                "dream_level5",
                lambda: _dream_wrapper(5),
                interval=self.dream_level5_interval
            )

        # ==================================================
        # 🧠 PREFERENCE EVOLUTION APPLY (weekly)
        # ==================================================
        #
        # M6 · Preference evolution apply (weekly) — background apply of
        # accumulated approval/disapproval evidence, gated by threshold +
        # cadence inside PreferenceEvolution. Evidence itself is recorded
        # on the conversation path (memory pipeline). Registration is
        # unconditional; the callback no-ops until the brain attaches a
        # PreferenceEvolution instance.

        def _preference_apply():
            brain = getattr(self.kernel, "brain", None)
            if brain is None:
                return
            pref = getattr(brain, "preference_evolution", None)
            if pref is None or not hasattr(pref, "apply_pending"):
                return
            try:
                changes = pref.apply_pending()
                if changes:
                    logger.info(
                        "[Scheduler] preference_apply: %d change(s): %s",
                        len(changes),
                        [c["topic"] for c in changes],
                    )
            except Exception as e:
                logger.error("[Scheduler] preference_apply error: %s", e)

        self.register_task(
            "preference_apply",
            _preference_apply,
            interval=self.preference_apply_interval
        )

    # ==================================================
    # 🧠 SAFE MEMORY DECAY
    # ==================================================

    def _safe_memory_decay(
        self,
        decay,
        graph,
        memory
    ):

        try:

            nodes = getattr(
                graph,
                "nodes",
                []
            )

            if not isinstance(
                nodes,
                list
            ):
                return

            graph.nodes = decay.apply(
                nodes
            )

            for node in list(decay.archived):
                graph.remove(node)
                vector_id = getattr(
                    node,
                    "vector_id",
                    None
                )
                if vector_id:
                    memory.vector.delete(vector_id)

        except Exception as e:

            logger.error(
                f"[MEMORY DECAY ERROR] {e}"
            )

    # ==================================================
    # 🔄 MAIN LOOP
    # ==================================================

    def loop(self):

        while self.running:

            try:

                now = time.time()

                with self.lock:
                    tasks_snapshot = list(self.tasks)

                for task in tasks_snapshot:

                    self._run_task(
                        task,
                        now
                    )

                # ==================================================
                # ⚡ ADAPTIVE SLEEP
                # ==================================================

                conversation_active = False
                try:
                    state = getattr(self.kernel, "state", None)
                    if state and hasattr(state, "runtime"):
                        with state.lock:
                            conversation_active = state.runtime.conversation_active
                except Exception as e:
                    logger.warning("Scheduler state read failed: %s", e)

                if conversation_active:

                    time.sleep(
                        self.loop_delay_active
                    )

                else:

                    time.sleep(
                        self.loop_delay_idle
                    )

                now = time.time()

                if (
                    now - self.last_recovery_check
                    > self.recovery_interval
                ):

                    self.last_recovery_check = now

                    with self.lock:
                        for task in self.tasks:

                            if not task["enabled"]:

                                task["enabled"] = True

                                task["failures"] = 0

                                logger.info(
                                    f"Re-enabled task "
                                    f"{task['name']} "
                                    f"after recovery cooldown"
                                )

            except Exception as e:

                self.total_errors += 1

                logger.error(
                    f"[SCHEDULER LOOP ERROR] {e}"
                )

                traceback.print_exc()

                time.sleep(
                    self.error_sleep
                )

    # ==================================================
    # 🧠 TASK EXECUTION
    # ==================================================

    def _run_task(
        self,
        task,
        now
    ):

        try:

            if not task.get(
                "enabled",
                True
            ):
                return

            elapsed = (
                now - task["last_run"]
            )

            if elapsed < task["interval"]:
                return

            start = time.time()

            callback = task["callback"]

            callback()

            duration = round(
                time.time() - start,
                4
            )

            with self.lock:
                task["last_run"] = now

                task["total_runs"] += 1

                task["failures"] = 0

                self.total_runs += 1

            if self.event_bus:
                from core.event_specs import SCHEDULER_TASK_COMPLETED
                from core.mai_message import publish_event
                publish_event(self.event_bus, SCHEDULER_TASK_COMPLETED, {
                    "name": task["name"],
                    "duration": duration,
                    "total_runs": task["total_runs"],
                }, source="scheduler")

            logger.info(

                f"[Scheduler] "

                f"{task['name']} "

                f"({duration}s)"
            )

        except Exception as e:

            logger.error(

                f"[Scheduler Error] "

                f"{task['name']}: {e}"
            )

            traceback.print_exc()

            with self.lock:
                task["failures"] += 1

                self.total_errors += 1

                if (
                    task["failures"]
                    >=
                    self.max_task_failures
                ):

                    task["enabled"] = False

            logger.warning(

                    f"[Scheduler] "

                    f"Disabled task "

                    f"{task['name']} "

                    f"after repeated failures"
                )

    # ==================================================
    # ➕ ENABLE TASK
    # ==================================================

    def enable_task(
        self,
        name
    ):

        with self.lock:
            for task in self.tasks:

                if task["name"] == name:

                    task["enabled"] = True

                    task["failures"] = 0

                    return True

        return False

    # ==================================================
    # ➖ DISABLE TASK
    # ==================================================

    def disable_task(
        self,
        name
    ):

        with self.lock:
            for task in self.tasks:

                if task["name"] == name:

                    task["enabled"] = False

                    return True

        return False

    # ==================================================
    # 🧹 REMOVE TASK
    # ==================================================

    def remove_task(
        self,
        name
    ):

        with self.lock:
            before = len(self.tasks)

            self.tasks = [

                t for t in self.tasks

                if t["name"] != name
            ]

        return len(self.tasks) < before

    # ==================================================
    # 📊 DEBUG STATS
    # ==================================================

    def stats(self):

        with self.lock:
            tasks_snapshot = [
                dict(t) for t in self.tasks
            ]

        return {

            "running":
                self.running,

            "tasks":
                len(tasks_snapshot),

            "total_runs":
                self.total_runs,

            "total_errors":
                self.total_errors,

            "thread_alive":
                (
                    self.thread.is_alive()
                    if self.thread
                    else False
                ),

            "registered_tasks": [

                {
                    "name":
                        t["name"],

                    "enabled":
                        t["enabled"],

                    "interval":
                        t["interval"],

                    "runs":
                        t["total_runs"],

                    "failures":
                        t["failures"]
                }

                for t in tasks_snapshot
            ]
        }