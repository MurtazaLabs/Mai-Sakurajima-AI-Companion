"""Voice event topics + payload builders.

Topic constants are the semantic ``data.voice.*`` names declared in
``core/event_specs.py`` (single source of truth). Re-exported here so
existing ``from voice.events import VOICE_STARTED`` imports keep working.
"""
from core.event_specs import (
    STATE_VOICE_IDLE,
    STATE_VOICE_LISTENING,
    STATE_VOICE_SPEAKING,
    STATE_VOICE_WAKE,
    VOICE_ERROR,
    VOICE_LISTENING_STARTED,
    VOICE_RECORDING_COMPLETED,
    VOICE_RETURNED,
    VOICE_SPEAKER_IDENTIFIED,
    VOICE_STARTED,
    VOICE_STATE_CHANGED,
    VOICE_STOPPED,
    VOICE_TRANSCRIPTION_COMPLETED,
    VOICE_WAKE_DETECTED,
    # Fired once when VoiceManager detects a wake word during idle listening.
    # Published for observability — kernel polls WakeWord (which reads
    # VoiceManager._wake_event) rather than subscribing to this event.
    VOICE_WAKE_FOUND,
)
from core.mai_message import publish_event

__all__ = [
    "STATE_VOICE_IDLE",
    "STATE_VOICE_LISTENING",
    "STATE_VOICE_SPEAKING",
    "STATE_VOICE_WAKE",
    "VOICE_ERROR",
    "VOICE_LISTENING_STARTED",
    "VOICE_RECORDING_COMPLETED",
    "VOICE_RETURNED",
    "VOICE_SPEAKER_IDENTIFIED",
    "VOICE_STARTED",
    "VOICE_STATE_CHANGED",
    "VOICE_STOPPED",
    "VOICE_TRANSCRIPTION_COMPLETED",
    "VOICE_WAKE_DETECTED",
    "VOICE_WAKE_FOUND",
]


def publish_voice(bus, topic, payload=None):
    """Fabric publish of a voice event (envelope + ``source='voice'``)."""
    publish_event(bus, topic, payload, source="voice")


def publish_voice_state(bus, topic, payload=None):
    """Publish a ``state.voice.*`` UI projection (Phase 5 — Reactive UI)."""
    publish_event(bus, topic, payload, source="voice")


def voice_state_listening_data(wake_required):
    return {"wake_required": wake_required}


def voice_state_speaking_data(text, speaker):
    return {"text": text, "speaker": speaker}


def voice_state_idle_data():
    return {}


def voice_state_wake_data(wake_word, text):
    return {"wake_word": wake_word, "text": text}


def voice_started_data():
    return {"state": "started"}


def voice_stopped_data():
    return {"state": "stopped"}


def voice_state_changed_data(old_state, new_state):
    return {"old_state": old_state, "new_state": new_state}


def voice_listening_started_data(wake_required):
    return {"wake_required": wake_required}


def voice_recording_completed_data(audio_length, duration):
    return {"audio_length": audio_length, "duration": duration}


def voice_speaker_identified_data(speaker, confidence):
    return {"speaker": speaker, "confidence": confidence}


def voice_transcription_completed_data(text, audio_length, duration):
    return {"text": text, "text_length": len(text), "audio_length": audio_length, "duration": duration}


def voice_wake_detected_data(wake_word, text):
    return {"wake_word": wake_word, "text": text}


def voice_wake_found_data(text, audio_length):
    """Published when VoiceManager detects wake from its own audio pipeline."""
    return {"text": text, "audio_length": audio_length}


def voice_returned_data(text, speaker, wake_detected, duration, extra=None):
    data = {"text": text, "speaker": speaker, "wake_detected": wake_detected, "duration": duration}
    if extra:
        data["extra"] = extra
    return data


def voice_error_data(error_type, message):
    return {"type": error_type, "message": str(message)}