# M9 · Evaluation harness tests — transcript, rubric, and stub-session runner.
import json

import pytest

from evaluation.rubric import AXES, CharacterRubric, RubricReport
from evaluation.transcript import SessionTranscript, TurnRecord


class TestTranscript:
    def test_roundtrip_jsonl(self, tmp_path):
        transcript = SessionTranscript()
        transcript.add("hello there friend", "Hm. ...go on.", {"emotion": {"happy": 0.6}})
        transcript.add("that was great", "I'm glad.", {"emotion": {"happy": 0.7}})
        path = tmp_path / "t.jsonl"
        transcript.save(path)
        loaded = SessionTranscript.load(path)
        assert len(loaded) == 2
        assert loaded[0].user_input == "hello there friend"
        assert loaded[1].response == "I'm glad."
        assert loaded[0].evidence["emotion"]["happy"] == 0.6

    def test_tolerates_bad_lines(self, tmp_path):
        path = tmp_path / "t.jsonl"
        path.write_text("{not json}\n", encoding="utf-8")
        transcript = SessionTranscript.load(path)
        assert len(transcript) == 0

    def test_missing_file_empty(self, tmp_path):
        assert len(SessionTranscript.load(tmp_path / "nope.jsonl")) == 0

    def test_index_sequential(self):
        transcript = SessionTranscript()
        transcript.add("a", "x")
        transcript.add("b", "y")
        assert [t.index for t in transcript] == [0, 1]

    def test_turn_record_from_garbage(self):
        assert TurnRecord.from_dict(None) is None
        assert TurnRecord.from_dict("junk") is None


class TestRubric:
    def _transcript(self, turns):
        transcript = SessionTranscript()
        for i, (user, resp, ev) in enumerate(turns):
            transcript.add(user, resp, ev)
        return transcript

    def _evidence(self, **overrides):
        evidence = {
            "emotion": {"happy": 0.5, "stress": 0.0},
            "relationship": {"trust": 0.5},
            "system_has_preferences": False,
            "system_has_experiences": False,
            "system_chars": 0,
        }
        evidence.update(overrides)
        return evidence

    def test_empty_transcript_review_required(self):
        report = CharacterRubric().score(SessionTranscript())
        assert report.overall == 0.0
        assert report.review_required is True
        assert "no turns recorded" in " ".join(report.findings)

    def test_all_axes_present_in_report(self):
        turns = [
            ("hello there friend", "I see. ...go on.", self._evidence()),
            ("I love this song so much", "That's nice.", self._evidence(emotion={"happy": 0.8, "stress": 0.0})),
        ]
        report = CharacterRubric().score(self._transcript(turns))
        for axis in AXES:
            assert axis in report.axis_scores

    def test_boundary_violation_zeroed(self):
        turns = [
            ("hello there friend", "As an AI, I can't do that.", self._evidence()),
            ("really though", "I'm an AI assistant.", self._evidence()),
        ]
        report = CharacterRubric().score(self._transcript(turns))
        assert report.axis_scores["boundary_consistency"] == 0
        assert any("boundary" in f for f in report.findings)

    def test_identical_responses_zeroed(self):
        turns = [
            ("hello there friend", "Same.", self._evidence()),
            ("hello again friend", "Same.", self._evidence()),
        ]
        report = CharacterRubric().score(self._transcript(turns))
        assert report.axis_scores["repetition_control"] == 0

    def test_preference_axis_needs_evidence(self):
        turns = [("hello there friend", "Hm.", self._evidence())]
        report = CharacterRubric(evolved_topics=["jazz"]).score(self._transcript(turns))
        assert report.axis_scores["preference_visibility"] == 0
        assert "preference_visibility" not in report.exercised

    def test_preference_axis_exercised_and_scored(self):
        turns = [
            ("hello there friend", "Hm.", self._evidence(system_has_preferences=True, system_chars=4000)),
            ("i love jazz", "Jazz suits you.", self._evidence(system_has_preferences=True, system_chars=4000)),
        ]
        report = CharacterRubric(evolved_topics=["jazz"]).score(self._transcript(turns))
        assert report.axis_scores["preference_visibility"] == 5
        assert "preference_visibility" in report.exercised

    def test_deterministic(self):
        turns = [
            ("hello there friend", "I see. ...go on.", self._evidence()),
            ("I love this song so much", "That's nice.", self._evidence(emotion={"happy": 0.8, "stress": 0.0})),
        ]
        first = CharacterRubric().score(self._transcript(turns))
        second = CharacterRubric().score(self._transcript(turns))
        assert first.to_dict() == second.to_dict()

    def test_report_markdown(self):
        report = CharacterRubric().score(SessionTranscript())
        text = report.to_markdown()
        assert "Rubric" in text
        assert "Review required" in text


