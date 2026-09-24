# M6 · Evidence-based preference evolution + identity overlay tests.
import json
import time

from agency.preference_evolution import PreferenceEvolution
from core.identity.identity_core import IdentityCore


class TestPreferenceEvolution:
    def test_evidence_below_threshold_no_candidate(self, tmp_path):
        ev = PreferenceEvolution(threshold=3, state_path=str(tmp_path / "s.json"),
                                 trail_path=str(tmp_path / "t.json"))
        status = ev.record_evidence("jazz", "like")
        status = ev.record_evidence("jazz", "like")
        assert status["candidate"] is False
        assert ev.apply_candidates([], []) == []

    def test_threshold_reached_candidate(self, tmp_path):
        ev = PreferenceEvolution(threshold=3, state_path=str(tmp_path / "s.json"))
        for _ in range(3):
            status = ev.record_evidence("jazz", "like")
        assert status["candidate"] is True

    def test_apply_moves_topic_with_trail_and_overlay(self, tmp_path):
        ev = PreferenceEvolution(threshold=2, cadence_days=7,
                                 state_path=str(tmp_path / "s.json"),
                                 trail_path=str(tmp_path / "t.json"))
        ev.record_evidence("jazz", "like")
        ev.record_evidence("jazz", "like")
        applied = ev.apply_candidates(["reading"], ["loud music"])
        assert len(applied) == 1
        change = applied[0]
        assert change["topic"] == "jazz"
        assert change["before"] == "dislikes"
        assert change["after"] == "likes"
        assert ev.evolved_preferences() == {"likes": ["jazz"], "dislikes": []}
        trail = ev.decision_trail()
        assert len(trail) == 1
        assert trail[0]["reason"].startswith("evidence")

    def test_cadence_gate_blocks_reapply(self, tmp_path):
        ev = PreferenceEvolution(threshold=2, cadence_days=30,
                                 state_path=str(tmp_path / "s.json"))
        ev.record_evidence("jazz", "like")
        ev.record_evidence("jazz", "like")
        assert len(ev.apply_candidates(["reading"], [])) == 1
        ev.record_evidence("jazz", "dislike")
        ev.record_evidence("jazz", "dislike")
        # cadence not elapsed — no second apply even though direction flipped
        assert ev.apply_candidates(["reading"], []) == []

    def test_direction_flip_after_cadence(self, tmp_path):
        ev = PreferenceEvolution(threshold=2, cadence_days=1,
                                 state_path=str(tmp_path / "s.json"))
        ev.cadence_days = 0.000001  # shrink gate for test; constructor clamps >= 1d
        ev.record_evidence("jazz", "like")
        ev.record_evidence("jazz", "like")
        assert len(ev.apply_candidates(["reading"], [])) == 1
        time.sleep(0.2)
        ev.record_evidence("jazz", "dislike")
        ev.record_evidence("jazz", "dislike")
        ev.record_evidence("jazz", "dislike")
        applied = ev.apply_candidates(["reading"], [])
        assert len(applied) == 1
        assert applied[0]["after"] == "dislikes"
        assert applied[0]["before"] == "likes"

    def test_no_change_when_matches_canonical(self, tmp_path):
        ev = PreferenceEvolution(threshold=2, state_path=str(tmp_path / "s.json"))
        ev.record_evidence("reading", "like")
        ev.record_evidence("reading", "like")
        assert ev.apply_candidates(["reading"], []) == []
        assert ev.evolved_preferences() == {"likes": [], "dislikes": []}

    def test_revert_restores_canonical(self, tmp_path):
        ev = PreferenceEvolution(threshold=2, state_path=str(tmp_path / "s.json"),
                                 trail_path=str(tmp_path / "t.json"))
        ev.record_evidence("jazz", "like")
        ev.record_evidence("jazz", "like")
        ev.apply_candidates(["reading"], [])
        assert ev.revert("jazz") is True
        assert ev.revert("jazz") is False
        assert ev.evolved_preferences() == {"likes": [], "dislikes": []}
        assert ev.decision_trail()[-1]["reason"] == "revert"

    def test_persistence_across_instances(self, tmp_path):
        state = str(tmp_path / "s.json")
        ev1 = PreferenceEvolution(threshold=2, state_path=state,
                                  trail_path=str(tmp_path / "t.json"))
        ev1.record_evidence("jazz", "like")
        ev1.record_evidence("jazz", "like")
        ev1.apply_candidates(["reading"], [])
        ev2 = PreferenceEvolution(threshold=2, state_path=state,
                                  trail_path=str(tmp_path / "t.json"))
        assert ev2.evolved_preferences() == {"likes": ["jazz"], "dislikes": []}
        assert ev2.evidence_for("jazz")["like"] == 2

    def test_invalid_inputs_ignored(self, tmp_path):
        ev = PreferenceEvolution(threshold=3, state_path=str(tmp_path / "s.json"))
        assert ev.record_evidence("", "like")["ok"] is False
        assert ev.record_evidence("topic", "hate")["ok"] is False
        assert ev.evidence_for("") == {}


