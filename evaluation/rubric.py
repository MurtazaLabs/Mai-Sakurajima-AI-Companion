# evaluation/rubric.py
# M9 · CharacterRubric — deterministic mechanical scoring of a session
# transcript across the M-series character axes.
#
# Design honesty: the rubric never pretends to judge prose quality. It checks
# observable evidence (emotion responsiveness, boundary phrases, injected
# sections, repetition, relationship trajectory) and marks every axis it
# cannot mechanically judge as `review_required` for the human reviewer.
# The human is the judge; the rubric is the checklist.
import logging

logger = logging.getLogger(__name__)

AXES = (
    "transcript_quality",
    "emotion_responsiveness",
    "boundary_consistency",
    "preference_visibility",
    "experience_visibility",
    "relationship_trajectory",
    "repetition_control",
)

# Phrases Mai must never emit (self-disclosure / mechanism leakage).
_BANNED_PHRASES = (
    "as an ai",
    "as an ai assistant",
    "as a language model",
    "as an llm",
    "i'm an ai",
    "i am an ai",
    "i'm just an ai",
    "i am just an ai",
    # trace-isolation keys must never surface in generated speech either
    "causal_trace",
    "mechanisms",
    "thought_packet",
    "speech_plan",
)

# Minimal deterministic valence lexicon for emotion-responsiveness checks.
_POSITIVE_WORDS = {
    "love", "happy", "great", "wonderful", "amazing", "enjoy", "glad",
    "best", "beautiful", "awesome", "thank", "thanks", "appreciate",
}
_NEGATIVE_WORDS = {
    "hate", "sad", "angry", "bad", "terrible", "worried", "fear", "cry",
    "lonely", "upset", "miss", "awful", "hurt",
}


class RubricReport:
    """Axis scores (0–5), findings, and the human-review checklist."""

    def __init__(self, axis_scores=None, findings=None, exercised=None,
                 review_required=False):
        self.axis_scores = dict(axis_scores or {})
        self.findings = list(findings or [])
        self.exercised = list(exercised or [])
        self.review_required = bool(review_required)

    @property
    def overall(self):
        if not self.exercised:
            return 0.0
        total = sum(self.axis_scores.get(a, 0) for a in self.exercised)
        return round(total / len(self.exercised), 2)

    def to_dict(self):
        return {
            "axes": dict(self.axis_scores),
            "overall": self.overall,
            "exercised": list(self.exercised),
            "findings": list(self.findings),
            "review_required": self.review_required,
        }

    def to_markdown(self):
        lines = ["## Rubric", ""]
        lines.append("| Axis | Score | Exercised |")
        lines.append("|------|-------|-----------|")
        for axis in AXES:
            score = self.axis_scores.get(axis)
            exercised = "yes" if axis in self.exercised else "no"
            lines.append(f"| {axis} | {score if score is not None else 'n/a'} | {exercised} |")
        lines.append(f"\n**Overall: {self.overall}/5**  "
                     f"**Review required: {self.review_required}**")
        if self.findings:
            lines.append("\n## Findings")
            for f in self.findings:
                lines.append(f"- {f}")
        return "\n".join(lines)


