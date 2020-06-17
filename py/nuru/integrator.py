import argparse
import asyncio
import collections
import time

from smanmi import hotplug
from smanmi import integrator
from smanmi import util
from . import settings
from . import state


parser = argparse.ArgumentParser(description='Integrates signals for NURU.')
parser.add_argument(
    '--idle_fps', type=float, default=25,
    help='Minimum frequency to integrate at (in absence of audio signals).')
parser.add_argument(
    '--midi_address', type=str, default='127.0.0.1',
    help='Address of machine running `smanmi.midi` script.')
parser.add_argument(
    '--server_address', type=str, default='127.0.0.1',
    help='Address of machine running `smanmi.server` script.')
args = parser.parse_args()

logger = util.createLogger('integrator')
hp_signals = hotplug.HotPlug('.hotplug.signals', logger)


class Integrator:

    def __init__(self):
        self.server = integrator.IntegrationServer(
            logger,
            sig_in_ports=(
                ('0.0.0.0', settings.integrator_sig_port),
            ),
            sig_out_ports=(
                (args.server_address, settings.server_sig_port),
                settings.player_sig_port,
                settings.player2_sig_port,
                settings.dmx_sig_port,
                (args.midi_address, settings.midi_sig_port),
            ),
            cmd_in_ports=(settings.integrator_cmd_port,),
            cmd_out_ports=(
                settings.recorder_cmd_port,
                settings.sonar_cmd_port,
                settings.cmd_cmd_port,
                (args.midi_address, settings.midi_cmd_port),
            ),
        )
        self.server.onsignal(self.onsignal)
        self.server.oncmd(self.oncmd)
        self.signals = dict(
            t=0,
            iso=0,
            rawloud=0,
            loud=0,
            sonar=1,
            state=state.State(),
            setstate={},
            target_css=None,
            fc=0,
        )
        self.overrides = {}
        self.transients = {
            name: collections.deque()
            for name in ('midi', 'action')
        }

    def start(self):
        self.schedule()
        self.server.start()

    def schedule(self):
        if hasattr(self, 'handle'):
            self.handle.cancel()  # pylint: disable=access-member-before-definition
        self.handle = asyncio.get_event_loop().call_later(
            1 / args.idle_fps, self.integrate)

    def onsignal(self, signals):
        for name, value in signals.items():
            if name in self.transients:
                self.transients[name].append(value)
            else:
                self.signals[name] = value
        self.signals.update(signals)
        if 'logmel' in signals:
            self.integrate()

    def override(self, name, value):
        self.overrides[name] = value
        if value is None:
            del self.overrides[name]

    def oncmd(self, cmd):
        self.onsignal(cmd)  # loop back commands into signals
        if 'setstate' in cmd:
            self.signals['setstate'] = cmd['setstate']
        if 'fc' in cmd:
            self.signals['fc'] = cmd['fc']
        if 'sonar' in cmd:
            self.override('sonar', cmd['sonar'])
        if 'target_css' in cmd:
            self.override('target_css', cmd['target_css'])

    def integrate(self):
        self.schedule()
        self.signals['t'] = time.time()
        signals = dict(**self.signals)
        for name, queue in self.transients.items():
            signals[name] = queue.popleft() if queue else None
        signals = hp_signals.integrator_runner(**{
            name: self.overrides.get(name, value)
            for name, value in signals.items()
        })
        self.server.send(signals)


Integrator().start()
