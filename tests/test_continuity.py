"""T8 · Continuity Engine — projects, commitments, checkpoints, reconciliation.

The engine must own no fact another subsystem already owns: project progress and
completion read through to ``GoalManager``; focus reads from ``CognitiveState``;
runtime truth reads from ``SharedState``. These tests pin that contract.
"""
import json
import time

import pytest


@pytest.fixture()
def store_path(tmp_path):
    return tmp_path / "continuity.json"


@pytest.fixture()
def goal_manager():
    from agency.goals import GoalManager
    return GoalManager()


@pytest.fixture()
def engine(store_path, goal_manager):
    from continuity.engine import ContinuityEngine
    return ContinuityEngine(store_path=str(store_path), goal_manager=goal_manager)


# ---------------------------------------------------------------------------
#  Due window parsing
# ---------------------------------------------------------------------------

class TestParseDue:

    def test_none_and_empty_mean_no_window(self):
        from continuity.models import parse_due
        assert parse_due(None) is None
        assert parse_due("") is None

    def test_numeric_epoch_passthrough(self):
        from continuity.models import parse_due
        assert parse_due(1700000000) == 1700000000.0
        assert parse_due("1700000000") == 1700000000.0

    def test_relative_windows(self):
        from continuity.models import parse_due
        now = 1_700_000_000.0
        assert parse_due("in 3h", now=now) == now + 3 * 3600
        assert parse_due("90m", now=now) == now + 90 * 60
        assert parse_due("2d", now=now) == now + 2 * 86400

    def test_iso_date(self):
        from continuity.models import parse_due
        value = parse_due("2026-11-20")
        assert value is not None and value > 0

    def test_unparseable_raises(self):
        from continuity.models import parse_due
        with pytest.raises(ValueError):
            parse_due("sometime next week-ish")


# ---------------------------------------------------------------------------
#  Persistence
# ---------------------------------------------------------------------------

class TestStore:

    def test_transaction_rollback_on_error(self, store_path):
        from continuity.store import ContinuityStore
        store = ContinuityStore(store_path)
        with pytest.raises(RuntimeError):
            with store.transaction() as document:
                document["projects"]["x"] = {"id": "x"}
                raise RuntimeError("boom")
        assert store.read()["projects"] == {}

    def test_writes_survive_reload(self, store_path):
        from continuity.engine import ContinuityEngine
        first = ContinuityEngine(store_path=str(store_path))
        project = first.projects.create("Mai AI")
        second = ContinuityEngine(store_path=str(store_path))
        reloaded = second.projects.get(project.id)
        assert reloaded is not None
        assert reloaded.name == "Mai AI"

    def test_corrupt_store_starts_empty(self, store_path):
        from continuity.store import ContinuityStore
        store_path.write_text("{ not json", encoding="utf-8")
        store = ContinuityStore(store_path)
        assert store.read()["projects"] == {}


# ---------------------------------------------------------------------------
#  Project memory — progress stays owned by GoalManager
# ---------------------------------------------------------------------------

