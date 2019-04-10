## pyaudio helpers

import numpy as np
import pyaudio

import os
import sys
lib_path = os.path.join(os.path.dirname(__file__), '../../py')
if lib_path not in sys.path:
    sys.path.insert(0, lib_path)

import settings

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
# RATE = 16000
RATE = 44100  # like abase
NORMALIZE_CST = 32768.0

# http://people.csail.mit.edu/hubert/pyaudio/

def record(secs, rate=settings.rate, dtype=settings.dtype, hop_size=settings.hop_size):

    p = pyaudio.PyAudio()

    stream = p.open(format=dtype,
                    channels=1,
                    rate=rate,
                    input=True,
                    frames_per_buffer=hop_size)

    print("* recording")

    frames = []

    for i in range(0, int(rate / CHUNK * secs)):
        data = stream.read(CHUNK)
        frames.append(data)

    print("* done recording")

    stream.stop_stream()
    stream.close()
    p.terminate()

    return np.concatenate([np.fromstring(frame, np.int16) for frame in frames])


def playback(data, rate=RATE):
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=rate,
                    output=True)
    
    if data.dtype != np.int16:
        data = (data * NORMALIZE_CST).astype(np.int16)

    stream.write(data.tostring())
    # for data in frames:
    #     stream.write(data)

    stream.stop_stream()
    stream.close()

    p.terminate()