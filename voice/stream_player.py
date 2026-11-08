# Mai_ai/voice/stream_player.py
import logging
import os
import queue
import threading
import time

try:
    import sounddevice as sd
except ImportError:
    sd = None
import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)


def _resample_to(data, sr, target_sr):
    """Resample mono audio for the AEC reference (only the reference needs it;
    playback always uses the file's own rate)."""
    data = np.asarray(data, dtype=np.float32)
    if len(data) == 0 or int(sr) == int(target_sr):
        return data
    from fractions import Fraction

    from scipy.signal import resample_poly

    ratio = Fraction(int(target_sr), int(sr)).limit_denominator(200)
    return resample_poly(data, ratio.numerator, ratio.denominator).astype(np.float32)


class StreamPlayer:

    def __init__(
        self,
        volume=1.0,
        output_device=None,
        speed=1.0,
    ):

        self.audio_queue = queue.Queue()

        self.stop_flag = threading.Event()

        self.pause_flag = threading.Event()

        self.thread = None

        self.volume = volume

        self.speed = max(0.5, min(2.0, speed))

        self.output_device = output_device

        self.current_audio = None

        self.state = "idle"

        self._lock = threading.RLock()

        # AEC far-end reference: receives exactly the audio sent to the DAC,
        # block by block, so echo cancellation has a sample-aligned reference.
        self.reference_tap = None
        self.reference_end = None
        self.reference_sample_rate = 16000
        self._playback_stream = None

    # ▶️ START PLAYER
    def play_async(self):

        # prevent duplicate threads
        if self.thread and self.thread.is_alive():
            return

        # drain any stale items from previous session
        self.audio_queue.queue.clear()

        self.stop_flag.clear()

        self.thread = threading.Thread(
            target=self._worker,
            daemon=True
        )

        self.thread.start()

        logger.info("[StreamPlayer] Started")

    # 🎧 AUDIO WORKER
    def _worker(self):

        if sd is None:
            with self._lock:
                self.state = "unavailable"
            logger.warning("StreamPlayer unavailable: sounddevice is not installed")
            return

        while not self.stop_flag.is_set():

            try:

                # paused state
                if self.pause_flag.is_set():

                    time.sleep(0.1)
                    continue

                with self._lock:
                    self.state = "idle"

                path = self.audio_queue.get(
                    timeout=1
                )

                if not path:
                    continue

                if not os.path.exists(path):
                    logger.warning("Missing file: %s", path)
                    continue

                with self._lock:
                    self.current_audio = path
                    self.state = "playing"

                # load audio
                data, sr = sf.read(path)

                # mono fix
                if len(data.shape) > 1:
                    data = np.mean(data, axis=1)

                # normalize safely
                peak = np.max(np.abs(data))

                if peak > 0:
                    data = data / peak

                # apply volume
                data = data * self.volume

                # apply speed (resample)
                if abs(self.speed - 1.0) > 0.01:
                    new_len = int(len(data) / self.speed)
                    data = np.interp(
                        np.linspace(0, len(data) - 1, new_len),
                        np.arange(len(data)),
                        data,
                    ).astype(data.dtype)
                    sr = int(sr / self.speed)

                logger.info("Playing: %s", path)

                self._play(data, sr)

                with self._lock:
                    self.current_audio = None

                try:
                    os.remove(path)
                except Exception as e:
                    logger.warning("Temp file cleanup error: %s", e)

            except queue.Empty:

                continue

            except Exception as e:
                logger.exception("StreamPlayer error: %s", e)
                time.sleep(0.5)

    # 🎧 PLAY (with optional AEC reference tap)
    def _play(self, data, sr):

        if self.reference_tap is None:
            if self.output_device is not None:
                sd.play(data, sr, device=self.output_device, blocking=True)
            else:
                sd.play(data, sr, blocking=True)
            return

        # Stream the clip ourselves instead of sd.play(): the block that goes to
        # the DAC is then exactly the block fed to the echo canceller, with no
        # drift and no latency guesswork. stream.write() blocks, which paces the
        # loop in real time.
        tap_data = _resample_to(data, sr, self.reference_sample_rate)
        block = 512
        total = len(data)
        pos = 0
        tap_pos = 0
        try:
            with sd.OutputStream(
                samplerate=sr,
                channels=1,
                dtype="float32",
                device=self.output_device,
            ) as stream:
                self._playback_stream = stream
                while pos < total and not self.stop_flag.is_set():
                    n = min(block, total - pos)
                    try:
                        stream.write(
                            np.ascontiguousarray(data[pos:pos + n], dtype=np.float32)
                        )
                    except Exception as e:
                        # abort() from pause()/stop() surfaces here as a PortAudio
                        # error; a real device failure must still be visible.
                        if not self.stop_flag.is_set():
                            logger.warning("[StreamPlayer] write failed: %s", e)
                        break
                    pos += n
                    tap_end = int(pos * len(tap_data) / total) if total else 0
                    if tap_end > tap_pos:
                        self.reference_tap(tap_data[tap_pos:tap_end])
                        tap_pos = tap_end
        finally:
            self._playback_stream = None
            # Leaving the context manager drains queued audio (Pa_StopStream).
            if self.reference_end is not None:
                try:
                    self.reference_end()
                except Exception as e:
                    logger.warning("AEC reference end error: %s", e)

    def _abort_playback_stream(self):
        stream = self._playback_stream
        if stream is not None:
            try:
                stream.abort()
            except Exception as e:
                logger.debug("[StreamPlayer] abort: %s", e)

    # 🎧 SET AEC REFERENCE TAP
    def set_reference_tap(self, tap, on_end=None, sample_rate=16000):
        """Route played audio into an echo-cancellation reference.

        tap(block) receives float32 mono blocks at `sample_rate`; on_end() fires
        once the clip (or a stopped clip) finishes playing.
        """
        self.reference_tap = tap
        self.reference_end = on_end
        self.reference_sample_rate = int(sample_rate or 16000)

    # ➕ ENQUEUE AUDIO
    def enqueue(
        self,
        audio_path
    ):

        if not audio_path:
            return

        self.audio_queue.put(audio_path)

    # ⏸️ PAUSE
    def pause(self):

        self.pause_flag.set()

        self._abort_playback_stream()

        if sd is not None:
            sd.stop()

        with self._lock:
            self.state = "paused"

    # ▶️ RESUME
    def resume(self):

        self.pause_flag.clear()

        with self._lock:
            self.state = "playing"

    # ⛔ STOP EVERYTHING
    def stop(self):

        self.stop_flag.set()

        self.pause_flag.clear()

        self._abort_playback_stream()

        if sd is not None:
            sd.stop()

        with self._lock:
            self.state = "stopped"

        # clear queue
        while not self.audio_queue.empty():

            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

        # wait for thread shutdown
        if self.thread:

            self.thread.join(timeout=2)

        with self._lock:
            self.current_audio = None

        logger.info("[StreamPlayer] Stopped")

    # 🔊 VOLUME
    def set_volume(
        self,
        volume
    ):

        self.volume = max(
            0.0,
            min(volume, 2.0)
        )

    # 🎧 SET AUDIO DEVICE
    def set_output_device(
        self,
        device_index
    ):

        self.output_device = device_index

    # 🎵 SET PLAYBACK SPEED
    def set_speed(
        self,
        speed
    ):

        self.speed = max(
            0.5,
            min(2.0, speed)
        )

    # 📊 DEBUG INFO
    def stats(self):
        with self._lock:
            state = self.state
            current_audio = self.current_audio

        return {

            "state":
                state,

            "queue_size":
                self.audio_queue.qsize(),

            "volume":
                self.volume,

            "speed":
                self.speed,

            "current_audio":
                current_audio,

            "device":
                self.output_device
        }

    # 🔎 LIST AUDIO DEVICES
    @staticmethod
    def list_devices():

        logger.info("%s", sd.query_devices())