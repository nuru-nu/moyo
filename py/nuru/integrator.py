import argparse

import numpy as np

from smanmi import hotplug
from smanmi import integrator
from smanmi import logic as L
from smanmi import state
from smanmi import util
from . import features
from . import settings


class Integrator(integrator.Integrator):

    def __init__(self, logger):
        super().__init__(
            logger, fps=0,
            address=settings.address,
            signalin_ports=[settings.signalin_port],
            signals_ports=[
                settings.server_port,
                settings.player_port,
                settings.player2_port,
                settings.dmx_port,
            ],
            recordings_path=settings.signalin_dir,
        )
        self.hp_signals = hotplug.HotPlug('.hotplug.signals', logger)
        self.state = state.State()
        self.signalin = {}
        self.signals = {}

    def integrate(self, signalin):
        if 'state' in signalin:
            self.state = state.State(signalin['state'])
        if 'signals' in signalin:
            signals = signalin.pop('signals')
            self.signals.update(signals)
            self.event.set()
        self.signalin.update(signalin)

    def compute(self):
        if not self.signals: return {}
        return self.hp_signals.integrator_runner(
            t=self.t, state=self.state, signalin=self.signalin, **self.signals)


logger = util.createLogger('integrator')
integrator = Integrator(logger)
integrator.start()

