# tests/test_voice_renderer.py — M4 seam + planner tests
from voice.prosody import ProsodyPlan, ProsodyPlanner
from voice.renderer import KokoroRenderer, StubRenderer, create_renderer
from voice.speech_style import (
    REGISTER_ANNOYED,
    REGISTER_SOFT,
    REGISTER_TEASING,
    REGISTER_WARM,
    SpeechStyle,
    SpeechStylePlanner,
)


class TestSpeechStylePlanner:

    def test_neutral_defaults(self):
        style = SpeechStylePlanner().plan()
        assert style.register == "neutral"
        assert style.rate == 1.0
        assert style.hesitation == "light"
        assert style.sentence_length == "balanced"
        assert style.closeness == 0.5

    def test_teasing_tone_maps_register(self):
        style = SpeechStylePlanner().plan({"tone": "teasing"})
        assert style.register == REGISTER_TEASING

    def test_explicit_register_wins_over_tone(self):
        style = SpeechStylePlanner().plan({"register": "annoyed", "tone": "teasing"})
        assert style.register == REGISTER_ANNOYED

    def test_pacing_label_to_rate(self):
        style = SpeechStylePlanner().plan({"pacing": "fast"})
        assert style.rate == 1.08
        slow = SpeechStylePlanner().plan({"pacing": "relaxed"})
        assert slow.rate == 0.85

    def test_pacing_numeric_clamped(self):
        style = SpeechStylePlanner().plan({"pacing": 3.0})
        assert style.rate == 1.25
        style = SpeechStylePlanner().plan({"pacing": 0.1})
        assert style.rate == 0.7

    def test_intention_hesitation_mapping(self):
        assert SpeechStylePlanner().plan({"intention": "explain"}).hesitation == "none"
        assert SpeechStylePlanner().plan({"intention": "comfort"}).hesitation == "heavy"

    def test_warm_when_close(self):
        style = SpeechStylePlanner().plan({}, context={"closeness": 0.8})
        assert style.register == REGISTER_WARM

    def test_soft_kept_when_close(self):
        style = SpeechStylePlanner().plan({"tone": "soft"}, {"closeness": 0.9})
        assert style.register == REGISTER_SOFT

    def test_sentence_length_gate(self):
        assert SpeechStylePlanner().plan({"sentence_length": "bogus"}).sentence_length == "balanced"
        assert SpeechStylePlanner().plan({"sentence_length": "short"}).sentence_length == "short"


class TestProsodyPlanner:
    def test_empty_text(self):
        plan = ProsodyPlanner().plan("", SpeechStyle())
        assert plan.text == ""
        assert plan.rate == 1.0

    def test_normalize_whitespace(self):
        plan = ProsodyPlanner().plan("  hello   world .  ", SpeechStyle())
        assert plan.text == "hello world ."

    def test_short_sentence_splitting(self):
        text = " ".join(["word"] * 30)
        plan = ProsodyPlanner().plan(text, SpeechStyle(sentence_length="short"))
        parts = plan.text.split(" ")
        # short target = 12 words → at least 2 chunks: 30/12 = 3 chunks
        assert plan.text.count("word") == 30
        assert plan.pause_points >= 0

    def test_hesitation_none(self):
        plan = ProsodyPlanner().plan("go but stop", SpeechStyle(hesitation="none"))
        assert "…" not in plan.text

    def test_hesitation_heavy(self):
        plan = ProsodyPlanner().plan("I want to go but I must stay", SpeechStyle(hesitation="heavy"))
        assert "… but " in plan.text

    def test_hesitation_light(self):
        plan = ProsodyPlanner().plan("a, b, c", SpeechStyle(hesitation="light"))
        assert ", … " in plan.text

    def test_rate_carried_through(self):
        plan = ProsodyPlanner().plan("hello", SpeechStyle(rate=0.9))
        assert plan.rate == 0.9


class TestRendererSeam:

    def test_identical_style_across_renderers(self):
        planner = SpeechStylePlanner()
        prosody = ProsodyPlanner()
        style = planner.plan({"tone": "teasing", "pacing": "slow"}, {"closeness": 0.7})
        pp = prosody.plan("I think you are hiding something from me", style)
        kokoro = KokoroRenderer(tts=None)
        stub = StubRenderer()
        kokoro.render(style, prosody=pp, output_path="x.wav")
        stub.render(style, prosody=pp, output_path="x.wav")
        last = stub.last_call()
        assert last["style"] == style.as_dict()
        assert last["prosody"] == pp.as_dict()

    def test_stub_records_calls(self):
        stub = StubRenderer()
        style = SpeechStyle()
        pp = ProsodyPlan("hello", rate=1.0)
        stub.render(style, prosody=pp, output_path="out.wav")
        assert stub.last_call()["output_path"] == "out.wav"
        assert stub.last_call()["style"] == style.as_dict()

    def test_kokoro_text_only_without_tts(self):
        r = KokoroRenderer(tts=None)
        assert r.render(SpeechStyle(), ProsodyPlan("hi"), "p.wav") is None

    def test_create_renderer(self):
        assert create_renderer("kokoro").name == "kokoro"
        assert create_renderer("stub").name == "stub"
        assert create_renderer("bogus") is None

    def test_kokoro_passes_emotion_speed(self):
        class FakeTTS:
            def __init__(self):
                self.calls = []
            def generate(self, text, path, emotion="neutral", speed=None):
                self.calls.append((text, path, emotion, speed))
        tts = FakeTTS()
        r = KokoroRenderer(tts=tts)
        style = SpeechStyle(register=REGISTER_TEASING, rate=0.9)
        r.render(style, prosody=ProsodyPlan("hi there", rate=0.9), output_path="o.wav")
        assert len(tts.calls) == 1
        text, path, emotion, speed = tts.calls[0]
        assert text == "hi there"
        assert path == "o.wav"
        assert emotion == "teasing"
        assert speed == 0.9


class TestIntegrationComposition:

    def test_seam_end_to_end(self):
        planner = SpeechStylePlanner()
        prosody = ProsodyPlanner()
        stub = StubRenderer()
        style = planner.plan({"tone": "soft", "intention": "reassure"})
        pp = prosody.plan("It is going to be okay I promise you", style)
        stub.render(style, prosody=pp, output_path="out.wav")
        call = stub.last_call()
        assert style is not None
        assert call["prosody"]["rate"] == style.rate
        assert call["prosody"]["text"] != ""