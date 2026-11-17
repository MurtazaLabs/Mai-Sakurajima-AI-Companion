"""T7 · Self — own-code index, health/error feeds, proactive self-diagnosis.

The pillar's guarantee is negative-shaped: she reads and diagnoses, and nothing
applies a fix. These tests pin the index facts, the feed grouping, the finding
shape (``auto_apply`` is always False) and the boundary that survives every
entry point (tools, REST, boot).
"""
import json

import pytest

_BRAIN = '''"""Brain module — cognition entry point."""
import os
import logging

logger = logging.getLogger(__name__)


class Brain:
    """Holds the cognitive loop."""

    def think(self, text):
        return text

    async def reflect(self):
        return None


def helper(value):
    return value
'''

_CHAT = '''"""Chat surface."""
from core.brain import Brain


def respond(text):
    return Brain().think(text)
'''


@pytest.fixture()
def project(tmp_path):
    root = tmp_path / "proj"
    (root / "core").mkdir(parents=True)
    (root / "api").mkdir()
    (root / "mai_env").mkdir()
    (root / "data").mkdir()
    (root / "core" / "brain.py").write_text(_BRAIN, encoding="utf-8")
    (root / "api" / "__init__.py").write_text("", encoding="utf-8")
    (root / "api" / "chat.py").write_text(_CHAT, encoding="utf-8")
    (root / "mai_env" / "venv_lib.py").write_text("x = 1\n", encoding="utf-8")
    (root / "data" / "generated.py").write_text("x = 1\n", encoding="utf-8")
    return root


@pytest.fixture()
def index(project, tmp_path):
    from self_awareness.code_index import OwnCodeIndex
    return OwnCodeIndex(
        root=project,
        store_path=tmp_path / "code_index.json",
        excludes={"mai_env", "data", "__pycache__"},
    )


def _log(tmp_path, lines):
    path = tmp_path / "mai.log"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _error(line="2026-11-17 10:00:00 | ERROR    | STT model failed to load"):
    return line


# ---------------------------------------------------------------------------
#  Own-code index
# ---------------------------------------------------------------------------

