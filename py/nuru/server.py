import argparse
import json
import traceback

from aiohttp import web
import numpy as np  # type: ignore

from openpixelcontrol import opc  # type: ignore
from smanmi import hotplug
from smanmi import perf
from smanmi.server import PeriodicCallback, Server, UdpForwarding, UdpEndpoint
from smanmi import util
from . import animations
from . import recording
from . import state
from . import settings


parser = argparse.ArgumentParser(
    description='Generates animation & web UI.')
parser.add_argument('--fps', type=int, default=60,
                    help='Frames per second for animation streaming.')
parser.add_argument('--fadecandy', action='store_true',
                    help='Whether to stream animations to fadecandy.')
parser.add_argument('--port', type=int, default=8080,
                    help='Port for HTTP server.')
parser.add_argument('--server_address', type=str, default='127.0.0.1',
                    help='Network address for HTTP server - can be 0.0.0.0.')
parser.add_argument('--integrator_address', type=str, default='127.0.0.1',
                    help='Address of machine running `smanmi.integrator`.')
args = parser.parse_args()


class Animator:

    def __init__(self, client, logger):
        self.client = client
        self.logger = logger
        self.hp_animations = hotplug.HotPlug(
            '.hotplug.animations', logger, autoreload=False)
        self.signals = None
        self.stats = None
        self.subsample = 1
        self.i = 0
        self.faulty_mtime = None

    def received_from_udp(self, data):
        self.signals = util.deserialize(data)

    def received_from_ws(self, data):
        signals = json.loads(data)
        if 'animator' in signals and 'subsample' in signals['animator']:
            self.subsample = signals['animator']['subsample']
            util.logger.info('Subsampling at %d', self.subsample)

    @perf.measure('Animator()')
    def __call__(self):
        self.i += 1
        if self.i % self.subsample != 0:
            return
        if self.signals is None:
            return

        self.hp_animations.hotplug_reload()
        if self.faulty_mtime == self.hp_animations._reload_mtime:
            # Don't generate an exception every frame - wait for next reload.
            return
        try:
            data = self.hp_animations.pixels(**self.signals)
        except Exception as e:
            self.faulty_mtime = self.hp_animations._reload_mtime
            self.logger.error('Animator() ERROR: %r', e)
            self.logger.warning(traceback.format_exc())
            self.logger.info('Waiting for next `hp_animations` reload.')
            return

        data = np.clip((255 * data).astype('uint8'), 0, 255)

        if self.client:
            fc_data = util.pad_fadecandy(data)
            ok = True
            for channel, i0 in enumerate(range(0, fc_data.shape[0], 512)):
                ok &= client.put_pixels(fc_data[i0: i0 + 512], channel + 1)
                if ok and self.stats:
                    self.stats('fc_animation', fc_data)
        return data.tostring()


recordings = {
    rec.name: dict(
        secs=rec.secs,
        envelope=list(rec.envelope(min(200, rec.secs * 10))),
    )
    for rec in recording.get_recordings()
}


async def send_defs(request):
    del request
    return web.Response(
        content_type='Application/JSON',
        text=json.dumps(util.pythonize(dict(
            mapping=dict(
                phi_r=animations.phi_r_mapping,
                xyz=animations.xyz_mapping,
            ),
            colors=state.Rizhom.COLORS,
            states=list(animator.hp_animations.states.keys()),
            recordings=recordings,
            animations=list(animator.hp_animations.animations.keys()),
        ))))


logger = util.createLogger('server')
hp_signals = hotplug.HotPlug('.hotplug.signals', logger)

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
    in_udp=UdpEndpoint(args.integrator_address, settings.server_sig_port),
    out_udp=UdpEndpoint(args.integrator_address, settings.integrator_cmd_port),
).with_callbacks(
    animator.received_from_udp,
    animator.received_from_ws,
))
server.run_periodically(
    PeriodicCallback('/+animation', animator, fps=args.fps))
server.routes.append(web.get('/defs', send_defs))
server.run(address=args.server_address, port=args.port)
print(perf.stats())
