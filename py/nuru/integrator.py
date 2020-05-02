import argparse
import asyncio
import collections
import time

from smanmi import hotplug
from smanmi import integrator
from smanmi import state
from smanmi import util
from . import settings


parser = argparse.ArgumentParser(description='Integrates signals for NURU.')
parser.add_argument(
    '--idle_fps', type=float, default=25,
    help='Minimum frequency to integrate at (in absence of audio signals).')
parser.add_argument(
    '--midi_address', type=str, default=settings.midi_address,
    help='Address of machine running `smanmi.midi` script.')
args = parser.parse_args()

logger = util.createLogger('integrator')
hp_signals = hotplug.HotPlug('.hotplug.signals', logger)


class Integrator:

    def __init__(self):
        self.server = integrator.IntegrationServer(
            logger,
            address=settings.address,
            sig_in_ports=(settings.integrator_sig_port,),
            sig_out_ports=(
                settings.server_sig_port,
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
            setstate={},
            sonar=1,
            state=state.State(),
            midi=None,
        )
        self.transients = {
            'midi': collections.deque(),
        }

    def start(self):
        self.schedule()
        self.server.start()

    def schedule(self):
        if hasattr(self, 'handle'):
            self.handle.cancel()
        self.handle = asyncio.get_event_loop().call_later(
            1 / args.idle_fps, self.integrate)

    def onsignal(self, signals):
        for name, queue in self.transients.items():
            if name in signals:
                queue.append(signals[name])
            else:
                self.signals[name] = signals[name]
        self.signals.update(signals)
        if 'logmel' in signals:
            self.integrate()

    def oncmd(self, cmd):
        if 'midi' in cmd:
            self.transients['midi'].append(cmd['midi'])

    def integrate(self):
        self.schedule()
        self.signals['t'] = time.time()
        signals = hp_signals.integrator_runner(**self.signals)
        for name, queue in self.transients.items():
            signals[name] = queue.pop() if queue else None
        self.server.send(signals)


Integrator().start()
