"""Recorder chunk sanitizer (Oct 25, live observation): hardware/driver glitches
and unstable DSP stages (adaptive AEC weights, FFT filter) emitted out-of-range
float chunks (observed peaks 30.4 and 1.17e11); the garbage peak then crushed
normalization (tone/30 ≈ silence → VAD gate rejected real speech). The recorder
clamps at its trust boundary so every upstream producer is covered."""
import logging

import numpy as np

from voice.recorder import Recorder


class _StubVAD:
    """Deterministic VAD: verdicts consumed in feed order."""

    def __init__(self, verdicts):
        self._verdicts = list(verdicts)

    def is_speech(self, chunk):
        return self._verdicts.pop(0) if self._verdicts else False


def _feed(recorder, pairs):
    """Feed (chunk, is_speech) pairs; return finalized utterances."""
    received = []
    recorder.set_callback(lambda a: received.append(a) if a is not None else None)
    for chunk, speech in pairs:
        recorder._vad = _StubVAD([speech])
        recorder.add_chunk(chunk)
    return received


def _tone(seconds=0.1, amp=0.4, sr=16000):
    n = int(seconds * sr)
    return (np.sin(2 * np.pi * 440 * np.arange(n) / sr) * amp).astype(np.float32)


def test_corrupt_peak_clamped_and_tone_preserved(caplog):
    r = Recorder(silence_timeout=0.0, min_recording=0.0,
                 speech_onset_frames=1, vad=None)
    corrupt = _tone().copy()
    corrupt[0] = 40.0
    with caplog.at_level(logging.WARNING, logger="voice.recorder"):
        got = _feed(r, [(corrupt, True), (_tone(), False), (_tone(), False)])
    assert any("Corrupt chunk clamped" in rec.message for rec in caplog.records)
    assert got, "utterance finalized"
    result = got[0]
    assert float(result.max()) <= 1.0
    # spike clamped to 1.0 pre-normalize, so the real tone survives at its
    # recorded amplitude instead of being crushed to ~0.01 by a /40 divisor
    assert float(np.mean(result > 0.3)) > 0.1


def test_clean_chunk_never_clamped(caplog):
    r = Recorder(silence_timeout=0.0, min_recording=0.0,
                 speech_onset_frames=1, vad=None)
    tone = _tone()
    with caplog.at_level(logging.WARNING, logger="voice.recorder"):
        got = _feed(r, [(tone, True), (tone, False), (tone, False)])
    assert not any("Corrupt" in rec.message for rec in caplog.records)
    assert got, "clean utterance finalized"
    assert abs(float(got[0].max()) - 1.0) < 1e-6  # honest peak-normalize result


def test_nan_chunk_sanitized_and_utterance_survives(caplog):
    # Live bug (Oct 25, 12:10:49): a NaN chunk passed every check (NaN > 1.0 is
    # False), reached the built utterance as max=nan, and the VAD gate
    # rejected real speech. Non-finite samples must be zeroed at entry.
    r = Recorder(silence_timeout=0.0, min_recording=0.0,
                 speech_onset_frames=1, vad=None)
    bad = _tone().copy()
    bad[0] = np.nan
    with caplog.at_level(logging.WARNING, logger="voice.recorder"):
        got = _feed(r, [(bad, True), (_tone(), False), (_tone(), False)])
    assert any("Non-finite chunk sanitized" in rec.message for rec in caplog.records)
    assert got, "utterance finalized despite nan chunk"
    assert np.all(np.isfinite(got[0]))
    # the tone itself survives at audible amplitude (peak-normalized)
    assert float(np.mean(got[0] > 0.3)) > 0.1


# ── recording boundaries (live log 2026-10-27) ───────────────────────────
#
# The onset frames used to be discarded: "hey mai" arrived at STT as a
# mid-word fragment and decoded to "" (a 2-4s transcription burned per
# attempt). The pre-roll must therefore carry the audio from *before* onset.

def test_pre_roll_keeps_audio_from_before_onset():
    r = Recorder(silence_timeout=0.0, min_recording=0.0, speech_onset_frames=1,
                 vad=None, pre_roll=0.3, trailing_keep=0.0)
    chunk = _tone()  # 0.1 s
    quiet = [_tone(amp=0.01) for _ in range(4)]
    got = _feed(r, [(c, False) for c in quiet] + [(chunk, True)]
                + [(chunk, False), (chunk, False)])
    assert got, "utterance finalized"
    # 3 pre-roll chunks (0.3 s incl. the onset chunk) + 2 silence chunks,
    # instead of the 3 chunks that arrive at/after onset
    assert len(got[0]) == 5 * len(chunk)


def test_zero_pre_roll_keeps_onset_chunk():
    r = Recorder(silence_timeout=0.0, min_recording=0.0, speech_onset_frames=1,
                 vad=None, pre_roll=0.0, trailing_keep=0.0)
    chunk = _tone()
    got = _feed(r, [(chunk, True), (chunk, False), (chunk, False)])
    assert got and len(got[0]) == 3 * len(chunk)


def test_trailing_silence_trimmed_to_keep_window():
    # silence_timeout is now long enough to survive mid-sentence pauses; the
    # extra tail must be trimmed or every clip pays extra STT decode time.
    r = Recorder(silence_timeout=10.0, min_recording=0.0, speech_onset_frames=1,
                 vad=None, pre_roll=0.0, trailing_keep=0.2)
    chunk = _tone()  # 0.1 s of speech
    received = []
    r.set_callback(received.append)
    for _ in range(5):                       # 0.5 s speech
        r._vad = _StubVAD([True])
        r.add_chunk(chunk)
    for _ in range(10):                      # 1.0 s silence, no timeout finalize
        r._vad = _StubVAD([False])
        r.add_chunk(np.zeros_like(chunk))
    r._finalize(reason="test")
    assert received, "utterance finalized"
    # 0.5 s speech + 0.2 s keep, not the full 1.5 s recorded
    assert 0.65 * 16000 <= len(received[0]) <= 0.72 * 16000
