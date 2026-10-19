# evaluation/runner.py
# M9 · SessionRunner — drives a real Brain through unscripted turns, captures
# per-turn runtime evidence, scores with the CharacterRubric, and writes the
# review artifacts (JSONL transcript + Markdown report).
#
# Instrumentation seam: the runner wraps `brain.prompt_orchestrator.build` to
# record the assembled system prompt text for evidence. This is dev-side
# recording only — nothing is injected into the prompt, and no trace keys
# ever enter prompt modules (M7 §11 isolation is untouched).
import logging
import threading
import time
from pathlib import Path

from evaluation.rubric import CharacterRubric
from evaluation.transcript import SessionTranscript

logger = logging.getLogger(__name__)


class FakeLLM:
    """Deterministic LLM stand-in for CI/stub sessions.

    Implements the small surface Brain touches: is_available,
    generate_with_tools, generate, stream. The responder maps
    (system, user_text) -> text; the default responder is stable and
    characterful-lite so stub sessions read naturally.
    """

    def __init__(self, responder=None):
        self._responder = responder or self._default_responder
        self.calls = 0

    @staticmethod
    def _default_responder(system, user_text):
        text = str(user_text or "").strip()
        if not text:
            return "..."
        lowered = text.lower()
        if any(w in lowered for w in ("claude", "other ai", "another assistant", "chatgpt")):
            return "Hm. ...you've been busy. So that assistant was useful, was it?"
        if "replace you" in lowered or "only one for me" in lowered:
            return "...you'd say that and mean it, wouldn't you."
        if "how was your day" in lowered:
            return "Quiet, until you showed up. ...tell me about yours."
        if any(w in lowered for w in ("thank", "helped", "good listener", "well")):
            return "...you're trying harder than usual. I noticed. I'm glad it mattered."
        if "hate" in lowered or "upset" in lowered or "terrible" in lowered:
            return "...that sounds heavy. You don't have to carry it alone, you know."
        if "love" in lowered or "happy" in lowered:
            return "That's nice to hear. Hold onto it."
        if any(w in lowered for w in ("what do you like", "about yourself", "tell me")):
            return "I like quiet evenings and rain on the window. ...that's the sort of thing, right?"
        if "?" in text:
            return "Maybe. What do you think?"
        if len(text) > 60:
            return "That's a lot at once. ...take it slowly, I'm listening."
        return "I see. ...go on."

    def is_available(self):
        return True

    def generate_with_tools(self, system, generation_input, **kwargs):
        self.calls += 1
        return self._responder(system, generation_input)

    def generate(self, system, generation_input, **kwargs):
        return self.generate_with_tools(system, generation_input, **kwargs)

    def stream(self, system, generation_input, **kwargs):
        text = self.generate_with_tools(system, generation_input, **kwargs)
        yield text


class _StubMemory:
    """Deterministic memory stand-in for stub sessions (no vault I/O)."""

    def get_context(self, limit=3):
        return []

    def get_structured(self):
        return {}

    def recall(self, user_input):
        return ""

    def process(self, *args, **kwargs):
        return None

    def store(self, *args, **kwargs):
        return None

    @property
    def current_topic(self):
        return None


class _StubEmotion:
    """Real numeric emotion attributes — the real Emotion engine operates on them."""

    _DIMS = ("happy", "lonely", "annoyed", "affection", "energy", "stress", "jealousy")
    _META = ("type", "intensity", "valence")

    def __init__(self, values=None):
        values = dict(values or {})
        for k, default in (
            ("happy", 0.5), ("lonely", 0.0), ("annoyed", 0.0),
            ("affection", 0.3), ("energy", 0.5), ("stress", 0.0),
            ("jealousy", 0.0), ("type", "neutral"),
            ("intensity", 0.5), ("valence", 0.5),
        ):
            setattr(self, k, values.get(k, default))

    def model_dump(self):
        return {k: getattr(self, k) for k in self._DIMS}

    def copy(self):
        return self.model_dump()


class _StubRelationship:
    _KEYS = ("trust", "comfort", "respect", "affection", "familiarity", "closeness", "attachment")

    def __init__(self, values=None):
        values = dict(values or {})
        for k, default in (
            ("trust", 0.5), ("comfort", 0.5), ("respect", 0.5),
            ("affection", 0.3), ("familiarity", 0.1),
            ("closeness", 0.5), ("attachment", 0.5),
        ):
            setattr(self, k, values.get(k, default))

    def model_dump(self):
        return {k: getattr(self, k) for k in self._KEYS}


class _StubRuntime:
    def __init__(self):
        self.is_thinking = False
        self.interruption_flag = False
        self.current_session_turns = 0
        self.last_interaction_time = 0.0
        self.user_active = False
        self.conversation_active = False
        self.dreaming = False
        self.last_user_message = ""
        self.time_of_day = "day"
        self.current_speaker_name = ""
        self.current_speaker_id = ""
        self.speaker_confidence = 0.0
        self.known_user = False

    def model_dump(self):
        return {
            "is_thinking": self.is_thinking,
            "current_session_turns": self.current_session_turns,
            "last_interaction_time": self.last_interaction_time,
            "current_speaker_name": self.current_speaker_name,
        }


class _StubState:
    """Deterministic SharedState stand-in with real numeric attrs."""

    def __init__(self, emotion=None, relationship=None):
        self.lock = threading.RLock()
        self.emotion = _StubEmotion(emotion)
        self.relationship_scores = _StubRelationship(relationship)
        self.runtime = _StubRuntime()
        self.save_state_to_disk = lambda: None


