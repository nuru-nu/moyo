import argparse
import re

from smanmi import hotplug
from smanmi import midi
from smanmi import util

from . import settings


SOUND_RE = re.compile('^sound=(.*)')

parser = argparse.ArgumentParser(description='Bridges UDP to MIDI.')
parser.add_argument('--integrator_address', type=str, default='127.0.0.1',
                    help='Machine running `smanmi.integrator` script.')
args = parser.parse_args()
logger = util.createLogger('midi')

hp_midi = hotplug.HotPlug('.hotplug.midi', logger)


def signal2midi(data, logger):
    action = data.get('action')
    if not action:
        return ()
    m = SOUND_RE.match(action)
    if not m:
        return ()
    sound = m.group(1)
    notes = hp_midi.signal2midi(sound)
    if not notes:
        logger.info('Cannot translate sound: %s', sound)
    return notes


def midi2signal(command, logger):
    return hp_midi.midi2signal(command)


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
forwarder.signal2midis.add(signal2midi)
forwarder.midi2signals.add(midi2signal)
forwarder.start()
