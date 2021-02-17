from typing import Dict, Sequence, Tuple

from smanmi import midi


def onoff(note: str, channel: int = 1) -> Tuple[midi.Command]:
    return (
        midi.Command(f'{channel}: {note} on'),
        midi.Command(f'{channel}: {note} off'),
    )


def off(note: str, channel: int = 1) -> Tuple[midi.Command]:
    return (
        midi.Command(f'{channel}: {note} off'),
    )


def on(note: str, channel: int = 1) -> Tuple[midi.Command]:
    return (
        midi.Command(f'{channel}: {note} on'),
    )


_last_value = 0


def signal2midi(data) -> Sequence[midi.Command]:
    global _last_signals
    action = data.get('action')
    commands: Tuple[midi.Command] = ()
    if action == 'scene=S1':
        commands += onoff('C2')
    elif action == 'scene=S2':
        commands += onoff('C#2')
    elif action == 'scene=S3':
        commands += onoff('D2')
    elif action == 'scene=S4':
        commands += onoff('D#2')
    elif action == 'scene=S5':
        commands += onoff('E2')
    elif action == 'scene=S6':
        commands += onoff('F2')
    elif action == 'scene=stop':
        commands += onoff('B2')
    elif action == 'charge=on':
        commands += on('C3', channel=2)
    elif action == 'charge=off':
        commands += off('C3', channel=2)
    closest = data.get('closest')
    if closest is not None:
        value = int(closest * 127)
        global _last_value
        if value != _last_value:
            _last_value = value
            commands += (midi.Command(f'1: X1={value}'),)
    return commands


def midi2signal(command: str) -> Sequence[Dict[str, str]]:
    # Heart
    for cmd in ('on', 'off'):
        note = 'C'
        event = 'heart'
        if command == midi.Command(f'1: {note}1 {cmd}'):
            return (dict(event=f'{event} {cmd}'),)
        if command == midi.Command(f'1: {note}3 {cmd}'):
            return (dict(event=f'{event} {cmd}'),)
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
