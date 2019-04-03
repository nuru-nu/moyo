## pyaudio helpers

import numpy as np
import pyaudio

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
# RATE = 16000
RATE = 44100  # like abase
NORMALIZE_CST = 32768.0

# http://people.csail.mit.edu/hubert/pyaudio/

def record(secs, rate=RATE):

    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=rate,
                    input=True,
                    frames_per_buffer=CHUNK)

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