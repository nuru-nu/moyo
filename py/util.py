
import json, logging, sys

import numpy as np

import features, settings

FORMAT = '%(asctime)s - %(levelname)s - %(message)s'


def createLogger(name, stderr=True, logfile=True):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(FORMAT)
    if stderr:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    if logfile:
        handler = logging.FileHandler(name + '.log')
        handler.setFormatter(formatter)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
    return logger


class NoLogger:
    def info(*args, **kw):
        pass

    def warn(*args, **kw):
        pass

    def warning(*args, **kw):
        pass

    def debug(*args, **kw):
        pass

    def error(*args, **kw):
        pass


class XtermScale(object):

    def __init__(self, f, n):
        def hex2tuple(color):
            return (int(color[:2], 16) / 255.,
                    int(color[2:4], 16) / 255.,
                    int(color[4:], 16) / 255.)
        colors = [
            hex2tuple(color)
            for color in json.load(open('colors.json'))
        ]

        def colordist(c1, c2):
            # https://en.wikipedia.org/wiki/Color_difference
            return sum([((a - b)**2) for a, b in zip(c1, c2)]) ** .5

        def closest(c):
            return min([(colordist(c, color), i)
                        for i, color in enumerate(colors)])[1]

        self.scale = [
            closest(f(1. * i / (n - 1))[:3])
            for i in range(n)
        ]

    def __call__(self, x):
        i = int(len(self.scale) * min(1, max(0, x)))
        return self.scale[min(i, len(self.scale) - 1)]


def int16_to_float(a):
    if a.dtype.name == 'int16':
        a = (a / 32768.0).astype(np.float32)
    return a


def float_to_int16(a):
    if not a.dtype.name == 'int16':
        a = (a * 32768.0).astype('int16')
    return a


def plot_logmel(logmel, ax=None, rate=settings.rate, hzmax=None,
                hop_secs=settings.hop_secs, **matshow_kw):
    from matplotlib import pyplot as plt
    f2hz = rate / logmel.shape[1] / np.pi
    if ax is None:
        plt.figure(figsize=(12, 4))
        ax = plt.subplot(111)
    if hzmax:
        logmel = logmel[:, :int(hzmax / f2hz)]
    ax.matshow(logmel.T, cmap='jet', **matshow_kw)
    ax.set_xticklabels([
        '%.1f' % (frame * hop_secs)
        for frame in ax.get_xticks()
    ])
    ax.set_yticklabels([
        '{:,}'.format(int(f * f2hz))
        for f in ax.get_yticks()
    ])
    ax.set_xlabel('t [s]')
    ax.set_ylabel('f [Hz]')


def pythonize(d):
    """Transforms numpy arrays, float32, int64 to native Python dtypes."""
    if isinstance(d, dict):
        return {pythonize(k): pythonize(v) for k, v in d.items()}
    if isinstance(d, np.ndarray) or isinstance(d, list):
        return [pythonize(v) for v in d]
    if isinstance(d, np.float32):
        return float(d)
    if isinstance(d, np.int64):
        return int(d)
    return d


class Streamer:
    """Access array in buf_size-sized chunks hop_size apart."""

    def __init__(self, data, buf_size=settings.buf_size,
                 hop_size=settings.hop_size):
        self.i = 0
        self.data = data
        self.buf_size = buf_size
        self.hop_size = hop_size

    def __iter__(self):
        return self

    def __next__(self):
        if self.i >= len(self.data):
            raise StopIteration
        ret = self.data[self.i:self.i + self.buf_size]
        self.i += self.hop_size
        if len(ret) < self.buf_size:
            ret = np.pad(ret, [(0, self.buf_size - len(ret))], mode='constant')
        return ret


def get_signals(wav, signals):
    """Iterates through `wav` and computes values for `signals`."""
    values = {name: [] for name in signals}
    for buf in Streamer(wav):
        feats = features.wav2features(buf)
        for name, signal in signals.items():
            values[name].append(signal(feats))
    return values


class RollingBuffer:
    def __init__(self, buf_size):
        self.buf = np.zeros(buf_size, dtype=np.float32)

    # TODO only roll() once.
    def __call__(self, buf):
        if len(self.buf):
            self.buf = np.roll(self.buf, shift=-len(buf))
            self.buf[-(len(buf)):] = buf
