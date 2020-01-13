# some constants shared between files

import collections, glob, os, subprocess, sys

import numpy as np
import pyaudio


is_osx = subprocess.check_output('uname').decode('utf8').startswith('Darwin')
import __main__ as main  # noqa
is_interactive = not hasattr(main, '__file__')


# audio
###############################################################################

# Recording mode & sample rate
if is_osx:
    in_channels = 1
else:
    in_channels = 2
    in_channels_comination = lambda left, right: left - right
rate = 16000

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
signalin_address = '0.0.0.0'  # TODO remove ?
monitor_listen_address = '0.0.0.0'
monitor_port = 6100
signalin_port = 6101
fadecandy_port = 6103
dmx_port = 6104
player_port = 6105
player2_port = 6106
ws_address = '127.0.0.1'
ws_address = '0.0.0.0'
ws_signals_port = 6108
ws_animation_port = 6109
status_address = 'figur.li'

# files
###############################################################################

root_dir = '.'
recordings_dir = os.path.join(root_dir, 'recordings')
abase_cache_dir = os.path.join(root_dir, '.abase_cache')
recorder2_dir = os.path.join(recordings_dir, 'recorder2')
recorder2_index = os.path.join(recorder2_dir, 'index.csv')
timetraces_dir = os.path.join(recordings_dir, 'timetraces')
samples_dir = os.path.join(root_dir, 'data', 'samples')


def get_recordings():
    return {
        os.path.basename(path)[:-4]: path
        for path in glob.glob(os.path.join(recordings_dir, '*.wav'))
    }

model_path = os.path.join(os.path.dirname(__file__), '../../data/models')

# animation
###############################################################################

# 2 in nuru, 2 for arms
fadecandies = 4

dg = np.pi / 180

enttec_channel = 6

phi0 = -30

SphereStrip = collections.namedtuple('SphereStrip', [
    # Number of LEDs that would fit between the first LED of the stripe
    # and the theta=0 point.
    'led0',
    # Number (1-based) of the LED that is at the theta=pi/2 point.
    'led1',
    # Number of LEDs after `led1` before going back.
    'border_leds',
])

sphere_strips = [
    SphereStrip(2, 30, 3),  # 0
    SphereStrip(1, 31, 2),  # 1
    SphereStrip(1, 31, 2),  # 2
    SphereStrip(0, 32, 2),  # 3
    SphereStrip(2, 30, 2),  # 4
    SphereStrip(2, 30, 2),  # 5
    SphereStrip(0, 32, 2),  # 6
    SphereStrip(2, 30, 2),  # 7
    SphereStrip(0, 32, 2),  # 8
    SphereStrip(0, 32, 2),  # 9
    SphereStrip(3, 29, 2),  # A
    SphereStrip(3, 29, 2),  # B
    SphereStrip(1, 31, 2),  # C
    SphereStrip(3, 29, 2),  # D
    SphereStrip(1, 31, 2),  # E
    SphereStrip(2, 30, 2),  # F
]

ArmSegment = collections.namedtuple('ArmSegmet', [
    # distance from the rim, in meters
    'distance',
    # fadecandy channel (i.e. every fadecandy is on a separate channel)
    'channel',
    # position within the fadecandy (from 0..7 within every fadecandy)
    'position',
    # every position can be used front/back
    'front',
])

ArmConfig = collections.namedtuple('ArmConfig', [
    # attachement angle of the arm, in degrees, top=0
    'phi',
    # list of ArmSegment
    'segments',
])

arm_configs = [
    ArmConfig(
        phi=-90,
        segments=[
            ArmSegment(distance=0, channel=2, position=0, front=True),
            ArmSegment(distance=0, channel=2, position=1, front=False),
            ArmSegment(distance=1, channel=2, position=2, front=True),
            ArmSegment(distance=1, channel=2, position=3, front=False),
        ],
    ),
    ArmConfig(
        phi=-45,
        segments=[
            ArmSegment(distance=0, channel=2, position=4, front=True),
            ArmSegment(distance=0, channel=2, position=5, front=False),
        ],
    ),
    ArmConfig(
        phi=45,
        segments=[
            ArmSegment(distance=0, channel=2, position=6, front=True),
            ArmSegment(distance=0, channel=2, position=7, front=False),
            ArmSegment(distance=1, channel=3, position=0, front=True),
            ArmSegment(distance=1, channel=3, position=1, front=False),
        ],
    ),
    ArmConfig(
        phi=90,
        segments=[
            ArmSegment(distance=0, channel=3, position=2, front=True),
            ArmSegment(distance=0, channel=3, position=3, front=False),
        ],
    ),
    ArmConfig(
        phi=135,
        segments=[
            ArmSegment(distance=0, channel=3, position=4, front=True),
            ArmSegment(distance=0, channel=3, position=5, front=False),
        ],
    ),
    ArmConfig(
        phi=180,
        segments=[
            ArmSegment(distance=0, channel=3, position=6, front=True),
            ArmSegment(distance=0, channel=3, position=7, front=False),
        ],
    ),
]


# Arduino
###############################################################################


arduino_ports = [
    "/dev/ttyACM0",
    "/dev/ttyACM1",
    "/dev/tty.usbmodem14344201",
]
sonar_hz = 4
