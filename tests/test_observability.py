import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from api.server import _build_dashboard_state, MaiAPI, app
from fastapi.testclient import TestClient
from observability.tracer import CognitiveAuditor


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _mock_brain(**overrides):
    brain = MagicMock()
    brain.think.return_value = overrides.get("think_response", "Hello from Mai")
    state = MagicMock()
    state.emotion = MagicMock()
    state.emotion.model_dump.return_value = {"happy": 0.5, "lonely": 0.0}
    state.relationship_scores = MagicMock()
    state.relationship_scores.model_dump.return_value = {"trust": 0.5, "closeness": 0.3}
    state.runtime = MagicMock()
    state.runtime.model_dump.return_value = {"current_session_turns": 5, "user_active": True}
    brain.state = state
    brain.personality_state = MagicMock()
    brain.personality_state.state = {"openness": 0.6, "conscientiousness": 0.7}
    brain.cognitive = MagicMock()
    brain.cognitive.get.return_value = {"focus": "test"}
    return brain


def _patch_mai(**attrs):
    """Context manager that patches api.server.mai with given attributes."""
    return patch.multiple("api.server.mai", **attrs, create=True)


client = TestClient(app)


# ──────────────────────────────────────────────
#  _build_dashboard_state tests
# ──────────────────────────────────────────────

class TestBuildDashboardState:

    def test_with_full_brain_and_managers(self):
        brain = _mock_brain()
        goal_manager = MagicMock()
        goal_manager.stats.return_value = {"active": 3, "completed": 10, "total": 13}
        world_model = MagicMock()
        world_model.stats.return_value = {"total_entities": 5, "categories": {}}
        world_model.all_entities.return_value = [{"name": "John", "category": "person"}]
        with _patch_mai(brain=brain, goal_manager=goal_manager, world_model=world_model,
                        _ready=True):
            state = _build_dashboard_state()

        assert "emotion" in state
        assert state["emotion"]["happy"] == 0.5
        assert "relationship" in state
        assert state["relationship"]["trust"] == 0.5
        assert "goals" in state
        assert state["goals"]["active"] == 3
        assert state["world"]["total_entities"] == 5
        assert state["personality"]["openness"] == 0.6

    def test_without_brain(self):
        with _patch_mai(brain=None, goal_manager=None, world_model=None, _ready=False):
            state = _build_dashboard_state()
        assert "emotion" not in state
        assert "relationship" not in state

    def test_handles_brain_attribute_errors(self):
        brain = MagicMock(spec=[])
        with _patch_mai(brain=brain, goal_manager=None, world_model=None, _ready=True):
            state = _build_dashboard_state()
        assert "emotion" not in state


# ──────────────────────────────────────────────
#  MaiAPI unit tests
# ──────────────────────────────────────────────

