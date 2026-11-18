"""T4 — silent research: lifecycle, artifacts, gates, honesty, events."""
from pathlib import Path

from research.artifacts import ResearchArtifacts
from research.engine import ResearchEngine
from research.fetch import extract_text, fetch_text
from research.models import QUEUED, RUNNING, ResearchJob
from research.store import ResearchStore


def _fetcher(url, timeout=1, max_chars=8000):
    return {
        "url": url,
        "final_url": url,
        "title": "Page for " + url,
        "text": "Alpha beta gamma. " * 80,
        "chars": 1440,
        "truncated": False,
        "error": "",
    }


def _failing_fetcher(url, timeout=1, max_chars=8000):
    return {"url": url, "final_url": url, "title": "", "text": "", "chars": 0,
            "truncated": False, "error": "URLError: blocked"}


def _searcher(query, limit=5, endpoint="", timeout=0):
    return {"results": [{"url": "https://example.com/a", "title": "A"}], "error": ""}


def _make_engine(tmp_path, **kwargs):
    store = ResearchStore(tmp_path / "jobs.json")
    artifacts = ResearchArtifacts(tmp_path / "artifacts")
    defaults = dict(store=store, artifacts=artifacts, fetcher=_fetcher,
                    searcher=_searcher, worker=False, browser_mode="urllib")
    defaults.update(kwargs)
    return ResearchEngine(**defaults)


def test_job_lifecycle_writes_and_verifies_artifact(tmp_path):
    engine = _make_engine(tmp_path)
    started = engine.start("test topic", depth="quick", urls=["https://example.com/a"])
    assert "job" in started
    result = engine.process_next()
    assert result["status"] == "done"
    artifact = Path(result["artifact"])
    assert artifact.exists()
    text = artifact.read_text(encoding="utf-8")
    assert text.startswith("---") and "## Findings" in text
    assert "https://example.com/a" in text
    assert engine.status()["ready"] == 1


