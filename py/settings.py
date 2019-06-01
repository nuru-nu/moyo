# some constants shared between files

import collections, glob, os, subprocess

import numpy as np
import pyaudio


is_osx = subprocess.check_output('uname').decode('utf8').startswith('Darwin')

# audio
###############################################################################

# Recording sample rate
rate = 16000
in_channels = 2

# Sample rate output 1
out1_rate = 44100
out1_names = (
    'HDA Intel PCH: ALC3232 Analog',  # Ubuntu
    'default',  # Ubuntu
    'Built-in Output',  # OS X
)
# Sample rate output 2
out2_rate = 44100
out2_names = (
    'default',  # Ubuntu - select "... - Audio Adapter"
    'C-Media USB Audio Device',  # Ubuntu
)

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

alive_secs = 10


def to_string():
    return (
        'rate={rate} '
        'buf_secs={buf_secs:.3f}s ({buf_size}) '
        'hop_secs={hop_secs:.3f}s ({hop_size}) '
    ).format(rate=rate,
             buf_secs=buf_secs, buf_size=buf_size,
             hop_secs=hop_secs, hop_size=hop_size)

# network
###############################################################################


address = 'localhost'
monitor_listen_address = '0.0.0.0'
monitor_port = 6100
signalin_port = 6101
lighter_port = 6102
fadecandy_port = 6103
dmx_port = 6104
player_port = 6105
player2_port = 6106

# files
###############################################################################

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

# animation
###############################################################################


sphere_channel = 1
sphere_pixels = 600
ArmConfig = collections.namedtuple('ArmConfig', [
    # the fade candy channel
    'channel',
    # list of lists : e.g. [[128, 192], [256, 320]] means that the first meter
    # is connected 129..191, 192..255 (in parallel) and the second meter is
    # connected 256..319, 320..385 (in parallel)
    'offsets',
    # matches phi of sphere
    'phi'])
arm_configs = [
    ArmConfig(2, [[0, 64]], np.pi + np.pi * 3 / 4),
    ArmConfig(2, [[128, 192], [256, 320]], 0),
]

blender_arm_configs = [
    ArmConfig('pixel_arm_01.', [[-1]], -1.4178),
    ArmConfig('pixel_arm_02.', [[-1]], -0.4700),
    ArmConfig('pixel_arm_03.', [[-1]], 2.8928),
    ArmConfig('pixel_arm_04.', [[-1]], 0.59689),
    ArmConfig('pixel_arm_05.', [[-1], [59]], -2.3322),
    ArmConfig('pixel_arm_06.', [[-1], [59]], 1.70411),
]