class TestMaiAPI:

    def test_chat_not_ready(self):
        api = MaiAPI()
        api._ready = False
        result = api.chat("hello")
        assert result == {"error": "system_not_ready"}

    def test_chat_no_brain(self):
        api = MaiAPI()
        api._ready = True
        api.brain = None
        result = api.chat("hello")
        assert result == {"error": "system_not_ready"}

    def test_chat_success(self):
        brain = MagicMock()
        brain.think.return_value = "Hello from Mai"
        api = MaiAPI()
        api._ready = True
        api.brain = brain
        result = api.chat("hi")
        brain.think.assert_called_once_with("hi", user_id="")
        assert result == {"response": "Hello from Mai", "status": "ok"}

    def test_chat_non_string_response(self):
        brain = MagicMock()
        brain.think.return_value = 42
        api = MaiAPI()
        api._ready = True
        api.brain = brain
        result = api.chat("hi")
        assert result == {"response": "42", "status": "ok"}

    def test_chat_brain_exception(self):
        brain = MagicMock()
        brain.think.side_effect = RuntimeError("brain failure")
        api = MaiAPI()
        api._ready = True
        api.brain = brain
        result = api.chat("hi")
        # S-5: backend exception details must not leak to the client
        assert result["error"] == "internal_error"

    def test_status_not_ready(self):
        api = MaiAPI()
        api._ready = False
        assert api.status() == {"ready": False}

    def test_status_ready(self):
        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.emotion.get.return_value = {"happy": 0.5}
        api = MaiAPI()
        api._ready = True
        api.brain = brain
        result = api.status()
        assert result["ready"] is True
        assert result["emotion"]["happy"] == 0.5

    def test_memory_query_not_ready(self):
        api = MaiAPI()
        api._ready = False
        result = api.memory_query("test")
        assert result == {"error": "system_not_ready"}

    def test_memory_query_success(self):
        brain = MagicMock()
        brain.retriever = None
        brain.memory = MagicMock()
        brain.memory.recall.return_value = ["result1"]
        api = MaiAPI()
        api._ready = True
        api.brain = brain
        result = api.memory_query("test", top_k=3)
        brain.memory.recall.assert_called_once_with("test", limit=3)
        assert result["results"] == ["result1"]

    def test_memory_query_recall_string(self):
        brain = MagicMock()
        brain.retriever = None
        brain.memory = MagicMock()
        brain.memory.recall.return_value = "recalled context text"
        api = MaiAPI()
        api._ready = True
        api.brain = brain
        result = api.memory_query("test", top_k=3)
        assert result["results"] == [{"content": "recalled context text"}]

    def test_memory_query_retriever_path(self):
        brain = MagicMock()
        brain.retriever = MagicMock()
        brain.retriever.retrieve.return_value = [
            {"content": "vector hit", "score": 0.91, "source": "vector"},
            {"content": "", "score": 0.8, "source": "belief"},
            {"content": "graph hit", "score": 0.72, "source": "knowledge_graph"},
        ]
        api = MaiAPI()
        api._ready = True
        api.brain = brain
        result = api.memory_query("test", top_k=3)
        brain.retriever.retrieve.assert_called_once_with("test", top_k=3)
        assert result["results"] == [
            {"content": "vector hit", "score": 0.91, "source": "vector"},
            {"content": "graph hit", "score": 0.72, "source": "knowledge_graph"},
        ]

    def test_knowledge_ingest_no_builder(self):
        api = MaiAPI()
        api.knowledge_builder = None
        result = api.knowledge_ingest("test", text="hello")
        assert result == {"error": "knowledge_builder_not_available"}

    def test_knowledge_ingest_with_text(self):
        kb = MagicMock()
        kb.build_from_text.return_value = {"chunks": 3}
        api = MaiAPI()
        api.knowledge_builder = kb
        result = api.knowledge_ingest("manual", text="hello world")
        kb.build_from_text.assert_called_once_with("hello world", source="manual")
        assert result["chunks"] == 3

    def test_knowledge_ingest_no_content(self):
        api = MaiAPI()
        api.knowledge_builder = MagicMock()
        result = api.knowledge_ingest("test")
        assert result == {"error": "no_content_provided"}


# ──────────────────────────────────────────────
#  FastAPI endpoint tests
# ──────────────────────────────────────────────

class TestAPIEndpoints:

    def test_health(self):
        with _patch_mai(_ready=True):
            resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_chat_missing_message(self):
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 422

    def test_chat_success(self):
        brain = MagicMock()
        brain.think.return_value = "Hello from Mai"
        with _patch_mai(_ready=True, brain=brain):
            resp = client.post("/api/chat", json={"message": "hi"})
        assert resp.status_code == 200
        assert resp.json()["response"] == "Hello from Mai"
        brain.think.assert_called_once()
        assert brain.think.call_args[0][0] == "hi"

    def test_chat_brain_error(self):
        brain = MagicMock()
        brain.think.side_effect = RuntimeError("fail")
        with _patch_mai(_ready=True, brain=brain):
            resp = client.post("/api/chat", json={"message": "hi"})
        assert resp.status_code == 500

    def test_status_endpoint(self):
        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.emotion.get.return_value = {"happy": 0.5}
        with _patch_mai(_ready=True, brain=brain, goal_manager=None, world_model=None):
            resp = client.get("/api/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ready"] is True

    def test_memory_no_query(self):
        with _patch_mai(_ready=True, brain=MagicMock()):
            resp = client.get("/api/memory")
        assert resp.status_code == 200

    def test_ingest_no_content(self):
        with _patch_mai(knowledge_builder=MagicMock(), _ready=True):
            resp = client.post("/api/knowledge/ingest", json={"source": "api"})
        assert resp.status_code == 400

    def test_state_endpoint(self):
        brain = _mock_brain()
        with _patch_mai(brain=brain, goal_manager=None, world_model=None, _ready=True):
            resp = client.get("/api/state")
        assert resp.status_code == 200
        data = resp.json()
        assert "emotion" in data

    def test_graph_endpoint(self):
        with _patch_mai(brain=None):
            resp = client.get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("nodes") == []
        assert data.get("edges") == []
        assert "type_breakdown" in data

    def test_dashboard_page(self):
        # OS desktop loads correctly
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Mai" in resp.text or "Desktop" in resp.text