def test_query_only_job_uses_search(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start("searchable query")
    result = engine.process_next()
    assert result["status"] == "done"
    assert result["sources"] == 1


def test_search_disabled_fails_honestly(tmp_path):
    engine = _make_engine(tmp_path, search_enabled=False)
    refused = engine.start("query only")
    assert refused["error"] == "search disabled; provide seed URLs"


def test_unreadable_sources_mark_job_failed(tmp_path):
    engine = _make_engine(tmp_path, fetcher=_failing_fetcher)
    engine.start("dead sources", urls=["https://example.com/dead"])
    result = engine.process_next()
    assert result["status"] == "failed"
    assert "no readable sources" in result["error"]


def test_artifact_write_failure_is_honest(tmp_path):
    blocked = tmp_path / "not-a-dir"
    blocked.write_text("x", encoding="utf-8")
    engine = _make_engine(tmp_path, artifacts=ResearchArtifacts(blocked / "research"))
    engine.start("artifact failure", urls=["https://example.com/a"])
    result = engine.process_next()
    assert result["status"] == "failed"


def test_autonomous_start_respects_quiet_mode(tmp_path):
    class _Presence:
        quiet_mode = True
        activity = "idle"

    engine = _make_engine(tmp_path, presence=_Presence())
    refused = engine.start("background research", urls=["https://example.com/a"], autonomous=True)
    assert refused["error"] == "quiet_mode"
    manual = engine.start("manual research", urls=["https://example.com/a"])
    assert "job" in manual


def test_autonomous_start_respects_activity_class(tmp_path):
    class _Presence:
        quiet_mode = False
        activity = "coding"

    engine = _make_engine(tmp_path, presence=_Presence())
    refused = engine.start("background research", urls=["https://example.com/a"], autonomous=True)
    assert refused["error"] == "activity_coding"


def test_cancel_queued_job(tmp_path):
    engine = _make_engine(tmp_path)
    job = engine.start("to cancel", urls=["https://example.com/a"])["job"]
    assert engine.cancel(job["id"]) == {"cancelled": job["id"]}
    assert engine.process_next() is None
    assert engine.get(job["id"])["status"] == "cancelled"


def test_interrupted_job_is_requeued_at_boot(tmp_path):
    store = ResearchStore(tmp_path / "jobs.json")
    job = ResearchJob(query="crashed", status=RUNNING, step=2)
    store.upsert(job)
    engine = ResearchEngine(
        store=store,
        artifacts=ResearchArtifacts(tmp_path / "artifacts"),
        fetcher=_fetcher, searcher=_searcher, worker=False,
    )
    assert engine.resumed == 1
    assert engine.get(job.id)["status"] == QUEUED
    assert engine.process_next()["status"] == "done"


def test_report_marks_reported_and_brief_line_clears(tmp_path):
    engine = _make_engine(tmp_path)
    engine.start("brief me", urls=["https://example.com/a"])
    result = engine.process_next()
    assert "brief me" in engine.brief_line()
    report = engine.report(result["id"])
    assert report["query"] == "brief me" and "## Findings" in report["text"]
    assert engine.brief_line() == ""


def test_events_are_published(tmp_path):
    class _Bus:
        def __init__(self):
            self.messages = []

        def publish_message(self, message, wait=True):
            self.messages.append(message)

    bus = _Bus()
    engine = _make_engine(tmp_path, event_bus=bus)
    engine.start("evented", urls=["https://example.com/a"])
    engine.process_next()
    topics = [getattr(message, "type", "") for message in bus.messages]
    assert "data.research.started" in topics
    assert "data.research.source_fetched" in topics
    assert "data.research.finished" in topics
    assert "state.research.updated" in topics


def test_extract_text_strips_scripts_and_prefers_article():
    html = """
    <html><head><title>Doc</title><script>alert('x')</script></head>
    <body><nav>menu</nav><article><h1>Head</h1><p>Body text.</p></article></body>
    </html>
    """
    title, text = extract_text(html)
    assert title == "Doc"
    assert "Body text." in text
    assert "alert" not in text and "menu" not in text


def test_fetch_refuses_loopback():
    result = fetch_text("http://127.0.0.1:9/", timeout=0.2)
    assert result["error"]
    assert "Blocked non-public target" in result["error"]


def test_research_routes_require_auth_when_gated(monkeypatch):
    from fastapi.testclient import TestClient

    from api.auth import api_auth_required
    from api.server import app
    from app import config_loader

    monkeypatch.setattr(config_loader, "API_HOST", "0.0.0.0")
    monkeypatch.setattr(config_loader, "API_REQUIRE_AUTH", False)
    api_auth_required.warned = False
    try:
        client = TestClient(app)
        assert client.get("/api/research").status_code == 401
        assert client.post("/api/research", json={"query": "x"}).status_code == 401
    finally:
        api_auth_required.warned = False

def test_browser_fetcher_override_is_used(tmp_path):
    calls = []

    def _browser(url, timeout=0, max_chars=8000):
        calls.append(url)
        return {"url": url, "final_url": url, "title": "Browser", "text": "Rendered text. " * 30,
                "chars": 450, "truncated": False, "error": ""}

    engine = _make_engine(tmp_path, browser_mode="playwright", browser_fetcher=_browser)
    engine.start("browser job", urls=["https://example.com/b"])
    result = engine.process_next()
    assert result["status"] == "done"
    assert calls == ["https://example.com/b"]


def test_browser_failure_falls_back_to_http(tmp_path):
    def _broken(url, timeout=0, max_chars=8000):
        return {"url": url, "text": "", "error": "navigation timeout"}

    engine = _make_engine(tmp_path, browser_mode="auto", browser_fetcher=_broken)
    engine.start("fallback job", urls=["https://example.com/c"])
    result = engine.process_next()
    assert result["status"] == "done"


def test_playwright_mode_without_package_fails_honestly(tmp_path, monkeypatch):
    import research.browser as browser_mod
    monkeypatch.setattr(browser_mod, "playwright_available", lambda: False)
    engine = _make_engine(tmp_path, browser_mode="playwright")
    engine.start("missing browser", urls=["https://example.com/d"])
    result = engine.process_next()
    assert result["status"] == "failed"


def test_idle_cycle_starts_research_job(tmp_path):
    from partner.cycles import IdleWorkCycle

    class _Commitment:
        id = "c1"
        promise = "Research forex trading basics"

    class _Commitments:
        def due(self, now=None):
            return [_Commitment()]

    class _Projects:
        def list(self, include_terminal=False):
            return []

    class _Checkpoints:
        def list(self):
            return []

    class _Continuity:
        commitments = _Commitments()
        projects = _Projects()
        checkpoints = _Checkpoints()

    class _Presence:
        quiet_mode = False
        activity = "idle"

    class _Actions:
        def register_verifier(self, name, verifier):
            self.verifier = (name, verifier)

        def execute(self, *args, **kwargs):
            raise AssertionError("research items must not fall through to plan-only")

    engine = _make_engine(tmp_path)
    cycle = IdleWorkCycle(
        continuity=_Continuity(), presence=_Presence(), actions=_Actions(),
        research=engine,
    )
    summary = cycle.run()
    assert summary["planned"] == 1
    assert summary["records"][0]["action_type"] == "research"
    assert engine.status()["queued"] == 1
    assert engine.process_next()["status"] == "done"
