# some constants shared between files

import glob, os

import numpy as np
import pyaudio


rate = 16000
# rate = 44100

if rate == 16000:
    # 32ms
    hop_size = 512
    # hop_size = 1024
    # hop_size = 4096
elif rate == 44100:
    # 23ms
    hop_size = 1024
    # 46ms
    hop_size = 2048
else:
    raise 'invalid rate={}'.format(rate)
buf_size = 2 * hop_size
dtype = pyaudio.paInt16
dtype_np = np.int16
sampwidth = 2

buf_secs = buf_size / rate
hop_secs = hop_size / rate

num_mel_bins = 64
f2hz = rate / num_mel_bins / np.pi
lower_edge_hertz = 125
upper_edge_hertz = 7500

num_mel_bins2 = 256
f2hz2 = rate / num_mel_bins2 / np.pi

address = 'localhost'
monitor_port = 6100
signalin_port = 6101
lighter_port = 6102
fadecandy_port = 6103
dmx_port = 6104
player_port = 6105


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
recorder2_dir = os.path.join(recordings_dir, 'recorder2')
recorder2_index = os.path.join(recorder2_dir, 'index.csv')


def get_recordings():
    return {
        os.path.basename(path)[:-4]: path
        for path in glob.glob(os.path.join(recordings_dir, '*.wav'))
    }


def get_model_path(model_name):
    return os.path.join(
        os.path.dirname(__file__), '../data/models', model_name)
