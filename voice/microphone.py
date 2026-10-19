import logging
import threading

from config.voice import MICROPHONE_DEVICE

logger = logging.getLogger(__name__)


class Microphone:
    def __init__(self, sample_rate=16000, channels=1, blocksize=512, device=None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.blocksize = blocksize
        # Use explicitly provided device, then config, then None (auto-detect)
        self.device = device if device is not None else MICROPHONE_DEVICE
        self._stream = None
        self._running = False
        self._lock = threading.RLock()
        self._callbacks = []
        self._error_count = 0
        self._max_errors = 5

    def start(self, callback=None):
        import sounddevice as sd

        if callback:
            self._callbacks.append(callback)

        with self._lock:
            if self._running:
                logger.debug("[Mic] Already running — skipping duplicate start")
                return

            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.debug("[Mic] Status: %s", status)
                chunk = indata.mean(axis=1) if indata.shape[1] > 1 else indata[:, 0].copy()
                with self._lock:
                    for cb in self._callbacks:
                        try:
                            cb(chunk)
                        except Exception as e:
                            logger.warning("[Mic] Callback error: %s", e)

            # --- Diagnostics: enumerate available devices ---
            try:
                devices = sd.query_devices()
                logger.info("[Mic] Available input devices:")
                for i, dev in enumerate(devices):
                    if dev["max_input_channels"] > 0:
                        logger.info("  %d: %s (inputs=%d, sr=%.0f)", i, dev["name"], dev["max_input_channels"], dev["default_samplerate"])
                if not any(d["max_input_channels"] > 0 for d in devices):
                    logger.warning("[Mic] No input devices found!")
            except Exception as e:
                logger.error("[Mic] Device query failed: %s", e)

            # --- Resolve target device ---
            target = self.device
            if target is None:
                # Auto-select first input-capable device
                for i, dev in enumerate(sd.query_devices()):
                    if dev["max_input_channels"] > 0:
                        target = i
                        break

            if target is not None:
                try:
                    dev_info = sd.query_devices(target)
                    logger.info("[Mic] Selected device %d: %s (inputs=%d, sr=%.0f)",
                                target, dev_info["name"], dev_info["max_input_channels"], dev_info["default_samplerate"])
                except Exception as e:
                    logger.warning("[Mic] Could not query device %s: %s", target, e)
            else:
                logger.error("[Mic] No input device available — microphone will fail")

            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    blocksize=self.blocksize,
                    device=target,
                    dtype="float32",
                    callback=audio_callback,
                )
                self._stream.start()
                self._running = True
                self._error_count = 0
                logger.info("[Mic] Started (sr=%d, blocksize=%d, device=%s)", self.sample_rate, self.blocksize, target)
            except Exception as e:
                logger.error("[Mic] Start failed — device=%s, sr=%d: %s", target, self.sample_rate, e)
                self._running = False

    def stop(self):
        with self._lock:
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    logger.warning("[Mic] Stop error: %s", e)
                self._stream = None
            self._running = False
            # Callbacks are per-stream closures; the stream is closed, so any
            # stale callbacks must not survive into the next start() cycle.
            self._callbacks.clear()

    @property
    def is_running(self):
        return self._running

    def add_callback(self, callback):
        with self._lock:
            self._callbacks.append(callback)

    def remove_callback(self, callback):
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
