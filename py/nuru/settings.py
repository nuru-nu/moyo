# some constants shared between files

import collections, os, subprocess
from dataclasses import dataclass
import sys
import json
import glob
import numpy as np  # type: ignore
import pyaudio  # type: ignore


is_osx = subprocess.check_output('uname').decode('utf8').startswith('Darwin')
import __main__ as main  # type: ignore  # noqa
is_interactive = not hasattr(main, '__file__')


timetracing = False
log_debug = False

nuru_path = os.path.dirname(os.path.abspath(__file__))

# ChatGPT

openai_api_key_gab = "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"
openai_api_key = "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"

chatgpt_personas = {}
for file in  glob.glob(os.path.join(nuru_path,'system_prompts','*.txt')):
    with open(file, 'r') as f:
        text = f.read()
    key = file.split('/')[-1].split('.')[0]  # extract the file name without extension
    chatgpt_personas[key] = text

# Available Models: https://platform.openai.com/docs/models/overview
chat_gpt_model = ["text-davinci-003", "gpt-3.5-turbo", "gpt-4"][1]

gpt_hz = 4

# GC Speech to text

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(
    nuru_path,
    "credentials/application_default_credentials.json"
)

# audio
###############################################################################

def in_channel_combination(left, right):
    return left - right


# Recording mode & sample rate
if is_osx:
    in_channels = 1
else:
    in_channels = 2
rate = 16000
chunk = int(rate / 10)  # 100ms

# Sample rate output 1
out1_rate = 44100
out1_names = (
    'HDA Intel PCH: ALC3232 Analog',  # Ubuntu
    'default',  # Ubuntu
    'Built-in Output',  # OS X
    'MacBook Pro Speakers',  # OS X
)
# Sample rate output 2
out2_rate = 44100
out2_names = (
    'default',  # Ubuntu - select "... - Audio Adapter"
    'C-Media USB Audio Device',  # Ubuntu
    'Built-in Output',  # OS X
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
    raise Exception('invalid rate={}'.format(rate))
buf_size = 2 * hop_size
dtype = pyaudio.paInt16
dtype_np = np.int16
sampwidth = 2


@dataclass
class AudioSettings:
    rate: int
    hop_size: int
    buf_size: int
    dtype: int

    @property
    def buf_secs(self) -> float:
        return self.buf_size / self.rate

    @property
    def hop_secs(self) -> float:
        return self.hop_size / self.rate

    @property
    def dtype_np(self):
        if self.dtype == pyaudio.paInt16:
            return np.int16
        raise ValueError(f'Invalid dtype={self.dtype}')

    @property
    def sampwidth(self) -> int:
        if self.dtype == pyaudio.paInt16:
            return 2
        raise ValueError(f'Invalid dtype={self.dtype}')


audio = AudioSettings(rate, hop_size, buf_size, dtype)
buf_secs = buf_size / rate
hop_secs = hop_size / rate

num_mel_bins = 64
f2hz = rate / num_mel_bins / np.pi
lower_edge_hertz = 125
upper_edge_hertz = 7500

num_mel_bins2 = 256
f2hz2 = rate / num_mel_bins2 / np.pi

reset_secs = 0


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

status_address = '127.0.0.1'
#status_address = 'figur.li'

integrator_sig_port = 6100
integrator_cmd_port = 6101
server_sig_port = 6102
dmx_sig_port = 6103
player_sig_port = 6104
player2_sig_port = 6105
sonar_cmd_port = 6106
recorder_cmd_port = 6107
cmd_cmd_port = 6108
midi_sig_port = 6109
kinect_cmd_port = 6111
server2_sig_port = 6112
server3_sig_port = 6113
gpt_cmd_port = 6114

# files
###############################################################################

root_dir = os.path.join(os.path.dirname(__file__), '..', '..')
recordings_dir = os.path.join(root_dir, 'recordings')
abase_cache_dir = os.path.join(root_dir, '.abase_cache')
recorder_dir = os.path.join(recordings_dir, 'recorder')
recs_dir = os.path.join(recordings_dir, 'recs')
timetraces_dir = os.path.join(recordings_dir, 'timetraces')
samples_dir = os.path.join(root_dir, 'data', 'samples')

model_path = os.path.join(os.path.dirname(__file__), '../../data/models')
kinect_mapping_path = os.path.join(
    root_dir, 'blender', 'data', 'kinect_mapping.json')


# animation
###############################################################################

# 2 in nuru, 2 for arms
fadecandies = 4

dg = np.pi / 180

enttec_channel = 6

phi0 = -140

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
            ArmSegment(distance=0, channel=3, position=2, front=True),
            ArmSegment(distance=0, channel=3, position=3, front=False),
            ArmSegment(distance=1, channel=3, position=4, front=False),#
            ArmSegment(distance=1, channel=3, position=5, front=True),#
        ],
    ),
    ArmConfig(
        phi=-45,
        segments=[
            ArmSegment(distance=0, channel=3, position=0, front=True),#
            ArmSegment(distance=0, channel=3, position=1, front=False),#
        ],
    ),
    ArmConfig(
        phi=45,
        segments=[
            ArmSegment(distance=0, channel=2, position=2, front=False),#
            ArmSegment(distance=0, channel=2, position=3, front=True),#
            ArmSegment(distance=1, channel=2, position=0, front=True),
            ArmSegment(distance=1, channel=2, position=1, front=False),
        ],
    ),
    ArmConfig(
        phi=90,
        segments=[
            ArmSegment(distance=0, channel=2, position=4, front=False),
            ArmSegment(distance=0, channel=2, position=5, front=True),
        ],
    ),
    ArmConfig(
        phi=135,
        segments=[
            ArmSegment(distance=0, channel=2, position=6, front=True),
            ArmSegment(distance=0, channel=2, position=7, front=False),
        ],
    ),
    ArmConfig(
        phi=180,
        segments=[
            ArmSegment(distance=0, channel=3, position=6, front=False),
            ArmSegment(distance=0, channel=3, position=7, front=True),
        ],
    ),
]

FcPos = collections.namedtuple('FcPos', ['fadecandy', 'pos'])

arm_mapping = {
    'arm_5-1': [FcPos(2, 1), FcPos(2, 6)],
    'arm_5-2': [FcPos(2, 0), FcPos(2, 7)],
    'arm_4-1': [FcPos(2, 2)],
    'arm_4-2': [FcPos(2, 3)],
    'arm_3-1': [FcPos(2, 4), FcPos(3, 0)],
    'arm_3-2': [FcPos(2, 5), FcPos(3, 1)],
    'arm_2-1': [FcPos(3, 2)],
    'arm_2-2': [FcPos(3, 3)],
    'arm_1-1': [FcPos(3, 4)],
    'arm_1-2': [FcPos(3, 5)],
    'arm_6-1': [FcPos(3, 6)],
    'arm_6-2': [FcPos(3, 7)],
}


# Arduino
###############################################################################

arduino_ports = [
    "/dev/ttyACM0",
    "/dev/ttyACM1",
    "/dev/cu.usbmodem14344201",
    "/dev/tty.usbmodem143344201",
]
sonar_hz = 4


if __name__ == '__main__':
    if len(sys.argv) == 2:
        print(globals()[sys.argv[1]])
    else:
        print('Usage:\n\t%s SETTING_NAME' % sys.argv[0])
