import logging
import threading

import numpy as np

logger = logging.getLogger(__name__)


class FullAEC:
    def __init__(self, sample_rate=16000, filter_length=2048,
                 adaptation_rate=0.01, max_echo_delay=0.5,
                 double_talk_threshold=0.3, residual_tail_length=256,
                 hangover_frames=20):
        self.sample_rate = sample_rate
        self.filter_length = filter_length
        self.adaptation_rate = adaptation_rate
        self.max_echo_delay_samples = int(max_echo_delay * sample_rate)
        self.double_talk_threshold = double_talk_threshold
        self.residual_tail_length = residual_tail_length
        self.hangover_frames = hangover_frames

        buf_size = self.max_echo_delay_samples + filter_length
        self._playback_buffer = np.zeros(buf_size, dtype=np.float32)
        self._filter_weights = np.zeros(filter_length, dtype=np.float32)
        self._playback_write = 0

        self._residual_weights = np.zeros(residual_tail_length, dtype=np.float32)
        self._residual_buffer = np.zeros(residual_tail_length, dtype=np.float32)
        self._residual_idx = 0

        self._near_end_power = 0.0
        self._far_end_power = 0.0
        self._double_talk = False
        self._hangover = 0
        self._clip_counter = 0
        self._lock = threading.RLock()

    def add_playback(self, audio):
        if len(audio) == 0:
            return
        with self._lock:
            total = len(self._playback_buffer)
            offset = 0
            remaining = len(audio)
            while remaining > 0:
                avail = total - self._playback_write
                chunk = min(remaining, avail)
                self._playback_buffer[self._playback_write:self._playback_write + chunk] = audio[offset:offset + chunk]
                self._playback_write = (self._playback_write + chunk) % total
                offset += chunk
                remaining -= chunk

    def process(self, mic_audio):
        if len(mic_audio) == 0:
            return mic_audio
        try:
            with self._lock:
                total = len(self._playback_buffer)
                n = len(mic_audio)

                near_power = np.mean(mic_audio ** 2) + 1e-12
                self._near_end_power = 0.95 * self._near_end_power + 0.05 * near_power

                far_end_samples = min(self.filter_length, total)
                if self._playback_write >= far_end_samples:
                    far_slice = self._playback_buffer[
                        self._playback_write - far_end_samples:self._playback_write
                    ]
                else:
                    part1 = self._playback_buffer[total - (far_end_samples - self._playback_write):]
                    part2 = self._playback_buffer[:self._playback_write]
                    far_slice = np.concatenate([part1, part2])
                far_slice = far_slice[:far_end_samples]
                far_power = np.mean(far_slice ** 2) + 1e-12
                self._far_end_power = 0.95 * self._far_end_power + 0.05 * far_power

                if self._far_end_power > 1e-6:
                    ratio = near_power / self._far_end_power
                    in_double_talk = ratio > self.double_talk_threshold
                else:
                    in_double_talk = False

                if in_double_talk:
                    self._hangover = self.hangover_frames
                    self._double_talk = True
                elif self._hangover > 0:
                    self._hangover -= 1
                else:
                    self._double_talk = False

                mu = self.adaptation_rate
                if self._double_talk:
                    mu *= 0.05

                # Build reference matrix (n x filter_length) in one shot
                start_idx = (self._playback_write - self.filter_length) % total
                indices = (start_idx + np.arange(n)[:, None] + np.arange(self.filter_length)[None, :]) % total
                ref_matrix = self._playback_buffer[indices.astype(np.intp)]

                # Echo estimation for all samples
                echo_ests = ref_matrix @ self._filter_weights
                errors = mic_audio - echo_ests

                # Residual filter processing (vectorized)
                res_start = self._residual_idx
                res_indices = (res_start + np.arange(n)[:, None] + np.arange(self.residual_tail_length)[None, :]) % self.residual_tail_length
                res_matrix = self._residual_buffer[res_indices.astype(np.intp)]
                residual_echoes = res_matrix @ self._residual_weights
                errors -= residual_echoes

                # Clipping
                threshold = 3.0 * np.sqrt(self._near_end_power + 1e-12)
                clip_mask = np.abs(errors) > threshold
                errors[clip_mask] *= 0.5

                # Update residual buffer (vectorized circular write)
                end = self._residual_idx + n
                if end <= self.residual_tail_length:
                    self._residual_buffer[self._residual_idx:end] = errors
                else:
                    wrap = end - self.residual_tail_length
                    first_part = self.residual_tail_length - self._residual_idx
                    self._residual_buffer[self._residual_idx:] = errors[:first_part]
                    self._residual_buffer[:wrap] = errors[first_part:first_part + wrap]
                self._residual_idx = end % self.residual_tail_length

                # NLMS weight update (accumulated across all samples)
                if not self._double_talk:
                    norms = np.sum(ref_matrix ** 2, axis=1) + 1e-10
                    update = ((mu * errors / norms)[:, None]) * ref_matrix
                    self._filter_weights += np.sum(update, axis=0)

                    res_norms = np.sum(res_matrix ** 2, axis=1) + 1e-10
                    res_update = ((mu * 0.3 * errors / res_norms)[:, None]) * res_matrix
                    self._residual_weights += np.sum(res_update, axis=0)

                return errors
        except Exception as e:
            logger.warning("[FullAEC] process error: %s", e)
            return mic_audio

    def is_double_talk(self):
        return self._double_talk

    def reset(self):
        with self._lock:
            buf_size = self.max_echo_delay_samples + self.filter_length
            self._playback_buffer = np.zeros(buf_size, dtype=np.float32)
            self._filter_weights = np.zeros(self.filter_length, dtype=np.float32)
            self._playback_write = 0
            self._residual_weights = np.zeros(self.residual_tail_length, dtype=np.float32)
            self._residual_buffer = np.zeros(self.residual_tail_length, dtype=np.float32)
            self._residual_idx = 0
            self._near_end_power = 0.0
            self._far_end_power = 0.0
            self._double_talk = False
            self._hangover = 0

    def stats(self):
        return {
            "filter_length": self.filter_length,
            "double_talk": self._double_talk,
            "near_end_power": round(self._near_end_power, 6),
            "far_end_power": round(self._far_end_power, 6),
        }
