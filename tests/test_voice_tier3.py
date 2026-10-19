import numpy as np

from voice.full_aec import FullAEC
from voice.noise_filter import NoiseFilter
from voice.utterance_segmenter import UtteranceSegmenter


class TestNoiseFilter:
    def test_init_defaults(self):
        nf = NoiseFilter()
        assert nf.sample_rate == 16000
        assert nf.low_cut == 80.0
        assert nf.high_cut == 7600.0
        assert nf.reduction_db == 6.0

    def test_filter_passthrough_empty(self):
        nf = NoiseFilter()
        result = nf.filter(np.array([], dtype=np.float32))
        assert len(result) == 0

    def test_filter_short_audio(self):
        nf = NoiseFilter()
        audio = np.array([0.1, -0.1, 0.2], dtype=np.float32)
        result = nf.filter(audio)
        assert len(result) == 3

    def test_filter_does_not_crash(self):
        nf = NoiseFilter()
        audio = np.random.randn(16000).astype(np.float32) * 0.1
        result = nf.filter(audio)
        assert len(result) == 16000
        assert not np.any(np.isnan(result))

    def test_filter_with_noise_profile(self):
        nf = NoiseFilter()
        noise = np.random.randn(16000).astype(np.float32) * 0.01
        nf.learn_noise(noise)
        audio = np.random.randn(16000).astype(np.float32) * 0.1
        result = nf.filter(audio)
        assert len(result) == 16000

    def test_bandpass_removes_dc(self):
        nf = NoiseFilter()
        audio = np.ones(1600, dtype=np.float32)
        result = nf.filter(audio)
        assert np.abs(np.mean(result)) < 0.1

    def test_learn_noise_failure_does_not_raise(self):
        nf = NoiseFilter()
        result = nf.learn_noise(np.array([], dtype=np.float32))
        assert result is False

    def test_filter_with_bad_params_returns_original(self):
        nf = NoiseFilter(low_cut=0, high_cut=0)
        audio = np.random.randn(160).astype(np.float32)
        result = nf.filter(audio)
        assert len(result) == 160


class TestFullAEC:
    def test_init_defaults(self):
        aec = FullAEC()
        assert aec.sample_rate == 16000
        assert aec.filter_length == 2048
        assert aec.adaptation_rate == 0.01

    def test_process_empty(self):
        aec = FullAEC()
        result = aec.process(np.array([], dtype=np.float32))
        assert len(result) == 0

    def test_process_without_playback_returns_original(self):
        aec = FullAEC()
        audio = np.random.randn(1600).astype(np.float32) * 0.1
        result = aec.process(audio)
        assert len(result) == 1600

    def test_add_playback_empty(self):
        aec = FullAEC()
        aec.add_playback(np.array([], dtype=np.float32))

    def test_subtracts_echo(self):
        aec = FullAEC(filter_length=128, adaptation_rate=0.1)
        playback = np.random.randn(1000).astype(np.float32) * 0.1
        aec.add_playback(playback)
        mic = playback[-128:].copy() * 0.5
        mic_power = np.mean(mic ** 2)
        result = aec.process(mic)
        result_power = np.mean(result ** 2)
        assert result_power < mic_power

    def test_does_not_increase_noise(self):
        aec = FullAEC(filter_length=64, adaptation_rate=0.01)
        aec.add_playback(np.random.randn(500).astype(np.float32) * 0.1)
        mic = np.random.randn(200).astype(np.float32) * 0.001
        mic_power = np.mean(mic ** 2)
        result = aec.process(mic)
        result_power = np.mean(result ** 2)
        assert result_power < mic_power * 10

    def test_circular_buffer_wrapping(self):
        aec = FullAEC(filter_length=128, adaptation_rate=0.01)
        playback = np.random.randn(2000).astype(np.float32) * 0.1
        aec.add_playback(playback)
        aec._playback_write = len(aec._playback_buffer) - 100
        playback2 = np.random.randn(200).astype(np.float32) * 0.1
        aec.add_playback(playback2)

    def test_process_large_audio(self):
        aec = FullAEC(filter_length=128)
        audio = np.random.randn(32000).astype(np.float32) * 0.01
        result = aec.process(audio)
        assert len(result) == 32000

    def test_process_single_sample(self):
        aec = FullAEC()
        audio = np.array([0.5], dtype=np.float32)
        result = aec.process(audio)
        assert len(result) == 1

    def test_is_double_talk(self):
        aec = FullAEC()
        assert not aec.is_double_talk()

    def test_reset(self):
        aec = FullAEC()
        aec.add_playback(np.random.randn(500).astype(np.float32) * 0.1)
        aec.process(np.random.randn(200).astype(np.float32) * 0.01)
        aec.reset()
        assert not aec.is_double_talk()
        assert aec._near_end_power == 0.0
        assert aec._far_end_power == 0.0

    def test_stats(self):
        aec = FullAEC()
        stats = aec.stats()
        assert "filter_length" in stats
        assert "double_talk" in stats
        assert "near_end_power" in stats


class TestUtteranceSegmenter:
    def test_init_defaults(self):
        us = UtteranceSegmenter()
        assert us.sample_rate == 16000
        assert us.min_silence_frames == int(0.6 * 16000)
        assert us.min_utterance_frames == int(0.3 * 16000)

    def test_segment_empty(self):
        us = UtteranceSegmenter()
        assert us.segment(np.array([], dtype=np.float32)) == []

    def test_segment_single_utterance(self):
        us = UtteranceSegmenter(min_utterance_duration=0.1)
        audio = np.ones(3200, dtype=np.float32) * 0.5
        result = us.segment(audio)
        assert len(result) == 1
        assert len(result[0]) > 0

    def test_segment_silence_only_returns_empty(self):
        us = UtteranceSegmenter(min_utterance_duration=0.1)
        audio = np.zeros(3200, dtype=np.float32)
        result = us.segment(audio)
        assert len(result) == 0

    def test_segment_two_utterances(self):
        us = UtteranceSegmenter(min_utterance_duration=0.05, min_silence_duration=0.05)
        speech = np.ones(800, dtype=np.float32) * 0.5
        silence = np.zeros(1600, dtype=np.float32)
        audio = np.concatenate([speech, silence, speech])
        result = us.segment(audio)
        assert len(result) == 2

    def test_segment_preserves_content(self):
        us = UtteranceSegmenter(min_utterance_duration=0.05, min_silence_duration=0.05)
        speech = np.ones(800, dtype=np.float32) * 0.5
        silence = np.zeros(1600, dtype=np.float32)
        audio = np.concatenate([speech, silence, speech])
        result = us.segment(audio)
        assert len(result) == 2
        assert np.all(result[0] == speech)

    def test_split_long_utterance(self):
        us = UtteranceSegmenter(
            min_utterance_duration=0.05,
            max_utterance_duration=0.1,
        )
        audio = np.random.randn(4800).astype(np.float32) * 0.1
        result = us.segment(audio)
        assert len(result) > 0
        for seg in result:
            assert len(seg) <= us.max_utterance_frames

    def test_segment_very_short_audio_returns_empty(self):
        us = UtteranceSegmenter(min_utterance_duration=10.0)
        audio = np.random.randn(100).astype(np.float32) * 0.1
        result = us.segment(audio)
        assert len(result) == 0
