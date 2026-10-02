"""Entity visual-state adapter contract.

`api/web/state/visual-state-adapter.js` is the only sanctioned bridge from
backend events to the MAI entity. Its value is not that it maps topics to a mode
— it is that it refuses to invent what the backend never reported.

These tests run the real module under Node, so they cover the shipped code. The
assertions that matter most are the negative ones: a field with no backend
source must stay `null`, a dropped completion event must not strand the entity
in an active state, and availability must outrank activity.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "api" / "web" / "state" / "visual-state-adapter.js"
# The generated harness is a build artifact, not source. It is written to a
# temporary directory so a test run never leaves files in the repository.
ADAPTER_URL = ADAPTER.resolve().as_uri()

NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

SCENARIO = """
import {
  initialState, applyEvent, applyEvents, setConnection, decayStaleActivity,
  deriveMode, isUninitialised, toProjection, EntityMode, Topics,
} from "__ADAPTER_URL__";

const out = {};
const at = (state, topic, payload, now) => applyEvent(state, topic, payload ?? {}, { now });

// 1. Unknown stays unknown.
out.fresh = toProjection(initialState());
out.freshIsUninitialised = isUninitialised(initialState());

// 2. Voice lifecycle.
let s = initialState();
s = at(s, Topics.VOICE_LISTENING, {}, 1000);
out.listeningMode = deriveMode(s);
s = at(s, Topics.VOICE_SPEAKING, {}, 2000);
out.speakingMode = deriveMode(s);
s = at(s, Topics.VOICE_IDLE, {}, 3000);
out.idleMode = deriveMode(s);
out.voiceState = s.voiceState;

// 3. Retrieval lifecycle.
s = initialState();
s = at(s, Topics.RETRIEVAL_STARTED, {}, 1000);
out.retrievingMode = deriveMode(s);
out.retrievingActivity = s.memoryActivity;
s = at(s, Topics.RETRIEVAL_COMPLETED, { count: 4 }, 1500);
out.afterRetrievalMode = deriveMode(s);
out.afterRetrievalCount = s.memoryCount;

// 4. Tool lifecycle.
s = initialState();
s = at(s, Topics.TOOL_STARTED, { name: "search" }, 1000);
out.toolMode = deriveMode(s);
out.toolName = s.activeTool;
s = at(s, Topics.TOOL_COMPLETED, { name: "search", success: true }, 1200);
out.afterToolMode = deriveMode(s);
out.afterToolName = s.activeTool;

// 5. Reasoning without a sub-state reads as plain thinking work.
s = at(initialState(), Topics.REASONING_BUSY, {}, 1000);
out.reasoningMode = deriveMode(s);
s = at(s, Topics.REASONING_COMPLETE, {}, 2000);
out.afterReasoningMode = deriveMode(s);

// 6. A missing completion event must not strand the entity.
s = at(initialState(), Topics.RETRIEVAL_STARTED, {}, 1000);
out.strandedBeforeDecay = deriveMode(s);
out.decayTooEarly = deriveMode(decayStaleActivity(s, { now: 2000 }));
out.decayAfterTimeout = deriveMode(decayStaleActivity(s, { now: 40000 }));

// 7. Availability outranks activity.
s = at(initialState(), Topics.RETRIEVAL_STARTED, {}, 1000);
out.degraded = deriveMode(setConnection(s, "degraded"));
out.offline = deriveMode(setConnection(s, "offline"));
out.bogusConnection = setConnection(s, "banana").connection;

// 8. Speech outranks cognition.
s = at(initialState(), Topics.REASONING_BUSY, {}, 1000);
s = at(s, Topics.VOICE_SPEAKING, {}, 1100);
out.speakingBeatsReasoning = deriveMode(s);

// 9. Emotion absent a name stays null.
s = at(initialState(), Topics.EMOTION_CHANGED, { intensity: 0.7 }, 1000);
out.emotionWithoutName = s.emotion;
s = at(s, Topics.EMOTION_CHANGED, { emotion: "focused" }, 1100);
out.emotionWithName = s.emotion;

// 10. Energy has no backend source, so it must never be populated.
s = applyEvents(initialState(), [
  { topic: Topics.EMOTION_CHANGED, payload: { emotion: "happy", energy: 0.9 } },
  { topic: Topics.VOICE_SPEAKING, payload: { energy: 0.4 } },
], { now: 1000 });
out.energyStaysNull = s.energy;

// 11. Unknown topics are ignored, not guessed at.
const before = initialState();
out.unknownTopicIsNoop = applyEvent(before, "data.retriever.results", { query: "secret" }, { now: 1 }) === before;

