import time
from dataclasses import dataclass, field


@dataclass
class VoiceEvent:
    text: str = ""
    speaker: str = ""
    speaker_confidence: float = 0.0
    wake_detected: bool = False
    audio_length: float = 0.0
    confidence: float = 0.0
    language: str = "en"
    timestamp: float = field(default_factory=time.time)
    duration: float = 0.0
    background_noise: float = 0.0
    emotion: dict | None = None
