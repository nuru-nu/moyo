from typing import Dict, Sequence

from smanmi import midi


def onoff(note: str, channel: int = 1) -> Sequence[midi.Command]:
    return (
        midi.Command(f'{channel}: {note} on'),
        midi.Command(f'{channel}: {note} off'),
    )


def signal2midi(sound: str) -> Sequence[midi.Command]:
    if sound == 'scene=S1':
        return onoff('C2')
    elif sound == 'scene=S2':
        return onoff('C#2')
    elif sound == 'scene=S3':
        return onoff('D2')
    elif sound == 'scene=S4':
        return onoff('D#2')
    elif sound == 'scene=S5':
        return onoff('E2')
    elif sound == 'scene=S6':
        return onoff('F2')
    elif sound == 'scene=stop':
        return onoff('B2')
    return ()


def midi2signal(command: str) -> Sequence[Dict[str, str]]:
    # Heart
    for cmd in ('on', 'off'):
        for note in ('A', 'C', 'E', 'G#', 'C'):
            if command == midi.Command(f'2: {note}1 {cmd}'):
                return (dict(event=f'heart {cmd}'),)
    return ()


scenes = (
    'S1',
    'S2',
    'S3',
    'S4',
    'S5',
    'S6',
    'stop',
)
