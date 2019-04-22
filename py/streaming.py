
import numpy as np
from PIL import Image


class OutlierFilter:
    def __init__(self, d, n):
        """Replaces outlier values with last non-outlier value.

        Args:
          d: Only consider values to be outliers if they are different by at
              least `d` compared to previous values.
          n: Accept any value if there are at least `n` consecutive values
              that are searated by no more than `d` from each other.
        """
        self.d = d
        self.n = n
        self.lv = 0
        self.buf = [0] * n
        self.i = 0

    def __call__(self, v):
        """Returns `v` with outliers replaced by previous values."""
        if self.n == 0:
            return v
        try:
            return np.array(list(map(self.__call__, v)))
        except TypeError:
            pass
        within = True
        for j, b in enumerate(self.buf):
            if abs(v - b) > self.d:
                within = False
                break
        self.buf[self.i % len(self.buf)] = v
        self.i += 1
        if within:
            self.lv = v
        return self.lv


class MovingAverage:
    def __init__(self, n):
        self.n = n
        self.buf = np.zeros(n)
        self.i = 0

    def __call__(self, v):
        if self.n == 0:
            return v
        try:
            return np.array(list(map(self.__call__, v)))
        except TypeError:
            pass
        self.buf[self.i % len(self.buf)] = v
        self.i += 1
        return self.buf.mean()


class EnvelopAverager:
    def __init__(self, buf_size, n):
        """Primitive loudness signal by averaging absolute amplitudes.

        Args:
          buf_size: number of samples of buffer for `__call__()`.
          n: number of buffers to average over (low pass filter).
        """
        self.n = n
        self.buf = np.zeros((n, buf_size))
        self.i = 0

    def __call__(self, buf):
        self.buf[self.i % self.n] = np.abs(buf)
        self.i += 1
        return np.mean(self.buf)


class WithPrevious:
    """Streaming implementation of with_previous()."""
    def __init__(self, n, d):
        self.n = n
        self.d = d
        self.buf = np.zeros((self.n, self.d), dtype='float32')
        self.i = 0

    def __call__(self, logmel):
        x = logmel
        if self.d != len(logmel):
            x = np.array(
                Image.fromarray(x.reshape((1, -1))).resize((self.d, 1)))[0]
        self.buf[self.i % self.n, :] = x
        self.i += 1
        return np.concatenate([logmel, self.buf.mean(axis=0)])


class KerasDetector:
    """Transforms logmel to keras model scalar output."""
    def __init__(self, model, preprocessor):
        self.model = model
        self.preprocessor = preprocessor
        self.t = None
        self.lv = None

    def __call__(self, logmel, t=None):
        if t and self.t == t:
            return self.lv
        self.lv = self.model.predict(
            np.array([self.preprocessor(logmel)]))[0, 1]
        return self.lv


class MedianFilter:
    """To be used with e.g. a ML detector."""

    def __init__(self, detector, n, threshold=None):
        self.detector = detector
        self.threshold = threshold
        self.buf = np.zeros(n, dtype='float32')
        self.i = 0

    def __call__(self, logmel, t=None):
        self.buf[self.i % len(self.buf)] = self.detector(logmel, t=t)
        self.i += 1
        x = np.median(self.buf)
        if self.threshold:
            x = 1. * (x > self.threshold)
        return x
