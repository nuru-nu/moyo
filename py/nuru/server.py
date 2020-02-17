import argparse
import json

from aiohttp import web
import numpy as np

from openpixelcontrol import opc
from smanmi import hotplug
from smanmi.server import PeriodicCallback, Server, UdpForwarding, UdpEndpoint
from smanmi import state
from smanmi import util
from . import animations
from . import settings


parser = argparse.ArgumentParser(
    description='Generates animation & web UI.')
parser.add_argument('--fps', type=int, default=60,
                    help='Frames per second for animation streaming.')
parser.add_argument('--fadecandy', action='store_true',
                    help='Whether to stream animations to fadecandy.')
args = parser.parse_args()


class Animator:

    def __init__(self, client, logger):
        self.client = client
        self.hp_animations = hotplug.HotPlug('.hotplug.animations', logger)
        self.signals = None
        self.stats = None

    def received_signals(self, data):
        self.signals = json.loads(data.decode('utf8'))
        if 'state' in self.signals:
            self.signals['state'] = state.State(self.signals['state'])

    def __call__(self):
        if self.signals is None:
            return
        data = self.hp_animations.pixels(**self.signals)['value']
        data = np.clip((255 * data).astype('uint8'), 0, 255)

        if self.client:
            fc_data = util.pad_fadecandy(data)
            ok = True
            for channel, i0 in enumerate(range(0, fc_data.shape[0], 512)):
                ok &= client.put_pixels(fc_data[i0: i0 + 512], channel + 1)
                if ok and self.stats:
                    self.stats('fc_animation', fc_data)
        return data.tostring()


async def send_mapping(request, digits=5):
    del request
    return web.Response(
        content_type='Application/JSON',
        text='[{}]'.format(','.join([
            '[{},{}]'.format(str(phi)[:digits + 2], str(r)[:digits + 2])
            for phi, r in animations.phi_r_mapping
        ])))


logger = util.createLogger('server')

client = None
if args.fadecandy:
    client = opc.Client('localhost:7890')
    assert client.can_connect()
    client.set_interpolation(False)
animator = Animator(client, logger)

server = Server(static_dir='static', logger=logger)
animator.stats = server.stats
server.forward_udp(UdpForwarding(
    '/+signals',
    in_udp=UdpEndpoint('127.0.0.1', settings.server_port),
    out_udp=UdpEndpoint('127.0.0.1', settings.signalin_port),
).with_callbacks(animator.received_signals))
server.run_periodically(
    PeriodicCallback('/+animation', animator, fps=args.fps))
server.routes.append(web.get('/mapping', send_mapping))
server.run(address=settings.server_address)
