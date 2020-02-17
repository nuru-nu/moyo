from smanmi import hotplug
from smanmi import integrator
from smanmi import state
from smanmi import util
from . import settings


class Integrator(integrator.Integrator):

    def __init__(self, logger):
        super().__init__(
            logger, fps=20,
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
        self.signalin = {}
        self.signals = dict(
            state=state.State(),
            rawloud=0.,
            iso=0.,
        )

    def integrate(self, signalin):
        if 'state' in signalin:
            self.state = state.State(signalin['state'])
        if 'signals' in signalin:
            signals = signalin.pop('signals')
            self.signals.update(signals)
            self.event.set()
        self.signalin.update(signalin)

    def compute(self):
        if not self.signals:
            return {}
        return self.hp_signals.integrator_runner(
            t=self.t, signalin=self.signalin, **self.signals)


logger = util.createLogger('integrator')
integrator = Integrator(logger)
integrator.start()
