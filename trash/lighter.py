
import argparse, array, json, math, os, random, socket, sys, time

from config import CHANNELS, CHANNELS_REAL, conf
import util

OLA_PATH = '/usr/local/Cellar/ola/0.10.6/lib/python2.7/site-packages'
import sys
if OLA_PATH not in sys.path:
    sys.path.append(OLA_PATH)
from ola.ClientWrapper import ClientWrapper

parser = argparse.ArgumentParser(description='Control the lights.')

parser.add_argument('--freq', type=float, default=20.,
        help='Update frequency [Hz].')
parser.add_argument('--show_secs', type=float, default=30.,
        help='How long to show flower [secs].')

parser.add_argument('--dry_run', type=bool, default=False,
        help='Dry run (do not try to connect to OLA daemon).')

parser.add_argument('--port', type=int, default=5618,
        help='Which port to listen on.')
parser.add_argument('--address', type=str, default='localhost',
        help='Which address to listen on.')

args = parser.parse_args()

logger = util.createLogger('lighter')
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

F = int(255./8)
MOVE_AMP = [None, 1, 2, 3, 4, 5, 6, 7, 8]
MOVE_FREQ = [None] + [int(60 * f) for f in range(8, 0, -1)]
PULSE_AMP = [None, 0.1, 0.2, 0.3, 0.5, 0.6, 0.8, 0.9, 1.0]
PULSE_FREQ = [None] + [int(20 * f) for f in range(8, 0, -1)]


def k(key):
    assert key in CHANNELS or key in range(len(CHANNELS)), key
    if key in CHANNELS:
        key = CHANNELS.index(key)
    return key


class FakeClientWrapper(object):
    def Stop(self): pass
    def Run(self): pass

class FakeClient(object):
    def SendDmx(self, *args, **kwargs): pass

def get_wrapper_client():
    if args.dry_run:
        return FakeClientWrapper(), FakeClient()
    wrapper = ClientWrapper()
    return wrapper, wrapper.Client()


class Lighter(object):

    def __init__(self):
        self.universe = 1
        self.wrapper, self.client = get_wrapper_client()
        self.state = [0] * len(CHANNELS)
        self['intensity'] = 255
        self['white'] = 255
        self['pan'] = 127
        self['tilt'] = 127
        self.i = 0
        self.update()

    def __setitem__(self, key, value):
        value = int(max(0, min(255, value)))
        self.state[k(key)] = value

    def __getitem__(self, key):
        return self.state[k(key)]

    def setchannels(self, state):
        # if self.idle:
        #     return
        if isinstance(state, list):
            state = {i: v for i, v in enumerate(state)}
        for key, value in state.items():
            self[key] = value

    def channels(self):
        channels = self.state[:CHANNELS_REAL]
        #print(preset)
        if self['move amp'] and self['move freq']:
            amp = MOVE_AMP[int(self['move amp'] / F)]
            t = MOVE_FREQ[int(self['move freq'] / F)]
            v = amp * (0.5 + math.sin(2 * math.pi * (self.i % t) / t) / 2)
            channels[k('pan')] += int(v)
            # channels[k('tilt')] += int(v)
        if self['pulse amp'] and self['pulse freq']:
            amp = PULSE_AMP[int(self['pulse amp'] / F)]
            t = PULSE_FREQ[int(self['pulse freq'] / F)]
            v = 1 - amp * (1 + math.cos(2 * math.pi * (self.i % t) / t)) / 2
            channels[k('intensity')] = int(v * channels[k('intensity')])
        return channels

    def update(self):
        def DmxSent(state):
            self.wrapper.Stop()  # or wrapper will block at next call
        data = array.array('B', self.channels())
        self.client.SendDmx(self.universe, data, DmxSent)
        self.wrapper.Run()
        self.i += 1


# Bind the socket to the port
server_address = (args.address, args.port)
logger.info('Starting UDP server')
sock.bind(server_address)
sock.settimeout(1./args.freq)

lighter = Lighter()

searching_preset = 0
searching_max = 0
searching_i0 = 0
searching_T = 0
presets_n = conf.get('presets_n', -1)
assert presets_n != -1, 'must define conf.presets_n'
def searching_dimmed(i):
    global searching_preset, searching_i0, searching_T
    searching_i0 = min(i, searching_i0)
    if i - searching_i0 > searching_T:
        searching_i0 = i
        searching_T = int((2 + random.random()) * args.freq)
        searching_preset = random.randint(0, presets_n - 1)
    i -= searching_i0
    channels = conf.getpreset(searching_preset)
    channels['intensity'] = min(20, i * 1)
    #print('%3d %3d %3d' % (channels['pan'], channels['tilt'], channels['intensity']))
    return channels

id_ = None
def statefunc(state, i):
    channels = [0] * len(CHANNELS)
    if state == 'start':
        # Started "a" -- full intensity after 4s.
        channels = conf.getpreset('wait')
        channels['intensity'] = min(255, channels['intensity'] + i*3)
        return channels
    elif state == 'search':
        # Finished "a", starting search.
        return searching_dimmed(i)
    elif state == 'wait':
        # Go back to shell.
        return conf.getpreset('wait')
    elif state == 'id':
        # Show flower.
        return conf.getpreset(id_)
    return channels

pos = 0
dpos = 1
state = 'wait'
t = i = 0
transitions = {
    'wait': ['start', 'search'],
    'start': ['search', 'wait'],
    'search': ['id'],
    'id': ['wait'],
}
while True:
    i += 1
    try:
        data, address = sock.recvfrom(4096)
    except socket.timeout:
        data = {}
    try:
        if data:
            data = json.loads(data)
    except JsonDecodeError as e:
        logger.warning('Could not decode "%r" : %s' % (data, e))
        continue

    if data:
        logger.info('Received : %r' % data)
    if 'channels' in data:
        lighter.setchannels(data['channels'])
        state = None
    elif 'state' in data:
        if state in transitions and data['state'] not in transitions[state]:
            logger.info('Ignoring invalid transition %s -> %s',
                    state, data['state'])
        elif state =='id' and i - t < args.freq * args.show_secs:
            logger.info('Ignoring invalid transition %s -> %s : %.1fs < %.1fs',
                    state, data['state'], (i - t)/args.freq, args.show_secs)
        else:
            state = data['state']
            if state == 'id':
                id_ = data['id']
            t = i

    if state == 'id' and i - t >= args.freq * args.show_secs:
        state = 'wait'
        logger.info('Auto-transitioning id -> wait')

    if state:
        lighter.setchannels(statefunc(state, i - t))
        if state in ('wait', 'start'):
            if data.get('overdrive'):
                logger.info('overdrive -> strobo')
                lighter['strobe'] = 255
            else:
                lighter['strobe'] = 0

    lighter.update()