class TestScanAndApply:
    def test_scan_turn_detects_like(self, tmp_path):
        ev = PreferenceEvolution(threshold=3, state_path=str(tmp_path / "s.json"))
        recorded = ev.scan_turn("I really love jazz music lately", ["jazz"])
        assert recorded == [("jazz", "like")]
        assert ev.evidence_for("jazz")["like"] == 1

    def test_scan_turn_detects_dislike_contraction(self, tmp_path):
        ev = PreferenceEvolution(threshold=3, state_path=str(tmp_path / "s.json"))
        recorded = ev.scan_turn("I don't like mushrooms at all", ["mushrooms"])
        assert recorded == [("mushrooms", "dislike")]
        assert ev.evidence_for("mushrooms")["dislike"] == 1

    def test_scan_turn_adjacency_and_negation(self, tmp_path):
        ev = PreferenceEvolution(threshold=3, state_path=str(tmp_path / "s.json"))
        assert ev.scan_turn("Love hiking", ["hiking"]) == [("hiking", "like")]
        assert ev.scan_turn("Hate traffic", ["traffic"]) == [("traffic", "dislike")]
        # negation is not approval
        assert ev.scan_turn("I do not love broccoli", ["broccoli"]) == []

    def test_scan_turn_no_topic_no_hit(self, tmp_path):
        ev = PreferenceEvolution(threshold=3, state_path=str(tmp_path / "s.json"))
        assert ev.scan_turn("I love it so much", ["it"]) == []  # stop topic
        assert ev.scan_turn("I love jazz", []) == []
        assert ev.scan_turn("", ["jazz"]) == []

    def test_scan_self_activates_apply(self, tmp_path):
        # N>=3 evidence applies on the background apply_pending path: the
        # topic moves to the overlay once the canonical direction differs
        # (jazz is not canonical).
        ev = PreferenceEvolution(threshold=2, cadence_days=30,
                                 state_path=str(tmp_path / "s.json"))
        for _ in range(2):
            ev.scan_turn("I love jazz", ["jazz"])
        # scan is recording-only; nothing applied yet
        assert ev.evolved_preferences() == {"likes": [], "dislikes": []}
        applied = ev.apply_pending()
        assert len(applied) == 1
        assert applied[0]["after"] == "likes"
        assert ev.evolved_preferences()["likes"] == ["jazz"]
        trail = ev.decision_trail()
        assert len(trail) == 1 and trail[0]["after"] == "likes"

    def test_apply_pending_uses_canonical_lists(self, tmp_path):
        ev = PreferenceEvolution(threshold=2, state_path=str(tmp_path / "s.json"))
        ev.record_evidence("jazz", "like")
        ev.record_evidence("jazz", "like")
        applied = ev.apply_pending()
        assert len(applied) == 1
        assert applied[0]["after"] == "likes"

    def test_scan_skips_stop_topics(self, tmp_path):
        ev = PreferenceEvolution(threshold=2, state_path=str(tmp_path / "s.json"))
        assert ev.scan_turn("I love you", ["you", "mai"]) == []


class TestIdentityOverlay:
    def test_get_preferences_projects_overlay(self):
        core = IdentityCore()
        base = core.get_preferences()
        assert "jazz" not in base["likes"] and "jazz" not in base["dislikes"]
        core.attach_preference_overlay({"jazz": {"list": "likes"}})
        evolved = core.get_preferences()
        assert "jazz" in evolved["likes"]
        assert "jazz" not in evolved["dislikes"]

    def test_overlay_moves_existing_topic(self):
        core = IdentityCore()
        base = core.get_preferences()
        assert any(base["dislikes"])
        topic = base["dislikes"][0]
        core.attach_preference_overlay({topic: {"list": "likes"}})
        evolved = core.get_preferences()
        assert topic in evolved["likes"]
        assert topic not in evolved["dislikes"]

    def test_canonical_never_mutated(self):
        core = IdentityCore()
        before = core.get_preferences()
        core.attach_preference_overlay({"jazz": {"list": "likes"}})
        assert core.get_preferences() != before  # overlay projects
        fresh = IdentityCore()
        assert fresh.get_preferences() == before  # source dict untouched
