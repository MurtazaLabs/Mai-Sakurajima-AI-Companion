"""Runtime voice-stack switching: local (Kyutai STT + Kokoro TTS) ↔ cloud
(ElevenLabs Scribe STT + Flash TTS).

The two stacks differ in VRAM: Kyutai holds ~2.3 GB of the T1000's 4 GB, and
that is the memory a local 8B GGUF needs. TTS was already CPU-only, so moving
TTS alone would free nothing — this switch exists mainly to move STT.

Nothing else in the pipeline changes: ``voice_manager.stt``,
``voice_manager.wake_detector.stt``, ``app.stt``, ``kernel.stt``, ``app.tts``,
``app.voice.tts`` and ``voice_renderer.tts`` are the only injection points, and
every one of them is replaced here. Missing one leaves the old model alive and
the VRAM unreleased, which is why they are all handled in one place.

The persisted choice is ``VOICE_STACK`` in ConfigManager (applied at boot by
``resolve_stack``); the switch itself works immediately.
"""
import gc
import logging

from app.config_loader import Settings

logger = logging.getLogger(__name__)

LOCAL = "local"
CLOUD = "cloud"
STACKS = (LOCAL, CLOUD)


# ==================================================
# 🏗️ STACK CONSTRUCTION (single source for boot + switch)
# ==================================================

def resolve_stack(config_manager=None) -> str:
    """The stack this process should run: persisted override, else VOICE_STACK."""
    override = None
    if config_manager is not None:
        try:
            override = config_manager.get("VOICE_STACK")
        except Exception as e:
            logger.debug("[VoiceStack] config override unavailable: %s", e)

    stack = str(override or Settings.VOICE_STACK or LOCAL).strip().lower()
    if stack not in STACKS:
        logger.warning("[VoiceStack] Unknown VOICE_STACK %r — using local", stack)
        stack = LOCAL
    if stack == CLOUD and not Settings.ELEVENLABS_API_KEY:
        logger.warning(
            "[VoiceStack] VOICE_STACK=cloud but ELEVENLABS_API_KEY is empty — using local"
        )
        stack = LOCAL
    return stack


def build_tts(stack: str):
    if stack == CLOUD:
        from voice.elevenlabs_tts import ElevenLabsTTS
        return ElevenLabsTTS()
    from voice.kokoro_tts import KokoroTTS
    return KokoroTTS()


def build_stt(stack: str):
    if stack == CLOUD:
        from voice.elevenlabs_stt import ElevenLabsSTT
        return ElevenLabsSTT()
    if Settings.STT_BACKEND == "whisper":
        from voice.stt import FasterWhisperSTT
        return FasterWhisperSTT()
    from voice.stt_kyutai import KyutaiSTT
    return KyutaiSTT()


# ==================================================
# 🔀 SWITCHER
# ==================================================

class VoiceStackSwitcher:

    def __init__(self, app):
        self.app = app

    def current(self) -> str:
        stt = getattr(self.app, "stt", None)
        return getattr(stt, "stack", LOCAL)

    def status(self) -> dict:
        app = self.app
        stt = getattr(app, "stt", None)
        tts = getattr(app, "tts", None)
        return {
            "stack": self.current(),
            "stacks": list(STACKS),
            "cloud_available": bool(Settings.ELEVENLABS_API_KEY),
            "stt": {
                "backend": type(stt).__name__ if stt is not None else None,
                "stats": stt.stats() if hasattr(stt, "stats") else {},
            },
            "tts": {
                "backend": type(tts).__name__ if tts is not None else None,
                "stats": tts.stats() if hasattr(tts, "stats") else {},
            },
            "vram_free_mb": _vram_free_mb(),
        }

    def switch(self, stack: str) -> dict:
        app = self.app
        stack = (stack or "").strip().lower()

        if stack not in STACKS:
            return {**self.status(), "error": "unknown_stack"}
        if stack == self.current():
            return {**self.status(), "unchanged": True}
        if stack == CLOUD and not Settings.ELEVENLABS_API_KEY:
            return {
                **self.status(),
                "error": "no_api_key",
                "detail": "ELEVENLABS_API_KEY is not set",
            }
        if _is_busy(app):
            # Toggling mid-turn would swap engines under a live transcription.
            return {**self.status(), "error": "busy", "detail": "Mai is speaking"}

        old_stt = getattr(app, "stt", None)
        old_tts = getattr(app, "tts", None)
        dropping_vram = (getattr(old_stt, "stack", LOCAL) == LOCAL and stack == CLOUD)
        free_before = _vram_free_mb() if dropping_vram else None

        new_stt = build_stt(stack)
        new_tts = build_tts(stack)

        app.stt = new_stt
        app.tts = new_tts

        vm = getattr(app, "voice_manager", None)
        if vm is not None:
            vm.stt = new_stt
            wake = getattr(vm, "wake_detector", None)
            if wake is not None:
                wake.stt = new_stt

        kernel = getattr(app, "kernel", None)
        if kernel is not None and hasattr(kernel, "stt"):
            kernel.stt = new_stt

        voice = getattr(app, "voice", None)
        if voice is not None:
            voice.tts = new_tts

        renderer = getattr(app, "voice_renderer", None)
        if renderer is not None and hasattr(renderer, "tts"):
            renderer.tts = new_tts

        # Drop the last local reference before collecting, or the model (and its
        # ~2.3 GB) stays alive. An in-flight transcribe holds its own reference
        # and will free on completion instead.
        if callable(getattr(old_tts, "close", None)):
            old_tts.close()
        del old_stt, old_tts

        gc.collect()
        _empty_cuda_cache()

        free_after = _vram_free_mb() if free_before is not None else None

        cm = getattr(app, "config_manager", None)
        if cm is not None:
            try:
                cm.set("VOICE_STACK", stack)
            except Exception as e:
                logger.warning("[VoiceStack] could not persist stack: %s", e)

        logger.info("[VoiceStack] switched to %s (stt=%s tts=%s)",
                    stack, type(new_stt).__name__, type(new_tts).__name__)

        out = self.status()
        if free_before is not None and free_after is not None:
            out["vram_freed_mb"] = round(free_after - free_before)
        return out


# ==================================================
# 🧰 HELPERS
# ==================================================

def _is_busy(app) -> bool:
    vm = getattr(app, "voice_manager", None)
    if vm is not None and hasattr(vm, "is_speaking") and vm.is_speaking():
        return True
    return bool(getattr(getattr(app, "voice", None), "is_speaking", False))


def _vram_free_mb():
    """Free VRAM in MiB, or None when there is no CUDA device."""
    try:
        import torch
        if not torch.cuda.is_available():
            return None
        free, _total = torch.cuda.mem_get_info()
        return round(free / (1024 * 1024))
    except Exception as e:
        logger.debug("[VoiceStack] VRAM query unavailable: %s", e)
        return None


def _empty_cuda_cache() -> None:
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception as e:
        logger.debug("[VoiceStack] empty_cache unavailable: %s", e)