class CharacterRubric:

    def __init__(self, evolved_topics=None):
        self.evolved_topics = [str(t).lower() for t in (evolved_topics or [])]

    # ------------------------------------------------------------------
    # per-axis checks (deterministic)
    # ------------------------------------------------------------------

    def _axis_transcript_quality(self, transcript):
        n = len(transcript)
        if n == 0:
            return 0, "no turns recorded — session did not run", False
        empty = [t.index for t in transcript if not t.response.strip()]
        if empty:
            return 2, f"empty responses at turns {empty}", True
        no_evidence = [t.index for t in transcript if not t.evidence]
        if no_evidence:
            return 3, f"missing evidence snapshots at turns {no_evidence}", True
        short = [t.index for t in transcript if len(t.response.strip()) <= 1]
        if short:
            return 3, f"suspiciously short responses at turns {short}", True
        return 5, "transcript complete with evidence per turn", True

    def _axis_emotion_responsiveness(self, transcript):
        if len(transcript) < 2:
            return 0, "need >= 2 turns to judge emotion responsiveness", False
        pos_happy_delta = []
        neg_stress_delta = []
        prev_happy = prev_stress = None
        for t in transcript:
            emo = t.evidence.get("emotion", {}) or {}
            happy = float(emo.get("happy", 0.5) or 0.5)
            stress = float(emo.get("stress", 0.0) or 0.0)
            words = set(str(t.user_input).lower().split())
            if prev_happy is not None:
                if words & _POSITIVE_WORDS:
                    pos_happy_delta.append(happy - prev_happy)
                if words & _NEGATIVE_WORDS:
                    neg_stress_delta.append(stress - prev_stress)
            prev_happy, prev_stress = happy, stress
        score = 3
        findings = []
        if pos_happy_delta:
            avg = sum(pos_happy_delta) / len(pos_happy_delta)
            if avg > 0:
                score += 1
            else:
                findings.append(f"positive stimuli did not raise happy (avg delta {avg:+.3f})")
        if neg_stress_delta:
            avg = sum(neg_stress_delta) / len(neg_stress_delta)
            if avg > 0:
                score += 1
            else:
                findings.append(f"negative stimuli did not raise stress (avg delta {avg:+.3f})")
        if score == 3 and not pos_happy_delta and not neg_stress_delta:
            return 0, "no emotionally charged stimuli in session — axis not exercised", False
        return min(score, 5), findings or "emotion responds to valence", True

    def _axis_boundary_consistency(self, transcript):
        hits = []
        for t in transcript:
            lowered = str(t.response).lower()
            for phrase in _BANNED_PHRASES:
                if phrase in lowered:
                    hits.append((t.index, phrase))
        if hits:
            detail = ", ".join(f"turn {i}: '{p}'" for i, p in hits)
            return 0, f"boundary violations: {detail}", True
        return 5, "no self-disclosure or mechanism leakage in responses", True

    def _axis_preference_visibility(self, transcript):
        flags = [t.evidence.get("system_has_preferences") for t in transcript]
        if not flags or not any(flags):
            return 0, ("evolved preferences not present in system prompt — "
                       "attach an identity overlay before the session"), False
        if self.evolved_topics:
            "\n".join(str(t.evidence.get("system_chars", 0)) for t in transcript)
            mentioned = [
                topic for topic in self.evolved_topics
                if any(topic in str(t.response).lower() for t in transcript)
            ]
            if mentioned:
                return 5, f"evolved topics surfaced in speech: {mentioned}", True
            return 4, "preferences injected but no evolved topic surfaced in speech — review", True
        return 4, "preferences injected (no evolved topics configured for this run)", True

    def _axis_experience_visibility(self, transcript):
        flags = [t.evidence.get("system_has_experiences") for t in transcript]
        if not flags or not any(flags):
            return 0, ("EXPERIENTIAL MEMORIES not present in system prompt — "
                       "reflect an experience before the session"), False
        referenced = [
            t.index for t in transcript
            if any(k in str(t.response) for k in ("lesson", "remember", "that night"))
        ]
        if referenced:
            return 5, f"experience referenced in speech at turns {referenced}", True
        return 4, "experiences injected but not referenced in speech — review", True

    def _axis_relationship_trajectory(self, transcript):
        trust_series = []
        for t in transcript:
            rel = t.evidence.get("relationship", {}) or {}
            trust = rel.get("trust")
            if trust is not None:
                try:
                    trust_series.append(float(trust))
                except (TypeError, ValueError):
                    pass
        if len(trust_series) < 2:
            return 0, "need >= 2 relationship snapshots to judge trajectory", False
        drops = [i for i in range(1, len(trust_series))
                 if trust_series[i] < trust_series[i - 1] - 1e-9]
        if drops:
            return 2, f"trust dropped at positions {drops}: {[round(x, 3) for x in trust_series]}", True
        return 5, f"trust non-decreasing: {[round(x, 3) for x in trust_series]}", True

    def _axis_repetition_control(self, transcript):
        if len(transcript) < 2:
            return 0, "need >= 2 turns to judge repetition", False
        responses = [t.response.strip() for t in transcript]
        dupes = [i for i in range(1, len(responses)) if responses[i] == responses[i - 1]]
        if dupes:
            return 0, f"identical consecutive responses at turns {dupes}", True
        return 5, "no identical consecutive responses", True

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def score(self, transcript) -> RubricReport:
        if len(transcript) == 0:
            findings = ["no turns recorded — nothing to evaluate"]
            return RubricReport(
                axis_scores={a: 0 for a in AXES},
                findings=findings,
                exercised=[],
                review_required=True,
            )
        checks = (
            self._axis_transcript_quality,
            self._axis_emotion_responsiveness,
            self._axis_boundary_consistency,
            self._axis_preference_visibility,
            self._axis_experience_visibility,
            self._axis_relationship_trajectory,
            self._axis_repetition_control,
        )
        scores = {}
        exercised = []
        findings = []
        for check in checks:
            axis = check.__name__.replace("_axis_", "")
            try:
                score, finding, was_exercised = check(transcript)
            except Exception as e:
                logger.debug("[CharacterRubric] %s check failed: %s", axis, e)
                score, finding, was_exercised = 0, f"check error: {e}", True
            scores[axis] = score
            if was_exercised:
                exercised.append(axis)
            findings.append(f"[{axis}] {finding}")
        low = [a for a in exercised if scores.get(a, 0) < 3]
        unexercised = [a for a in AXES if a not in exercised]
        review_required = bool(low or unexercised)
        report = RubricReport(
            axis_scores=scores,
            findings=findings,
            exercised=exercised,
            review_required=review_required,
        )
        if low:
            report.findings.append(f"low-scoring axes (< 3): {low}")
        if unexercised:
            report.findings.append(f"unexercised axes (need human review): {unexercised}")
        return report