class TestOwnCodeIndex:

    def test_indexes_the_project_and_skips_excluded_trees(self, index):
        summary = index.refresh()
        modules = {entry["module"] for entry in index.entries().values()}
        assert {"core.brain", "api", "api.chat"} <= modules
        assert not any("mai_env" in module for module in modules)
        assert not any(module.startswith("data") for module in modules)
        assert summary["modules"] == 3
        assert summary["parse_errors"] == 0

    def test_parses_structure(self, index):
        index.refresh()
        entry = index.entries()["core/brain.py"]
        assert entry["module"] == "core.brain"
        assert entry["classes"] == ["Brain"]
        assert "helper" in entry["functions"]
        assert "Brain.think" in entry["functions"]
        assert "Brain.reflect" in entry["functions"]
        assert entry["imports"] == ["logging", "os"]
        assert entry["docstring"] == "Brain module — cognition entry point."
        assert entry["lines"] > 10
        assert entry["sha256"]
        assert "__init__.py" not in entry["path"]

    def test_package_init_uses_the_package_name(self, index):
        index.refresh()
        assert index.entries()["api/__init__.py"]["module"] == "api"

    def test_utf8_bom_is_not_a_syntax_error(self, project, index):
        (project / "bommy.py").write_bytes(
            b"\xef\xbb\xbf" + b'"""BOM module."""\n\ndef ok():\n    return 1\n'
        )
        summary = index.refresh()
        assert summary["parse_errors"] == 0
        assert "ok" in index.entries()["bommy.py"]["functions"]
        assert not index.read_module("bommy.py")["content"].startswith("\ufeff")

    def test_syntax_error_is_recorded_not_raised(self, project, index):
        (project / "broken.py").write_text("def broken(:\n", encoding="utf-8")
        summary = index.refresh()
        assert summary["parse_errors"] == 1
        stats = index.stats()
        assert "broken.py" in stats["parse_errors"]
        assert "syntax error" in stats["parse_errors"]["broken.py"]
        assert index.entries()["broken.py"]["error"]

    def test_second_refresh_is_incremental(self, index):
        index.refresh()
        second = index.refresh()
        assert second["added"] == 0
        assert second["changed"] == 0
        assert second["removed"] == 0
        assert second["modules"] == 3

    def test_changed_file_is_reparsed(self, project, index):
        index.refresh()
        (project / "core" / "brain.py").write_text(_BRAIN + "\n\ndef extra():\n    pass\n", encoding="utf-8")
        summary = index.refresh()
        assert summary["changed"] == 1
        assert "extra" in index.entries()["core/brain.py"]["functions"]

    def test_deleted_file_is_removed(self, project, index):
        index.refresh()
        (project / "api" / "chat.py").unlink()
        summary = index.refresh()
        assert summary["removed"] == 1
        assert "api/chat.py" not in index.entries()

    def test_force_refresh_reparses_everything(self, index):
        index.refresh()
        summary = index.refresh(force=True)
        assert summary["changed"] == summary["modules"]

    def test_stale_detection(self, project, index):
        index.refresh()
        assert index.stats()["stale"] == 0
        (project / "core" / "brain.py").write_text(_BRAIN + "\n# touched\n", encoding="utf-8")
        assert index.stats()["stale"] == 1

    def test_search_by_symbol_module_and_docstring(self, index):
        index.refresh()
        hits = index.search("Brain")
        assert hits
        assert hits[0]["path"] == "core/brain.py"
        assert index.search("core.brain")[0]["module"] == "core.brain"
        assert index.search("cognition entry point")[0]["path"] == "core/brain.py"
        assert index.search("") == []
        assert index.search("nothing-matches-this") == []

    def test_search_limit(self, index):
        index.refresh()
        assert len(index.search("a", limit=1)) == 1

    def test_read_module_by_path_and_module_name(self, index):
        index.refresh()
        by_path = index.read_module("core/brain.py")
        by_name = index.read_module("core.brain")
        assert "class Brain" in by_path["content"]
        assert by_path["path"] == by_name["path"] == "core/brain.py"
        assert by_path["module"] == "core.brain"

    def test_read_module_truncates(self, index):
        index.refresh()
        result = index.read_module("core/brain.py", max_lines=2)
        assert result["truncated"] is True
        assert result["returned"] == 2

    def test_read_module_refuses_escapes(self, project, tmp_path, index):
        index.refresh()
        (tmp_path / "outside.py").write_text("x = 1\n", encoding="utf-8")
        assert "error" in index.read_module("../outside.py")
        assert "error" in index.read_module(str(project / "core" / "brain.py"))
        assert "absolut" in index.read_module("C:/Windows/x.py")["error"]
        assert "no such module" in index.read_module("does/not/exist.py")["error"]

    def test_read_module_refuses_non_python(self, project, index):
        (project / "notes.txt").write_text("hello", encoding="utf-8")
        assert "Python" in index.read_module("notes.txt")["error"]

    def test_corrupt_index_document_recovers(self, project, tmp_path):
        from self_awareness.code_index import OwnCodeIndex
        path = tmp_path / "code_index.json"
        path.write_text("{not json", encoding="utf-8")
        rebuilt = OwnCodeIndex(root=project, store_path=path, excludes={"mai_env", "data"})
        assert rebuilt.refresh()["modules"] == 3


# ---------------------------------------------------------------------------
#  Health / error feeds
# ---------------------------------------------------------------------------