class TestProjectMemory:

    def test_create_links_a_goal(self, engine, goal_manager):
        project = engine.projects.create("Continuity Engine", summary="T8")
        assert project is not None
        assert project.goal_id is not None
        assert goal_manager.get(project.goal_id) is not None

    def test_create_requires_a_name(self, engine):
        assert engine.projects.create("") is None
        assert engine.projects.create(None) is None

    def test_create_is_idempotent_for_open_projects(self, engine):
        first = engine.projects.create("Same project")
        second = engine.projects.create("same project")
        assert first.id == second.id

    def test_progress_reads_through_to_the_goal(self, engine, goal_manager):
        project = engine.projects.create("Ship T8")
        engine.projects.add_step(project.id, "write tests")
        engine.projects.add_step(project.id, "wire scheduler")
        assert engine.projects.progress(project) == 0.0

        engine.projects.complete_step(project.id, "write tests")
        assert engine.projects.progress(project) == 0.5

        engine.projects.complete_step(project.id, "wire scheduler")
        goal = goal_manager.get(project.goal_id)
        assert goal.status == "completed"
        assert engine.projects.progress(project) == 1.0

    def test_completing_a_project_completes_its_goal(self, engine, goal_manager):
        project = engine.projects.create("Finish audit")
        engine.projects.complete(project.id)
        assert engine.projects.get(project.id).status == "completed"
        assert goal_manager.get(project.goal_id).status == "completed"

    def test_abandoning_a_project_cancels_its_goal(self, engine, goal_manager):
        project = engine.projects.create("Dead end")
        engine.projects.update(project.id, status="abandoned")
        assert goal_manager.get(project.goal_id).status == "cancelled"

    def test_unknown_status_rejected(self, engine):
        project = engine.projects.create("Valid")
        with pytest.raises(ValueError):
            engine.projects.update(project.id, status="vibing")

    def test_decisions_questions_and_blockers(self, engine):
        project = engine.projects.create("Decision heavy")
        decision = engine.projects.record_decision(project.id, "Use a thin reconciler")
        question = engine.projects.raise_question(project.id, "SQLite or JSON?")
        blocker = engine.projects.add_blocker(project.id, "no JDK on host")

        reloaded = engine.projects.get(project.id)
        assert reloaded.decisions[0]["text"] == "Use a thin reconciler"
        assert len(reloaded.open_questions_live()) == 1
        assert len(reloaded.blockers_live()) == 1

        assert engine.projects.resolve_question(project.id, question["id"]) is True
        assert engine.projects.clear_blocker(project.id, blocker["id"]) is True
        reloaded = engine.projects.get(project.id)
        assert reloaded.open_questions_live() == []
        assert reloaded.blockers_live() == []

    def test_next_checkpoint_and_deadline(self, engine):
        project = engine.projects.create("Has deadline", deadline="in 2d")
        engine.projects.update(project.id, next_checkpoint="write the scheduler task")
        reloaded = engine.projects.get(project.id)
        assert reloaded.deadline > time.time()
        assert reloaded.next_checkpoint == "write the scheduler task"

    def test_listing_orders_active_before_terminal(self, engine):
        done = engine.projects.create("Done thing")
        engine.projects.complete(done.id)
        active = engine.projects.create("Active thing")
        ordered = engine.projects.list()
        assert [p.id for p in ordered][0] == active.id
        assert done.id not in [p.id for p in engine.projects.list(include_terminal=False)]


# ---------------------------------------------------------------------------
#  Commitments ledger
# ---------------------------------------------------------------------------

class TestCommitments:

    def test_add_with_relative_window(self, engine):
        commitment = engine.commitments.add("research forex", due_in_hours=2)
        assert commitment.due_at == pytest.approx(time.time() + 7200, abs=5)

    def test_add_requires_a_promise(self, engine):
        assert engine.commitments.add("") is None

    def test_add_rejects_unparseable_window(self, engine):
        with pytest.raises(ValueError):
            engine.commitments.add("research forex", due_at="soonish")

    def test_sweep_marks_overdue_as_missed(self, engine):
        commitment = engine.commitments.add("send the report", due_in_hours=1)
        summary = engine.commitments.sweep(now=time.time() + 7200)
        assert summary["missed_count"] == 1
        assert engine.commitments.get(commitment.id).status == "missed"

    def test_sweep_leaves_future_promises_open(self, engine):
        engine.commitments.add("later thing", due_in_hours=10)
        assert engine.commitments.sweep(now=time.time())["missed_count"] == 0
        assert len(engine.commitments.list(status="open")) == 1

    def test_open_ended_commitment_never_misses(self, engine):
        engine.commitments.add("someday thing")
        assert engine.commitments.sweep(now=time.time() + 10 * 86400)["missed_count"] == 0

    def test_missed_commitments_surface_once(self, engine):
        engine.commitments.add("missed promise", due_in_hours=1)
        engine.commitments.sweep(now=time.time() + 7200)
        missed = engine.commitments.unsurfaced()
        assert [c.promise for c in missed] == ["missed promise"]

        engine.commitments.mark_surfaced([c.id for c in missed])
        assert engine.commitments.unsurfaced() == []

    def test_keep_and_cancel(self, engine):
        kept = engine.commitments.add("do the thing", due_in_hours=1)
        cancelled = engine.commitments.add("skip the thing", due_in_hours=1)
        assert engine.commitments.keep(kept.id).status == "kept"
        assert engine.commitments.cancel(cancelled.id).status == "cancelled"
        # Neither is overdue-reported after being closed.
        assert engine.commitments.sweep(now=time.time() + 7200)["missed_count"] == 0

    def test_resolve_rejects_unknown_outcome(self, engine):
        commitment = engine.commitments.add("thing")
        with pytest.raises(ValueError):
            engine.commitments.resolve(commitment.id, "vibes")

    def test_check_commitments_publishes_state(self, store_path, goal_manager):
        from core.event_bus import EventBus
        from core.event_specs import STATE_CONTINUITY_UPDATED, register_event_specs
        from continuity.engine import ContinuityEngine

        bus = EventBus()
        register_event_specs(bus)
        seen = []
        bus.subscribe(STATE_CONTINUITY_UPDATED, lambda msg: seen.append(msg))
        engine = ContinuityEngine(store_path=str(store_path), event_bus=bus,
                                 goal_manager=goal_manager)
        engine.commitments.add("promised thing", due_in_hours=1)
        engine.check_commitments(now=time.time() + 7200)
        assert seen, "continuity state event was not published"
        assert seen[-1]["missed"] == 1


