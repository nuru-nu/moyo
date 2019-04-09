
import json, logging, sys

import numpy as np

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


class XtermScale(object):

    def __init__(self, f, n):
        hex2tuple = lambda color: (
            int(color[:2], 16) / 255.,
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
            return min([(colordist(c, color), i) for i, color in enumerate(colors)])[1]

        self.scale = [
                closest(f(1. * i / (n - 1))[:3])
                for i in range(n)
                ]

    def __call__(self, x):
        i = int(len(self.scale) * min(1, max(0, x)))
        return self.scale[min(i, len(self.scale) - 1)]


def debounce(dt, f, wait_first=True):
    #TODO write version that works with logging
    t0 = None
    def wrapper(*args, **kwargs):
        if t0 is None:
            t0 = time.time()
            return
        if time.time() - t0 < dt:
            return
        if wait_first:
            wait_first = False
            return
        t0 = time.time()
        return f(*args, **kwargs)
    return wrapper


def int16_to_float(a):
    if a.dtype.name == 'int16':
        a =  (a / 32768.0).astype(np.float32)
    return a

def float_to_int16(a):
    if not a.dtype.name == 'int16':
        a = (a * 32768.0).astype('int16')
    return a

