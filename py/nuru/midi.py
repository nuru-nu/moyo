import argparse

from smanmi import midi
from smanmi import util

from . import settings


parser = argparse.ArgumentParser(description='Bridges UDP to MIDI.')
parser.add_argument('--integrator_address', type=str, default='127.0.0.1',
                    help='Machine running `smanmi.integrator` script.')
args = parser.parse_args()
logger = util.createLogger('midi')


def onoff(note, port=0):
    return (
        midi.Command.parse(f'{port}: {note} on'),
        midi.Command.parse(f'{port}: {note} off'),
    )


def signal2midi(data):
    action = data.get('action')
    if action and action.startswith('sound='):
        sound = action.split('=')[1]
        if sound == 'scene1':
            return onoff('C2')
        elif sound == 'scene2':
            return onoff('D2')
        elif sound == 'scene3':
            return onoff('E2')
        elif sound == 'scene4':
            return onoff('F2')
        elif sound == 'sirene':
            return onoff('G2')
        elif sound == 'head':
            return onoff('A2')
        elif sound == 'stop':
            return onoff('B2')
        else:
            logger.warning('Unknown sound: %s', sound)
    return ()


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
forwarder.register_signal2midi(signal2midi)
forwarder.start()
