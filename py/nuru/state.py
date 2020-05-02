import random

from smanmi import logic as L
from smanmi import util


@util.register_serializer('state')
class State:
    """For (de)serializing S.State."""

    def __init__(self, serialized=''):
        parts = {}
        if serialized.startswith('State(') and serialized.endswith(')'):
            parts = dict([
                part.split('=')
                for part in serialized[6:-1].split(',')
                if part
            ])
        self.playing = parts.get('playing')
        self.state = parts.get('state', 'std')
        self.color = parts.get('color', 'brownish')
        self.rnd = parts.get('rnd', 0)

    def goto(self, state):
        """Sets a new state."""
        self.state = state

    def play(self, what):
        """Stops if `what=None`."""
        self.playing = what

    def __repr__(self):
        parts = [
            '{}={}'.format(k, v)
            for k, v in dict(
                playing=self.playing,
                state=self.state,
                color=self.color,
                rnd=self.rnd,
            ).items()
            if v is not None
        ]
        return 'State({})'.format(','.join(parts))


class Css(L.Signal):
    """Continuous State Space."""

    def init(self, alpha: float = 10):
        self.valence = self.arousal = 0

    def call(self, valence_target, arousal_target):
        self.valence += (valence_target - self.valence) / self.alpha
        self.arousal += (arousal_target - self.arousal) / self.alpha
        return dict(
            valence=self.valence,
            arousal=self.arousal,
        )


class Rizhom(L.Signal):
    """Updates the state, Rizhom-style."""

    COLORS = (
        'brownish_palette',
        'coolors_rainbow',
        'just_greens',
        'blue_purple',
        'funny_rainbow',
        'barbie',
        'purple_haze',
        'red_death',
        'gabe_red',
        'super_red',
        'ultra_rainbows',
        'earth_life',
    )

    STATES = (
        'std', 'std2', 'into', 'ooo', 'flash', 'test',
    )

    def init(self):
        self.last_change = 0

    def call(self, t, state, into, ooo_intensity, setstate):
        oldstate = state.state
        dt = t - self.last_change

        if setstate.get('color'):
            state.color = setstate['color']
        if setstate.get('state'):
            state.state = setstate['state']
            return state

        if not state.state.startswith('std') and not into:
            state.goto(random.choice(['std', 'std2']))
            state.rnd = random.choice(range(10))
            state.color = random.choice(self.COLORS)
        elif state.state == 'test':
            return state
        elif state.state.startswith('std') and into:
            state.goto('into')
        elif state.state == 'into' and dt > 2:
            state.goto('ooo')
        # elif state.state == 'ooo' and ooo_intensity == 1.0:
        #     state.state = 'flash'
        elif state.state == 'flash' and t - self.last_change > 10:
            state.state = 'std'

        if oldstate != state.state:
            self.last_change = t

        return state
