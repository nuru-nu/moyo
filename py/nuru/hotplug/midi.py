from typing import Dict, Sequence, Tuple

from nurulib import midi
from .. import state


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
    if action == f'scene={state.STATE_SLEEP}':
        commands += onoff('C0')
    elif action == f'scene={state.STATE_WAKEUP}':
        commands += onoff('C#0')
    elif action == f'scene={state.STATE_AWAKE}':
        commands += onoff('D0')
    elif action == f'scene=angry':
        commands += onoff('D#0')
    elif action == f'scene=happy':
        commands += onoff('E0')
    elif action == 'scene=stop':
        commands += onoff('B2')

    elif action == 'charge=on':
        commands += on('C3', channel=2)
    elif action == 'charge=off':
        commands += off('C3', channel=2)
    elif action == 'growl=off':
        commands += onoff('C#3', channel=2)
    elif action == 'charge=down':
        commands += onoff('D3', channel=2)
    elif action == 'hi=on':
        commands += on('E3', channel=2)
    elif action == 'hi=off':
        commands += off('E3', channel=2)

    elif action == 'growl=happy':
        commands += onoff('E4', channel=3)
    elif action == 'growl=angry':
        commands += onoff('D4', channel=3)
    elif action == 'growl=hole':
        commands += onoff('E4', channel=3)
    elif action == 'sub=on':
        commands += on('C4', channel=3)
    elif action == 'sub=off':
        commands += off('C4', channel=3)
    arousal = data.get('arousal')
    if arousal is not None:
        value = int(arousal * 127)
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
    state.STATE_SLEEP,
    state.STATE_WAKEUP,
    state.STATE_AWAKE,
    'angry',
    'happy',
    'stop',
)
