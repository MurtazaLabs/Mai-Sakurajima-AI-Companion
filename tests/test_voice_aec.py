"""AEC wiring — the echo canceller must receive the real playback reference.

Regression this guards: `FullAEC.add_playback()` had no production caller, so
the AEC was a pass-through; and with the old 0.3 double-talk threshold the
filter never adapted even when fed (probe: 1.2 dB, all clipping).
"""
import numpy as np
import pytest

from voice.full_aec import FullAEC

SR = 16000
BLOCK = 512


def _room(n=SR * 4, user_from=None, seed=7):
    """Two-path synthetic room: far-end speech, 0.35/0.15 echo, optional user."""
    rng = np.random.default_rng(seed)
    t = np.arange(n) / SR
    ref = sum(np.sin(2 * np.pi * f * t) for f in (180, 360, 540, 720)) / 4.0
    ref = (ref * (0.5 + 0.5 * np.sin(2 * np.pi * 2.5 * t))).astype(np.float32) * 0.6
    echo = np.zeros_like(ref)
    for delay, gain in ((40, 0.35), (300, 0.15)):
        echo[delay:] += gain * ref[:-delay]
    near = np.zeros_like(ref)
    if user_from is not None:
        near[user_from:] = (rng.standard_normal(n - user_from) * 0.08).astype(np.float32)
    return ref, near, echo + near


def _run_aec(aec, ref, mic):
    out = np.zeros_like(mic)
    for start in range(0, len(mic), BLOCK):
        aec.add_playback(ref[start:start + BLOCK])
        out[start:start + BLOCK] = aec.process(mic[start:start + BLOCK])
    return out


def _erle(before, after, sl):
    return 10 * np.log10(np.mean(before[sl] ** 2) / max(np.mean(after[sl] ** 2), 1e-20))


class TestFullAECCancels:

    def test_real_time_reference_cancels_echo(self):
        ref, _, mic = _room()
        aec = FullAEC(sample_rate=SR, filter_length=2048, adaptation_rate=0.01,
                      max_echo_delay=0.5, double_talk_threshold=1.0)
        out = _run_aec(aec, ref, mic)
        assert _erle(mic, out, slice(SR, SR * 4)) > 10.0
        assert np.all(np.isfinite(out))

    def test_configured_settings_cancel_echo(self):
        """The shipped config must actually adapt, not latch into double talk."""
        import config.voice as cfg

        ref, _, mic = _room()
        aec = FullAEC(
            sample_rate=SR,
            filter_length=cfg.FULL_AEC_FILTER_LENGTH,
            adaptation_rate=cfg.FULL_AEC_ADAPTATION_RATE,
            max_echo_delay=cfg.FULL_AEC_MAX_DELAY,
            double_talk_threshold=cfg.FULL_AEC_DOUBLE_TALK_THRESHOLD,
            residual_tail_length=cfg.FULL_AEC_RESIDUAL_TAIL,
            hangover_frames=cfg.FULL_AEC_HANGOVER,
        )
        out = _run_aec(aec, ref, mic)
        assert _erle(mic, out, slice(SR, SR * 4)) > 10.0
        assert not aec.is_double_talk()

    def test_user_speech_survives_cancellation(self):
        ref, near, mic = _room(user_from=SR * 2)
        aec = FullAEC(sample_rate=SR, double_talk_threshold=1.0)
        out = _run_aec(aec, ref, mic)
        # user speech must not be attenuated by more than 2 dB
        kept = _erle(near[SR * 2:], out[SR * 2:], slice(0, len(near) - SR * 2))
        assert kept > -2.0


class TestPlaybackLifecycle:

    def test_end_playback_restores_pass_through(self):
        aec = FullAEC(sample_rate=SR)
        aec.add_playback(np.random.randn(BLOCK).astype(np.float32) * 0.1)
        assert aec._has_playback is True
        aec.end_playback()
        assert aec._has_playback is False
        mic = np.random.randn(BLOCK).astype(np.float32)
        assert np.array_equal(aec.process(mic), mic)

    def test_end_playback_is_safe_on_fresh_instance(self):
        FullAEC(sample_rate=SR).end_playback()


