from smanmi import hotplug
from smanmi import integrator
from smanmi import logic as L
from smanmi import state
from smanmi import util
from . import settings


class Integrator(integrator.Integrator):

    def __init__(self, logger):
        super().__init__(
            logger, fps=20,
            address=settings.address,
            sig_in_ports=(settings.integrator_sig_port,),
            sig_out_ports=(
                settings.server_sig_port,
                settings.player_sig_port,
                settings.player2_sig_port,
                settings.dmx_sig_port,
                settings.midi_sig_port,
            ),
            cmd_in_ports=(settings.integrator_cmd_port,),
            cmd_out_ports=(
                settings.recorder_cmd_port,
                settings.sonar_cmd_port,
                settings.cmd_cmd_port,
                settings.midi_cmd_port,
            ),
        )
        self.hp_signals = hotplug.HotPlug('.hotplug.signals', logger)
        self.signalin = {}
        self.signals = dict(
            state=state.State(),
            rawloud=0.,
            iso=0.,
        )
        self.last_missing = None

    def __call__(self):
        try:
            signals = self.hp_signals.integrator_runner(**self.signals)
            if self.last_missing:
                self.logger.info('Got complete signals')
            self.last_missing = None
            return signals
        except L.MissingInputsException as e:
            e = str(e)
            if self.last_missing != e:
                self.logger.warning('Incomplete signals : %s', e)
            self.last_missing = e
            return {}


logger = util.createLogger('integrator')
integrator = Integrator(logger)
integrator.start()
