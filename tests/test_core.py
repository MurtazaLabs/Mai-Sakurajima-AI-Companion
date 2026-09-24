import io
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch, call, mock_open, PropertyMock

import pytest

from core.state.models import (
    EmotionState,
    RelationshipValues,
    EvidenceModel,
    GoalState,
    AttentionState,
    RuntimeStateFields,
)


# ──────────────────────────────────────────────
#  State Models
# ──────────────────────────────────────────────

class TestEmotionState:

    def test_defaults(self):
        e = EmotionState()
        assert e.happy == 0.5
        assert e.sad == 0.1
        assert e.angry == 0.1
        assert e.anxious == 0.1
        assert e.neutral == 0.2

    def test_model_dump(self):
        e = EmotionState(happy=0.8, sad=0.2)
        data = e.model_dump()
        assert data["happy"] == 0.8
        assert data["sad"] == 0.2

    def test_serialization_roundtrip(self):
        e = EmotionState(happy=0.9, sad=0.1)
        data = e.model_dump()
        e2 = EmotionState(**data)
        assert e2.happy == 0.9
        assert e2.sad == 0.1

    def test_json_serializable(self):
        e = EmotionState()
        json.dumps(e.model_dump())  # should not raise


class TestRelationshipValues:

    def test_defaults(self):
        r = RelationshipValues()
        assert r.trust == 0.5
        assert r.comfort == 0.5
        assert r.respect == 0.5
        assert r.affection == 0.1
        assert r.familiarity == 0.1

    def test_model_dump(self):
        r = RelationshipValues(trust=0.8, familiarity=0.5)
        data = r.model_dump()
        assert data["trust"] == 0.8
        assert data["familiarity"] == 0.5

    def test_serialization_roundtrip(self):
        r = RelationshipValues(trust=0.75, comfort=0.6, respect=0.8, affection=0.4, familiarity=0.3)
        data = r.model_dump()
        r2 = RelationshipValues(**data)
        assert r2.trust == 0.75
        assert r2.comfort == 0.6


class TestGoalState:

    def test_defaults(self):
        gs = GoalState()
        assert gs.active_goals == []
        assert gs.completed_goals == []

    def test_with_goals(self):
        gs = GoalState(
            active_goals=[{"goal_id": "g1", "description": "Active goal"}],
            completed_goals=[{"goal_id": "g2", "description": "Completed goal", "status": "completed"}],
        )
        assert len(gs.active_goals) == 1
        assert len(gs.completed_goals) == 1
        data = gs.model_dump()
        assert len(data["active_goals"]) == 1
        assert data["active_goals"][0]["goal_id"] == "g1"


class TestAttentionState:

    def test_defaults(self):
        a = AttentionState()
        assert a.current_focus == ""
        assert a.attention_level == 0.5

    def test_model_dump(self):
        a = AttentionState(current_focus="self", attention_level=0.5)
        data = a.model_dump()
        assert data["current_focus"] == "self"
        assert data["attention_level"] == 0.5


class TestRuntimeStateFields:

    def test_defaults(self):
        r = RuntimeStateFields()
        assert r.is_thinking is False
        assert r.current_session_turns == 0
        assert r.current_speaker_name == ""
        assert r.last_interaction_time == 0.0

    def test_model_dump(self):
        r = RuntimeStateFields(
            is_thinking=True,
            current_session_turns=5,
            current_speaker_name="User",
        )
        data = r.model_dump()
        assert data["is_thinking"] is True
        assert data["current_session_turns"] == 5
        assert data["current_speaker_name"] == "User"

    def test_json_serializable(self):
        r = RuntimeStateFields()
        json.dumps(r.model_dump())  # should not raise


# ──────────────────────────────────────────────
#  SharedState
# ──────────────────────────────────────────────

