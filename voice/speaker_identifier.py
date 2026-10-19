import logging

logger = logging.getLogger(__name__)


class SpeakerIdentifier:
    def __init__(self, speaker_manager=None, sample_rate=16000):
        self.speaker_manager = speaker_manager
        self.sample_rate = sample_rate

    def identify(self, audio):
        if self.speaker_manager is None or not self.speaker_manager.ready:
            return "", 0.0
        try:
            profile, confidence = self.speaker_manager.identify_raw(
                audio, sample_rate=self.sample_rate
            )
            if profile and confidence >= 0.3:
                return profile.name, round(confidence, 3)
            return "", 0.0
        except Exception as e:
            logger.warning("[SpeakerIdentifier] Error: %s", e)
            return "", 0.0

    def register(self, name, audio):
        if self.speaker_manager is None:
            return None
        try:
            profile = self.speaker_manager.register_raw(
                name, audio, sample_rate=self.sample_rate
            )
            return profile
        except Exception as e:
            logger.warning("[SpeakerIdentifier] Register error: %s", e)
            return None
