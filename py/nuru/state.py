"""State-machine related code.

There are currently two ways of implementing a state machine:

1. Use `State` class to (de) serialize the entire state and then have a state
   generator like `Rizhom` to update it.
2. Split state into normal independent signals and then use looped transient
   actions to update these state signals, like `CssAction`.
"""
import json
import glob
import os
import random
import time

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

    alpha: float
    beta: float
    gamma: float

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
            # -1 .. +1
            self.valence,
            # -1 .. +1
            self.arousal,
        ]


class CssAction(L.Signal):
    """Emits CSS related actions."""

    threshold: float

    def init(self, threshold: float):
        pass

    def call(self, mode, css, scene):
        if mode == 'css':
            if scene == 'S1' and css[1] > self.threshold:
                return ['scene=S3', 'animation=S3']
            if scene == 'S3' and css[1] < self.threshold:
                return ['scene=S1', 'animation=S1']
        return []


class NcaAction(L.Signal):
    """Manages NCA related state."""

    def init(self, timeouts_secs=3*60):
        self.json = json.load(open(os.path.join(
            os.path.dirname(__file__), 'nca.json'
        )))
        nca_glob = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir,
            os.path.pardir,
            'nca',
            f'*.npy',
        )
        print('nca_glob', nca_glob)
        self.names = [
            path.split('/')[-1][:-4] for path in glob.glob(nca_glob)]
        self.t = time.time()

    def call(self, mode, t, action):
        nca_actions = []
        if action == 'nca=next':
            self.t = 0
        if t - self.t > self.timeouts_secs and mode == 'rnca':
            name = self.names[random.randint(0, len(self.names))]
            nca_actions.append(f'nca=set={name}')
            self.t = t
        return nca_actions


class SonarAction(L.Signal):
    """Emits sonar related actions."""

    threshold: float

    def init(self, threshold=0.5):
        self.on = False
        self.lastanim = None

    def call(self, sonar, animation):
        if sonar is not None:
            if sonar > self.threshold and not self.on:
                self.on = True
                self.lastanim = animation
                return ['charge=on', 'animation=charge']
            if sonar < self.threshold and self.on:
                self.on = False
                return ['charge=off', f'animation={self.lastanim}']
        return []


STATE_SLEEP = 'sleep'
STATE_WAKEUP = 'wakeup'
STATE_AWAKE = 'awake'


class SimpleStateAction(L.Signal):
    """First trial at a state that is split between sigs & actions."""

    def init(self):
        ...

    def call(self, mode, state, pir, closest, wakeup, active):
        actions = []
        if mode != 'simple':
            return actions
        if state == STATE_SLEEP:
            if pir > 0 or closest > 0:
                actions.append(f'state={STATE_WAKEUP}')
                actions.append(f'animation={STATE_WAKEUP}')
        if state == STATE_WAKEUP:
            if wakeup == 1:
                actions.append(f'state={STATE_AWAKE}')
                actions.append(f'animation={STATE_AWAKE}')
        if state == STATE_AWAKE:
            if active == 0 and pir == 0:
                actions.append(f'state={STATE_SLEEP}')
                actions.append(f'animation={STATE_SLEEP}')
        return actions


class Reservoir(L.Signal):
    """When in `state` then starts at `start` and moves by `diff`."""

    def init(self, state, start, diff):
        self.value = 0
        self.lt = None

    def call(self, t, state):
        if state == self.state:
            if self.lt is None:
                self.lt = t
                self.value = self.start
            dt = t - self.lt
            self.lt = t
            self.value += self.diff * dt
        else:
            self.lt = None
        self.value = min(1, max(0, self.value))
        return self.value


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