# ---------------------------------------------------------------------------
#  Checkpoints
# ---------------------------------------------------------------------------

class TestCheckpoints:

    def test_save_and_resume(self, engine):
        engine.checkpoints.save("research-forex", step=3, state={"url": "x"}, note="next: compare")
        resumed = engine.checkpoints.resume("research-forex")
        assert resumed["step"] == 3
        assert resumed["state"] == {"url": "x"}
        assert resumed["resume_count"] == 1

    def test_save_requires_task_id(self, engine):
        assert engine.checkpoints.save("") is None

    def test_save_keeps_state_when_omitted(self, engine):
        engine.checkpoints.save("task", step=1, state={"a": 1})
        engine.checkpoints.save("task", step=2)
        checkpoint = engine.checkpoints.get("task")
        assert checkpoint.step == 2
        assert checkpoint.state == {"a": 1}

    def test_resume_unknown_returns_none(self, engine):
        assert engine.checkpoints.resume("never-saved") is None

    def test_clear(self, engine):
        engine.checkpoints.save("task", step=1)
        assert engine.checkpoints.clear("task") is True
        assert engine.checkpoints.get("task") is None
        assert engine.checkpoints.clear("task") is False


# ---------------------------------------------------------------------------
#  Reconciliation snapshot + brief
# ---------------------------------------------------------------------------

class _FakeCognitive:

    def get(self):
        return {
            "current_topic": "continuity engine",
            "current_goal": "build T8",
            "active_task": "writing tests",
            "conversation_intent": "engineering",
            "confidence": 0.8,
        }


class _FakeRuntime:
    is_thinking = False
    current_session_turns = 4
    current_speaker_name = "Syed"


class _FakeSharedState:
    def __init__(self):
        import threading
        self.lock = threading.RLock()
        self.runtime = _FakeRuntime()


class TestReconciliation:

    def test_snapshot_reconciles_all_owners(self, store_path, goal_manager):
        from continuity.engine import ContinuityEngine
        engine = ContinuityEngine(
            store_path=str(store_path),
            goal_manager=goal_manager,
            cognitive_state=_FakeCognitive(),
            shared_state=_FakeSharedState(),
        )
        project = engine.projects.create("Continuity")
        engine.projects.add_step(project.id, "step one")
        engine.commitments.add("promise", due_in_hours=1)
        engine.checkpoints.save("job", step=2)

        snapshot = engine.snapshot()

        assert [p["name"] for p in snapshot["projects"]] == ["Continuity"]
        assert snapshot["projects"][0]["goal"]["id"] == project.goal_id
        assert [g["description"] for g in snapshot["goals"]] == ["Continuity"]
        assert snapshot["commitments"]["open"] == 1
        assert snapshot["checkpoints"]["total"] == 1
        assert snapshot["focus"]["goal"] == "build T8"
        assert snapshot["runtime"]["session_turns"] == 4

    def test_snapshot_survives_missing_dependencies(self, store_path):
        from continuity.engine import ContinuityEngine
        engine = ContinuityEngine(store_path=str(store_path))
        snapshot = engine.snapshot()
        assert snapshot["goals"] == []
        assert snapshot["focus"] == {}
        assert snapshot["runtime"] == {}

    def test_brief_is_empty_when_nothing_is_ongoing(self, engine):
        assert engine.brief() == ""

    def test_brief_reports_projects_and_mixed_promises(self, engine):
        project = engine.projects.create("Continuity", next_checkpoint="wire scheduler")
        engine.projects.add_blocker(project.id, "no JDK")
        engine.projects.add_step(project.id, "a")
        engine.commitments.add("due promise", due_in_hours=1)
        engine.commitments.add("missed promise", due_in_hours=1)
        engine.commitments.sweep(now=time.time() + 7200)

        brief = engine.brief()
        assert "Continuity" in brief
        assert "wire scheduler" in brief
        assert "no JDK" in brief
        assert "missed promise" in brief
        assert "missed and not yet reported" in brief

    def test_brief_marks_missed_surfaced_only_when_asked(self, engine):
        engine.commitments.add("one off", due_in_hours=1)
        engine.commitments.sweep(now=time.time() + 7200)

        engine.brief()
        assert len(engine.commitments.unsurfaced()) == 1

        engine.brief(mark_surfaced=True)
        assert engine.commitments.unsurfaced() == []

    def test_brief_respects_max_chars(self, engine):
        for index in range(10):
            project = engine.projects.create(f"Project {index} " + "x" * 200)
            engine.projects.update(project.id, next_checkpoint="y" * 300)
        assert len(engine.brief(max_chars=120)) <= 120


