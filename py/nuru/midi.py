import argparse

from smanmi import midi
from smanmi import util

from . import settings


parser = argparse.ArgumentParser(description='Bridges UDP to MIDI.')
parser.add_argument('--address', type=str, default='127.0.0.1',
                    help='IP address to listen at.')
args = parser.parse_args()

logger = util.createLogger('midi')
forwarder = midi.MidiForwarder(
    address=args.address,
    cmd_port=settings.midi_cmd_port,
    logger=logger,
    midi_name=settings.midi_name,
)
forwarder.start()
