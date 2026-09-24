from dataclasses import dataclass, field


@dataclass
class VoiceConfig:
    sample_rate: int = 16000
    blocksize: int = 512
    vad_threshold: float = 0.5
    silence_timeout: float = 1.5
    min_recording: float = 0.5
    max_recording: float = 30.0
    interrupt_energy_threshold: float = 0.015
