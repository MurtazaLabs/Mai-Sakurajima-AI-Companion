# Mai_ai/voice/realtime.py
import logging
import os
import tempfile
import threading
import time

from voice.interrupt import InterruptManager
from voice.stream_player import StreamPlayer

logger = logging.getLogger(__name__)


class RealtimeVoice:

    def __init__(
        self,
        tts_engine=None,
        max_queue=10,
        emotion=None,
    ):

        self.tts = tts_engine

        self.player = StreamPlayer()

        self.interrupt = InterruptManager()

        self.max_queue = max_queue

        self.is_speaking = False

        self.is_generating = False

        self.current_text = None

        self._lock = threading.RLock()

        self.voice_lock = threading.RLock()

        self.emotion = emotion

        # 🧠 state tracking
        self.last_activity = time.time()

    # ==================================================
    # 🗣️ NORMAL SPEECH
    # ==================================================
    def speak(self, text):

        if not text:
            return

        text = str(text).strip()

        if not text:
            return

        with self.voice_lock:

            try:

                self.interrupt.reset()

                if self.emotion:
                    try:
                        speed = self.emotion.influence("speech_speed")
                        self.player.set_speed(speed)
                    except Exception as e:
                        logger.debug("Emotion influence(speech_speed): %s", e)

                self.player.play_async()

                self.is_speaking = True

                self.current_text = text

                self.last_activity = time.time()

                path = self._temp_path()

                if self.tts:

                    self.is_generating = True

                    emotion_label = "neutral"
                    if self.emotion:
                        try:
                            word_bias = self.emotion.influence("word_choice")
                            if word_bias == "positive":
                                emotion_label = "happy"
                            elif word_bias == "warm":
                                emotion_label = "soft"
                            elif word_bias == "cautious":
                                emotion_label = "neutral"
                        except Exception as e:
                            logger.debug("Emotion influence(word_choice): %s", e)
                    kwargs = {}
                    if hasattr(self.tts, 'generate'):
                        import inspect
                        sig = inspect.signature(self.tts.generate)
                        if 'emotion' in sig.parameters:
                            kwargs['emotion'] = emotion_label
                    self.tts.generate(text, path, **kwargs)

                    self.is_generating = False

                    # ✅ don't enqueue empty/broken files
                    if self._valid_audio(path):

                        self.player.enqueue(path)

                    else:
                        logger.warning("Invalid audio generated")

                else:
                    logger.info("Mai: %s", text)

            except Exception as e:
                logger.exception("Voice error: %s", e)

            finally:

                self.is_generating = False

                # ✅ wait for playback to finish
                self.wait_until_done()

                self.is_speaking = False

    # ==================================================
    # 🎙️ STREAMED SPEECH
    # ==================================================
    def speak_stream(self, text_chunks):

        with self.voice_lock:

            try:

                self.interrupt.reset()

                self.player.play_async()

                self.is_speaking = True

                buffer = ""

                last_emit = time.time()

                for chunk in text_chunks:

                    if self.interrupt.is_interrupted():

                        logger.info("[Voice Interrupted]")

                        break

                    if not chunk:
                        continue

                    chunk = str(chunk).strip()

                    if not chunk:
                        continue

                    # queue protection
                    while (
                        self.player.audio_queue.qsize()
                        >= self.max_queue
                    ):

                        if self.interrupt.is_interrupted():
                            break

                        self.voice_lock.release()
                        time.sleep(0.05)
                        self.voice_lock.acquire()

                    buffer += " " + chunk

                    buffer = buffer.strip()

                    # ==================================================
                    # 🧠 SMART CHUNKING
                    # ==================================================

                    ends_sentence = any(
                        buffer.rstrip().endswith(p)
                        for p in [
                            ".",
                            "?",
                            "!",
                            "…"
                        ]
                    )

                    should_emit = (

                        (ends_sentence and len(buffer) >= 50)

                        or

                        len(buffer) >= 180

                        or

                        (
                            time.time() - last_emit
                        ) > 3.5
                    )

                    if not should_emit:
                        continue

                    try:

                        self._generate_and_queue(buffer)

                        buffer = ""

                        last_emit = time.time()

                    except Exception as e:
                        logger.exception("Stream voice error: %s", e)

                # ==================================================
                # 🧠 FINAL BUFFER FLUSH
                # ==================================================

                if (
                    buffer.strip()
                    and not self.interrupt.is_interrupted()
                ):

                    try:
                        self._generate_and_queue(buffer.strip())
                    except Exception as e:
                        logger.exception("Final chunk error: %s", e)

            finally:

                self.is_generating = False

                # ✅ wait until ALL playback ends
                had_output = self.tts is not None and (not self.player.audio_queue.empty() or self.player.state == "playing")
                self.wait_until_done()

                self.is_speaking = False
                if not had_output:
                    logger.warning("[speak_stream] No TTS engine — response was text-only")

    # ==================================================
    # 🧠 GENERATE + QUEUE AUDIO
    # ==================================================
    def _generate_and_queue(self, text):

        if not text:
            return

        text = str(text).strip()

        if not text:
            return

        with self._lock:
            self.current_text = text

        self.last_activity = time.time()

        path = self._temp_path()
        enqueued = False

        try:
            if self.tts:

                try:
                    with self._lock:
                        self.is_generating = True

                    emotion_label = "neutral"
                    if self.emotion:
                        try:
                            word_bias = self.emotion.influence("word_choice")
                            if word_bias == "positive":
                                emotion_label = "happy"
                            elif word_bias == "warm":
                                emotion_label = "soft"
                            elif word_bias == "cautious":
                                emotion_label = "neutral"
                        except Exception as e:
                            logger.debug("Emotion influence(word_choice): %s", e)
                    kwargs = {}
                    if hasattr(self.tts, 'generate'):
                        import inspect
                        sig = inspect.signature(self.tts.generate)
                        if 'emotion' in sig.parameters:
                            kwargs['emotion'] = emotion_label
                    self.tts.generate(text, path, **kwargs)

                finally:
                    with self._lock:
                        self.is_generating = False

                # validate before enqueue
                if self._valid_audio(path):
                    self.player.enqueue(path)
                    enqueued = True
                else:
                    logger.warning("Skipping invalid audio")

            else:
                logger.warning("[TTS unavailable] Mai: %s", text)
                print(f"\n🤍 Mai: {text}\n")
        finally:
            if not enqueued:
                try:
                    os.remove(path)
                except Exception as e:
                    logger.warning("[Realtime] Failed to remove temp audio file: %s", e)

    # ==================================================
    # ✅ WAIT FOR AUDIO COMPLETION
    # ==================================================
    def wait_until_done(self):

        timeout = 60

        start = time.time()

        while True:

            # ✅ fully idle
            if (
                not self.is_generating
                and self.player.audio_queue.empty()
                and self.player.state != "playing"
            ):
                break

            # 🛑 deadlock protection
            if (
                time.time() - start
            ) > timeout:

                logger.warning("wait_until_done timeout")

                break

            time.sleep(0.05)

    # ==================================================
    # 🛑 STOP SPEECH
    # ==================================================
    def stop(self):

        self.interrupt.trigger()

        try:

            self.player.stop()

        except Exception as e:
            logger.exception("Voice stop error: %s", e)

        with self.voice_lock:

            self.is_speaking = False

            self.is_generating = False

            self.current_text = None

    # ==================================================
    # 🧠 VALID AUDIO CHECK
    # ==================================================
    def _valid_audio(self, path):

        try:
            if not path or not os.path.isfile(path):
                return False
            ext = os.path.splitext(path)[1].lower()
            if ext not in ('.wav', '.mp3', '.ogg', '.flac'):
                return False
            with open(path, 'rb') as f:
                header = f.read(12)
            if ext == '.wav' and header[:4] != b'RIFF':
                return False
            if ext == '.mp3' and header[:3] != b'ID3':
                return False
            return True

        except Exception as e:
            logger.warning("Audio validation failed: %s", e)
            return False

    # ==================================================
    # 🧠 TEMP FILE CREATION
    # ==================================================
    def _temp_path(self):

        temp = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        )

        path = temp.name

        temp.close()

        return path

    # ==================================================
    # 📊 DEBUG INFO
    # ==================================================
    def stats(self):
        with self._lock:
            is_speaking = self.is_speaking
            is_generating = self.is_generating
            current_text = self.current_text

        return {

            "is_speaking":
                is_speaking,

            "is_generating":
                is_generating,

            "current_text":
                current_text,

            "queue_size":
                self.player.audio_queue.qsize(),

            "player_state":
                self.player.state,

            "last_activity":
                self.last_activity,
        }