# ──────────────────────────────────────────────
#  CognitiveAuditor tests (unchanged)
# ──────────────────────────────────────────────

class TestCognitiveAuditor:

    def make(self, log_dir=None):
        if log_dir is None:
            log_dir = tempfile.mkdtemp()
        auditor = CognitiveAuditor(log_dir=log_dir)
        return auditor

    def test_begin_cycle_returns_tx_id(self):
        auditor = self.make()
        tx_id = auditor.begin_cycle("hello")
        assert tx_id is not None
        assert len(tx_id) > 0
        assert tx_id in auditor.active_audits
        assert auditor.active_audits[tx_id]["inputs"]["user_raw"] == "hello"

    def test_begin_cycle_empty_input(self):
        auditor = self.make()
        tx_id = auditor.begin_cycle("")
        assert tx_id in auditor.active_audits
        assert auditor.active_audits[tx_id]["inputs"]["user_raw"] == ""

    def test_log_step_appends_to_cognitive_steps(self):
        auditor = self.make()
        tx_id = auditor.begin_cycle("test")
        auditor.log_step(tx_id, "memory_recall", {"recalled": True})
        auditor.log_step(tx_id, "emotion_sync", {"emotion": "happy"})
        steps = auditor.active_audits[tx_id]["cognitive_steps"]
        assert len(steps) == 2
        assert steps[0]["step"] == "memory_recall"
        assert steps[0]["snapshot"] == {"recalled": True}
        assert steps[1]["step"] == "emotion_sync"

    def test_log_step_none_tx_id(self):
        auditor = self.make()
        auditor.log_step(None, "test", {})

    def test_log_unknown_tx_id(self):
        auditor = self.make()
        auditor.log_step("nonexistent", "test", {})

    def test_log_metadata(self):
        auditor = self.make()
        tx_id = auditor.begin_cycle("test")
        auditor.log_metadata(tx_id, "model", "gpt-4")
        assert auditor.active_audits[tx_id]["metadata"]["model"] == "gpt-4"

    def test_log_metadata_none_tx_id(self):
        auditor = self.make()
        auditor.log_metadata(None, "k", "v")

    def test_log_unknown_tx_id_metadata(self):
        auditor = self.make()
        auditor.log_metadata("nonexistent", "k", "v")

    def test_complete_cycle_returns_trail(self):
        auditor = self.make()
        tx_id = auditor.begin_cycle("hello")
        auditor.log_step(tx_id, "reasoning", {"depth": 3})
        with patch.object(CognitiveAuditor, "_flush_to_disk"):
            trail = auditor.complete_cycle(tx_id, "Goodbye")
        assert trail["transaction_id"] == tx_id
        assert trail["inputs"]["user_raw"] == "hello"
        assert trail["outputs"]["mai_raw"] == "Goodbye"
        assert len(trail["cognitive_steps"]) == 1
        assert trail["metrics"]["total_latency_ms"] >= 0
        assert trail["metrics"]["end_time"] is not None
        assert tx_id not in auditor.active_audits

    @patch.object(CognitiveAuditor, "_flush_to_disk")
    def test_complete_cycle_none_tx_id(self, mock_flush):
        auditor = self.make()
        result = auditor.complete_cycle(None, "output")
        assert result == {}
        mock_flush.assert_not_called()

    @patch.object(CognitiveAuditor, "_flush_to_disk")
    def test_complete_unknown_tx_id(self, mock_flush):
        auditor = self.make()
        result = auditor.complete_cycle("nonexistent", "output")
        assert result == {}
        mock_flush.assert_not_called()

    def test_flush_to_disk_writes_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            auditor = CognitiveAuditor(log_dir=tmpdir)
            tx_id = auditor.begin_cycle("hello world")
            trail = {
                "transaction_id": tx_id,
                "inputs": {"user_raw": "hello world"},
                "outputs": {"mai_raw": "hi back"},
                "metrics": {"total_latency_ms": 100},
                "cognitive_steps": [],
                "metadata": {},
            }
            auditor._flush_to_disk(trail)
            files = os.listdir(tmpdir)
            assert len(files) == 1
            assert tx_id in files[0]
            with open(os.path.join(tmpdir, files[0]), "r") as f:
                data = json.load(f)
            assert data["transaction_id"] == tx_id

    def test_ensure_log_directory_creates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = os.path.join(tmpdir, "nested", "audit")
            auditor = CognitiveAuditor(log_dir=log_dir)
            assert os.path.isdir(log_dir)

    def test_flush_redacts_pii_on_disk(self):
        """Raw user/Mai text and snapshot strings must be PII-redacted in the
        persisted file while the in-memory trail keeps raw values (S-3)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auditor = CognitiveAuditor(log_dir=tmpdir)
            tx_id = auditor.begin_cycle(
                "my email is john.doe@example.com call me at +1 555 123 4567 ip 192.168.1.10")
            auditor.log_step(tx_id, "memory_recall",
                             {"text": "contact sarah@test.io", "n": 1})
            trail = {
                "transaction_id": tx_id,
                "inputs": {"user_raw": "my email is john.doe@example.com call me at +1 555 123 4567 ip 192.168.1.10"},
                "outputs": {"mai_raw": "ok, wrote to sarah@test.io"},
                "metrics": {"total_latency_ms": 100},
                "cognitive_steps": [
                    {"step": "memory_recall",
                     "snapshot": {"text": "contact sarah@test.io", "n": 1}},
                ],
                "metadata": {},
            }
            auditor._flush_to_disk(trail)
            files = os.listdir(tmpdir)
            assert len(files) == 1
            with open(os.path.join(tmpdir, files[0]), "r") as f:
                data = json.load(f)
            assert "john.doe@example.com" not in json.dumps(data)
            assert "sarah@test.io" not in json.dumps(data)
            assert "555 123 4567" not in json.dumps(data)
            assert "192.168.1.10" not in json.dumps(data)
            assert "[REDACTED_EMAIL]" in json.dumps(data)
            assert "[REDACTED_PHONE]" in json.dumps(data)
            assert "[REDACTED_IP]" in json.dumps(data)

    def test_flush_redacts_api_key_and_uuid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            auditor = CognitiveAuditor(log_dir=tmpdir)
            tx_id = "11111111-2222-3333-4444-555555555555"
            trail = {
                "transaction_id": tx_id,
                "inputs": {"user_raw": "use sk-1234567890abcdef and id 11223344-5566-7788-99aa-bbccddeeff00"},
                "outputs": {"mai_raw": "done"},
                "metrics": {"total_latency_ms": 1},
                "cognitive_steps": [],
                "metadata": {},
            }
            auditor._flush_to_disk(trail)
            files = os.listdir(tmpdir)
            with open(os.path.join(tmpdir, files[0]), "r") as f:
                data = json.load(f)
            payload = json.dumps(data)
            assert "sk-1234567890abcdef" not in payload
            assert "11223344-5566-7788-99aa-bbccddeeff00" not in payload
            assert "[REDACTED_KEY]" in payload
            # transaction_id stays — it identifies the audit, not user PII
            assert data["transaction_id"] == tx_id

    def test_redact_disabled_keeps_raw(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            auditor = CognitiveAuditor(log_dir=tmpdir, redact_pii=False)
            tx_id = "tx-1"
            trail = {
                "transaction_id": tx_id,
                "inputs": {"user_raw": "email me at a@b.com"},
                "outputs": {"mai_raw": "ok"},
                "metrics": {"total_latency_ms": 1},
                "cognitive_steps": [],
                "metadata": {},
            }
            auditor._flush_to_disk(trail)
            files = os.listdir(tmpdir)
            with open(os.path.join(tmpdir, files[0]), "r") as f:
                data = json.load(f)
            assert "a@b.com" in json.dumps(data)


class TestHealthMetrics:

    def test_health_metrics_endpoint(self):
        with _patch_mai(_ready=True):
            resp = client.get("/api/health/metrics")
        assert resp.status_code == 200
        data = resp.json()
        assert "uptime_seconds" in data
        assert "process" in data
        assert "system" in data
        assert "cpu_percent" in data["system"]
        assert "memory_percent" in data["system"]

    def test_health_endpoint_not_ready(self):
        with _patch_mai(_ready=False):
            resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["ready"] is False

    def test_health_endpoint_ready(self):
        with _patch_mai(_ready=True):
            resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["ready"] is True
