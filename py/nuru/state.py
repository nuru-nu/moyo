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

import numpy as np

from smanmi import logic as L
from smanmi import util

from . import presets


# See individual states for exact definition.
STATE_SLEEP = 'sleep'
STATE_WAKEUP = 'wakeup'
STATE_AWAKE = 'awake'
STATE_ANGRY = 'angry'
STATE_OK = 'ok'
STATE_HAPPY = 'happy'

_presets = presets.load()


class One(L.Signal):
    """State Version One (KOSMOS).

    States:
    - sleep:
    - wakeup
    - awake
    - angry
    - happy

    Transitions:
    - sleep->wakeup
    - wakeup->awake
    - awake->angry
    - angry->awake
    - ok->happy
    - happy->awake

    Attributes:
    - valency: -1..+1
    - arousal: -1..+1
    - state: string (from module's STATE_*)
    - valency_attractors
    - overwrites: changed signals incl. actions
    """

    sleep_next: float
    awake_next: float
    wakeup_duration: float
    asleep_duration: float

    def init(self,
            r_z2,
            # How frequently to cycle animations.
            sleep_next=180, awake_next=180,
            # Transition times.
            wakeup_duration=5, asleep_duration=300,
        ):
        self.valency = 0
        self.arousal = -1
        self.state = STATE_SLEEP
        self.timer = sleep_next
        self.sleep_ncas = [
            "konfetti_sleep",
            "blue_sleep",
        ]
        self.awake_ncas = [
            "holz",
            "flow_calm",
            "spiral_underwater",
        ]
        self.presets = {
            preset['name']: preset
            for preset in _presets['animations']
        }
        for name in self.sleep_ncas + self.awake_ncas:
            assert name in self.presets, name

    def next_nca(self, which, overwrites):
        overwrites['action'].append('animation=nca')
        ncas = getattr(self, f'{which}_ncas')
        preset = self.presets[np.random.choice(ncas)]
        overwrites.update({k: v for k, v in preset['signals'].items()})
        print(f'One next {which} preset={preset}')

    def call(self, mode, action, dt, closest, pir, people, likes):
        if mode != 'one':
            return None
        valency_attractors, overwrites = [], {'action': []}

        self.timer = max(0, self.timer - dt)

        if self.state == STATE_SLEEP:
            if self.timer <= 0 or action == 'one=next':
                self.next_nca('sleep', overwrites)
                self.timer = self.sleep_next

            if pir or closest:
                self.state = STATE_WAKEUP
                print('One pir/closest -> wakeup')

        elif self.state == STATE_WAKEUP:
            self.arousal += dt / self.wakeup_duration
            if self.arousal >= .1:
                self.state = STATE_AWAKE
                self.timer = self.awake_next

        elif self.state == STATE_AWAKE:
            if self.timer <= 0 or action == 'one=next':
                self.next_nca('awake', overwrites)
                self.timer = self.sleep_next

            if pir or closest:
                self.arousal = closest
            else:
                self.arousal = -dt / self.asleep_duration

            if people:
                closest = sorted(
                    people,
                    key=lambda person: np.linalg.norm(person['cm'][:2]),
                )[0]
                like = likes.get(str(closest['id']), 0)
                overwrites['anim_into'] = 1 * (like > 1)

            if self.valency < -0.25:
                self.state = STATE_ANGRY
                print('One getting angry')
                overwrites['action'].append('animation=angry')
            elif self.valency > 0.25:
                self.state = STATE_HAPPY
                print('One getting happy')
                overwrites['action'].append('animation=happy')

            if self.arousal < -0.9:
                self.state = STATE_SLEEP
                self.timer = self.sleep_next

        elif self.state == STATE_ANGRY:
            if self.valency > -0.25:
                self.state = STATE_AWAKE
                self.timer = 0

        elif self.state == STATE_HAPPY:
            if self.valency < 0.25:
                self.state = STATE_AWAKE
                self.timer = 0

        for person in people:
            dist = np.linalg.norm(person['cm'][:2])
            if dist < self.r_z2:
                like = likes.get(str(person['id']), 0)
                if like > 1:
                    valency_attractors.append([1.5, .4])
                else:
                    valency_attractors.append([-0.4, 1])
                    self.arousal = max(0, self.arousal)

        dvdt = 0
        valency_attractors.append([0, .2])
        for target, alpha in valency_attractors:
            dvdt += (target - self.valency) * alpha
        self.valency += dt * dvdt

        overwrites['css'] = [
            max(-1, min(1, self.valency)),
            max(-1, min(1, self.arousal)),
        ]
        return dict(
            state=self.state,
            timer=self.timer,
            valency=self.valency,
            arousal=self.arousal,
            valency_attractors=valency_attractors,
            overwrites=overwrites,
        )