class TestHealthErrorFeeds:

    def test_groups_repeated_signatures(self, tmp_path):
        from self_awareness.feeds import HealthErrorFeeds
        path = _log(tmp_path, [
            "2026-11-17 10:00:00 | ERROR    | STT failed on port 1234",
            "2026-11-17 10:01:00 | INFO     | all good",
            "2026-11-17 10:02:00 | ERROR    | STT failed on port 5678",
            "2026-11-17 10:03:00 | ERROR    | STT failed on port 9999",
        ])
        errors = HealthErrorFeeds(log_path=path).recent_errors()
        assert errors["available"] is True
        assert errors["total"] == 3
        assert len(errors["groups"]) == 1
        group = errors["groups"][0]
        assert group["count"] == 3
        assert "STT failed" in group["signature"]
        assert len(group["examples"]) <= 3

    def test_traceback_lines_count_as_errors(self, tmp_path):
        from self_awareness.feeds import HealthErrorFeeds
        path = _log(tmp_path, [
            "Traceback (most recent call last):",
            "2026-11-17 10:00:00 | INFO     | unrelated",
        ])
        errors = HealthErrorFeeds(log_path=path).recent_errors()
        assert errors["total"] == 1

    def test_missing_log_is_reported_not_raised(self, tmp_path):
        from self_awareness.feeds import HealthErrorFeeds
        errors = HealthErrorFeeds(log_path=tmp_path / "absent.log").recent_errors()
        assert errors["available"] is False
        assert errors["total"] == 0
        assert errors["groups"] == []

    def test_tail_is_bounded_and_truncated_flag_set(self, tmp_path):
        from self_awareness.feeds import HealthErrorFeeds
        filler = ["2026-11-17 09:00:00 | INFO     | padding %d" % n for n in range(400)]
        path = _log(tmp_path, filler + [_error()])
        errors = HealthErrorFeeds(log_path=path, max_log_bytes=4096).recent_errors()
        assert errors["truncated"] is True
        assert errors["scanned_bytes"] <= 4096
        assert errors["total"] >= 1

    def test_group_limit(self, tmp_path):
        from self_awareness.feeds import HealthErrorFeeds
        names = ["alpha", "beta", "gamma", "delta", "epsilon"]
        lines = [
            _error(f"2026-11-17 10:00:0{n} | ERROR    | {name} failure")
            for n, name in enumerate(names)
        ]
        errors = HealthErrorFeeds(log_path=_log(tmp_path, lines)).recent_errors(limit=2)
        assert len(errors["groups"]) == 2

    def test_health_snapshot_exposes_unhealthy_components(self):
        from observability.health import HealthRegistry
        from self_awareness.feeds import HealthErrorFeeds
        registry = HealthRegistry()
        registry.register("stt")
        registry.report_error("stt", "model missing")
        registry.report_error("stt", "model missing again")
        health = HealthErrorFeeds(health_registry=registry).health()
        assert health["available"] is True
        assert health["summary"]["error"] == 1
        assert [item["name"] for item in health["unhealthy"]] == ["stt"]
        assert health["unhealthy"][0]["status"] == "error"
        assert len(health["errors"]) == 2

    def test_health_without_registry(self):
        from self_awareness.feeds import HealthErrorFeeds
        health = HealthErrorFeeds().health()
        assert health["available"] is False
        assert health["unhealthy"] == []

    def test_registry_errors_are_read_only_copies(self):
        from observability.health import HealthRegistry
        registry = HealthRegistry()
        registry.report_error("voice", "device busy")
        rows = registry.recent_errors(5)
        rows[0]["error"] = "tampered"
        assert registry.errors("voice")[0]["error"] == "device busy"

    def test_stats_shape(self, tmp_path):
        from self_awareness.feeds import HealthErrorFeeds
        stats = HealthErrorFeeds(log_path=_log(tmp_path, [_error()])).stats()
        assert stats["log_available"] is True
        assert stats["error_lines"] == 1
        assert stats["health_available"] is False


# ---------------------------------------------------------------------------
#  Diagnosis
# ---------------------------------------------------------------------------

def _feeds(tmp_path, registry=None, lines=None):
    from self_awareness.feeds import HealthErrorFeeds
    log = _log(tmp_path, lines or []) if lines is not None else tmp_path / "absent.log"
    return HealthErrorFeeds(health_registry=registry, log_path=log)


