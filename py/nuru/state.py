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
    """Continuous State Space (-1..+1)."""

    def init(self, alpha=10, beta=200, gamma=100):
        """Time constants for target (alpha) and zero (beta)."""
        self.valence = self.valence0 = 0
        self.arousal = self.arousal0 = -0.9

    def call(self, target_css, randval, closest, n_people):
        # Reversal to the mean.
        self.valence -= (self.valence - self.valence0) / self.beta
        self.arousal -= (self.arousal - self.arousal0) / self.beta
        # Moodswings.
        self.valence += 2 * (randval - 0.5) / self.gamma
        if target_css:
            valence, arousal = target_css
            self.valence += (valence - self.valence) / self.alpha
            self.arousal += (arousal - self.arousal) / self.alpha
        else:
            # Kinect -> arousal.
            self.arousal = self.arousal0 + closest * (1 - self.arousal0)
        return [
            self.valence,
            self.arousal,
        ]


class CssAction(L.Signal):
    """Emits CSS related actions."""

    def init(self, threshold):
        pass

    def call(self, css, scene):
        if scene == 'S1' and css[1] > self.threshold:
            return ['scene=S3', 'animation=S3']
        if scene == 'S3' and css[1] < self.threshold:
            return ['scene=S1', 'animation=S1']
        return []


class SonarAction(L.Signal):
    """Emits sonar related actions."""

    def init(self, threshold=0.5):
        self.on = False

    def call(self, sonar):
        if sonar is not None:
            if sonar < self.threshold and not self.on:
                self.on = True
                return ['growl=on']
            if sonar > self.threshold and self.on:
                self.on = False
                return ['growl=off']
        return []

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

    def call(self, t, state, into, ooo_intensity, action):
        oldstate = state.state
        dt = t - self.last_change

        if action:
            if action.startswith('color='):
                state.color = action.split('=')[1]
            if action.startswith('state='):
                state.state = action.split('=')[1]
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
