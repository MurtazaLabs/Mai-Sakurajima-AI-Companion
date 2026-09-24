# Mai_ai/voice/renderer.py
# M4 · VoiceRenderer seam — the boundary between the character speech
# pipeline (SpeechStyle + ProsodyPlan) and a concrete TTS engine.
# KokoroRenderer is the default implementation; additional engines
# (Fish Chat, CosyVoice) drop in later behind the same interface.

import logging

logger = logging.getLogger("Mai.Renderer")


class VoiceRenderer:

    name = "base"

    def __init__(self, tts=None):
        self.tts = tts

    def render(self, style, prosody=None, output_path=None):
        """Render prosody text to audio at output_path. Returns the audio
        path on success (or the path for dry-run stubs), else None."""
        raise NotImplementedError

    def describe(self):
        return {"name": self.name}


class KokoroRenderer(VoiceRenderer):

    name = "kokoro"

    def render(self, style, prosody=None, output_path=None):
        text = (prosody.text if prosody else "").strip()
        if not text or self.tts is None:
            if text:
                logger.info("Mai (text-only): %s", text)
            return None
        if hasattr(self.tts, "generate"):
            import inspect
            kwargs = {}
            sig = inspect.signature(self.tts.generate)
            if "emotion" in sig.parameters:
                kwargs["emotion"] = style.register if style else "neutral"
            if "speed" in sig.parameters and style is not None:
                kwargs["speed"] = style.rate
            try:
                self.tts.generate(text, output_path, **kwargs)
                return output_path
            except Exception as e:
                logger.exception("[RenderError] %s", e)
        return None


class StubRenderer(VoiceRenderer):

    """Test / dry-run implementation — records every render call so the
    seam can be asserted identically across renderer impls."""

    name = "stub"

    def __init__(self, tts=None):
        super().__init__(tts)
        self.calls = []

    def render(self, style, prosody=None, output_path=None):
        self.calls.append(
            {
                "text": prosody.text if prosody else "",
                "style": style.as_dict() if style else None,
                "prosody": prosody.as_dict() if prosody else None,
                "output_path": output_path,
            }
        )
        return output_path

    def last_call(self):
        return self.calls[-1] if self.calls else None


def create_renderer(name, tts=None):
    if name == "kokoro":
        return KokoroRenderer(tts=tts)
    if name == "stub":
        return StubRenderer(tts=tts)
    return None