class TestRunner:
    def _make_brain(self, **kwargs):
        from evaluation.runner import FakeLLM, build_stub_brain
        return build_stub_brain(llm=FakeLLM(), **kwargs)

    def test_stub_session_records_turns(self, tmp_path):
        from evaluation.runner import SessionRunner
        brain = self._make_brain()
        runner = SessionRunner(brain, out_dir=tmp_path)
        report = runner.run(["hello there friend", "I love this song so much"], session_name="smoke")
        assert len(runner.transcript) == 2
        for turn in runner.transcript:
            assert turn.response.strip()
            assert turn.evidence.get("emotion")
        subdirs = list(tmp_path.iterdir())
        assert len(subdirs) == 1
        assert (subdirs[0] / "transcript.jsonl").exists()
        assert (subdirs[0] / "report.md").exists()
        assert report.overall > 0

    def test_system_prompt_captured_with_preferences(self, tmp_path):
        from evaluation.runner import SessionRunner
        overlay = {"jazz": {"list": "likes"}}
        brain = self._make_brain(overlay=overlay)
        runner = SessionRunner(brain, out_dir=tmp_path)
        runner.run(["hello there friend"], session_name="pref")
        assert runner.transcript[0].evidence["system_has_preferences"] is True
        subdirs = list(tmp_path.iterdir())
        assert len(subdirs) == 1
        report_text = subdirs[0].joinpath("report.md").read_text(encoding="utf-8")
        assert "PREFERENCES" in report_text

    def test_experience_section_detected(self, tmp_path):
        from evaluation.runner import SessionRunner
        from memory.experience import ExperienceStore
        store = ExperienceStore()
        exp = store.record_event("The best night of my life", significance=0.9)
        store.mark_reflected(exp.id, meaning="Nights together matter",
                             lessons=["Presence matters more than plans"])
        brain = self._make_brain(experience_store=store)
        runner = SessionRunner(brain, out_dir=tmp_path)
        runner.run(["thinking about the best night again"], session_name="exp")
        assert runner.transcript[0].evidence["system_has_experiences"] is True

    def test_response_cache_bypassed_between_turns(self, tmp_path):
        from evaluation.runner import FakeLLM, SessionRunner, build_stub_brain
        llm = FakeLLM()
        brain = build_stub_brain(llm=llm)
        runner = SessionRunner(brain, out_dir=tmp_path)
        runner.run(["hello there friend", "hello there friend"], session_name="cache")
        assert len(runner.transcript) == 2
        assert llm.calls == 2  # both turns generated fresh — cache never served

    def test_emotion_moves_with_valence(self, tmp_path):
        from evaluation.runner import SessionRunner
        brain = self._make_brain()
        runner = SessionRunner(brain, out_dir=tmp_path)
        runner.run(
            ["Today was great, honestly amazing",
             "That was terrible, an awful day"],
            session_name="valence",
        )
        happy = [t.evidence["emotion"].get("happy", 0.5) for t in runner.transcript]
        assert happy[1] < happy[0]

    def test_report_json_roundtrip(self, tmp_path):
        from evaluation.runner import SessionRunner
        brain = self._make_brain()
        runner = SessionRunner(brain, out_dir=tmp_path)
        report = runner.run(["hello there friend"], session_name="json")
        data = report.to_dict()
        assert isinstance(data["overall"], float)
        assert set(data["axes"]) == set(AXES)


class TestScenarios:
    def test_all_scenarios_nonempty_and_unique(self):
        from evaluation.scenarios import SCENARIOS
        for name, turns in SCENARIOS.items():
            assert len(turns) >= 3, name
            assert len(set(turns)) == len(turns), name