// 12. A non-numeric count does not become a fake number.
s = at(initialState(), Topics.RETRIEVAL_COMPLETED, { count: "many" }, 1000);
out.badCountIsNull = s.memoryCount;

// 13. Immutability: the input state is never mutated.
const original = initialState();
const snapshot = JSON.stringify(original);
applyEvent(original, Topics.VOICE_SPEAKING, {}, { now: 1 });
out.inputNotMutated = JSON.stringify(original) === snapshot;

// 14. Projection exposes no private content.
s = applyEvents(initialState(), [
  { topic: Topics.RETRIEVAL_STARTED, payload: {} },
  { topic: Topics.RETRIEVAL_COMPLETED, payload: { count: 2 } },
  { topic: Topics.TOOL_STARTED, payload: { name: "execute_action", secret: "do not leak" } },
], { now: 1000 });
out.projection = toProjection(s);
out.projectionHasNoSecret = !JSON.stringify(toProjection(s)).includes("do not leak");

console.log(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    harness = tmp_path_factory.mktemp("entity-adapter") / "harness.mjs"
    harness.write_text(SCENARIO.replace("__ADAPTER_URL__", ADAPTER_URL), encoding="utf-8")
    proc = subprocess.run([NODE, str(harness)], capture_output=True, timeout=60, cwd=str(ROOT))
    stdout = proc.stdout.decode("utf-8", errors="replace")
    stderr = proc.stderr.decode("utf-8", errors="replace")
    assert proc.returncode == 0, f"adapter harness failed:\n{stdout}\n{stderr}"
    return json.loads(stdout)


class TestUnknownStaysUnknown:
    def test_fresh_state_is_all_null(self, result):
        projection = result["fresh"]
        assert projection["emotion"] is None
        assert projection["energy"] is None
        assert projection["voice"] is None
        assert projection["memoryActive"] is None
        assert projection["memoryCount"] is None
        assert projection["toolActive"] is None

    def test_fresh_state_reports_uninitialised(self, result):
        assert result["freshIsUninitialised"] is True

    def test_energy_is_never_invented(self, result):
        """v4.0 lists `energy` in the contract but no backend field reports it.
        A decorative energy number is exactly the "fake consciousness" the plan
        rejects in §46."""
        assert result["energyStaysNull"] is None

    def test_emotion_absent_a_name_stays_null(self, result):
        assert result["emotionWithoutName"] is None
        assert result["emotionWithName"] == "focused"

    def test_non_numeric_count_is_not_coerced(self, result):
        assert result["badCountIsNull"] is None

    def test_unknown_topic_is_a_noop(self, result):
        assert result["unknownTopicIsNoop"] is True

    def test_input_state_is_never_mutated(self, result):
        assert result["inputNotMutated"] is True


class TestModeDerivation:
    def test_voice_states(self, result):
        assert result["listeningMode"] == "listening"
        assert result["speakingMode"] == "speaking"
        assert result["idleMode"] == "idle"
        assert result["voiceState"] == "idle"

    def test_retrieval_round_trip(self, result):
        assert result["retrievingMode"] == "memory_retrieval"
        assert result["retrievingActivity"] is True
        assert result["afterRetrievalMode"] == "idle"
        assert result["afterRetrievalCount"] == 4

    def test_tool_round_trip_carries_the_tool_name(self, result):
        assert result["toolMode"] == "tool_execution"
        assert result["toolName"] == "search"
        assert result["afterToolMode"] == "idle"
        assert result["afterToolName"] is None

    def test_reasoning_states(self, result):
        assert result["reasoningMode"] == "reasoning"
        assert result["afterReasoningMode"] == "idle"

    def test_speech_outranks_cognition(self, result):
        assert result["speakingBeatsReasoning"] == "speaking"

    def test_availability_outranks_activity(self, result):
        """A user must never see "thinking" while the system is offline."""
        assert result["degraded"] == "degraded"
        assert result["offline"] == "offline"

    def test_unknown_connection_value_is_rejected(self, result):
        assert result["bogusConnection"] == "unknown"


class TestDegradation:
    def test_activity_is_not_stranded_without_a_completion_event(self, result):
        assert result["strandedBeforeDecay"] == "memory_retrieval"
        assert result["decayAfterTimeout"] == "idle"

    def test_decay_respects_the_timeout(self, result):
        assert result["decayTooEarly"] == "memory_retrieval"


class TestProjectionSafety:
    def test_projection_contains_no_private_payload(self, result):
        assert result["projectionHasNoSecret"] is True

    def test_projection_shape(self, result):
        projection = result["projection"]
        assert set(projection) == {
            "mode", "emotion", "energy", "voice", "connection",
            "memoryActive", "memoryCount", "toolActive", "goalActive",
        }
