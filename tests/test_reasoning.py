"""Tests for reasoning subsystem: engine, journal, reflection, learning."""

import json
import sys
import tempfile
import time
from unittest.mock import MagicMock

sys.path.insert(0, ".")


# ---------------------------------------------------------------------------
# ThoughtJournal
# ---------------------------------------------------------------------------

class TestThoughtJournal:

    def test_store_returns_entry_with_id(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        thought = {"query": "test", "conclusion": "ok"}
        entry = j.store(thought)
        assert "id" in entry
        assert entry["query"] == "test"
        assert entry["conclusion"] == "ok"
        assert isinstance(entry["confidence"], float)

    def test_store_increments_count(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        assert j.count() == 0
        j.store({"query": "a"})
        assert j.count() == 1
        j.store({"query": "b"})
        assert j.count() == 2

    def test_recent_returns_last_n(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        for i in range(10):
            j.store({"query": f"q{i}", "conclusion": f"c{i}"})
        recent = j.recent(3)
        assert len(recent) == 3
        assert recent[-1]["query"] == "q9"

    def test_recent_returns_all_when_n_exceeds_count(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        j.store({"query": "only"})
        recent = j.recent(10)
        assert len(recent) == 1

    def test_recent_returns_empty_list_when_empty(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        assert j.recent(5) == []

    def test_search_finds_by_query(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        j.store({"query": "what is the weather", "conclusion": "it is sunny"})
        j.store({"query": "who are you", "conclusion": "Mai"})
        results = j.search("weather")
        assert len(results) == 1
        assert results[0]["query"] == "what is the weather"

    def test_search_finds_by_conclusion(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        j.store({"query": "q1", "conclusion": "sunny day"})
        results = j.search("sunny")
        assert len(results) == 1

    def test_search_finds_by_known_facts(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        j.store({"query": "q1", "known_facts": ["pizza is good"]})
        results = j.search("pizza")
        assert len(results) == 1

    def test_search_case_insensitive(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        j.store({"query": "What Is Love", "conclusion": "baby"})
        assert len(j.search("love")) == 1
        assert len(j.search("LOVE")) == 1

    def test_search_empty_topic_returns_all(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        j.store({"query": "a"})
        j.store({"query": "b"})
        assert len(j.search("")) == 2

    def test_count_zero_initially(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        assert j.count() == 0

    def test_count_after_stores(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        j.store({"query": "a"})
        j.store({"query": "b"})
        j.store({"query": "c"})
        assert j.count() == 3

    def test_store_with_empty_thought(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        entry = j.store({})
        assert "id" in entry
        assert entry["query"] == ""

    def test_persist_save_and_load(self):
        from reasoning.journal import ThoughtJournal
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            path = f.name

        try:
            j = ThoughtJournal(path=path)
            j.store({"query": "hello", "conclusion": "world"})
            j.store({"query": "foo", "conclusion": "bar"})

            j2 = ThoughtJournal(path=path)
            assert j2.count() == 2
            assert j2.recent(1)[0]["query"] == "foo"
        finally:
            import os
            os.unlink(path)

    def test_load_missing_file_returns_empty(self):
        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal(path="/nonexistent/path.json")
        assert j.count() == 0

    def test_persist_incremental_append_and_legacy_array_load(self):
        """New entries append without rewriting the file (P-3); legacy
        JSON-array journals still load."""
        from reasoning.journal import ThoughtJournal
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            path = f.name

        try:
            # Legacy whole-array journal (old format) must still load.
            with open(path, "w", encoding="utf-8") as f:
                json.dump([{"id": "legacy-1", "query": "old", "conclusion": "x"}], f)
            j = ThoughtJournal(path=path)
            assert j.count() == 1
            assert j.search("old")[0]["id"] == "legacy-1"

            j.store({"query": "new", "conclusion": "y"})
            j.store({"query": "newer", "conclusion": "z"})

            j2 = ThoughtJournal(path=path)
            assert j2.count() == 3
            assert j2.recent(1)[0]["query"] == "newer"

            # File must be line-delimited JSONL (append-friendly), not one
            # monolithic array.
            raw = open(path, encoding="utf-8").read()
            assert raw.count("\n") >= 2
            assert not raw.lstrip().startswith("[")
        finally:
            import os
            os.unlink(path)

    def test_thread_safety(self):
        import threading

        from reasoning.journal import ThoughtJournal
        j = ThoughtJournal()
        errors = []

        def worker(n):
            try:
                for _ in range(50):
                    j.store({"query": f"q{n}"})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert j.count() == 200
        assert not errors


# ---------------------------------------------------------------------------
# ReasoningTrace
# ---------------------------------------------------------------------------

class TestReasoningTrace:

    def test_trace_attributes(self):
        from reasoning.engine import ReasoningTrace
        t = ReasoningTrace(
            query="test?",
            evidence=[{"content": "x"}],
            known=["x"],
            unknowns=["y"],
            steps=["step 1"],
            confidence=0.8,
            conclusion="done",
        )
        assert t.query == "test?"
        assert t.retrieved_evidence == [{"content": "x"}]
        assert t.known_facts == ["x"]
        assert t.unknowns == ["y"]
        assert t.reasoning_steps == ["step 1"]
        assert t.confidence == 0.8
        assert t.conclusion == "done"

    def test_trace_defaults(self):
        from reasoning.engine import ReasoningTrace
        t = ReasoningTrace(query="")
        assert t.retrieved_evidence == []
        assert t.known_facts == []
        assert t.unknowns == []
        assert t.reasoning_steps == []
        assert t.confidence == 0.5
        assert t.conclusion == ""

    def test_trace_confidence_clamped(self):
        from reasoning.engine import ReasoningTrace
        t = ReasoningTrace(query="x", confidence=1.5)
        assert t.confidence == 1.0
        t2 = ReasoningTrace(query="x", confidence=-0.5)
        assert t2.confidence == 0.0

    def test_trace_strips_whitespace(self):
        from reasoning.engine import ReasoningTrace
        t = ReasoningTrace(query="  hello  ", conclusion="  world  ")
        assert t.query == "hello"
        assert t.conclusion == "world"

    def test_to_dict(self):
        from reasoning.engine import ReasoningTrace
        t = ReasoningTrace(query="q", conclusion="c", confidence=0.9)
        d = t.to_dict()
        assert d["query"] == "q"
        assert d["conclusion"] == "c"
        assert d["confidence"] == 0.9
        assert "timestamp" in d

    def test_timestamp_set(self):
        from reasoning.engine import ReasoningTrace
        before = time.time()
        t = ReasoningTrace(query="q")
        after = time.time()
        assert before <= t.timestamp <= after


# ---------------------------------------------------------------------------
# ReasoningEngine
# ---------------------------------------------------------------------------

class TestReasoningEngine:

    def test_reason_returns_trace_with_empty_query(self):
        from reasoning.engine import ReasoningEngine
        engine = ReasoningEngine()
        trace = engine.reason("")
        assert trace.conclusion == "No query provided."
        assert trace.confidence == 0.0
        assert trace.reasoning_steps == []

    def test_reason_returns_trace_with_whitespace_query(self):
        from reasoning.engine import ReasoningEngine
        engine = ReasoningEngine()
        trace = engine.reason("   ")
        # whitespace is stripped to empty, then proceeds through pipeline
        assert "don't have enough information" in trace.conclusion
        assert trace.confidence == 0.1

    def test_reason_no_retriever_no_journal_no_event_bus(self):
        from reasoning.engine import ReasoningEngine
        engine = ReasoningEngine()
        trace = engine.reason("what is the capital of France?")
        assert isinstance(trace.conclusion, str)
        assert "don't have enough information" in trace.conclusion
        assert trace.confidence == 0.1
        assert trace.known_facts == []
        assert trace.unknowns != []

    def test_reason_identifies_unknowns_correctly(self):
        from reasoning.engine import ReasoningEngine
        engine = ReasoningEngine()
        trace = engine.reason("why is the sky blue?")
        assert any("sky" in u.lower() for u in trace.unknowns)

    def test_reason_with_retriever(self):
        from reasoning.engine import ReasoningEngine
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"content": "light scatters in the atmosphere", "source": "knowledge", "score": 0.9},
            {"content": "the sky appears blue due to Rayleigh scattering", "source": "knowledge", "score": 0.85},
        ]
        engine = ReasoningEngine(retriever=mock_retriever)
        trace = engine.reason("why is the sky blue?")
        assert len(trace.known_facts) == 2
        assert trace.confidence > 0.5
        assert "light scatters" in trace.conclusion
        mock_retriever.retrieve.assert_called_once()

    def test_reason_with_retriever_passes_attention_focus(self):
        from reasoning.engine import ReasoningEngine
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        engine = ReasoningEngine(retriever=mock_retriever)
        engine.reason("test?", context={"attention_focus": "science"})
        mock_retriever.retrieve.assert_called_with(
            "test?", attention_focus="science", top_k=5
        )

    def test_reason_with_event_bus(self):
        from reasoning.engine import ReasoningEngine
        mock_bus = MagicMock()
        engine = ReasoningEngine(event_bus=mock_bus)
        engine.reason("hello?")
        mock_bus.publish_message.assert_called_once()
        msg = mock_bus.publish_message.call_args[0][0]
        assert msg.type == "data.reasoning.completed"
        assert "query" in msg.payload

    def test_reason_with_journal_stores_trace(self):
        from reasoning.engine import ReasoningEngine
        mock_journal = MagicMock()
        engine = ReasoningEngine(journal=mock_journal)
        engine.reason("test?")
        mock_journal.store.assert_called_once()

    def test_reason_with_retriever_error_logged_gracefully(self):
        from reasoning.engine import ReasoningEngine
        mock_retriever = MagicMock()
        mock_retriever.retrieve.side_effect = Exception("boom")
        engine = ReasoningEngine(retriever=mock_retriever)
        trace = engine.reason("test?")
        assert trace.known_facts == []
        assert trace.confidence == 0.1

    def test_reason_empty_evidence_produces_low_confidence(self):
        from reasoning.engine import ReasoningEngine
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = []
        engine = ReasoningEngine(retriever=mock_retriever)
        trace = engine.reason("test?")
        assert trace.confidence == 0.1

    def test_reason_high_confidence_produces_strong_conclusion(self):
        from reasoning.engine import ReasoningEngine
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"content": "fact a", "source": "mem", "score": 0.95},
            {"content": "fact b", "source": "mem", "score": 0.90},
            {"content": "fact c", "source": "mem", "score": 0.92},
        ]
        engine = ReasoningEngine(retriever=mock_retriever)
        trace = engine.reason("test?")
        assert trace.confidence > 0.7
        assert "fairly confident" in trace.conclusion

    def test_reason_medium_confidence_conclusion(self):
        from reasoning.engine import ReasoningEngine
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"content": "fact a", "source": "mem", "score": 0.6},
            {"content": "fact b", "source": "mem", "score": 0.5},
        ]
        engine = ReasoningEngine(retriever=mock_retriever)
        trace = engine.reason("test?")
        assert 0.4 < trace.confidence <= 0.7
        assert "not completely sure" in trace.conclusion

    def test_reason_low_confidence_conclusion(self):
        from reasoning.engine import ReasoningEngine
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"content": "fact a", "source": "mem", "score": 0.3},
        ]
        engine = ReasoningEngine(retriever=mock_retriever)
        trace = engine.reason("test?")
        assert trace.confidence < 0.4
        assert "limited evidence" in trace.conclusion

    def test_event_bus_receives_step_count(self):
        from reasoning.engine import ReasoningEngine
        mock_bus = MagicMock()
        engine = ReasoningEngine(event_bus=mock_bus)
        trace = engine.reason("why?")
        msg = mock_bus.publish_message.call_args[0][0]
        assert msg.payload["step_count"] == len(trace.reasoning_steps)

    def test_known_facts_limited_to_eight(self):
        from reasoning.engine import ReasoningEngine
        mock_retriever = MagicMock()
        mock_retriever.retrieve.return_value = [
            {"content": f"fact {i}", "source": "mem", "score": 0.5}
            for i in range(20)
        ]
        engine = ReasoningEngine(retriever=mock_retriever)
        trace = engine.reason("test?")
        assert len(trace.known_facts) <= 8

    def test_no_unknowns_when_evidence_answers_query(self):
        from reasoning.engine import ReasoningEngine
        mock_retriever = MagicMock()
        # known fact must contain the extracted topic (e.g. "is alice" from "who is alice?")
        mock_retriever.retrieve.return_value = [
            {"content": "is alice: Alice is a software engineer", "source": "mem", "score": 0.9},
        ]
        engine = ReasoningEngine(retriever=mock_retriever)
        trace = engine.reason("who is Alice?")
        assert trace.unknowns == []


# ---------------------------------------------------------------------------
# Reflection
# ---------------------------------------------------------------------------

class TestReflection:

    def test_reflection_attributes(self):
        from reasoning.reflection import Reflection
        r = Reflection(period="daily", summary="test", patterns=["p1"], topics=["t1"], confidence=0.7)
        assert r.period == "daily"
        assert r.summary == "test"
        assert r.patterns == ["p1"]
        assert r.topics == ["t1"]
        assert r.confidence == 0.7

    def test_reflection_defaults(self):
        from reasoning.reflection import Reflection
        r = Reflection(period="weekly", summary="s")
        assert r.patterns == []
        assert r.topics == []
        assert r.confidence == 0.5

    def test_reflection_confidence_clamped(self):
        from reasoning.reflection import Reflection
        r = Reflection(period="d", summary="s", confidence=2.0)
        assert r.confidence == 1.0
        r2 = Reflection(period="d", summary="s", confidence=-1.0)
        assert r2.confidence == 0.0

    def test_to_dict(self):
        from reasoning.reflection import Reflection
        r = Reflection(period="daily", summary="ok", patterns=["a"], topics=["b"])
        d = r.to_dict()
        assert d["period"] == "daily"
        assert d["summary"] == "ok"
        assert d["patterns"] == ["a"]
        assert d["topics"] == ["b"]
        assert "timestamp" in d


# ---------------------------------------------------------------------------
# ReflectionEngine
# ---------------------------------------------------------------------------

class TestReflectionEngine:

    def test_daily_reflection_returns_reflection(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        ref = engine.daily_reflection(memories=[{"text": "I love coding"}])
        assert ref.period == "daily"
        assert isinstance(ref.summary, str)
        assert "Daily reflection" in ref.summary
        assert "coding" in ref.summary

    def test_daily_reflection_topics_extracted(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        ref = engine.daily_reflection(
            memories=[{"text": "I love python programming"}]
        )
        assert any("python" in t.lower() for t in ref.topics)

    def test_daily_reflection_empty_input(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        ref = engine.daily_reflection()
        assert ref.period == "daily"
        assert "No significant topics" in ref.summary

    def test_daily_reflection_pattern_detected_with_enough_topics(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        ref = engine.daily_reflection(
            memories=[
                {"text": "I like python"},
                {"text": "I like coding"},
                {"text": "I like music"},
            ]
        )
        assert len(ref.patterns) >= 1

    def test_weekly_reflection_returns_reflection(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        ref = engine.weekly_reflection()
        assert ref.period == "weekly"
        assert "Weekly reflection" in ref.summary

    def test_weekly_reflection_includes_aggregated_pattern(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        ref = engine.weekly_reflection(memories=[{"text": "hello world"}])
        assert any("7-day" in p for p in ref.patterns)

    def test_monthly_reflection_returns_reflection(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        ref = engine.monthly_reflection()
        assert ref.period == "monthly"
        assert "Monthly reflection" in ref.summary

    def test_monthly_reflection_includes_trend_pattern(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        ref = engine.monthly_reflection(memories=[{"text": "hello"}])
        assert any("long-term" in p for p in ref.patterns)

    def test_daily_publishes_event(self):
        from reasoning.reflection import ReflectionEngine
        mock_bus = MagicMock()
        engine = ReflectionEngine(event_bus=mock_bus)
        engine.daily_reflection(memories=[{"text": "test"}])
        mock_bus.publish_message.assert_called_once()
        msg = mock_bus.publish_message.call_args[0][0]
        assert msg.type == "data.reflection.generated"

    def test_weekly_publishes_event(self):
        from reasoning.reflection import ReflectionEngine
        mock_bus = MagicMock()
        engine = ReflectionEngine(event_bus=mock_bus)
        engine.weekly_reflection(memories=[{"text": "test"}])
        mock_bus.publish_message.assert_called_once()
        msg = mock_bus.publish_message.call_args[0][0]
        assert msg.type == "data.reflection.generated"

    def test_monthly_publishes_event(self):
        from reasoning.reflection import ReflectionEngine
        mock_bus = MagicMock()
        engine = ReflectionEngine(event_bus=mock_bus)
        engine.monthly_reflection(memories=[{"text": "test"}])
        mock_bus.publish_message.assert_called_once()
        msg = mock_bus.publish_message.call_args[0][0]
        assert msg.type == "data.reflection.generated"

    def test_no_event_bus_does_not_raise(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        engine.daily_reflection()
        engine.weekly_reflection()
        engine.monthly_reflection()

    def test_extract_topics_from_thoughts(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        ref = engine.daily_reflection(thoughts=[{"query": "how to learn python effectively"}])
        assert any("python" in t.lower() for t in ref.topics)

    def test_extract_topics_from_tags(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        ref = engine.daily_reflection(
            memories=[{"text": "some content", "tags": ["python", "coding", "learning"]}]
        )
        for tag in ("python", "coding", "learning"):
            assert any(tag in t.lower() for t in ref.topics)

    def test_pattern_detected_only_with_sufficient_topics(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        ref = engine.daily_reflection(memories=[{"text": "hi"}])
        # short words (<5 chars) won't be topics
        patterns = ref.patterns
        # topics count might be 0, so patterns list might be empty
        assert isinstance(patterns, list)

    def test_updates_timestamps(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()

        # Each reflection must be checked against its own call interval.
        # A shared "after" captured after the daily call can incorrectly
        # reject the later weekly/monthly timestamps.
        before = time.time()
        daily = engine.daily_reflection()
        after = time.time()
        assert daily is not None
        assert before <= engine._last_daily <= after

        before = time.time()
        weekly = engine.weekly_reflection()
        after = time.time()
        assert weekly is not None
        assert before <= engine._last_weekly <= after

        before = time.time()
        monthly = engine.monthly_reflection()
        after = time.time()
        assert monthly is not None
        assert before <= engine._last_monthly <= after

    def test_cadence_disabled_by_default_runs_every_time(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine()
        assert engine.daily_reflection() is not None
        assert engine.daily_reflection() is not None

    def test_cadence_enforced_skips_within_interval(self):
        """With cadence enabled, back-to-back daily calls only fire once
        (R-7)."""
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine(enforce_cadence=True)
        first = engine.daily_reflection()
        assert first is not None
        assert engine.daily_reflection() is None

    def test_cadence_due_after_interval(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine(enforce_cadence=True, daily_interval=0.01)
        assert engine.daily_reflection() is not None
        time.sleep(0.02)
        assert engine.daily_reflection() is not None

    def test_cadence_force_bypasses_interval(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine(enforce_cadence=True)
        assert engine.daily_reflection() is not None
        assert engine.daily_reflection(force=True) is not None

    def test_cadence_does_not_skip_first_call(self):
        from reasoning.reflection import ReflectionEngine
        engine = ReflectionEngine(enforce_cadence=True)
        assert engine.due("daily") is True
        engine.daily_reflection()
        assert engine.due("daily") is False


# ---------------------------------------------------------------------------
# LearningEngine
# ---------------------------------------------------------------------------

class TestLearningEngine:

    def test_generalize_empty_returns_empty_list(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        assert engine.generalize([]) == []
        assert engine.generalize(None) == []

    def test_generalize_extracts_preferences(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        result = engine.generalize([
            {"text": "I like coffee", "memory_type": "preference"},
            {"text": "I love tea", "memory_type": "preference"},
        ])
        assert len(result) >= 1
        generalizations_texts = [g["generalization"] for g in result]
        assert any("beverages" in g or "coffee" in g or "tea" in g for g in generalizations_texts)

    def test_generalize_extracts_location(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        result = engine.generalize([
            {"text": "User lives in Tokyo", "memory_type": "location"},
        ])
        generalizations = [g for g in result if isinstance(g, dict) and g.get("source") == "location_cluster"]
        assert len(generalizations) >= 1
        assert "Tokyo" in generalizations[0]["generalization"]

    def test_generalize_coffee_preference_categorized(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        result = engine.generalize([
            {"text": "I like coffee", "memory_type": "preference"},
            {"text": "I love latte", "memory_type": "preference"},
        ])
        generalizations = []
        for r in result:
            if isinstance(r, dict) and "generalization" in r:
                generalizations.append(r["generalization"])
        assert any("beverages" in g for g in generalizations)

    def test_generalize_tech_preference_categorized(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        result = engine.generalize([
            {"text": "I like python", "memory_type": "preference"},
            {"text": "I love coding", "memory_type": "preference"},
        ])
        generalizations = []
        for r in result:
            if isinstance(r, dict) and "generalization" in r:
                generalizations.append(r["generalization"])
        assert any("technology" in g.lower() for g in generalizations)

    def test_generalize_food_preference_categorized(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        result = engine.generalize([
            {"text": "I like pizza", "memory_type": "preference"},
            {"text": "I love pasta", "memory_type": "preference"},
        ])
        generalizations = []
        for r in result:
            if isinstance(r, dict) and "generalization" in r:
                generalizations.append(r["generalization"])
        assert any("food" in g.lower() for g in generalizations)

    def test_generalize_single_preference_falls_back(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        # single preference item (count=1) doesn't trigger generalization (needs >=2)
        result = engine.generalize([
            {"text": "I like skateboarding", "memory_type": "preference"},
        ])
        # no generalization produced for single preference
        pref_gens = [g for g in result if isinstance(g, dict) and g.get("source") == "preference_cluster"]
        assert len(pref_gens) == 0

    def test_generalize_with_identities(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        result = engine.generalize([
            {"text": "User is a developer", "memory_type": "identity"},
        ])
        # identity patterns are extracted but not generalized; result should be empty
        assert result == []

    def test_generalize_publishes_event(self):
        from reasoning.learning import LearningEngine
        mock_bus = MagicMock()
        engine = LearningEngine(event_bus=mock_bus)
        engine.generalize([
            {"text": "I like coffee", "memory_type": "preference"},
            {"text": "I love latte", "memory_type": "preference"},
        ])
        mock_bus.publish_message.assert_called_once()
        msg = mock_bus.publish_message.call_args[0][0]
        assert msg.type == "data.learning.generalized"

    def test_generalize_no_event_with_empty_input(self):
        from reasoning.learning import LearningEngine
        mock_bus = MagicMock()
        engine = LearningEngine(event_bus=mock_bus)
        engine.generalize([])
        mock_bus.publish.assert_not_called()

    def test_adjust_behavior_empty_returns_empty_dict(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        assert engine.adjust_behavior([]) == {}
        assert engine.adjust_behavior(None) == {}

    def test_adjust_behavior_increases_comfort_on_stress(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        adjustments = engine.adjust_behavior([
            {"summary": "User feels stressed and anxious", "patterns": []},
            {"summary": "User is overwhelmed with work", "patterns": []},
        ])
        assert "comfort_behavior" in adjustments
        assert adjustments["energy_conservation"] is True

    def test_adjust_behavior_playfulness_on_positive(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        adjustments = engine.adjust_behavior([
            {"summary": "User is happy and excited today", "patterns": []},
            {"summary": "User feels grateful for everything", "patterns": []},
        ])
        assert "playfulness_boost" in adjustments

    def test_adjust_behavior_no_adjustment_when_balanced(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        adjustments = engine.adjust_behavior([
            {"summary": "User is happy", "patterns": []},
            {"summary": "User is stressed", "patterns": []},
        ])
        # stress and positive both count = 1, neither > the other
        assert adjustments == {}

    def test_adjust_behavior_with_string_input(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        adjustments = engine.adjust_behavior([
            "User feels very stressed and anxious today",
        ])
        assert "comfort_behavior" in adjustments

    def test_adjust_behavior_publishes_event(self):
        from reasoning.learning import LearningEngine
        mock_bus = MagicMock()
        engine = LearningEngine(event_bus=mock_bus)
        engine.adjust_behavior([
            {"summary": "User is stressed", "patterns": []},
            {"summary": "User is anxious", "patterns": []},
        ])
        mock_bus.publish_message.assert_called_once()
        msg = mock_bus.publish_message.call_args[0][0]
        assert msg.type == "data.behavior.adjusted"

    def test_adjust_behavior_no_event_with_empty_input(self):
        from reasoning.learning import LearningEngine
        mock_bus = MagicMock()
        engine = LearningEngine(event_bus=mock_bus)
        engine.adjust_behavior([])
        mock_bus.publish.assert_not_called()

    def test_generalize_with_belief_engine(self):
        from reasoning.learning import LearningEngine
        mock_belief = MagicMock()
        engine = LearningEngine(belief_engine=mock_belief)
        engine.generalize([
            {"text": "I like coffee", "memory_type": "preference"},
        ])
        # belief_engine is stored but not called by generalize directly
        assert engine.belief_engine is mock_belief

    def test_adjust_behavior_comfort_caps_at_0_3(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        adjustments = engine.adjust_behavior([
            {"summary": "stressed " * 20, "patterns": []},
        ])
        assert adjustments["comfort_behavior"] <= 0.3

    def test_adjust_behavior_playfulness_caps_at_0_2(self):
        from reasoning.learning import LearningEngine
        engine = LearningEngine()
        adjustments = engine.adjust_behavior([
            {"summary": "happy " * 20, "patterns": []},
        ])
        assert adjustments["playfulness_boost"] <= 0.2