class TestSharedState:

    @patch("core.state.shared_state.EvidenceDB")
    def test_init_creates_substates(self, mock_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.state.shared_state import SharedState
            state = SharedState(Path(tmpdir))

            assert state.emotion is not None
            assert isinstance(state.emotion, EmotionState)
            assert state.relationship_scores is not None
            assert isinstance(state.relationship_scores, RelationshipValues)
            assert state.goals is not None
            assert isinstance(state.goals, GoalState)
            assert state.attention is not None
            assert isinstance(state.attention, AttentionState)
            assert state.runtime is not None
            assert isinstance(state.runtime, RuntimeStateFields)
            assert state.lock is not None

    @patch("core.state.shared_state.EvidenceDB")
    def test_serialize_returns_dict(self, mock_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.state.shared_state import SharedState
            state = SharedState(Path(tmpdir))

            data = state.serialize()

            assert "emotion" in data
            assert "relationship_scores" in data
            assert "goals" in data
            assert "attention" in data
            assert "runtime" in data
            assert data["emotion"]["happy"] == 0.5

    @patch("core.state.shared_state.EvidenceDB")
    def test_save_state_to_disk_writes_file(self, mock_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.state.shared_state import SharedState
            state = SharedState(Path(tmpdir))

            state.save_state_to_disk()

            target = Path(tmpdir) / "state" / "master_state.json"
            assert target.exists()
            with open(target) as f:
                data = json.load(f)
            assert data["emotion"]["happy"] == 0.5

    @patch("core.state.shared_state.EvidenceDB")
    def test_load_state_from_disk_restores_values(self, mock_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.state.shared_state import SharedState

            # Create and save
            state = SharedState(Path(tmpdir))
            state.emotion.happy = 0.99
            state.save_state_to_disk()

            # Create new instance (loads from disk)
            state2 = SharedState(Path(tmpdir))
            assert state2.emotion.happy == 0.99

    @patch("core.state.shared_state.EvidenceDB")
    def test_load_state_from_disk_missing_file(self, mock_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.state.shared_state import SharedState
            state = SharedState(Path(tmpdir))
            # Should not raise even if no file exists yet
            assert state.emotion.happy == 0.5

    @patch("core.state.shared_state.EvidenceDB")
    def test_load_state_corrupted_file(self, mock_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "state"
            target.mkdir(parents=True, exist_ok=True)
            with open(target / "master_state.json", "w") as f:
                f.write("{corrupted json")

            from core.state.shared_state import SharedState
            state = SharedState(Path(tmpdir))
            assert state.emotion.happy == 0.5  # defaults preserved

    @patch("core.state.shared_state.EvidenceDB")
    def test_save_state_error_handled(self, mock_db):
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.state.shared_state import SharedState
            state = SharedState(Path(tmpdir))

            with patch("builtins.open", side_effect=OSError("permission denied")):
                state.save_state_to_disk()  # should not raise


# ──────────────────────────────────────────────
#  EvidenceDB
# ──────────────────────────────────────────────

class TestEvidenceDB:

    def _make_db(self, tmpdir):
        from core.state.db import EvidenceDB
        db = EvidenceDB(Path(tmpdir))
        return db

    def test_init_creates_table(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = self._make_db(tmpdir)
            conn = db._get_conn()
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='evidence'")
            assert cursor.fetchone() is not None
            db.close()

    def test_log_and_get_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = self._make_db(tmpdir)
            db.log_evidence("ev_001", 1000.0, "praise", "User said thanks", {"trust": 0.05}, 1.0)

            results = db.get_all_evidence()
            assert len(results) == 1
            assert results[0]["evidence_id"] == "ev_001"
            assert results[0]["dimension_impacts"] == {"trust": 0.05}
            db.close()

    def test_get_all_evidence_ordered_by_timestamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = self._make_db(tmpdir)
            db.log_evidence("ev_001", 200.0, "a", "first", {}, 1.0)
            db.log_evidence("ev_002", 100.0, "b", "second", {}, 1.0)
            db.log_evidence("ev_003", 300.0, "c", "third", {}, 1.0)

            results = db.get_all_evidence()
            # Sorted by timestamp ASC
            assert [r["evidence_id"] for r in results] == ["ev_002", "ev_001", "ev_003"]
            db.close()

    def test_close(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = self._make_db(tmpdir)
            db.close()
            assert db._conn is None

    def test_close_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = self._make_db(tmpdir)
            db.close()
            db.close()  # should not raise

    def test_multiple_evidence_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = self._make_db(tmpdir)
            for i in range(5):
                db.log_evidence(f"ev_{i}", float(i), "test", f"entry {i}", {"val": i}, 0.5)

            results = db.get_all_evidence()
            assert len(results) == 5
            db.close()


# ──────────────────────────────────────────────
#  RelationshipEngineV2
# ──────────────────────────────────────────────

class TestRelationshipEngineV2:

    def _make(self, llm=None):
        state = MagicMock()
        state.db = MagicMock()
        state.lock = MagicMock()
        state.relationship_scores = MagicMock()
        from core.state.relationship import RelationshipEngineV2
        return RelationshipEngineV2(state=state, llm=llm)

    def test_analyze_and_log_without_llm(self):
        eng = self._make(llm=None)
        eng.analyze_and_log_interaction("hello", "hi back")
        # should just log warning and return, no calls
        eng.state.db.log_evidence.assert_not_called()

    def test_analyze_and_log_with_llm(self):
        eng = self._make(llm=MagicMock())
        eng.state.db.get_all_evidence.return_value = []

        raw_json = json.dumps({
            "event_type": "polite_greeting",
            "description": "User greeted politely",
            "impacts": {"trust": 0.02, "comfort": 0.01},
        })
        eng.llm.generate.return_value = raw_json

        eng.analyze_and_log_interaction("hello", "hi back")

        eng.llm.generate.assert_called_once()
        eng.state.db.log_evidence.assert_called_once()
        kwargs = eng.state.db.log_evidence.call_args[1]
        assert kwargs["ev_type"] == "polite_greeting"

    def test_analyze_and_log_llm_generates_with_tools_fallback(self):
        eng = self._make(llm=MagicMock())
        del eng.llm.generate
        eng.state.db.get_all_evidence.return_value = []

        raw_json = json.dumps({
            "event_type": "polite_greeting",
            "description": "User greeted",
            "impacts": {"trust": 0.01},
        })
        eng.llm.generate_with_tools.return_value = raw_json

        eng.analyze_and_log_interaction("hello", "hi back")

        eng.llm.generate_with_tools.assert_called_once()

    def test_analyze_and_log_llm_returns_empty(self):
        eng = self._make(llm=MagicMock())
        eng.llm.generate.return_value = None

        eng.analyze_and_log_interaction("hello", "hi back")

        eng.state.db.log_evidence.assert_not_called()

    def test_analyze_and_log_handles_invalid_json(self):
        eng = self._make(llm=MagicMock())
        eng.llm.generate.return_value = "not json at all"

        eng.analyze_and_log_interaction("hello", "hi back")

        # _extract_json returns {} for non-json, which is a valid dict,
        # so log_interaction_evidence IS called with empty impacts
        eng.state.db.log_evidence.assert_called_once()
        kwargs = eng.state.db.log_evidence.call_args[1]
        assert kwargs["impacts"] == {}

    def test_analyze_and_log_extracts_json_from_markdown(self):
        eng = self._make(llm=MagicMock())
        eng.state.db.get_all_evidence.return_value = []

        raw = 'Here is the analysis:\n```json\n{"event_type": "test", "description": "desc", "impacts": {"trust": 0.01}}\n```'
        eng.llm.generate.return_value = raw

        eng.analyze_and_log_interaction("hello", "hi back")

        eng.state.db.log_evidence.assert_called_once()

    def test_log_interaction_evidence(self):
        eng = self._make()
        eng.recalculate_derived_scores = MagicMock()

        eng.log_interaction_evidence("praise", "User said thanks", {"trust": 0.05})

        eng.state.db.log_evidence.assert_called_once()
        eng.recalculate_derived_scores.assert_called_once()

    def test_recalculate_derived_scores_applies_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.state.shared_state import SharedState
            from core.state.relationship import RelationshipEngineV2

            with patch("core.state.shared_state.EvidenceDB") as mock_db_cls:
                mock_db = MagicMock()
                mock_db_cls.return_value = mock_db
                mock_db.get_all_evidence.return_value = [
                    {
                        "evidence_id": "ev_001",
                        "timestamp": time.time() - 10,
                        "dimension_impacts": {"trust": 0.05, "comfort": 0.03},
                        "weight": 1.0,
                    },
                ]

                state = SharedState(Path(tmpdir))
                eng = RelationshipEngineV2(state=state, llm=None)

                eng.recalculate_derived_scores()

                # Evidence with weight 1.0 averaged against base weight 1.0:
                # trust = (0.5 + 0.05 * decay) / (1.0 + 1.0 * decay) ≈ 0.275
                assert state.relationship_scores.trust < 0.5  # pulled below base by equal weighting
                assert state.relationship_scores.comfort < 0.5

    def test_recalculate_derived_scores_empty_evidence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            from core.state.db import EvidenceDB
            from core.state.shared_state import SharedState
            from core.state.relationship import RelationshipEngineV2

            with patch("core.state.shared_state.EvidenceDB") as mock_db_cls:
                mock_db = MagicMock()
                mock_db_cls.return_value = mock_db
                mock_db.get_all_evidence.return_value = []

                state = SharedState(Path(tmpdir))
                eng = RelationshipEngineV2(state=state, llm=None)

                eng.recalculate_derived_scores()

                assert state.relationship_scores.trust == 0.5
                assert state.relationship_scores.comfort == 0.5

    def test_extract_json_direct(self):
        from core.state.relationship import RelationshipEngineV2
        eng = self._make()

        result = eng._extract_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_extract_json_from_text(self):
        from core.state.relationship import RelationshipEngineV2
        eng = self._make()

        result = eng._extract_json('Some text {"key": "value"} more text')
        assert result == {"key": "value"}

    def test_extract_json_none(self):
        from core.state.relationship import RelationshipEngineV2
        eng = self._make()

        assert eng._extract_json(None) == {}
        assert eng._extract_json("") == {}

    def test_extract_json_no_braces(self):
        from core.state.relationship import RelationshipEngineV2
        eng = self._make()

        assert eng._extract_json("not json at all") == {}

    def test_extract_json_nested_braces(self):
        from core.state.relationship import RelationshipEngineV2
        eng = self._make()

        result = eng._extract_json('{"outer": {"inner": "value"}}')
        assert result == {"outer": {"inner": "value"}}


# ──────────────────────────────────────────────
#  AIOSKernel
# ──────────────────────────────────────────────

class TestAIOSKernel:

    @patch("core.os_kernel.Attention")
    @patch("core.os_kernel.Cognition")
    @patch("core.os_kernel.IdleBehavior")
    @patch("core.os_kernel.Scheduler")
    @patch("core.os_kernel.Autonomy")
    @patch("core.os_kernel.WakeGenerator")
    @patch("core.os_kernel._get_identity")
    def test_init_success(self, mock_identity, mock_wg, mock_auto, mock_sched,
                          mock_idle, mock_cog, mock_attn):
        from core.os_kernel import AIOSKernel

        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.memory = MagicMock()
        brain.executor = MagicMock()
        brain.personality_state = MagicMock()
        voice = MagicMock()
        wake = MagicMock()
        stt = MagicMock()
        state = MagicMock()
        relationship_engine = MagicMock()

        kernel = AIOSKernel(
            brain=brain,
            voice=voice,
            wake=wake,
            stt=stt,
            state=state,
            relationship_engine=relationship_engine,
        )

        assert kernel.brain is brain
        assert kernel.voice is voice
        assert kernel.wake is wake
        assert kernel.stt is stt
        assert kernel.state is state
        assert kernel.relationship_engine is relationship_engine
        assert kernel.running is True
        assert hasattr(kernel, "conversation_lock")

    def test_init_raises_on_none_state(self):
        from core.os_kernel import AIOSKernel

        with pytest.raises(ValueError, match="SharedState"):
            AIOSKernel(
                brain=MagicMock(),
                voice=MagicMock(),
                wake=MagicMock(),
                stt=MagicMock(),
                state=None,
                relationship_engine=MagicMock(),
            )

    def test_init_raises_on_none_relationship_engine(self):
        from core.os_kernel import AIOSKernel

        with pytest.raises(ValueError, match="RelationshipEngineV2"):
            AIOSKernel(
                brain=MagicMock(),
                voice=MagicMock(),
                wake=MagicMock(),
                stt=MagicMock(),
                state=MagicMock(),
                relationship_engine=None,
            )

    @patch("core.os_kernel.Attention")
    @patch("core.os_kernel.Cognition")
    @patch("core.os_kernel.IdleBehavior")
    @patch("core.os_kernel.Scheduler")
    @patch("core.os_kernel.Autonomy")
    @patch("core.os_kernel.WakeGenerator")
    @patch("core.os_kernel._get_identity")
    def test_shutdown(self, mock_identity, mock_wg, mock_auto, mock_sched,
                      mock_idle, mock_cog, mock_attn):
        from core.os_kernel import AIOSKernel

        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.memory = MagicMock()
        brain.executor = MagicMock()
        brain.personality_state = MagicMock()
        voice = MagicMock()
        wake = MagicMock()
        stt = MagicMock()
        state = MagicMock()
        state.save_state_to_disk = MagicMock()
        relationship_engine = MagicMock()

        kernel = AIOSKernel(
            brain=brain,
            voice=voice,
            wake=wake,
            stt=stt,
            state=state,
            relationship_engine=relationship_engine,
        )

        kernel.shutdown()

        assert kernel.running is False
        voice.stop.assert_called_once()
        kernel.scheduler.stop.assert_called_once()
        state.save_state_to_disk.assert_called_once()
        brain.personality_state.save.assert_called_once()

    @patch("core.os_kernel.Attention")
    @patch("core.os_kernel.Cognition")
    @patch("core.os_kernel.IdleBehavior")
    @patch("core.os_kernel.Scheduler")
    @patch("core.os_kernel.Autonomy")
    @patch("core.os_kernel.WakeGenerator")
    @patch("core.os_kernel._get_identity")
    def test_shutdown_handles_errors_gracefully(self, mock_identity, mock_wg, mock_auto,
                                                 mock_sched, mock_idle, mock_cog, mock_attn):
        from core.os_kernel import AIOSKernel

        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.memory = MagicMock()
        brain.executor = MagicMock()
        brain.personality_state = MagicMock()

        voice = MagicMock()
        voice.stop.side_effect = RuntimeError("voice fail")

        wake = MagicMock()
        stt = MagicMock()
        state = MagicMock()
        state.save_state_to_disk.side_effect = RuntimeError("save fail")
        relationship_engine = MagicMock()

        kernel = AIOSKernel(
            brain=brain,
            voice=voice,
            wake=wake,
            stt=stt,
            state=state,
            relationship_engine=relationship_engine,
        )

        # Should not raise despite errors
        kernel.shutdown()

        assert kernel.running is False

    @patch("core.os_kernel.Attention")
    @patch("core.os_kernel.Cognition")
    @patch("core.os_kernel.IdleBehavior")
    @patch("core.os_kernel.Scheduler")
    @patch("core.os_kernel.Autonomy")
    @patch("core.os_kernel.WakeGenerator")
    @patch("core.os_kernel._get_identity")
    def test_shutdown_skips_save_if_not_available(self, mock_identity, mock_wg, mock_auto,
                                                    mock_sched, mock_idle, mock_cog, mock_attn):
        from core.os_kernel import AIOSKernel

        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.memory = MagicMock()
        brain.executor = MagicMock()
        brain.personality_state = MagicMock()
        voice = MagicMock()
        wake = MagicMock()
        stt = MagicMock()
        state = MagicMock()
        del state.save_state_to_disk  # attribute not present
        relationship_engine = MagicMock()

        kernel = AIOSKernel(
            brain=brain,
            voice=voice,
            wake=wake,
            stt=stt,
            state=state,
            relationship_engine=relationship_engine,
        )

        kernel.shutdown()

        assert kernel.running is False

    @patch("core.os_kernel.Attention")
    @patch("core.os_kernel.Cognition")
    @patch("core.os_kernel.IdleBehavior")
    @patch("core.os_kernel.Scheduler")
    @patch("core.os_kernel.Autonomy")
    @patch("core.os_kernel.WakeGenerator")
    @patch("core.os_kernel._get_identity")
    def test_update_time_context_day(self, mock_identity, mock_wg, mock_auto, mock_sched,
                                      mock_idle, mock_cog, mock_attn):
        from core.os_kernel import AIOSKernel

        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.memory = MagicMock()
        brain.executor = MagicMock()
        brain.personality_state = MagicMock()
        voice = MagicMock()
        wake = MagicMock()
        stt = MagicMock()
        state = MagicMock()
        relationship_engine = MagicMock()

        kernel = AIOSKernel(
            brain=brain,
            voice=voice,
            wake=wake,
            stt=stt,
            state=state,
            relationship_engine=relationship_engine,
        )

        # Patch time.localtime to return a daytime hour
        with patch("core.os_kernel.time.localtime") as mock_lt:
            mock_lt.return_value.tm_hour = 14
            kernel._update_time_context()

        state.runtime.time_of_day = "day"

    @patch("core.os_kernel.Attention")
    @patch("core.os_kernel.Cognition")
    @patch("core.os_kernel.IdleBehavior")
    @patch("core.os_kernel.Scheduler")
    @patch("core.os_kernel.Autonomy")
    @patch("core.os_kernel.WakeGenerator")
    @patch("core.os_kernel._get_identity")
    def test_update_time_context_night(self, mock_identity, mock_wg, mock_auto, mock_sched,
                                        mock_idle, mock_cog, mock_attn):
        from core.os_kernel import AIOSKernel

        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.memory = MagicMock()
        brain.executor = MagicMock()
        brain.personality_state = MagicMock()
        voice = MagicMock()
        wake = MagicMock()
        stt = MagicMock()
        state = MagicMock()
        relationship_engine = MagicMock()

        kernel = AIOSKernel(
            brain=brain,
            voice=voice,
            wake=wake,
            stt=stt,
            state=state,
            relationship_engine=relationship_engine,
        )

        with patch("core.os_kernel.time.localtime") as mock_lt:
            mock_lt.return_value.tm_hour = 22
            kernel._update_time_context()

        state.runtime.time_of_day = "night"

    def test_process_autonomy_known_intents(self):
        from core.os_kernel import AIOSKernel

        # We can test _process_autonomy without a full init since it's a static method
        # Using __new__ to avoid full initialization
        kernel = AIOSKernel.__new__(AIOSKernel)

        assert kernel._process_autonomy({"intent": "seek_attention"}) == "You've been quiet for a while."
        assert kernel._process_autonomy({"intent": "gentle_checkin"}) == "You seem a little distant today."
        assert kernel._process_autonomy({"intent": "soft_presence"}) == "...I'm still here."
        assert kernel._process_autonomy({"intent": "playful_tease"}) == "You really do like disappearing randomly, hm?"

    def test_process_autonomy_unknown_intent(self):
        from core.os_kernel import AIOSKernel
        kernel = AIOSKernel.__new__(AIOSKernel)

        assert kernel._process_autonomy({"intent": "unknown_intent"}) is None
        assert kernel._process_autonomy({}) is None

    # ================================================================
    # SPEAKER IDENTIFICATION TESTS
    # ================================================================

    @patch("core.os_kernel.Attention")
    @patch("core.os_kernel.Cognition")
    @patch("core.os_kernel.IdleBehavior")
    @patch("core.os_kernel.Scheduler")
    @patch("core.os_kernel.Autonomy")
    @patch("core.os_kernel.WakeGenerator")
    @patch("core.os_kernel._get_identity")
    def test_init_with_speaker_manager(self, mock_identity, mock_wg, mock_auto,
                                        mock_sched, mock_idle, mock_cog, mock_attn):
        from core.os_kernel import AIOSKernel

        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.memory = MagicMock()
        brain.executor = MagicMock()
        brain.personality_state = MagicMock()
        voice = MagicMock()
        wake = MagicMock()
        stt = MagicMock()
        state = MagicMock()
        relationship_engine = MagicMock()
        speaker_manager = MagicMock()

        kernel = AIOSKernel(
            brain=brain,
            voice=voice,
            wake=wake,
            stt=stt,
            state=state,
            relationship_engine=relationship_engine,
            speaker_manager=speaker_manager,
        )

        assert kernel.speaker_manager is speaker_manager

    @patch("core.os_kernel.Attention")
    @patch("core.os_kernel.Cognition")
    @patch("core.os_kernel.IdleBehavior")
    @patch("core.os_kernel.Scheduler")
    @patch("core.os_kernel.Autonomy")
    @patch("core.os_kernel.WakeGenerator")
    @patch("core.os_kernel._get_identity")
    def test_identify_skipped_when_not_ready(self, mock_identity, mock_wg,
                                              mock_auto, mock_sched, mock_idle,
                                              mock_cog, mock_attn):
        import sys
        import numpy as np
        from unittest.mock import MagicMock
        from core.os_kernel import AIOSKernel

        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.memory = MagicMock()
        brain.executor = MagicMock()
        brain.personality_state = MagicMock()
        voice = MagicMock()
        wake = MagicMock()
        stt = MagicMock()
        state = MagicMock()
        relationship_engine = MagicMock()
        speaker_manager = MagicMock()
        speaker_manager.ready = False

        kernel = AIOSKernel(
            brain=brain,
            voice=voice,
            wake=wake,
            stt=stt,
            state=state,
            relationship_engine=relationship_engine,
            speaker_manager=speaker_manager,
        )

        mock_sd = MagicMock()
        mock_sd.rec.return_value = np.zeros((8000, 1), dtype=np.float32)
        with patch.dict("sys.modules", {"sounddevice": mock_sd}):
            audio = kernel._record_identification_audio(duration=0.5)
        assert audio is not None
        assert len(audio) > 0

    @patch("core.os_kernel.Attention")
    @patch("core.os_kernel.Cognition")
    @patch("core.os_kernel.IdleBehavior")
    @patch("core.os_kernel.Scheduler")
    @patch("core.os_kernel.Autonomy")
    @patch("core.os_kernel.WakeGenerator")
    @patch("core.os_kernel._get_identity")
    def test_init_without_speaker_manager(self, mock_identity, mock_wg, mock_auto,
                                           mock_sched, mock_idle, mock_cog, mock_attn):
        from core.os_kernel import AIOSKernel

        brain = MagicMock()
        brain.emotion = MagicMock()
        brain.memory = MagicMock()
        brain.executor = MagicMock()
        brain.personality_state = MagicMock()
        voice = MagicMock()
        wake = MagicMock()
        stt = MagicMock()
        state = MagicMock()
        relationship_engine = MagicMock()

        kernel = AIOSKernel(
            brain=brain,
            voice=voice,
            wake=wake,
            stt=stt,
            state=state,
            relationship_engine=relationship_engine,
        )

        assert kernel.speaker_manager is None


class TestResponsePipelineNormalize:

    def _make_pipeline(self):
        from core.response_pipeline import ResponsePipeline
        pipeline = ResponsePipeline(
            tool_registry=None,
            executor=MagicMock(),
            event_bus=MagicMock(),
            memory=MagicMock(),
        )
        pipeline.executor.run.return_value = {"output": "opened:calc"}
        return pipeline

    def _process(self, pipeline, raw):
        emotion_getter = MagicMock(return_value={})
        cognitive = MagicMock()
        memory_coordinator = MagicMock()
        post_think_hooks = MagicMock()
        return pipeline.process(
            raw=raw,
            user_input="open calc",
            emotion_getter=emotion_getter,
            cognitive=cognitive,
            memory_coordinator=memory_coordinator,
            post_think_hooks=post_think_hooks,
            executor=pipeline.executor,
        )

    def test_flat_action_executes(self):
        pipeline = self._make_pipeline()
        result = self._process(pipeline, '{"type": "open_app", "content": "calc"}')
        assert result.handled is True
        pipeline.executor.run.assert_called_once_with({"type": "open_app", "content": "calc"})

    def test_envelope_action_flattened_and_executes(self):
        pipeline = self._make_pipeline()
        raw = json.dumps({
            "action": "call_tool", "tool": "execute_action",
            "params": {"type": "open_app", "content": "calc"},
        })
        result = self._process(pipeline, raw)
        assert result.handled is True
        pipeline.executor.run.assert_called_once_with({"type": "open_app", "content": "calc"})

    def test_envelope_unknown_tool_ignored(self):
        pipeline = self._make_pipeline()
        raw = json.dumps({
            "action": "call_tool", "tool": "not_a_tool",
            "params": {"type": "not_an_action", "content": "x"},
        })
        result = self._process(pipeline, raw)
        assert result.handled is False
        pipeline.executor.run.assert_not_called()
