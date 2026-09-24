# M7 · Renderer Parity Contract — the renderer must not decide who Mai is.
# Spec: docs/m7-character-behavioral-spec.md §10.

from .fixtures import make_packet
from voice.prosody import ProsodyPlanner
from voice.renderer import (
    KokoroRenderer,
    StubRenderer,
    VoiceRenderer,
    create_renderer,
)
from voice.speech_style import SpeechStylePlanner


class FakeTTS:
    """Records generate() kwargs — KokoroRenderer introspects the signature."""

    def __init__(self):
        self.calls = []

    def generate(self, text, output_path, emotion="neutral", speed=1.0):
        self.calls.append({
            "text": text, "output_path": output_path,
            "emotion": emotion, "speed": speed,
        })
        return output_path


class ThirdRenderer(VoiceRenderer):
    """Duck-typed future renderer — proves the seam is open."""

    name = "third"

    def __init__(self):
        super().__init__()
        self.calls = []

    def render(self, style, prosody=None, output_path=None):
        self.calls.append({
            "text": prosody.text if prosody else "",
            "style": style.as_dict() if style else None,
            "prosody": prosody.as_dict() if prosody else None,
            "output_path": output_path,
        })
        return output_path


def _fixture_style_prosody(closeness=0.7):
    packet = make_packet("teasing")
    style = SpeechStylePlanner().plan(
        packet.speech_plan, {"closeness": closeness}
    )
    prosody = ProsodyPlanner().plan(packet.response, style)
    return packet, style, prosody


class TestRendererParity:
    """Same semantic input through Kokoro / Stub / future renderer.

    Only acoustic realization may differ — personality, word choice,
    emotional intention, and prosody semantics must be identical.
    """

    def test_semantic_identity_across_renderers(self):
        packet, style, prosody = _fixture_style_prosody()
        tts = FakeTTS()
        kokoro = KokoroRenderer(tts=tts)
        stub = StubRenderer()
        third = ThirdRenderer()

        out_k = kokoro.render(style, prosody, output_path="out_k.wav")
        out_s = stub.render(style, prosody, output_path="out_s.wav")
        out_t = third.render(style, prosody, output_path="out_t.wav")

        assert out_k == "out_k.wav" and out_s == "out_s.wav" and out_t == "out_t.wav"

        # identical input text everywhere
        assert tts.calls[0]["text"] == prosody.text
        assert stub.last_call()["text"] == prosody.text
        assert third.calls[0]["text"] == prosody.text

        # semantic mapping preserved: register -> emotion, rate -> speed
        assert tts.calls[0]["emotion"] == style.register
        assert tts.calls[0]["speed"] == style.rate

        # style/prosody objects untouched by any renderer
        style_before = style.as_dict()
        prosody_before = prosody.as_dict()
        assert stub.last_call()["style"] == style_before
        assert stub.last_call()["prosody"] == prosody_before
        assert third.calls[0]["style"] == style_before
        assert third.calls[0]["prosody"] == prosody_before
        assert style.as_dict() == style_before
        assert prosody.as_dict() == prosody_before

    def test_teasing_semantics_survive_kokoro(self):
        packet, style, prosody = _fixture_style_prosody()
        tts = FakeTTS()
        kokoro = KokoroRenderer(tts=tts)
        kokoro.render(style, prosody, output_path="out.wav")
        # personality survives the renderer: register and prosody text intact
        assert tts.calls[0]["emotion"] == "teasing"
        assert prosody.text  # hesitation/duration markers preserved

    def test_renderer_never_alters_packet(self):
        packet, style, prosody = _fixture_style_prosody()
        plan_before = dict(packet.speech_plan)
        for renderer in (KokoroRenderer(tts=FakeTTS()), StubRenderer(), ThirdRenderer()):
            renderer.render(style, prosody, output_path="out.wav")
        assert dict(packet.speech_plan) == plan_before

    def test_create_renderer_factory(self):
        assert isinstance(create_renderer("kokoro", tts=FakeTTS()), KokoroRenderer)
        assert isinstance(create_renderer("stub"), StubRenderer)
        assert create_renderer("missing") is None
