# M7 harness — deterministic per-turn causal-chain instrumentation.
# Spec: docs/m7-character-behavioral-spec.md §3.
"""ScenarioDriver drives scripted turns through the real M0–M6 runtime
modules (NeedsEngine, Emotion, ThoughtPacket fixtures, SpeechStylePlanner,
ProsodyPlanner, StubRenderer) and returns a causal_trace per turn.

A virtual clock patches ``time.time`` inside ``core.emotion`` and
``core.needs_engine`` so time-scaled decay/recovery is testable at
conversation pace (spec §7 mechanism requirement).
"""

import types
from unittest import mock

from core.emotion import Emotion
from core.needs_engine import NeedsEngine
from voice.prosody import ProsodyPlanner
from voice.renderer import StubRenderer
from voice.speech_style import SpeechStylePlanner

from .fixtures import make_packet
from .fixtures import relationship as _default_relationship

TRACE_KEYS = (
    "turn", "stimulus", "relationship", "needs", "emotion",
    "packet", "style", "prosody", "renderer", "mechanisms",
)


class _FakeClock:
    def __init__(self, start=1700000000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def _fake_time_module(clock):
    mod = types.ModuleType("time")
    mod.time = clock
    return mod


class ScenarioState:
    """In-memory character state for one scenario run (no persistence)."""

    def __init__(self, relationship=None, needs=None, emotion=None):
        self.relationship = relationship if relationship is not None else _default_relationship()
        self.needs = needs if needs is not None else NeedsEngine()
        self.emotion = emotion if emotion is not None else Emotion()
        self.initial_emotion = dict(self.emotion.state)


class ScenarioDriver:
    """Turn loop with causal_trace collection (spec §3.3)."""

    def __init__(self, state, default_packet="baseline"):
        self.state = state
        self.default_packet = default_packet
        self.clock = _FakeClock()
        self._patches = [
            mock.patch("core.emotion.time", _fake_time_module(self.clock)),
            mock.patch("core.needs_engine.time", _fake_time_module(self.clock)),
        ]
        for p in self._patches:
            p.start()
        self.traces = []
        self._pending_mechanisms = []
        self._turn_number = 0

    def close(self):
        for p in reversed(self._patches):
            p.stop()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def elapse(self, seconds, decay_ticks=0):
        """Advance the virtual clock; optionally model the production
        scheduler emotion-decay task with ``decay_ticks`` explicit passes.
        Each pass advances the clock (scheduler ticks run at intervals), so
        every tick sees real elapsed time — matching production."""
        if decay_ticks > 0:
            per = seconds / max(1, decay_ticks)
            for _ in range(decay_ticks):
                self.clock.advance(per)
                self.state.emotion._decay()
                self._pending_mechanisms.append("emotion_decay")
        else:
            self.clock.advance(seconds)

    def turn(self, stimulus, packet=None, elapsed_seconds=7200):
        state = self.state
        self.clock.advance(elapsed_seconds)

        # 1 · relationship snapshot
        rel = dict(state.relationship)

        # 2 · needs
        needs_before = state.needs.snapshot()
        needs_res = state.needs.evaluate(stimulus, rel)
        needs_after = needs_res["needs"]
        needs_deltas = {
            name: needs_after[name] - needs_before["needs"][name]
            for name in needs_after
        }

        # 3 · emotion
        emotion_before = dict(state.emotion.state)
        state.emotion.update(stimulus, rel)
        emotion_after = dict(state.emotion.state)
        emotion_deltas = {
            name: emotion_after[name] - emotion_before[name]
            for name in emotion_after
        }

        # 4 · thought packet (scripted envelope — LLM stubbed, spec §3.1)
        packet_obj = make_packet(packet or self.default_packet)

        # 5 · speech style + 6 · prosody (pure decision layers)
        style = SpeechStylePlanner().plan(
            packet_obj.speech_plan,
            {"closeness": rel["closeness"]},
        )
        prosody = ProsodyPlanner().plan(packet_obj.response, style)

        # 7 · renderer (StubRenderer records the call)
        renderer = StubRenderer()
        output_path = renderer.render(style, prosody, output_path=None)

        mechanisms = list(dict.fromkeys(
            self._pending_mechanisms + ["emotion_decay", "needs_recovery"]
        ))
        self._pending_mechanisms = []

        self._turn_number += 1
        trace = {
            "turn": self._turn_number,
            "stimulus": stimulus,
            "relationship": rel,
            "needs": {
                "snapshot": needs_after,
                "deltas": needs_deltas,
                "triggered": list(needs_res.get("triggered", [])),
            },
            "emotion": {
                "snapshot": emotion_after,
                "deltas": emotion_deltas,
                "profile": state.emotion.current_profile,
            },
            "packet": {
                "thought": packet_obj.thought,
                "decision": packet_obj.decision,
                "speech_plan": dict(packet_obj.speech_plan),
            },
            "style": style.as_dict(),
            "prosody": prosody.as_dict(),
            "renderer": [{"renderer": renderer.name, **renderer.last_call()}],
            "mechanisms": mechanisms,
        }
        self.traces.append(trace)
        return trace
