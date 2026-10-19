import threading

import numpy as np


class AudioBuffer:
    def __init__(self, max_seconds=3.0, sample_rate=16000):
        self.sample_rate = sample_rate
        self.max_samples = int(max_seconds * sample_rate)
        self._buffer = np.zeros(self.max_samples, dtype=np.float32)
        self._pos = 0
        self._lock = threading.RLock()
        self._full = False

    def add(self, chunk):
        n = len(chunk)
        with self._lock:
            if n >= self.max_samples:
                self._buffer[:] = chunk[-self.max_samples:]
                self._pos = 0
                self._full = True
                return
            end = self._pos + n
            if end <= self.max_samples:
                self._buffer[self._pos:end] = chunk
            else:
                first = self.max_samples - self._pos
                self._buffer[self._pos:] = chunk[:first]
                self._buffer[:n - first] = chunk[first:]
                self._full = True
            self._pos = (self._pos + n) % self.max_samples

    def get_last(self, duration):
        n = int(duration * self.sample_rate)
        if n <= 0:
            return np.array([], dtype=np.float32)
        with self._lock:
            n = min(n, self.max_samples)
            if not self._full and self._pos == 0:
                return np.array([], dtype=np.float32)
            available = self._pos if not self._full else self.max_samples
            n = min(n, available)
            if n == 0:
                return np.array([], dtype=np.float32)
            start = self._pos - n
            if start >= 0:
                return self._buffer[start:self._pos].copy()
            result = np.zeros(n, dtype=np.float32)
            first = -start
            result[:first] = self._buffer[self.max_samples - first:]
            result[first:] = self._buffer[:self._pos]
            return result

    def clear(self):
        with self._lock:
            self._buffer.fill(0)
            self._pos = 0
            self._full = False