class TestSelfDiagnosis:

    def test_clean_system_has_no_findings(self, index, tmp_path):
        from self_awareness.diagnosis import SelfDiagnosis
        index.refresh()
        report = SelfDiagnosis(index=index, feeds=_feeds(tmp_path)).analyze()
        assert report["findings"] == []
        assert report["healthy"] is True
        assert report["boundary"] == "read_and_diagnose_only"

    def test_unhealthy_component_is_a_finding(self, index, tmp_path):
        from observability.health import HealthRegistry
        from self_awareness.diagnosis import SelfDiagnosis
        index.refresh()
        registry = HealthRegistry()
        registry.report_error("stt", "model missing")
        report = SelfDiagnosis(index=index, feeds=_feeds(tmp_path, registry)).analyze()
        finding = next(f for f in report["findings"] if f["kind"] == "health")
        assert finding["id"] == "health:stt"
        assert finding["severity"] == "error"
        assert finding["auto_apply"] is False
        assert finding["proposal"]

    def test_repeated_error_signature_is_a_finding(self, index, tmp_path):
        from self_awareness.diagnosis import SelfDiagnosis
        index.refresh()
        lines = [_error(f"2026-11-17 10:0{n}:00 | ERROR    | IMAP login failed {n}") for n in range(3)]
        report = SelfDiagnosis(
            index=index, feeds=_feeds(tmp_path, lines=lines), error_threshold=3,
        ).analyze()
        finding = next(f for f in report["findings"] if f["kind"] == "errors")
        assert finding["severity"] == "warn"
        assert "3×" in finding["title"]
        assert finding["auto_apply"] is False

    def test_single_error_below_threshold_is_ignored(self, index, tmp_path):
        from self_awareness.diagnosis import SelfDiagnosis
        index.refresh()
        report = SelfDiagnosis(
            index=index, feeds=_feeds(tmp_path, lines=[_error()]), error_threshold=3,
        ).analyze()
        assert not [f for f in report["findings"] if f["kind"] == "errors"]

    def test_unparsed_module_is_an_error_finding(self, project, index, tmp_path):
        from self_awareness.diagnosis import SelfDiagnosis
        (project / "broken.py").write_text("def broken(:\n", encoding="utf-8")
        index.refresh()
        report = SelfDiagnosis(index=index, feeds=_feeds(tmp_path)).analyze()
        finding = next(f for f in report["findings"] if f["kind"] == "code")
        assert finding["id"] == "code:broken.py"
        assert finding["severity"] == "error"
        assert "does not parse" in finding["title"]

    def test_stale_index_is_an_info_finding(self, project, index, tmp_path):
        from self_awareness.diagnosis import SelfDiagnosis
        index.refresh()
        (project / "core" / "brain.py").write_text(_BRAIN + "\n# touched\n", encoding="utf-8")
        report = SelfDiagnosis(index=index, feeds=_feeds(tmp_path)).analyze()
        finding = next(f for f in report["findings"] if f["id"] == "index:stale")
        assert finding["severity"] == "info"
        assert report["healthy"] is True

    def test_empty_index_is_a_warning(self, tmp_path):
        from self_awareness.code_index import OwnCodeIndex
        from self_awareness.diagnosis import SelfDiagnosis
        empty = tmp_path / "empty"
        empty.mkdir()
        empty_index = OwnCodeIndex(root=empty, store_path=tmp_path / "empty.json")
        report = SelfDiagnosis(index=empty_index, feeds=_feeds(tmp_path)).analyze()
        finding = next(f for f in report["findings"] if f["id"] == "index:empty")
        assert finding["severity"] == "warn"
        assert report["healthy"] is False

    def test_report_is_appended_as_jsonl(self, index, tmp_path):
        from self_awareness.diagnosis import SelfDiagnosis
        index.refresh()
        path = tmp_path / "diagnoses.jsonl"
        diagnosis = SelfDiagnosis(index=index, feeds=_feeds(tmp_path), store_path=path)
        diagnosis.analyze()
        diagnosis.analyze()
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == 2
        assert "findings" in rows[0] and "counts" in rows[0]

    def test_counts_summary_and_text(self, index, tmp_path):
        from observability.health import HealthRegistry
        from self_awareness.diagnosis import SelfDiagnosis
        index.refresh()
        registry = HealthRegistry()
        registry.report_error("voice", "device busy")
        diagnosis = SelfDiagnosis(index=index, feeds=_feeds(tmp_path, registry))
        report = diagnosis.analyze()
        assert report["counts"]["error"] == 1
        assert diagnosis.summary()["findings"] == len(report["findings"])
        text = diagnosis.report_text()
        assert "Self-diagnosis" in text
        assert "voice" in text

    def test_clean_report_text(self, index, tmp_path):
        from self_awareness.diagnosis import SelfDiagnosis
        index.refresh()
        diagnosis = SelfDiagnosis(index=index, feeds=_feeds(tmp_path))
        diagnosis.analyze()
        assert "nothing to report" in diagnosis.report_text()

    def test_findings_are_stable_ids_across_runs(self, index, tmp_path):
        from observability.health import HealthRegistry
        from self_awareness.diagnosis import SelfDiagnosis
        index.refresh()
        registry = HealthRegistry()
        registry.report_error("stt", "boom")
        diagnosis = SelfDiagnosis(index=index, feeds=_feeds(tmp_path, registry))
        first = [f["id"] for f in diagnosis.analyze()["findings"]]
        second = [f["id"] for f in diagnosis.analyze()["findings"]]
        assert first == second


# ---------------------------------------------------------------------------
#  Engine
# ---------------------------------------------------------------------------

def _engine(project, tmp_path, bus=None, registry=None, interval=3600.0,
            lines=None, clock=None):
    from self_awareness.engine import SelfAwarenessEngine
    return SelfAwarenessEngine(
        root=project,
        store_dir=tmp_path / "self",
        event_bus=bus,
        health_registry=registry,
        log_path=_log(tmp_path, lines) if lines is not None else tmp_path / "absent.log",
        diagnosis_interval=interval,
        error_threshold=3,
        clock=clock,
    )


