import argparse
import asyncio
import collections
import re
import time
import traceback

from smanmi import hotplug
from smanmi import integrator
from smanmi import util
from . import recording
from . import settings
from . import state

import functiontrace


parser = argparse.ArgumentParser(description='Integrates signals for NURU.')
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
        self.signals = hp_signals.defaults
        self.signals['t'] = time.time()
        self.transients = {
            name: collections.deque()
            for name in hp_signals.transients
        }
        self.rec_play = self.rec_ongoing = self.rec_t = None
        self.rec_enabled = set()

    def start(self):
        self.schedule()
        self.server.start()

    def schedule(self):
        if hasattr(self, 'handle'):
            self.handle.cancel()  # pylint: disable=access-member-before-definition
        self.handle = asyncio.get_event_loop().call_later(
            1 / settings.integrator_fps, util.print_exc(self.integrate))

    def onsignal(self, signals, playback=False):
        if self.rec_play:
            if playback:
                signals = {
                    key: value for key, value in signals.items()
                    if key in self.rec_enabled
                }
                if not signals: return
            else:
                signals = {
                    key: value for key, value in signals.items()
                    if key not in self.rec_enabled
                }
                if not signals: return
        if self.rec_ongoing:
            assert not self.rec_play
            self.rec_ongoing.write(signals, hp_signals.transients)

        for name, value in signals.items():
            if name in self.transients:
                if len(self.transients[name]) > 5:
                    logger.warning('Ignoring transient: %s', name)
                    continue
                self.transients[name].append(value)
            else:
                self.signals[name] = value
        self.signals.update(signals)
        # if not self.rec_play:
        #     # Note: Only use fixed FPS during playback to avoid doubling
        #     # frequency when mixing data from sensor/recording.
        #     self.integrate()

    def oncmd(self, cmd):
        if cmd.get('action') == 'trace':
            functiontrace.trace()
            return
        rec_action = cmd.get('rec_action')
        if rec_action:
            self.handle_rec_action(rec_action)
            return
        self.onsignal(cmd)  # loop back commands into signals

    def integrate(self):
        self.schedule()
        dt = time.time() - self.signals['t']
        self.signals['t'] += dt
        signals = dict(**self.signals)
        for name, queue in self.transients.items():
            signals[name] = queue.popleft() if queue else None
        signals = hp_signals.integrator_runner(**signals)
        for name, value in signals.items():
            if name in hp_signals.transient_loops and value is not None:
                transient = hp_signals.transient_loops[name]
                self.transients[transient] += value
        if self.rec_ongoing:
            signals['rec_state'] = dict(start=self.rec_ongoing.info['start'])
        if self.rec_play:
            self.rec_t += dt
            signals['rec_state'] = dict(
                play=self.rec_play.info['id'],
                enabled=sorted(list(self.rec_enabled)),
                t=self.rec_t,
                )
        self.server.send(signals)

    def handle_rec_action(self, rec_action):
        if rec_action == 'start':
            self.rec_ongoing = recording.Recording.create()
            logger.info('Started recording: %s', self.rec_ongoing)
        if rec_action == 'stop':
            if self.rec_ongoing:
                logger.info('Stopping recording: %s', self.rec_ongoing)
                self.rec_ongoing.close()
                self.rec_ongoing = None
            elif self.rec_play:
                self.rec_play = None
            else:
                logger.warn('Ignoring rec_action=stop')
        m = re.match(r'^play=(.*)', rec_action)
        if m:
            self.rec_play = recording.Recording.load(m.group(1))
            if not self.rec_play:
                logger.error('Could not load %s', m.group(1))
            else:
                self.rec_t = self.rec_play.info['start']
                self.rec_schedule(self.rec_play.next())
                self.rec_enabled = self.rec_enabled.intersection(
                    self.rec_play.info['signals'])
        m = re.match(r'^toggle=(.*)', rec_action)
        if m:
            if m.group(1) in self.rec_enabled:
                self.rec_enabled.remove(m.group(1))
            else:
                self.rec_enabled.add(m.group(1))
        m = re.match(r'^t=(.*)', rec_action)
        if self.rec_play and m:
            t = self.rec_t = float(m.group(1))
            self.rec_play.seek(t)
            self.rec_schedule(self.rec_play.next())
        current = self.rec_ongoing or self.rec_play
        if current:
            for which in ('name', 'comments'):
                m = re.match(rf'^{which}=(.*)', rec_action)
                if m:
                    current.info[which] = m.group(1)
                    current.saveinfo()

    def rec_schedule(self, signals):
        def scheduled():
            if not self.rec_play:
                return
            next_signals = signals
            while next_signals['t'] <= self.rec_t:
                self.onsignal(next_signals, playback=True)
                try:
                    next_signals = self.rec_play.next()
                except StopIteration:
                    self.rec_play.restart()
                    next_signals = self.rec_play.next()
                    self.rec_t = next_signals['t']
            self.rec_schedule(next_signals)
        dt = max(0, signals['t'] - self.rec_t)
        if hasattr(self, 'rec_handle'):
            self.rec_handle.cancel()  # pylint: disable=access-member-before-definition
        self.rec_handle = asyncio.get_event_loop().call_later(
            dt, util.print_exc(scheduled))


Integrator().start()
