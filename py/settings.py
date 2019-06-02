# some constants shared between files

import collections, json, glob, os, subprocess, sys

import numpy as np
import pyaudio


is_osx = subprocess.check_output('uname').decode('utf8').startswith('Darwin')
is_blender = 'blenderplayer' in sys.argv[0]
import __main__ as main  # noqa
is_interactive = not hasattr(main, '__file__')

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


sphere_channel1 = 1
sphere_channel2 = 3
sphere_pixels = 600

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


def generate_mapping(phi0=0):
    global sphere_strips
    mapping = np.zeros((64 * len(sphere_strips), 2))
    dphi = 2 * np.pi / len(sphere_strips)
    for led, sphere_strip in enumerate(sphere_strips):
        dtheta = np.pi / 2 / (sphere_strip.led0 + sphere_strip.led1)
        phi1 = phi0 + led * dphi
        phi2 = phi1 + dphi / 2
        sphere_strip_mapping = []
        # going outward
        values = [
            [phi1, i * dtheta]
            for i in range(sphere_strip.led0,
                           sphere_strip.led0 + sphere_strip.led1)
        ]
        # border
        values += [
            [phi1 + i * dphi / 2 / sphere_strip.border_leds, np.pi / 2]
            for i in range(sphere_strip.border_leds)
        ]
        # going inward
        values += [
            [phi2, np.pi / 2 - i * dtheta]
            for i in range(0, 60 - sphere_strip.led1 - sphere_strip.border_leds)
        ]
        assert len(values) == 60, len(values)
        mapping[led * 64: led * 64 + 60, :] = np.array(values)
    return mapping


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
    ArmConfig('pixel_arm_06.', [[0], [60]], 1.70411),
    ArmConfig('pixel_arm_02.', [[0]], -0.4700),
    ArmConfig('pixel_arm_03.', [[0]], 2.8928),
    ArmConfig('pixel_arm_04.', [[0]], 0.59689),
    ArmConfig('pixel_arm_05.', [[0], [60]], -2.3322),
    ArmConfig('pixel_arm_01.', [[0]], -1.4178),
]


def load_mapping():
    path = os.path.join(
        os.path.dirname(__file__),
        '../data',
        'blender_polar.json' if is_blender else 'rec_2_polar.json')
    mapping = np.zeros((sphere_pixels, 2))
    with open(path) as json_file:
        data = json.load(json_file)
        for coord_data in data:
            idx = int(coord_data['idx'])
            phi = float(coord_data['phi'])
            theta = float(coord_data['theta'])
            # phi: -pi - pi, theta 0 - pi
            mapping[idx - 1] = np.array([phi, theta])
    return mapping



# Arduino
###############################################################################


arduino_ports = [
    "/dev/ttyACM0",
    "/dev/ttyACM1",
]
sonar_hz = 2