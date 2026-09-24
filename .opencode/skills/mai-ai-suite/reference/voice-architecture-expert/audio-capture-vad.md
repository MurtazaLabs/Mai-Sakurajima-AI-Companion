# Audio Capture & VAD

## Audio Capture

- Library: sounddevice
- Format: float32, mono, 16kHz
- Buffer: 512 samples (32ms at 16kHz)
- Device: user-configurable, auto-detect default
- Sample rate conversion: scipy.signal.resample if needed
- Threading: dedicated capture thread, never blocks

```python
async def capture_loop(device_id: int, callback: Callable[[np.ndarray], None]):
    with sd.InputStream(device=device_id, samplerate=16000, channels=1,
                        dtype='float32', blocksize=512, callback=callback):
        while running:
            await asyncio.sleep(0.1)  # yield control
```

## Voice Activity Detection

- Library: Silero VAD (ONNX runtime)
- Model: silero_vad.onnx (~2MB)
- Window: 32ms frames, 10ms shift
- Threshold: 0.5 (configurable 0.3-0.7)
- Pre-speech padding: 300ms
- Post-speech silence: 500ms

```python
class SileroVAD:
    def __init__(self, threshold=0.5):
        self.model = silero_vad.load_model()
        self.triggered = False
        self.speech_frames = 0
        self.silent_frames = 0
    
    async def process(self, chunk: np.ndarray) -> VADEvent:
        speech_prob = self.model.predict(chunk)
        if speech_prob > self.threshold and not self.triggered:
            self.triggered = True
            return VADEvent.SPEECH_START
        elif speech_prob < self.threshold and self.triggered:
            self.silent_frames += 1
            if self.silent_frames > 50:  # 500ms silence
                self.triggered = False
                self.silent_frames = 0
                return VADEvent.SPEECH_END
        return VADEvent.SILENCE
```

## Noise Suppression

- Library: DeepFilterNet (lightweight) or RNNoise
- Placement: Before VAD (reduces false triggers)
- CPU impact: <5% on modern CPU
- Fallback: spectral subtraction via scipy