class TestSelfAwarenessEngine:

    def test_refresh_index_publishes(self, project, tmp_path):
        from core.event_bus import EventBus
        from core.event_specs import SELF_INDEX_BUILT, register_event_specs
        bus = EventBus()
        register_event_specs(bus)
        seen = []
        bus.subscribe(SELF_INDEX_BUILT, lambda payload: seen.append(payload))
        engine = _engine(project, tmp_path, bus=bus)
        summary = engine.refresh_index()
        assert summary["modules"] == 3
        assert seen and seen[0]["modules"] == 3

    def test_diagnose_publishes_and_records(self, project, tmp_path):
        from core.event_bus import EventBus
        from core.event_specs import SELF_DIAGNOSIS, register_event_specs
        bus = EventBus()
        register_event_specs(bus)
        seen = []
        bus.subscribe(SELF_DIAGNOSIS, lambda payload: seen.append(payload))
        engine = _engine(project, tmp_path, bus=bus)
        engine.refresh_index()
        report = engine.diagnose()
        assert report["boundary"] == "read_and_diagnose_only"
        assert seen and seen[0]["findings"] == len(report["findings"])

    def test_tick_is_gated_by_the_interval(self, project, tmp_path):
        engine = _engine(project, tmp_path, interval=3600.0)
        first = engine.tick(now=1000.0)
        assert first["diagnosed"] is True
        assert engine.tick(now=1100.0)["reason"] == "not_due"
        assert engine.tick(now=5000.0)["diagnosed"] is True

    def test_status_exposes_boundary_and_index(self, project, tmp_path):
        engine = _engine(project, tmp_path)
        engine.refresh_index()
        status = engine.status()
        assert status["boundary"] == "read_and_diagnose_only"
        assert status["index"]["modules"] == 3
        assert "diagnosis" in status and "health" in status

    def test_brief_line_is_read_only(self, project, tmp_path):
        engine = _engine(project, tmp_path)
        engine.refresh_index()
        line = engine.brief_line()
        assert "3 modules indexed" in line
        assert "Read-only" in line

    def test_brief_line_reports_unhealthy(self, project, tmp_path):
        from observability.health import HealthRegistry
        registry = HealthRegistry()
        registry.report_error("stt", "boom")
        engine = _engine(project, tmp_path, registry=registry)
        assert "stt:error" in engine.brief_line()

    def test_errors_and_search_surface(self, project, tmp_path):
        engine = _engine(project, tmp_path, lines=[_error()])
        engine.refresh_index()
        assert engine.errors()["total"] == 1
        assert engine.search_code("Brain")[0]["path"] == "core/brain.py"
        assert "class Brain" in engine.read_code("core.brain")["content"]

    def test_report_uses_last_diagnosis(self, project, tmp_path):
        engine = _engine(project, tmp_path)
        engine.refresh_index()
        engine.diagnose()
        assert engine.report().startswith("Self-diagnosis")


# ---------------------------------------------------------------------------
#  Tools
# ---------------------------------------------------------------------------

@pytest.fixture()
def tools(project, tmp_path):
    from agency.registry import ToolRegistry
    from self_awareness.tools import register_self_tools
    engine = _engine(project, tmp_path)
    engine.refresh_index()
    registry = ToolRegistry()
    count = register_self_tools(registry, engine)
    return registry, engine, count


class TestSelfTools:

    def test_registers_seven_self_tools(self, tools):
        registry, _engine, count = tools
        assert count == 7
        names = set(registry.list(category="self"))
        assert names == {
            "self_status", "self_index", "self_read_code", "self_health",
            "self_errors", "self_diagnose", "self_report",
        }

    def test_self_index_searches_own_code(self, tools):
        registry, _engine, _count = tools
        result = registry.call("self_index", query="Brain")["result"]
        assert result["count"] >= 1
        assert result["modules"][0]["path"] == "core/brain.py"

    def test_self_read_code_reads_and_refuses_escape(self, tools):
        registry, _engine, _count = tools
        assert "class Brain" in registry.call("self_read_code", module="core/brain.py")["result"]["content"]
        refused = registry.call("self_read_code", module="../outside.py")["result"]
        assert "error" in refused

    def test_self_diagnose_reports_the_boundary(self, tools):
        registry, _engine, _count = tools
        result = registry.call("self_diagnose")["result"]
        assert result["boundary"] == "read_and_diagnose_only"
        assert "no fix is applied" in result["note"]
        assert all(finding["auto_apply"] is False for finding in result["findings"])

    def test_self_status_health_errors_report(self, tools):
        registry, _engine, _count = tools
        assert registry.call("self_status")["result"]["boundary"] == "read_and_diagnose_only"
        assert "components" in registry.call("self_health")["result"]
        assert "groups" in registry.call("self_errors")["result"]
        assert "Self-diagnosis" in registry.call("self_report")["result"]["text"]


