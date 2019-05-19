
import random

import numpy as np
import scipy

import perf, settings, util


class Effector:
    """Composes effects and handles channels."""
    def __init__(self, effects, buf_size=settings.buf_size):
        self.effects = effects
        self.bufs = [
            util.RollingBuffer(buf_size) for _ in range(len(effects))
            if buf_size
        ]

    @perf.measure('effector')
    def __call__(self, input_data, signals):
        assert len(input_data) == settings.hop_size, (
            'Expected input_data={}!={}'.format(
                settings.hop_size, len(input_data)))
        input_data = util.int16_to_float(input_data)

        output_datas = [
            effect(input_data, signals)
            for effect in self.effects
        ]
        for buf, output_data in zip(self.bufs, output_datas):
            buf(output_data)
        return output_datas


class Effect:
    def __or__(self, other):
        return ChainedEffect(self, other)


class ChainedEffect(Effect):
    def __init__(self, effect1, effect2):
        self.effect1 = effect1
        self.effect2 = effect2

    def __call__(self, buf, signals):
        return self.effect2(self.effect1(buf, signals), signals)


class Echo(Effect):
    def __init__(self, delay_s=0.2, coeff=0.7):
        self.delay_s = delay_s
        self.delay_n = int(delay_s / settings.hop_secs)
        self.coeff = coeff
        self.bufs = np.zeros((self.delay_n, settings.hop_size))
        self.i = 0

    def __call__(self, buf, signals):
        buf = buf[:settings.hop_size]
        n = self.bufs.shape[0]
        delayed = self.bufs[self.i % n].copy()
        self.bufs[self.i % n] = buf + delayed * self.coeff
        ret = self.bufs[self.i % n]
        self.i += 1
        return ret


class Delay(Effect):
    def __init__(self, delay_s=0.2):
        self.delay_s = delay_s
        self.delay_n = int(delay_s / settings.hop_secs)
        self.bufs = np.zeros((self.delay_n, settings.hop_size))
        self.i = 0

    def __call__(self, buf, signals):
        buf = buf[:settings.hop_size]
        n = self.bufs.shape[0]
        delayed = self.bufs[self.i % n].copy()
        self.bufs[self.i % n] = buf
        ret = delayed
        self.i += 1
        return ret


class Passthrough(Effect):
    def __call__(self, buf, signals):
        return buf


class Silence(Effect):
    def __init__(self):
        self.buf = np.zeros(settings.hop_size)

    def __call__(self, buf, signals):
        return self.buf


class Sinusoidal(Effect):
    def __init__(self, hz, A=0.2):
        T = int(settings.rate / hz)
        n = np.ceil(settings.hop_size / T)
        self.buf = A * np.sin(np.linspace(0, n * 2 * np.pi, n * T))

    def __call__(self, buf, signals):
        self.buf = np.roll(self.buf, shift=-len(buf))
        return self.buf[:len(buf)]


class Square(Effect):
    def __init__(self, hz, A=0.2):
        T = int(settings.rate / hz)
        n = np.ceil(settings.hop_size / T)
        self.buf = A * np.sin(np.linspace(0, n * 2 * np.pi, n * T))
        self.buf = np.repeat(np.concatenate([
            np.zeros(T // 2, dtype=np.float32),
            A * np.ones(T - T // 2, dtype=np.float32),
        ]), n)

    def __call__(self, buf, signals):
        self.buf = np.roll(self.buf, shift=-len(buf))
        return self.buf[:len(buf)]


class SigAmp:
    def __init__(self, signal_name):
        self.signal_name = signal_name

    def __call__(self, buf, signals):
        return buf * np.clip(signals.get(self.signal_name, 0), 0, 1)


class Compressor(Effect):
    def __init__(self, factor):
        self.factor = factor

    def __call__(self, data, signals=None):
        # TODO interpol
        return np.arctan(data * self.factor) / np.pi * 2


class Linear(Effect):
    def __init__(self, mult=1, shift=0):
        self.shift = shift
        self.mult = mult

    def __call__(self, data, signals=None):
        return (data + self.shift) * self.mult


class Iir(Effect):
    def __init__(self, b, a):
        self.b = b
        self.a = a
        self.zi = scipy.signal.lfiltic(b, a, [])

    def __call__(self, data, signals=None):
        data, self.zi = scipy.signal.lfilter(self.b, self.a, data, zi=self.zi)
        return data


class Notch(Iir):
    def __init__(self, hz, Q):
        super().__init__(*scipy.signal.iirnotch(hz, Q, settings.rate))


class LowPass(Iir):
    def __init__(self, hz, order):
        b, a = scipy.signal.butter(order, hz, btype='low', fs=settings.rate)
        super().__init__(b, a)


class HighPass(Iir):
    def __init__(self, hz, order):
        b, a = scipy.signal.butter(order, hz, btype='high', fs=settings.rate)
        super().__init__(b, a)


class BandPass(Iir):
    def __init__(self, hz1, hz2, order):
        b, a = scipy.signal.butter(
            order, [hz1, hz2], btype='band', fs=settings.rate)
        super().__init__(b, a)


class RndSub(Effect):
    """Randomly plays subsamples from provided sample."""

    def __init__(self, wav, sample_minmax, break_minmax,
                 ramp_minmax=(0.5, 0.5)):
        self.wav = wav
        self.sample_minmax = sample_minmax
        self.break_minmax = break_minmax
        self.ramp_minmax = ramp_minmax
        self.zeros = np.zeros(settings.hop_size)
        self.state = 'on'
        self.next()

    def next(self):
        self.state = dict(on='off', off='on')[self.state]
        self.left = self.rnd_n(dict(
            on=self.sample_minmax, off=self.break_minmax)[self.state])
        if self.state == 'on':
          self.win = scipy.hamming(2 * self.rnd_n(self.ramp_minmax))
          self.wav_i = self.wav_i0 = self.rnd_n([
              0, len(self.wav)/settings.rate - self.sample_minmax[1]])

    def rnd_n(self, minmax):
        secs = minmax[0] + random.random() * (minmax[1] - minmax[0])
        return int(settings.rate * secs)

    def __call__(self, buf, signals):
        n = len(buf)
        if self.state == 'off':
            buf = self.zeros
        else:
            buf = self.wav[self.wav_i: self.wav_i + n]
            dwav = self.wav_i - self.wav_i0
            if dwav < len(self.win) // 2:
                buf = np.array(buf)
                m = min(n, len(self.win) // 2 - dwav)
                buf[:m] *= self.win[dwav:][:m]
            elif self.left < len(self.win) // 2:
                buf = np.array(buf)
                m = min(self.left, n)
                buf[:m] *= self.win[-self.left:][:m]
                buf[m:] *= 0
            self.wav_i += n
        self.left -= len(buf)
        if self.left < 0:
            self.next()
        return buf

