
import collections

import numpy as np


class Buf(object):
    """Ringbuffer."""
    def __init__(self, null=None):
        self.deque = collections.deque()
        self.null = null
    def append(self, value):
        self.deque.append(value)
        return value
    def cut(self, length):
        while len(self.deque) > length:
            self.deque.popleft()
    def pop(self):
        self.deque.pop()
    def last(self):
        return self.deque[-1] if self.deque else self.null
    def __getitem__(self, index):
        return self.deque[index]
    def __len__(self):
        return len(self.deque)
    def as_list(self):
        return list(self.deque)
    def as_array(self):
        return np.array(self.deque)


class Bufs(object):
    """List of named ringbuffers."""
    def __init__(self, *names):
        self.names = names
        self.bufs = [Buf() for name in names]
    def cut(self, length):
        for buf in self.bufs:
            buf.cut(length)
    def pop(self):
        for buf in self.bufs:
            buf.pop()
    def items(self):
        return ((name, self[name]) for name in self.names)
    def __str__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            ', '.join(['{}[{}]'.format(name, len(self[name])) for name in self.names])
        )
    def __getitem__(self, name):
        if name not in self.names:
            raise KeyError('Buffer "{}" not known.'.format(name))
        return self.bufs[self.names.index(name)]
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(str(e))


def ceps_amp(bufs):
    return bufs.ceps.last().max() - bufs.ceps.last().min()


def detector1_adaptor(detector1):
    """Wraps Detector1 to be called with (keeper.bufs)."""
    def wrapped(bufs):
        return detector1(
            x_logmel=bufs.logmel[-1],
            x_dlogmel=(bufs.logmel[-1] -
                       (bufs.logmel[-2] if len(bufs.logmel)>1 else bufs.logmel[-1])),
            x_E=bufs.E[-1],
        )
    return wrapped


class Keeper(object):
    """Keeps rolling buffers of data and signals end of recording."""

    BELOW = 0
    ABOVE = 1
    DONE = 2

    def __init__(self,
                 # chunks to keep beofre, after, minimum length of recording
                 before=2, after=1, min_len=30,
                 intensity=ceps_amp, threshold=7, hysteresis=1,
                 detector=lambda bufs: 1, detector_threshold=0.4, detector_minlen=10,
                 threshold_late=5, detector_threshold_late=0.2,
                 logger=None):
        assert after <= hysteresis  # lazyness
        self.before = before
        self.after = after
        self.min_len = min_len
        self.threshold = threshold
        self.hysteresis = hysteresis
        self.intensity = intensity
        self.detector = detector
        self.detector_threshold = detector_threshold
        self.detector_minlen = detector_minlen
        self.threshold_late = threshold_late
        self.detector_threshold_late = detector_threshold_late
        self.logger = logger
        self._init()

    def _init(self):
        self.bufs = Bufs('data', 'ceps', 'logmel', 'intensity', 'E', 'detector')
        self.state = self.BELOW

    def add(self, data, ceps, logmel):
        """Returns True iff .data should be written."""
        if self.state == self.DONE:
            self._init()
            return False  # glitch
        self.bufs.data.append(data)
        self.bufs.ceps.append(ceps)
        self.bufs.logmel.append(logmel)
        self.bufs.intensity.append(self.intensity(self.bufs))
        self.bufs.E.append((np.array(data)**2).mean())
        if self.state == self.BELOW:
            if self.bufs.intensity.last() >= self.threshold:
                self.state = self.ABOVE
#                 print(self.bufs)
                self.bufs.detector.append(self.detector(self.bufs))
            else:
                self.bufs.cut(self.before)
                self.bufs.detector.append(0)
        else:
            # self.state == self.ABOVE
            self.bufs.detector.append(self.detector(self.bufs))
            done = True
            for i in range(self.hysteresis):
                if self.bufs.intensity[-i-1] >= self.get_threshold():
                    done = False
                    break
            if len(self.bufs.detector) - self.before >= self.detector_minlen:
                detector = np.mean(self.bufs.detector.as_list()[self.before:])
                if detector < self.get_detector_threshold():
                    self.logger.info('Discarding recording length {} : {:.2f}<{:.2f}'.format(
                        len(self.bufs.detector), detector, self.detector_threshold
                    ))
                    self.state = self.DONE
                    return False
            if done:
                self.state = self.DONE
                for i in range(self.end_dt()):
                    self.bufs.pop()
                return len(self.bufs.data) - self.before - self.after >= self.min_len
        return False

    def is_late(self):
        return len(self.bufs.intensity) - self.before > self.min_len

    def get_detector_threshold(self):
        return self.detector_threshold_late if self.is_late() else self.detector_threshold

    def get_threshold(self):
        return self.threshold_late if self.is_late() else self.threshold

    def stats(self):
        def tofloat(x):
            return [float(_) for _ in x]
        return {
            'state': self.state,
            'intensity': tofloat(self.bufs.intensity.as_list()),
            'detector': tofloat(self.bufs.detector.as_list()),
            'E': tofloat(self.bufs.E.as_list()),
        }

    def lastdbg(self):
        return {
            'state': self.state,
            'intensity': float(self.bufs.intensity.last() or 0),
            'detector': float(self.bufs.detector.last() or 0),
        }

    def end_dt(self):
        return self.hysteresis - self.after

    def extract(self, data, ceps, logmel):
        """Returns extraction indices and buffers."""
        n = int(len(data) / ceps.shape[0])
        extractions = []
        bufs = {
            name: [] for name in self.bufs.names
        }
        for i in range(ceps.shape[0]):
            d = data[i*n: (i+1)*n]
            done = self.add(d, ceps[i], logmel[i])
            for name in self.bufs.names:
                bufs[name].append(self.bufs[name].last())
            if done:
                i1 = i + 1 - self.end_dt()
                i0 = i1 - len(self.bufs.data)
                extractions.append((i0, i1))
        return extractions, bufs