# ---------------------------------------------------------------------------
#  Boot wiring
# ---------------------------------------------------------------------------

class TestSelfBoot:

    @staticmethod
    def _stub(monkeypatch, project):
        from types import SimpleNamespace
        import app.builders.self_awareness as builder
        from agency.registry import ToolRegistry
        from core.event_bus import EventBus
        from core.event_specs import register_event_specs
        from observability.health import HealthRegistry

        monkeypatch.setattr(builder, "ROOT_DIR", project)
        bus = EventBus()
        register_event_specs(bus)
        app = SimpleNamespace(
            event_bus=bus,
            brain=SimpleNamespace(),
            partner=SimpleNamespace(),
            tool_registry=ToolRegistry(),
            health_registry=HealthRegistry(),
        )
        builder.build(app)
        return app

    def test_builder_wires_engine_tools_health_and_partner(self, monkeypatch, project):
        app = self._stub(monkeypatch, project)
        assert app.self_awareness is not None
        assert app.self_awareness.index.stats()["modules"] == 3
        assert len(app.tool_registry.list(category="self")) == 7
        assert app.health_registry.status("self_awareness")["status"] == "ok"
        assert app.brain.self_awareness is app.self_awareness
        assert app.partner.self_awareness is app.self_awareness

    def test_partner_briefing_carries_the_self_line(self, monkeypatch, project):
        """The ritual brief picks up the line the builder attached."""
        app = self._stub(monkeypatch, project)
        from partner.engine import PartnerEngine
        from partner.calendar import IcsCalendar
        engine = PartnerEngine(
            store_path=str(project / "partner.json"),
            audit_path=str(project / "partner_actions.jsonl"),
            calendar=IcsCalendar(project / "calendar.ics"),
        )
        engine.self_awareness = app.self_awareness
        assert "Self-check" in engine.briefing()

    def test_state_topic_is_streamed(self):
        from api.stream_manager import STREAM_TOPICS
        from core.event_specs import STATE_SELF_UPDATED
        assert STATE_SELF_UPDATED in STREAM_TOPICS


# ---------------------------------------------------------------------------
#  REST
# ---------------------------------------------------------------------------

@pytest.fixture()
def api_client(project, tmp_path):
    from fastapi.testclient import TestClient

    from api.server import _require_auth, app, mai

    engine = _engine(project, tmp_path)
    engine.refresh_index()
    previous_engine, previous_brain = mai.self_awareness, mai.brain
    mai.self_awareness = engine
    app.dependency_overrides[_require_auth] = lambda: None
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.pop(_require_auth, None)
        mai.self_awareness = previous_engine
        mai.brain = previous_brain


class TestSelfAPI:

    def test_status(self, api_client):
        body = api_client.get("/api/self/status").json()
        assert body["boundary"] == "read_and_diagnose_only"
        assert body["index"]["modules"] == 3

    def test_index_search(self, api_client):
        body = api_client.get("/api/self/index", params={"query": "Brain"}).json()
        assert body["count"] >= 1
        assert body["modules"][0]["path"] == "core/brain.py"

    def test_read_code_and_refusal(self, api_client):
        body = api_client.get("/api/self/code", params={"module": "core/brain.py"}).json()
        assert "class Brain" in body["content"]
        refused = api_client.get("/api/self/code", params={"module": "../outside.py"})
        assert refused.status_code == 400
        assert "error" in refused.json()

    def test_health_and_errors(self, api_client):
        assert "components" in api_client.get("/api/self/health").json()
        assert "groups" in api_client.get("/api/self/errors").json()

    def test_diagnose_and_report(self, api_client):
        report = api_client.post("/api/self/diagnose").json()
        assert report["boundary"] == "read_and_diagnose_only"
        assert "counts" in report
        text = api_client.get("/api/self/report").json()["text"]
        assert "Self-diagnosis" in text

    def test_unavailable_engine_is_reported(self, api_client):
        from api.server import mai
        mai.self_awareness = None
        mai.brain = None
        assert api_client.get("/api/self/status").json() == {"error": "self_unavailable"}
