from typing import Dict, Sequence

from smanmi import midi


def onoff(note: str, port: int = 0) -> Sequence[midi.Note]:
    return (
        midi.Command.parse(f'{port}: {note} on'),
        midi.Command.parse(f'{port}: {note} off'),
    )


def signal2midi(sound: str) -> Sequence[midi.Note]:
    if sound == 'S1':
        return onoff('C2')
    elif sound == 'S2':
        return onoff('C#2')
    elif sound == 'S3':
        return onoff('D2')
    elif sound == 'S4':
        return onoff('D#2')
    elif sound == 'S5':
        return onoff('E2')
    elif sound == 'S6':
        return onoff('F2')
    elif sound == 'sirene':
        return onoff('G2')
    elif sound == 'head':
        return onoff('A2')
    elif sound == 'stop':
        return onoff('B2')
    return ()


def midi2signal(command: str) -> Sequence[Dict[str, str]]:
    # Heart
    for cmd in ('on', 'off'):
        for note in ('A', 'C', 'E', 'G#', 'C'):
            if command == midi.Command.parse(f'0: {note}1 {cmd}'):
                return (dict(event=f'heart {cmd}'),)
    return ()
