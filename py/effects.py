

import numpy as np

import settings, util


class Effector:
    """Composes effects and handles channels."""
    def __init__(self, effects, buf_size=settings.buf_size):
        self.effects = effects
        self.bufs = [
            util.RollingBuffer(buf_size) for _ in range(len(effects))
            if buf_size
        ]

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
        return buf * np.clip(0, 1, signals[self.signal_name])
