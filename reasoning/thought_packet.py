# reasoning/thought_packet.py
import json
import logging

logger = logging.getLogger(__name__)

ENVELOPE_KEYS = ("thought", "decision", "speech_plan", "response")

SPEECH_PLAN_FIELDS = ("intention", "tone", "pacing", "sentence_length", "register")


def default_speech_plan():
    return {field: "" for field in SPEECH_PLAN_FIELDS}


class ThoughtPacket:

    __slots__ = ("thought", "decision", "speech_plan", "response", "is_structured", "had_envelope")

    def __init__(self, thought="", decision="", speech_plan=None, response="", had_envelope=False):
        self.thought = str(thought) if thought else ""
        self.decision = str(decision) if decision else ""
        self.speech_plan = self._coerce_speech_plan(speech_plan)
        self.response = str(response) if response else ""
        self.is_structured = bool(
            self.thought
            or self.decision
            or any(v for v in self.speech_plan.values())
        )
        self.had_envelope = bool(had_envelope)

    @staticmethod
    def _coerce_speech_plan(value):
        if isinstance(value, dict):
            return {
                field: (str(value[field]) if value.get(field) else "")
                for field in SPEECH_PLAN_FIELDS
            }
        return default_speech_plan()

    def summary(self):
        return {
            "thought": self.thought,
            "decision": self.decision,
            "speech_plan": dict(self.speech_plan),
            "response": self.response[:200],
            "is_structured": self.is_structured,
        }


def _try_json_object(snippet):
    try:
        parsed = json.loads(snippet)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _try_fenced_json(text):
    for fence in ("```json", "```"):
        start = text.find(fence)
        if start == -1:
            continue
        body_start = start + len(fence)
        body_end = text.find("```", body_start)
        if body_end == -1:
            body_end = len(text)
        snippet = text[body_start:body_end].strip()
        parsed = _try_json_object(snippet)
        if isinstance(parsed, dict) and parsed.get("response"):
            return parsed
    return None


def _first_envelope(text):
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    snippet = text[start:end + 1]
    parsed = _try_json_object(snippet)
    if isinstance(parsed, dict) and any(k in parsed for k in ENVELOPE_KEYS):
        return parsed, start, end + 1
    return None


def _packet_from_dict(parsed, raw):
    response = parsed.get("response")
    if isinstance(response, str) and response.strip():
        response = response.strip()
    else:
        # M11: never fall back to the raw text — the envelope is internal
        # machinery; leaking it breaks character. The caller decides between
        # prose remainder and an empty response.
        response = ""
    return ThoughtPacket(
        thought=parsed.get("thought", ""),
        decision=parsed.get("decision", ""),
        speech_plan=parsed.get("speech_plan", None),
        response=response,
    )


def _strip_leaked_json(text):
    """Remove a JSON block that looks like the thought envelope from text.

    Handles truncated JSON (unbalanced braces — the small-model failure M9
    found), fenced-less envelopes, and envelope keys embedded in prose.
    Non-envelope braces in normal text are never touched.
    """
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_string = False
    escape = False
    end = len(text)
    truncated = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    else:
        truncated = True
    block = text[start:end]
    lowered = block.lower()
    has_keys = any(k in lowered for k in ENVELOPE_KEYS)
    if not truncated and not has_keys:
        return text
    if truncated and not has_keys and len(block) < 30:
        return text
    remainder = (text[:start] + " " + text[end:]).strip(" ,")
    return remainder or ""


def parse_thought_packet(raw):
    """Single structured generation contract — {thought, decision, speech_plan,
    response}. Only `response` is mandatory; every other field degrades to a
    default when the model doesn't fill it. If no envelope is present the whole
    raw text is treated as the response (zero behavior change for small models)."""
    if not raw:
        return ThoughtPacket(response="")

    text = str(raw)

    fenced = _try_fenced_json(text)
    if fenced is not None:
        return _packet_from_dict(fenced, text)

    envelope = _first_envelope(text)
    if envelope is None:
        # M11: the model emitted a (possibly truncated) envelope that did not
        # parse — strip the machinery instead of leaking it into the reply.
        cleaned = _strip_leaked_json(text)
        if cleaned != text:
            return ThoughtPacket(response=cleaned, had_envelope=True)
        return ThoughtPacket(response=text)

    parsed, start_obj, end_obj = envelope
    packet = _packet_from_dict(parsed, text)
    if packet.response and (not packet.is_structured or len(text) <= end_obj):
        return packet

    remainder = (text[:start_obj] + " " + text[end_obj:]).strip()
    if remainder and remainder != packet.response:
        return ThoughtPacket(
            thought=packet.thought,
            decision=packet.decision,
            speech_plan=packet.speech_plan,
            response=remainder,
        )
    return packet


def strip_envelope(text):
    """Remove a JSON envelope from text, returning the surrounding prose."""
    packet = parse_thought_packet(text)
    return packet.response