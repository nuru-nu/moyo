import argparse
import re

from smanmi import hotplug
from smanmi import midi
from smanmi import util

from . import settings


parser = argparse.ArgumentParser(description='Bridges UDP to MIDI.')
parser.add_argument('--integrator_address', type=str, default='127.0.0.1',
                    help='Machine running `smanmi.integrator` script.')
parser.add_argument('--ignore', type=str, default='1: X1,3: C3',
                    help='Do not show events for these notes.')
args = parser.parse_args()
logger = util.createLogger('midi')

hp_midi = hotplug.HotPlug('.hotplug.midi', logger)


def signal2midi(data, logger):
    # This is additional to the default nuru.midi.signal2midi().
    return hp_midi.signal2midi(data)


def midi2signal(command, logger):
    return hp_midi.midi2signal(command)


cmd_address = args.integrator_address
if cmd_address != '127.0.0.1':
    cmd_address = '0.0.0.0'
forwarder = midi.MidiForwarder(
    midi=midi.Midi(logger, ignore=args.ignore),
    signal_in=(cmd_address, settings.midi_sig_port),
    signal_out=(args.integrator_address, settings.integrator_sig_port),
    logger=logger,
    ignore=args.ignore.split(','),
)
forwarder.signal2midis.add(signal2midi)
forwarder.midi2signals.add(midi2signal)
forwarder.start()
