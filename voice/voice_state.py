from enum import Enum


class VoiceState(str, Enum):
    OFF = "off"
    IDLE = "idle"
    LISTENING = "listening"
    LISTENING_FOR_WAKE = "listening_for_wake"
    WAKE_DETECTED = "wake_detected"
    SPEECH = "speech"
    RECORDING = "recording"
    PROCESSING = "processing"
    TRANSCRIBING = "transcribing"
    RETURN = "return"