class ArtificialHeart(L.Signal):
    """Simulates Ableton heart if `on`."""

    def init(self, on, freq, duration=0.3):
        self.lt = 0
        self.state = 0

    def call(self, t):
        if not self.lt:
            self.lt = t
        if self.on:
            dt = t - self.lt
            if dt > 1 / self.freq + self.duration:
                self.state = 0
                self.lt = t + self.duration
                return ['heart off']
            elif dt > 1 / self.freq:
                if self.state == 0:
                    self.state = 1
                    return ['heart on']
        return []


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
        self.lt = None

    def call(self, t, target_css, randval, closest, mvmt):

        # stay angry
        if self.lt:
            if t - self.lt < 20:
                return [self.valence, self.arousal]
            self.lt = None

        # Reversal to the mean.
        self.valence -= (self.valence - self.valence0) / self.beta
        self.arousal -= (self.arousal - self.arousal0) / self.beta

        # Random moodswings.
        # self.valence += 2 * (randval - 0.5) / self.gamma

        # Getting angry...
        if mvmt > 0.8:
            self.valence += (-1 - self.valence) * .9 ** 20
            if self.valence < -0.8:
                self.lt = t

        # Getting interested.
        if mvmt < 0.1 and closest > 0.6:
            self.valence = min(1, self.valence + 1 / 20 / 10)

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
        if mode == 'simple':
            if scene != 'angry' and css[0] < -0.8:
                return ['scene=angry', 'animation=angry']
            if scene == 'angry' and css[0] > -0.2:
                return ['scene=awake', 'animation=awake']
            if scene == 'awake' and css[0] > 0.95:
                return ['scene=happy', 'animation=happy']
            if scene == 'happy' and css[0] < 0.1:
                return ['scene=awake', 'animation=awake']
        return []


class RNCA(L.Signal):
    """Random NCA state."""

    def init(self, timeouts_secs=3*60):
        self.json = json.load(open(os.path.join(
            os.path.dirname(__file__), 'nca.json'
        )))
        self.ncas = _presets['ncas']
        self.t = time.time()

    def call(self, mode, t):
        if mode != 'rnca':
            return None

        overwrites = {}
        if t - self.t > self.timeouts_secs:
            nca = self.ncas[random.randint(0, len(self.ncas))]
            overwrites['nca'] = nca
            self.t = t
        return dict(
            overwrites=overwrites,
        )


class SonarAction(L.Signal):
    """Emits sonar related actions."""

    threshold: float

    def init(self, threshold=0.5):
        self.on = False
        self.lastanim = None

    def call(self, sonar, state, animation):
        if sonar is not None:
            if sonar > self.threshold and not self.on:
                self.on = True
                self.lastanim = animation
                if state == 'rnca':
                    return ['nca=next']
                return ['charge=on', 'animation=charge']
            if sonar < self.threshold and self.on:
                self.on = False
                return ['charge=off', f'animation={self.lastanim}']
        return []


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
                actions.append(f'scene={STATE_WAKEUP}')
        if state == STATE_WAKEUP:
            if wakeup == 1:
                actions.append(f'state={STATE_AWAKE}')
                actions.append(f'animation={STATE_AWAKE}')
                actions.append(f'scene={STATE_AWAKE}')
        if state == STATE_AWAKE:
            if active == 0 and pir == 0:
                actions.append(f'state={STATE_SLEEP}')
                actions.append(f'animation={STATE_SLEEP}')
                actions.append(f'scene={STATE_SLEEP}')
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
