import re
from typing import Dict, Sequence

from smanmi import midi


def onoff(note: str, channel: int = 1) -> Sequence[midi.Command]:
    return (
        midi.Command(f'{channel}: {note} on'),
        midi.Command(f'{channel}: {note} off'),
    )


def off(note: str, channel: int = 1) -> Sequence[midi.Command]:
    return (
        midi.Command(f'{channel}: {note} off'),
    )


def on(note: str, channel: int = 1) -> Sequence[midi.Command]:
    return (
        midi.Command(f'{channel}: {note} on'),
    )


def signal2midi(action: str) -> Sequence[midi.Command]:
    if action == 'scene=S1':
        return onoff('C2')
    elif action == 'scene=S2':
        return onoff('C#2')
    elif action == 'scene=S3':
        return onoff('D2')
    elif action == 'scene=S4':
        return onoff('D#2')
    elif action == 'scene=S5':
        return onoff('E2')
    elif action == 'scene=S6':
        return onoff('F2')
    elif action == 'scene=stop':
        return onoff('B2')
    elif action == 'charge=on':
        return on('C3', channel=2)
    elif action == 'charge=off':
        return off('C3', channel=2)
    return ()


def midi2signal(command: str) -> Sequence[Dict[str, str]]:
    # Heart
    for cmd in ('on', 'off'):
        for note in ('A', 'C', 'D#', 'E', 'G#', 'C'):
            if command == midi.Command(f'1: {note}1 {cmd}'):
                return (dict(event=f'heart {cmd}'),)
            if command == midi.Command(f'1: {note}3 {cmd}'):
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