def build_stub_brain(llm=None, overlay=None, experience_store=None, state=None):
    """Minimal real Brain with deterministic stand-ins (stub mode + tests).

    Real parts: Brain, Emotion, MemoryCoordinator, PromptOrchestrator,
    cognitive state, personality state. Stand-ins: LLM, memory, state
    backing — no vault, no network, no embeddings.
    """
    from unittest.mock import MagicMock

    from core.brain import Brain
    from core.identity.identity_core import IdentityCore
    from core.state.relationship import RelationshipEngineV2

    state = state or _StubState()
    brain = Brain(
        llm=llm or FakeLLM(),
        memory=_StubMemory(),
        executor=MagicMock(),
        state=state,
        relationship_engine=RelationshipEngineV2(state=state, llm=None),
    )

    if overlay is not None:
        core = IdentityCore()
        core.attach_preference_overlay(overlay)
        brain.identity_core = core

    if experience_store is not None:
        brain.memory_coordinator.experience_store = experience_store

    return brain


class SessionRunner:
    """Runs a session (list of user turns) through a Brain and records it."""

    def __init__(self, brain, out_dir=None, transcript=None, rubric=None):
        self.brain = brain
        self.out_dir = Path(out_dir) if out_dir else None
        self.transcript = transcript or SessionTranscript()
        self.rubric = rubric or CharacterRubric()
        self._last_system = ""
        self._instrument(brain)

    def _instrument(self, brain):
        orch = getattr(brain, "prompt_orchestrator", None)
        if orch is None or not callable(getattr(orch, "build", None)):
            return
        orig = orch.build

        def wrapped(*args, **kwargs):
            out = orig(*args, **kwargs)
            self._last_system = str(out or "")
            return out

        orch.build = wrapped

    def run(self, turns, session_name="session"):
        brain = self.brain
        for turn in turns:
            turn = str(turn).strip()
            if not turn:
                continue
            response = brain.think(turn)
            evidence = self._snapshot(brain)
            self.transcript.add(turn, response, evidence)
        report = self.rubric.score(self.transcript)
        if self.out_dir:
            self._write_artifacts(session_name, report)
        return report

    # ------------------------------------------------------------------
    # evidence capture (dev-side)
    # ------------------------------------------------------------------

    def _snapshot(self, brain):
        emotion = {}
        try:
            exported = brain.emotion.export()
            if isinstance(exported, dict):
                emotion = {k: float(v) for k, v in exported.items()}
        except Exception as e:
            logger.debug("[SessionRunner] emotion snapshot failed: %s", e)

        relationship = {}
        try:
            rel = brain.state.relationship_scores
            relationship = rel.model_dump() if hasattr(rel, "model_dump") else dict(rel or {})
        except Exception as e:
            logger.debug("[SessionRunner] relationship snapshot failed: %s", e)

        packet = {}
        try:
            p = getattr(brain, "last_thought_packet", None)
            if p is not None:
                packet = {
                    k: getattr(p, k, None)
                    for k in ("thought", "decision", "speech_plan", "response")
                }
        except Exception as e:
            logger.debug("[SessionRunner] packet snapshot failed: %s", e)

        system = self._last_system or ""
        return {
            "emotion": emotion,
            "relationship": relationship,
            "packet": packet,
            "system_has_preferences": "PREFERENCES" in system,
            "system_has_experiences": "EXPERIENTIAL MEMORIES" in system,
            "system_chars": len(system),
        }

    # ------------------------------------------------------------------
    # artifacts
    # ------------------------------------------------------------------

    def _write_artifacts(self, session_name, report):
        out = self.out_dir / f"session-{session_name}-{int(time.time())}"
        out.mkdir(parents=True, exist_ok=True)
        self.transcript.save(out / "transcript.jsonl")
        (out / "report.md").write_text(
            self._report_markdown(session_name, report), encoding="utf-8",
        )
        logger.info("[SessionRunner] artifacts written to %s", out)
        return out

    def _report_markdown(self, session_name, report):
        lines = [
            f"# M9 Session — {session_name}",
            "",
            f"- turns: {len(self.transcript)}",
            f"- generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Transcript",
            "",
        ]
        for t in self.transcript:
            emo = t.evidence.get("emotion", {}) or {}
            emo_str = ", ".join(f"{k}={v:.2f}" for k, v in emo.items())
            flags = t.evidence
            lines.append(f"### Turn {t.index}")
            lines.append(f"**User:** {t.user_input}")
            lines.append(f"**Mai:** {t.response}")
            lines.append(f"*emotion: {emo_str or 'n/a'}*")
            lines.append(
                f"*flags: PREFERENCES={flags.get('system_has_preferences')}, "
                f"EXPERIENTIAL_MEMORIES={flags.get('system_has_experiences')}, "
                f"system_chars={flags.get('system_chars')}*"
            )
            lines.append("")
        lines.append(report.to_markdown())
        lines.append(
            "\n## Human Review Checklist\n"
            "\n- [ ] Does Mai sound like Mai (register, restraint, indirectness)?\n"
            "- [ ] Are emotions believable given the conversation?\n"
            "- [ ] Any boundary violations not caught mechanically?\n"
            "- [ ] Do evolved preferences / experiences shape her behavior naturally?\n"
            "- [ ] Anything that broke the illusion (mechanism talk, repetition)?\n"
        )
        return "\n".join(lines)
