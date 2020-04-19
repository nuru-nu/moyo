import argparse

from smanmi import midi
from smanmi import util

from . import settings


parser = argparse.ArgumentParser(description='Bridges UDP to MIDI.')
parser.add_argument('--cmd_address', type=str, default='127.0.0.1',
                    help='IP address to listen at.')
parser.add_argument('--signal_address', type=str, default='127.0.0.1',
                    help='IP address to send UDP packets to.')
args = parser.parse_args()

logger = util.createLogger('midi')
forwarder = midi.MidiForwarder(
    midi=midi.Midi(logger),
    cmd_address_port=(args.cmd_address, settings.midi_cmd_port),
    signal_address_port=(args.signal_address, settings.integrator_sig_port),
    logger=logger,
)
forwarder.start()
