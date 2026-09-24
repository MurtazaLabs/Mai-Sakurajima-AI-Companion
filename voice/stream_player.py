# Mai_ai/voice/stream_player.py
import threading
import queue
import time
import os
import logging

import sounddevice as sd
import soundfile as sf
import numpy as np

logger = logging.getLogger(__name__)


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

                # use chosen device
                if self.output_device is not None:

                    sd.play(
                        data,
                        sr,
                        device=self.output_device,
                        blocking=True
                    )

                else:

                    sd.play(
                        data,
                        sr,
                        blocking=True
                    )

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