class _FakeStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.written = []
        self.aborted = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def write(self, block):
        self.written.append(np.array(block, copy=True))

    def abort(self):
        self.aborted = True


class _FakeSD:
    def __init__(self):
        self.streams = []
        self.played = []
        self.stopped = 0

    def OutputStream(self, **kwargs):
        stream = _FakeStream(**kwargs)
        self.streams.append(stream)
        return stream

    def play(self, data, sr, device=None, blocking=True):
        self.played.append((len(data), sr, device))

    def stop(self):
        self.stopped += 1


@pytest.fixture()
def fake_sd(monkeypatch):
    import voice.stream_player as sp

    fake = _FakeSD()
    monkeypatch.setattr(sp, "sd", fake)
    return fake


class TestStreamPlayerTap:

    def test_tap_receives_resampled_played_audio(self, fake_sd):
        from voice.stream_player import StreamPlayer

        blocks, ended = [], []
        player = StreamPlayer()
        player.set_reference_tap(blocks.append, on_end=lambda: ended.append(True),
                                 sample_rate=SR)
        data = (np.random.randn(24000).astype(np.float32) * 0.1)
        player._play(data, 24000)

        fed = np.concatenate(blocks)
        assert len(fed) == pytest.approx(len(data) * SR // 24000, abs=8)
        from scipy.signal import resample_poly

        assert np.allclose(fed, resample_poly(data, 2, 3), atol=1e-6)
        assert ended == [True]
        played = np.concatenate(fake_sd.streams[0].written)
        assert len(played) == len(data)                    # playback keeps its rate
        assert fake_sd.played == []                        # no sd.play when tapping

    def test_no_tap_keeps_sd_play(self, fake_sd):
        from voice.stream_player import StreamPlayer

        player = StreamPlayer()
        player._play(np.zeros(1600, dtype=np.float32), SR)
        assert fake_sd.played == [(1600, SR, None)]
        assert fake_sd.streams == []

    def test_stop_aborts_active_stream(self, fake_sd):
        from voice.stream_player import StreamPlayer

        player = StreamPlayer()
        stream = fake_sd.OutputStream(samplerate=SR)
        player._playback_stream = stream
        player.stop()
        assert stream.aborted is True

    def test_device_write_failure_ends_clip_cleanly(self, fake_sd):
        """A device error must not escape the player, and the AEC reference must
        still be flushed (otherwise it adapts against audio nobody heard)."""
        from voice.stream_player import StreamPlayer

        class _BrokenStream(_FakeStream):
            def write(self, block):
                raise RuntimeError("PortAudioError: device lost")

        ended = []
        player = StreamPlayer()
        player.set_reference_tap(lambda b: None, on_end=lambda: ended.append(True),
                                 sample_rate=SR)
        import voice.stream_player as sp

        sp.sd.OutputStream = lambda **kw: _BrokenStream(**kw)
        player._play(np.zeros(4096, dtype=np.float32), SR)
        assert ended == [True]


class TestWiring:

    def test_attach_playback_tap_wires_bound_methods(self):
        from voice.voice_manager import VoiceManager

        aec = FullAEC(sample_rate=SR)
        vm = VoiceManager(sample_rate=SR, full_aec=aec)

        class _Player:
            def __init__(self):
                self.args = None

            def set_reference_tap(self, tap, on_end=None, sample_rate=16000):
                self.args = (tap, on_end, sample_rate)

        player = _Player()
        assert vm.attach_playback_tap(player) is True
        tap, on_end, rate = player.args
        assert tap == vm.send_playback_audio
        assert on_end == vm.end_playback_audio
        assert rate == SR

    def test_attach_playback_tap_without_aec_is_noop(self):
        from voice.voice_manager import VoiceManager

        vm = VoiceManager(sample_rate=SR)
        assert vm.attach_playback_tap(object()) is False

    def test_tap_reaches_aec_through_voice_manager(self):
        from voice.voice_manager import VoiceManager

        aec = FullAEC(sample_rate=SR)
        vm = VoiceManager(sample_rate=SR, full_aec=aec)
        vm.send_playback_audio(np.ones(256, dtype=np.float32) * 0.1)
        assert aec._has_playback is True
        vm.end_playback_audio()
        assert aec._has_playback is False
