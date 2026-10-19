import logging
import threading
import time
from datetime import datetime

from agency.dream_report import LEVEL_TASKS, DreamReport
from agency.dream_tasks import DREAM_TASKS

logger = logging.getLogger(__name__)


class DreamEngine:
    """State-first dreaming engine.

    Orchestrates maintenance tasks over ``MemoryState`` and recompiles the
    vault (it never edits Markdown directly). Task implementations live in
    ``agency.dream_tasks`` and are dispatched by name via ``DREAM_TASKS``.
    """

    def __init__(self, knowledge_graph=None, llm=None, event_bus=None,
                 vault_root=None, obsidian_writer=None, vault_compiler=None,
                 experience_store=None):
        self.knowledge_graph = knowledge_graph
        self.llm = llm
        self.event_bus = event_bus
        self.vault_root = vault_root
        self.obsidian_writer = obsidian_writer
        self.vault_compiler = vault_compiler
        self.experience_store = experience_store
        self._last_dream = 0.0
        self._min_idle_seconds = 300
        self._dreaming_lock = threading.RLock()
        self._dreaming = False

    @property
    def is_dreaming(self):
        return self._dreaming

    def should_dream(self, idle_seconds):
        if self._dreaming:
            return False
        if idle_seconds < self._min_idle_seconds:
            return False
        if time.time() - self._last_dream < 3600:
            return False
        return True

    def run_cycle(self, level=1, date_str=None):
        from memory.state import MemoryState

        if not self.vault_root or not self.obsidian_writer:
            logger.warning("[DreamEngine] run_cycle L%s: missing vault_root or writer", level)
            return None
        with self._dreaming_lock:
            if self._dreaming:
                logger.debug("[DreamEngine] run_cycle L%s: already dreaming", level)
                return None
            self._dreaming = True
            if self.event_bus:
                from core.event_specs import DREAM_STARTED, STATE_DREAMING_STARTED
                from core.mai_message import publish_event
                publish_event(self.event_bus, DREAM_STARTED, {"level": level}, source="agency")
                publish_event(self.event_bus, STATE_DREAMING_STARTED, {"level": level}, source="agency")
            date_str = date_str or datetime.now().strftime("%Y-%m-%d")
            try:
                state = MemoryState()
                vault = self.vault_root
                for folder, filename in [
                    ("identity", "user.md"),
                    ("preferences", "preferences.md"),
                    ("knowledge", "knowledge.md"),
                    ("dreams", "dreams.md"),
                    ("people", "people.md"),
                    ("places", "places.md"),
                    ("projects", "projects.md"),
                ]:
                    path = vault / folder / filename
                    state.load_from_file(path, folder)
                stats_path = vault / "statistics" / "stats.md"
                state.load_statistics_from_file(stats_path)
                report = self.run(state, level=level)
                if report:
                    if self.vault_compiler is not None:
                        self.vault_compiler.compile_state(state, date_str)
                        try:
                            self.vault_compiler.logger.dream_completed(
                                level=level,
                                detail=f"tasks={','.join(report.tasks_run)}",
                            )
                            # Audit Step 8: surface maintenance detail in its own log.
                            if report.tasks_run:
                                self.vault_compiler.logger.maintenance_log(
                                    f"dream L{level}: "
                                    f"merged={report.duplicates_merged}, "
                                    f"orphans={report.orphans_found}, "
                                    f"links={report.links_created}, "
                                    f"archived={report.archived}, "
                                    f"contradictions={report.contradictions_found}, "
                                    f"split={report.pages_split}, "
                                    f"patterns={report.patterns_discovered}, "
                                    f"exp_reflected={report.experiences_reflected}, "
                                    f"graph_opt={report.graph_optimized}"
                                )
                        except Exception as e:
                            logger.warning("[DreamEngine] report log formatting failed: %s", e)
                    elif self.obsidian_writer is not None:
                        self.obsidian_writer.dump(state, date_str)
                return report
            except Exception as e:
                logger.error("[DreamEngine] run_cycle L%s: %s", level, e)
                return None
            finally:
                with self._dreaming_lock:
                    self._dreaming = False
                if self.event_bus:
                    from core.event_specs import DREAM_ENDED
                    from core.mai_message import publish_event
                    publish_event(self.event_bus, DREAM_ENDED, {"level": level}, source="agency")

    def run(self, state, level=1):
        start = time.time()
        report = DreamReport(level=level)
        tasks = LEVEL_TASKS.get(level, [])

        for task_name in tasks:
            task_fn = DREAM_TASKS.get(task_name)
            if not task_fn:
                continue
            try:
                metric = task_fn(self, state, report)
            except Exception as e:
                logger.error("[DreamEngine] task '%s' error: %s", task_name, e)
                report.errors.append(f"{task_name}: {e}")
                continue
            report.tasks_run.append(task_name)
            _assign_metric(report, task_name, metric)

        report.duration = round(time.time() - start, 3)
        self._last_dream = time.time()

        if self.event_bus:
            from core.event_specs import DREAM_COMPLETED, STATE_DREAMING_FINISHED
            from core.mai_message import publish_event
            publish_event(self.event_bus, DREAM_COMPLETED, {
                "level": level,
                "tasks": report.tasks_run,
                "duration": report.duration,
                "errors": report.errors,
            }, source="agency")
            publish_event(self.event_bus, STATE_DREAMING_FINISHED, {
                "level": level,
                "tasks": report.tasks_run,
                "duration": report.duration,
            }, source="agency")

        return report


    # ── Private dispatch helper for individual task execution ──
    # Tests may call this directly instead of going through run().
    # Production path: run() -> DREAM_TASKS[task_name](engine, state, report)
    def _run_task(self, task_name, state, report):
        fn = DREAM_TASKS.get(task_name)
        if fn is None:
            return None
        return fn(self, state, report)


def _assign_metric(report, task_name, metric):
    """Map a task's returned metric onto the correct DreamReport field."""
    if task_name == "graph_optimization":
        report.graph_optimized = True
        return
    if task_name == "weekly_digest":
        report.digest_created = bool(metric)
        return
    if isinstance(metric, int):
        # Map task name -> report attribute.
        attr = {
            "orphans": "orphans_found",
            "merge_duplicates": "duplicates_merged",
            "merge_knowledge": "knowledge_merged",
            "link_notes": "links_created",
            "importance": "importance_recalculated",
            "importance_full": "importance_recalculated",
            "relationship_building": "relationships_built",
            "conversation_compression": "conversations_compressed",
            "reflections": "reflections_generated",
            "knowledge_discovery": "knowledge_discovered",
            "emotional_reflection": "emotional_reflections",
            "contradictions": "contradictions_found",
            "archive_stale": "archived",
            "split_giant": "pages_split",
            "patterns": "patterns_discovered",
            "experience_reflection": "experiences_reflected",
        }.get(task_name)
        if attr:
            setattr(report, attr, metric)
