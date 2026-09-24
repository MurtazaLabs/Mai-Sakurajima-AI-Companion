import numpy as np


def normalize(audio):
    max_val = np.max(np.abs(audio))
    if max_val > 0:
        return audio / max_val
    return audio


def resample(audio, orig_sr, target_sr=16000):
    if orig_sr == target_sr:
        return audio
    ratio = target_sr / orig_sr
    new_len = int(len(audio) * ratio)
    return np.interp(
        np.linspace(0, len(audio) - 1, new_len),
        np.arange(len(audio)),
        audio,
    ).astype(audio.dtype)


def frames_to_seconds(frames, sample_rate=16000):
    return frames / sample_rate


def seconds_to_frames(seconds, sample_rate=16000):
    return int(seconds * sample_rate)
