# M7 · causal_trace schema + isolation invariants.
# Spec: docs/m7-character-behavioral-spec.md §3.3, §3.4, §11.

import glob
import os

from .fixtures import BASELINE_STIMULI
from .harness import TRACE_KEYS, ScenarioDriver, ScenarioState

# Developer-observability keys that must never appear inside prompt/context
# modules (spec §11.2) — Mai must not see her own machinery.
_FORBIDDEN_KEYS = ("causal_trace", "deltas", "snapshot", "mechanisms")
_SCANNED_DIRS = (os.path.join("prompt", "*.py"),)
_SCANNED_FILES = ("core/prompt_builder.py",)


class TestTraceSchema:
    def _trace(self):
        with ScenarioDriver(ScenarioState()) as d:
            return d.turn(BASELINE_STIMULI[0], elapsed_seconds=7200)

    def test_all_keys_present(self):
        trace = self._trace()
        for key in TRACE_KEYS:
            assert key in trace, f"trace missing '{key}'"

    def test_schema_shapes(self):
        trace = self._trace()
        rel = trace["relationship"]
        assert {"trust", "closeness", "attachment"} <= set(rel)
        needs = trace["needs"]
        assert {"snapshot", "deltas", "triggered"} <= set(needs)
        emotion = trace["emotion"]
        assert {"snapshot", "deltas", "profile"} <= set(emotion)
        assert set(emotion["snapshot"]) >= {"happy", "jealousy", "stress"}
        packet = trace["packet"]
        assert {"thought", "decision", "speech_plan"} <= set(packet)
        assert {"intention", "tone", "pacing", "sentence_length", "register"} <= set(
            packet["speech_plan"]
        )
        style = trace["style"]
        assert {"register", "rate", "hesitation", "sentence_length", "closeness"} <= set(style)
        prosody = trace["prosody"]
        assert {"text", "pause_points", "rate", "sentence_length"} <= set(prosody)
        assert len(trace["renderer"]) == 1
        assert trace["renderer"][0]["renderer"] == "stub"
        assert "emotion_decay" in trace["mechanisms"]
        assert "needs_recovery" in trace["mechanisms"]


class TestTraceIsolation:
    def test_prompt_modules_never_reference_trace_keys(self):
        files = []
        for pattern in _SCANNED_DIRS:
            files.extend(glob.glob(pattern))
        files.extend(_SCANNED_FILES)
        files = [f for f in files if os.path.exists(f)]
        assert files, "no prompt modules to scan — scan scope may be wrong"
        for path in files:
            content = open(path, encoding="utf-8").read()
            for key in _FORBIDDEN_KEYS:
                assert key not in content, (
                    f"trace key '{key}' leaked into {path} (spec §11.2)"
                )

    def test_harness_trace_never_feeds_packet_or_context(self):
        """The driver builds packets from fixtures only — the trace is
        returned to the caller and never re-injected into the chain."""
        with ScenarioDriver(ScenarioState()) as d:
            trace = d.turn(BASELINE_STIMULI[0], elapsed_seconds=7200)
            packet_plan = trace["packet"]["speech_plan"]
            from .fixtures import make_packet
            baseline_plan = dict(make_packet("baseline").speech_plan)
            assert packet_plan == baseline_plan  # packet came from fixtures
