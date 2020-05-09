import argparse

from smanmi import midi
from smanmi import util

from . import settings


parser = argparse.ArgumentParser(description='Bridges UDP to MIDI.')
parser.add_argument('--integrator_address', type=str, default='127.0.0.1',
                    help='Machine running `smanmi.integrator` script.')
args = parser.parse_args()

logger = util.createLogger('midi')
cmd_address = args.integrator_address
if cmd_address != '127.0.0.1':
    cmd_address = '0.0.0.0'
forwarder = midi.MidiForwarder(
    midi=midi.Midi(logger),
    cmd_address_port=(cmd_address, settings.midi_cmd_port),
    signal_address_port=(
        args.integrator_address, settings.integrator_sig_port),
    logger=logger,
)
forwarder.start()