# ---------------------------------------------------------------------------
#  Tools
# ---------------------------------------------------------------------------

class TestContinuityTools:

    def _registry(self, engine):
        from agency.registry import ToolRegistry
        from continuity.tools import register_continuity_tools
        registry = ToolRegistry()
        assert register_continuity_tools(registry, engine) == 6
        return registry

    def test_tools_are_registered(self, engine):
        registry = self._registry(engine)
        for name in (
            "continuity_status", "project_open", "project_update",
            "commitment_add", "commitment_resolve", "checkpoint",
        ):
            assert registry.get(name) is not None

    def test_project_tool_roundtrip(self, engine):
        registry = self._registry(engine)
        opened = registry.call("project_open", project_name="Tool project")
        assert opened["success"] is True
        project_id = opened["result"]["id"]

        updated = registry.call(
            "project_update", project_id=project_id,
            decision="keep it thin", next_checkpoint="tests",
        )
        assert updated["success"] is True
        assert updated["result"]["next_checkpoint"] == "tests"

        status = registry.call("continuity_status")
        assert status["result"]["projects"][0]["id"] == project_id

    def test_project_update_unknown_project_is_an_error(self, engine):
        registry = self._registry(engine)
        result = registry.call("project_update", project_id="nope", status="paused")
        assert result["result"].get("error")

    def test_commitment_tools(self, engine):
        registry = self._registry(engine)
        added = registry.call("commitment_add", promise="check the logs", due_in_hours=1)
        commitment_id = added["result"]["id"]
        resolved = registry.call("commitment_resolve", commitment_id=commitment_id, outcome="kept")
        assert resolved["result"]["status"] == "kept"

    def test_commitment_tool_reports_bad_window(self, engine):
        registry = self._registry(engine)
        result = registry.call("commitment_add", promise="x", due_at="whenever")
        assert "error" in result["result"]

    def test_checkpoint_tool_actions(self, engine):
        registry = self._registry(engine)
        saved = registry.call("checkpoint", action="save", task_id="job", step=1)
        assert saved["result"]["step"] == 1
        resumed = registry.call("checkpoint", action="resume", task_id="job")
        assert resumed["result"]["resume_count"] == 1
        cleared = registry.call("checkpoint", action="clear", task_id="job")
        assert cleared["result"]["cleared"] is True
        bad = registry.call("checkpoint", action="rewind", task_id="job")
        assert "error" in bad["result"]

    def test_register_is_a_noop_without_an_engine(self):
        from agency.registry import ToolRegistry
        from continuity.tools import register_continuity_tools
        registry = ToolRegistry()
        assert register_continuity_tools(registry, None) == 0
        assert register_continuity_tools(None, object()) == 0


# ---------------------------------------------------------------------------
#  Wiring — event catalog + prompt
# ---------------------------------------------------------------------------

class TestWiring:

    def test_state_topic_flows_to_the_ui_stream(self):
        from api.stream_manager import STREAM_TOPICS
        from core.event_specs import STATE_CONTINUITY_UPDATED
        assert STATE_CONTINUITY_UPDATED in STREAM_TOPICS

    def test_catalog_declares_the_continuity_publisher(self):
        from core.event_registry import EventRegistry
        from core.event_specs import VERTEX_SPECS
        registry = EventRegistry()
        registry.register_many(VERTEX_SPECS)
        assert registry.can_publish("continuity", "state.continuity.updated") is True
        assert registry.can_publish("voice", "state.continuity.updated") is False

    def test_brief_reaches_the_prompt(self):
        from prompt.builder import PromptBuilder
        prompt = PromptBuilder().build_system(continuity="Ongoing projects:\n  - T8")
        assert "CONTINUITY" in prompt
        assert "Ongoing projects:" in prompt

    def test_prompt_builder_skips_an_empty_brief(self):
        from prompt.builder import PromptBuilder
        assert "CONTINUITY" not in PromptBuilder().build_system(continuity="")

    def test_settings_expose_the_check_interval(self):
        from config.settings import Settings
        assert Settings.SCHEDULER_CONTINUITY_CHECK_INTERVAL > 0
