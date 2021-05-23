import argparse
import json
import os
import random
import traceback

from aiohttp import web
import numpy as np  # type: ignore

from openpixelcontrol import opc  # type: ignore
from smanmi import hotplug
from smanmi import perf
from smanmi.server import PeriodicCallback, Server, UdpForwarding, UdpEndpoint
from smanmi import util
from . import nca
from . import presets
from . import recording
from . import state
from . import settings


parser = argparse.ArgumentParser(
    description='Generates animation & web UI.')
parser.add_argument('--fps', type=int, default=60,
                    help='Frames per second for animation streaming.')
parser.add_argument('--fadecandy', action='store_true',
                    help='Whether to stream animations to fadecandy.')
parser.add_argument('--secondary', action='store_true',
                    help='Secondary server does not generate animations.')
parser.add_argument('--port', type=int, default=8080,
                    help='Port for HTTP server.')
parser.add_argument('--server_address', type=str, default='127.0.0.1',
                    help='Network address for HTTP server - can be 0.0.0.0.')
parser.add_argument('--integrator_address', type=str, default='127.0.0.1',
                    help='Address of machine running `smanmi.integrator`.')
parser.add_argument('--debug', action='store_true', help='Show debug logs.')
args = parser.parse_args()

if not args.secondary:
    # Avoid loading expensive frameworks if not needed.
    from . import animations

logger = util.createLogger('server', debug=args.debug)
hp_signals = hotplug.HotPlug('.hotplug.signals', logger)
_nca_names = presets.load()['ncas']

class Animator:

    def __init__(self, client, logger):
        self.client = client
        self.logger = logger
        self.hp_animations = hotplug.HotPlug(
            '.hotplug.animations', logger, autoreload=False)
        self.hp_midi = hotplug.HotPlug(
            '.hotplug.midi', logger, autoreload=False)
        self.signals = None
        self.stats = None
        self.subsample = 1
        self.i = 0
        self.faulty_mtime = None
        self.faulty_animation = None

    def received_from_udp(self, data):
        signals = util.deserialize(data)
        if self.signals is None:
            if not signals.get('_full'):
                return logger.info('Waiting for _full signals...')
            self.signals = {}
        self.signals.update(signals)

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
        if (self.faulty_mtime == self.hp_animations._reload_mtime and
            self.faulty_animation == self.signals.get('animation')):
            # Don't generate an exception every frame - wait for next reload.
            return
        try:
            data = self.hp_animations.pixels(**self.signals)
            assert data.shape == (1920, 3), f'Invalid shape: {data.shape}'
        except Exception as e:
            self.faulty_mtime = self.hp_animations._reload_mtime
            self.faulty_animation = self.signals.get('animation')
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
        return data.tobytes()


recordings = {
    rec.name: dict(
        secs=rec.secs,
        envelope=list(rec.envelope(min(200, rec.secs * 10))),
    )
    for rec in recording.get_recordings()
}


async def send_defs(request):
    del request
    data = dict(
        mapping=dict(
            phi_r=animations.phi_r_mapping,
            xyz=animations.xyz_mapping,
        ),
        colors=state.Rizhom.COLORS,
        recordings=recordings,
        animations=list(animator.hp_animations.animations.keys()),
        images=list(animator.hp_animations.images.keys()),
        presets=presets.load(),
        palettes=list(animator.hp_animations.palettes.keys()),
        scenes=animator.hp_midi.scenes,
        modes=hp_signals.modes,
        monitor_def=hp_signals.monitor_def,
    )
    return web.Response(
        content_type='Application/JSON',
        text=json.dumps(util.pythonize(data)))


async def send_recs(request):
    del request
    return web.Response(
        content_type='Application/JSON',
        text=json.dumps(recording.Recording.read_recs()),
        )


async def send_kinect(request):
    del request
    return web.Response(
        content_type='image/jpeg',
        body=open('tmp/kinect_frame.jpg', 'rb').read(),
    )


async def send_nca(request):
    # import pdb; pdb.set_trace()
    nca_path = os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        'nca',
    )
    name = request.query.get('name')
    if not name:
        name = _nca_names[random.randint(0, len(_nca_names))]
    models = nca.export_models_to_js({
        name: np.load(f'{nca_path}/{name}.npy', allow_pickle=True),
    })
    content = open(os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        os.pardir,
        'static',
        'ca.html'
    )).read().replace('__models__', json.dumps(models))
    return web.Response(
        content_type='text/html',
        body=content,
    )


client = None
if args.fadecandy:
    assert not args.secondary
    client = opc.Client('localhost:7890')
    assert client.can_connect()
    client.set_interpolation(False)

index_html = 'index2.html' if args.secondary else 'index.html'
server = Server(static_dir='static', logger=logger, index_html=index_html)
sig_port = settings.server2_sig_port if args.secondary else settings.server_sig_port
udp_forwarding = UdpForwarding(
    '/+signals',
    in_udp=UdpEndpoint(args.integrator_address, sig_port),
    out_udp=UdpEndpoint(args.integrator_address, settings.integrator_cmd_port),
)
server.forward_udp(udp_forwarding)
server.routes.append(web.get('/nca', send_nca))

if not args.secondary:
    server.routes.append(web.get('/defs', send_defs))
    animator = Animator(client, logger)
    animator.stats = server.stats
    udp_forwarding.with_callbacks(
        animator.received_from_udp,
        animator.received_from_ws,
    )
    server.run_periodically(
        PeriodicCallback('/+animation', animator, fps=args.fps))
    server.routes.append(web.get('/recs', send_recs))
    server.routes.append(web.get('/kinect', send_kinect))

server.run(address=args.server_address, port=args.port)
print(perf.stats())
