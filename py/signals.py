"""Signals transform sound to scalars."""

import aubio
import numpy as np
import PIL
import tensorflow as tf

import settings, util


# utils
###############################################################################


class Signal:
    def __or__(self, other):
        return SignalChain(self, other)

    def __mul__(self, other):
        return SignalMult(self, other)


class SignalChain(Signal):
    def __init__(self, sig1, sig2):
        self.sig1 = sig1
        self.sig2 = sig2

    def __call__(self, features):
        return self.sig2(self.sig1(features))

    def __repr__(self):
        return ' | '.join([repr(self.sig1), repr(self.sig2)])


class SignalMult(Signal):
    def __init__(self, sig1, sig2):
        self.sig1 = sig1
        self.sig2 = sig2

    def __call__(self, features):
        return self.sig2(features) * self.sig1(features)

    def __repr__(self):
        return ' * '.join([repr(self.sig1), repr(self.sig2)])


class WithPrevious:
    """Extends features with scaled averaged copy."""
    def __init__(self, n, d):
        self.n = n
        self.d = d
        self.buf = np.zeros((self.n, self.d), dtype='float32')
        self.i = 0

    def __call__(self, logmel):
        x = logmel
        if self.d != len(logmel):
            x = np.array(
                PIL.Image.fromarray(x.reshape((1, -1))).resize((self.d, 1)))[0]
        self.buf[self.i % self.n, :] = x
        self.i += 1
        return np.concatenate([logmel, self.buf.mean(axis=0)])

# features.wav
###############################################################################


class Pitcher(Signal):
    """Extracts pitch signal in Hz using `aubio`."""
    def __init__(self, tolerance=0.8):
        self.pitcher = aubio.pitch(
            method='yinfft', buf_size=settings.buf_size,
            hop_size=settings.hop_size, samplerate=settings.rate)
        self.pitcher.set_unit('Hz')
        self.pitcher.set_tolerance(tolerance)

    def __call__(self, features):
        wav = features.wav
        pitch = self.pitcher(util.int16_to_float(wav[:settings.hop_size]))
        assert len(pitch) == 1
        return pitch[0]


class Louder(Signal):
    """Extracts loudness from averaged envelope."""
    def __init__(self, n):
        self.buf = np.zeros(n * settings.hop_size)
        self.n = n
        self.i = 0

    def __call__(self, features):
        i0 = settings.hop_size * (self.i % self.n)
        self.buf[i0: i0 + settings.hop_size] = np.abs(
            features.wav[:settings.hop_size])
        self.i += 1
        return self.buf.mean()

# features.logmel
###############################################################################


class WeightedAverage(Signal):
    def __call__(self, features):
        logmel = features.logmel
        assert list(logmel.shape) == [settings.num_mel_bins]
        return ((logmel - logmel.min()) * range(len(logmel))).mean()


class FreqBreadth(Signal):
    def __init__(self, threshold):
        self.threshold = threshold

    def __call__(self, feats):
        breadth = 0
        start = None
        for i, v in enumerate(list(feats.logmel > self.threshold) + [0]):
            if v:
                if start is None:
                    start = i
            else:
                if start is not None:
                    breadth = max(breadth, i - start)
                    start = None
        return breadth


class FreqBand(Signal):
    """Frequency band with cosine slope. Values not normalized."""
    def __init__(self, hzmin, hzmax, hzslope=1, n=settings.num_mel_bins):
        self.n = n
        fmin, fmax, df = self.hz2f(hzmin), self.hz2f(hzmax), self.hz2f(hzslope)
        self.kernel = np.array([
            self.f01((f + df - fmin) / df) * self.f01((fmax + df - f) / df)
            for f in range(n)
        ])
        self.kernel /= self.kernel.sum()

    def __call__(self, feats):
        return (self.kernel * feats.logmel).sum()

    def hz2f(self, hz):
        return hz * np.pi * self.n / settings.rate

    def f01(self, x):
        return (1 + np.cos((np.clip(x, 0, 1) - 1) * np.pi)) / 2


class KerasDetector(Signal):
    """Transforms logmel to keras model scalar output."""

    PREPROCESSORS = {
        'none': lambda x: x,
        'wp_5_5': WithPrevious(n=5, d=5),
        'wp_10_10': WithPrevious(n=10, d=10),
        'wp_20_50': WithPrevious(n=20, d=50),
    }

    CACHE = {}

    def __init__(self, model_name, preprocessor):
        self.model = tf.keras.models.load_model(
            settings.get_model_path(model_name + '.h5'))
        self.preprocessor = self.PREPROCESSORS[preprocessor]
        self.lastv = self.lastlm = None

    def __call__(self, features):
        if not (features.logmel == self.lastlm).all():
            self.lastlm = features.logmel
            batch = np.array([self.preprocessor(features.logmel)])
            self.lastv = self.model.predict(batch)[0, 1]
        return self.lastv

    @classmethod
    def get(cls, model_name, preprocessor):
        key = '/'.join([model_name, preprocessor])
        if key not in cls.CACHE:
            cls.CACHE[key] = KerasDetector(model_name, preprocessor)
        return cls.CACHE[key]


# wants not set
###############################################################################


class F(Signal):
    """Linear transformation of scalar signal."""
    def __init__(self, shift=0, mult=1):
        self.mult = mult
        self.shift = shift

    def __call__(self, value):
        return self.mult * (value + self.shift)


class Limiter(Signal):
    """Ignores (keeps latest) values outside [minv..maxv]."""
    def __init__(self, minv=0.0, maxv=1.0):
        self.minv = minv
        self.maxv = maxv
        self.lastv = 0

    def __call__(self, value):
        if value < self.maxv and value > self.minv:
            self.lastv = value
        return self.lastv


class MovingAverage:
    def __init__(self, n):
        self.n = n
        self.buf = np.zeros(n)
        self.i = 0

    def __call__(self, v):
        if self.n == 0:
            return v
        self.buf[self.i % len(self.buf)] = v
        self.i += 1
        return self.buf.mean()


class Exponential(Signal):
    """Exponential smoothing (alpha=0 disables)."""
    def __init__(self, alpha):
        self.alpha = alpha
        self.lastv = 0

    def __call__(self, value):
        self.lastv = self.lastv + (value - self.lastv) * (1 - self.alpha)
        return self.lastv


class Median(Signal):
    """To be used with e.g. a ML detector."""
    def __init__(self, n, threshold=None):
        self.threshold = threshold
        self.buf = np.zeros(n, dtype='float32')
        self.i = 0

    def __call__(self, value):
        self.buf[self.i % len(self.buf)] = value
        self.i += 1
        x = np.median(self.buf)
        if self.threshold:
            x = 1. * (x > self.threshold)
        return x


class Hamming(Signal):
    def __init__(self, n):
        self.w = np.hamming(n)
        self.w /= self.w.sum()
        self.buf = np.zeros(n)

    def __call__(self, value):
        self.buf[0] = value
        self.buf = np.roll(self.buf, shift=1)
        return (self.buf * self.w).sum()


class Clip(Signal):
    def __init__(self, amin=0, amax=1):
        self.amin = amin
        self.amax = amax

    def __call__(self, value):
        return np.clip(value, self.amin, self.amax)
