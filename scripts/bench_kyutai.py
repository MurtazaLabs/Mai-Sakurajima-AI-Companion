"""Phase 1 RTF benchmark for the Kyutai STT backend (one-off).

Measures wall-clock transcribe time / audio duration (RTF) for KyutaiSTT on
representative utterances (2-8 s). Gate: median RTF <= 0.7 on this machine
(CPU counted first; CUDA torch only if the CPU fails the gate).

Usage:
    mai_env/Scripts/python.exe scripts/bench_kyutai.py                  # synth speech
    mai_env/Scripts/python.exe scripts/bench_kyutai.py --audio clip.wav # real clip
"""
import argparse
import math
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np


def _synth_speech(seconds: float, rate: int = 16000) -> np.ndarray:
    """Vowel-ish formant-stack stand-in for speech — the model does full-frame
    computation regardless of content, so latency numbers stay representative."""
    n = int(seconds * rate)
    t = np.arange(n) / rate
    tone = (np.sin(2 * np.pi * 140 * t) + 0.6 * np.sin(2 * np.pi * 700 * t)
            + 0.4 * np.sin(2 * np.pi * 1220 * t) + 0.2 * np.sin(2 * np.pi * 2600 * t))
    env = 0.6 + 0.4 * np.sin(2 * np.pi * 0.8 * t)
    return (tone * env * 0.25).astype(np.float32)


def _load_wav(path: str, rate: int) -> np.ndarray:
    import soundfile as sf
    x, sr = sf.read(path, dtype="float32")
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr == rate:
        return x
    from scipy.signal import resample_poly
    g = math.gcd(sr, rate)
    return resample_poly(x, rate // g, sr // g).astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description="Kyutai STT RTF benchmark")
    parser.add_argument("--audio", help="optional wav path (resampled to STT rate)")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--lengths", type=float, nargs="+", default=[2.0, 4.0, 8.0])
    args = parser.parse_args()

    from voice.stt_kyutai import KyutaiSTT

    stt = KyutaiSTT()
    cases: list[tuple[str, np.ndarray]] = [
        (f"synth-{s:.0f}s", _synth_speech(s, stt.sample_rate)) for s in args.lengths
    ]
    if args.audio:
        cases.append((os.path.basename(args.audio), _load_wav(args.audio, stt.sample_rate)))

    t0 = time.perf_counter()
    stt.transcribe(cases[0][1])  # warmup: model load + first transcribe
    load_s = time.perf_counter() - t0

    print(f"model ready in {load_s:.1f}s (incl. warmup transcribe); device={stt._device}")
    print(f"{'case':>10} | {'audio_s':>7} | {'stt_s':>7} | {'RTF':>6} | text")
    rtfs: list[float] = []
    for label, audio in cases:
        times: list[float] = []
        text = ""
        for _ in range(args.runs):
            t0 = time.perf_counter()
            text = stt.transcribe(audio)
            times.append(time.perf_counter() - t0)
        speech = len(audio) / stt.sample_rate
        rtf = statistics.median(times) / speech
        rtfs.append(rtf)
        print(f"{label:>10} | {speech:7.2f} | {statistics.median(times):7.2f} | "
              f"{rtf:6.3f} | {text[:60]!r}")

    gate = 0.7
    verdict = "GO" if statistics.median(rtfs) <= gate else "NO-GO"
    print(f"\nmedian RTF over all cases: {statistics.median(rtfs):.3f}   gate {gate} -> {verdict}")
    s = stt.stats()
    print(f"stats: device={s['device']} calls={s['calls']} "
          f"speech={s['speech_seconds']:.1f}s stt={s['stt_seconds']:.1f}s avg_rtf={s['avg_rtf']:.3f}")
    return 0 if verdict.startswith("GO") else 2


if __name__ == "__main__":
    raise SystemExit(main())
