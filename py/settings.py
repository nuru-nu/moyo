# some constants shared between files

import glob, os

import numpy as np
import pyaudio


rate = 16000
buf_size = 1024
hop_size = 512
dtype = pyaudio.paInt16
dtype_np = np.int16

buf_secs = buf_size / rate
hop_secs = hop_size / rate

num_mel_bins = 64
lower_edge_hertz = 125
upper_edge_hertz = 7500

pitch_tolerance = 0.8

address = 'localhost'
monitor_port = 6100
recorder_port = 6101
lighter_port = 6102


def to_string():
    return (
        'rate={rate} '
        'buf_secs={buf_secs:.3f}s ({buf_size}) '
        'hop_secs={hop_secs:.3f}s ({hop_size}) '
    ).format(rate=rate,
             buf_secs=buf_secs, buf_size=buf_size,
             hop_secs=hop_secs, hop_size=hop_size)


root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
recordings_dir = os.path.join(root_dir, 'recordings')
abase_cache_dir = os.path.join(root_dir, '.abase_cache')

recordings = {
    os.path.basename(path)[:-4]: path
    for path in glob.glob(os.path.join(recordings_dir, '*.wav'))
}
