"""Signals transform sound to scalars."""

import aubio
import numpy as np

import settings, streaming, util

# utils
###############################################################################


class Signal:
    def __or__(self, other):
        return SignalChain(self, other)


class SignalChain(Signal):
    def __init__(self, sig1, sig2):
        self.sig1 = sig1
        self.sig2 = sig2

    def __call__(self, features):
        return self.sig2(self.sig1(features))

    def __repr__(self):
        return ' | '.join([repr(self.sig1), repr(self.sig2)])

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
        self.outlier_filter = streaming.OutlierFilter(d=100, n=2)

    def __call__(self, features):
        wav = features.wav
        pitch = self.pitcher(util.int16_to_float(wav[:settings.hop_size]))
        assert len(pitch) == 1
        return self.outlier_filter(pitch[0])


class Louder(Signal):
    """Extracts loudness from averaged envelope."""
    def __init__(self):
        self.envelop_averager = streaming.EnvelopAverager(
            buf_size=settings.buf_size, n=10)

    def __call__(self, features):
        return self.envelop_averager(features.wav)

# features.logmel
###############################################################################


class WeightedAverage(Signal):
    def __init__(self, n=5):
        self.moving_average = streaming.MovingAverage(n=n)

    def __call__(self, features):
        logmel = features.logmel
        assert list(logmel.shape) == [settings.num_mel_bins]
        return self.moving_average(
            ((logmel - logmel.min()) * range(len(logmel))).mean())


class ThresholdedFrequencies(Signal):
    def __init__(self, hz, threshold, bins):
        """Checks (logmel[f2bin(hz):] > threshold).sum() > bins"""
        self.n0 = int(hz / settings.rate * settings.num_mel_bins * np.pi)
        self.threshold = threshold
        self.bins = bins

    def __call__(self, features):
        logmel = features.logmel
        assert list(logmel.shape) == [settings.num_mel_bins]
        return 1.0 * ((logmel[self.n0:] > self.threshold).sum() > self.bins)

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


class Exponential(Signal):
    """Exponential smoothing (alpha=0 disables)."""
    def __init__(self, alpha):
        self.alpha = alpha
        self.lastv = 0

    def __call__(self, value):
        self.lastv = self.lastv + (value - self.lastv) * (1 - self.alpha)
        return self.lastv
