import importlib, random

from smanmi import effects as E, logic as L, signals as S
from .. import settings


importlib.reload(E)
importlib.reload(S)
E.init(settings)
S.init(settings)


class State(L.Signal):
    """Updates the state."""

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


audio_runner = L.SignalRunner(dict(
    # raw audio
    #_pitch=(
    #    S.Pitcher(tolerance=0.7) | S.Limiter(minv=0, maxv=400) |
    #    S.Exponential(alpha=0.8)
    #),
    loud=S.Louder(n=10) | S.ClipToMaxOfMin(),
    rawloud=S.Louder(n=3) | S.Lin(mult=2),
    overdrive=S.Overdrive(0.8),
    peak=S.Max(),

    # tf
    #tf=ml.KerasDetector(model='tmo_wp_20_50_linear'),
    #tf2=ml.KerasDetector(model='s2_linear_wp_10_10'),
    #tf3=ml.KerasDetector(model='s2_linear_wp_20_20'),
    tf=L.Constant(0),
    tf2=L.Constant(0),
    tf3=L.Constant(0),
    iso=(
        L.Named('tf') |
        S.Median(n=10, threshold=0.7)
    ),
    iso2=(
        L.Named('tf') |
        S.Median(n=10, threshold=0.7)
    ) | S.Exponential(alpha=0.95),
    # sig1=(
    #     S.Louder(n=10) | S.Lin(mult=20)
    # ) * (
    #     L.Named('tf') |
    #     S.Median(n=10, threshold=0.7)
    # ),

    # logmel
    breadth=(
        S.FreqBreadth(threshold=-1) | S.Lin(mult=1 / 20) |
        S.Clip(0, 1) | S.MovingAverage(n=5)
    ),
    low=(
        S.FreqBand(hzmin=0, hzmax=800, hzslope=100) |
        S.Lin(shift=3 / 5, mult=1 / 5) | S.Clip() | S.MovingAverage(n=5)
    ),
    medium=(
        S.FreqBand(hzmin=800, hzmax=2500, hzslope=400) |
        S.Lin(shift=3) | S.Clip() | S.MovingAverage(n=5)
    ),
    high=(
        S.FreqBand(hzmin=2500, hzmax=1e10, hzslope=500) |
        S.Lin(shift=3 / 5, mult=1 / 5) | S.Clip() | S.MovingAverage(n=5)
    ),

    #std3=S.SinT(hz=0.5) | S.Lin(shift=0.75, mult=0.25),
))

integrator_runner = L.SignalRunner(dict(
    # only compute if we have `audio_runner` input signals
    loud_=L.Named('loud'),

    # state
    state=State(),

    # generated
    std2=S.Saw(hz=0.5, dt=0),
    std22=S.Saw(hz=1.0, dt=0),
    std3=S.Saw(hz=0.5, dt=0),
    drone1=(
        S.RndRamp(break_minmax=[1, 5], duration_minmax=[3, 10])
        | S.InState('std') | S.MovingAverage(secs=0.5)
    ),
    drone2=(
        S.RndRamp(break_minmax=[1, 5], duration_minmax=[3, 10])
        | S.InState('std') | S.MovingAverage(secs=0.5)
    ),
    drone3=S.RndRamp(),

    # non-audio input
    into=S.Into(),

    # derived
    ooo=(
        L.Named('iso') |
        S.Ramp(up_s=2, down_s=2) | S.Hyst(up_th=0.5, down_th=0.2) |
        S.Ramp(up_s=5, down_s=0.5) | S.Tocos()
    ) | S.InState('ooo'),
    bass_ooo=S.RndRamp([20, 30], [3, 4], [1, 4], state='ooo'),
    ooo_intensity=(
        L.Named('ooo') | S.Ramp(up_s=0.2, down_s=0.4) | S.Clip()),
    #flash_pulse=S.TriggerPulse(state='flash', secs=3),

    # output
    flash_pulse=L.Named('rawloud') | S.Smoke(0.5, 2, 40),
), defaults=dict(
    loud=0,
    setstate={},
    sonar=0,
))
