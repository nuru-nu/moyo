import functools
import importlib
import operator

from smanmi import effects as E, midi, logic as L, signals as S

from .. import settings
from .. import state


importlib.reload(E)
importlib.reload(S)
importlib.reload(state)
importlib.reload(state)
E.init(settings)
S.init(settings)


class Into(L.Signal):
    """Turns on when head presence is detected by sonar."""

    def init(self, limit=0.3):
        self.value = 0

    def call(self, sonar):
        if sonar > 0:
            self.value = sonar < self.limit
        return self.value


def make_runner(*dicts):
    signals = {}
    for d in dicts:
        signals.update(d)
    return L.SignalRunner(signals)


audio = dict(
    # raw audio
    #_pitch=(
    #    S.Pitcher(tolerance=0.7) | S.Clip(0, 400) |
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
    tf=S.Const(0),
    tf2=S.Const(0),
    tf3=S.Const(0),
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
        S.FreqBand(fmin=0, fmax=10, df=1.2) |
        S.Lin(shift=3 / 5, mult=1 / 5) | S.Clip() | S.MovingAverage(n=5)
    ),
    medium=(
        S.FreqBand(fmin=10, fmax=30, df=5) |
        S.Lin(shift=3) | S.Clip() | S.MovingAverage(n=5)
    ),
    high=(
        S.FreqBand(fmin=31, fmax=1e10, df=6) |
        S.Lin(shift=3 / 5, mult=1 / 5) | S.Clip() | S.MovingAverage(n=5)
    ),

    #std3=S.Sin(hz=0.5) | S.Lin(shift=0.75, mult=0.25),
)

generated = dict(
    saw_v=S.Saw(hz=L.Named('valence')),
    saw_a=S.Saw(hz=L.Named('arousal')),
    saw_ac2=L.Named('saw_a') | S.Lin(0, 2) | S.Tocos(),
    std2=S.Saw(hz=0.5),
    std22=S.Saw(hz=1.0),
    std2_cos2=L.Named('std2') | S.Lin(mult=2) | S.Tocos(),
    std3=S.Saw(hz=0.5),
    saw_slow=S.Saw(hz=0.05),
    cos2_slow=S.Saw(hz=0.2) | S.Lin(mult=2) | S.Tocos(),
    drone1=(
        S.RndRamp(break_minmax=[1, 5], duration_minmax=[3, 10])
        | S.InState('std') | S.MovingAverage(secs=0.5)
    ),
    drone2=(
        S.RndRamp(break_minmax=[1, 5], duration_minmax=[3, 10])
        | S.InState('std') | S.MovingAverage(secs=0.5)
    ),
    drone3=S.RndRamp(),
)

css = dict(
    randval=(
        S.Const(0.5) +
        (S.RandomPulse(hz=0.1, duration=1) | S.To(0, 0.5)) +
        (S.RandomPulse(hz=0.1, duration=1) | S.To(0, -0.5))
    ),
    # 0..1
    valence=L.Named('css') | S.ElementAt(0) | S.Lin(0.5, 0.5),
    # 0..1
    arousal=L.Named('css') | S.ElementAt(1) | S.Lin(0.5, 0.5),
)

states = dict(
    css=state.Css(alpha=L.Named('css_alpha')),
    state=state.Rizhom(),
    scene=S.ActionLatch('scene=(.*)', 'S1'),
    animation=S.ActionLatch('animation=(.*)', 'S1'),
    print_action=S.Print('action', L.Named('action')),
)

ooo = dict(
    ooo=(
        L.Named('iso') |
        S.ClampSlope(up_s=2, down_s=2) | S.Hyst(up_th=0.5, down_th=0.2) |
        S.ClampSlope(up_s=5, down_s=0.5) | S.Tocos()
    ) | S.InState('ooo'),
    bass_ooo=S.RndRamp([20, 30], [3, 4], [1, 4], state='ooo'),
    ooo_intensity=(
        L.Named('ooo') | S.ClampSlope(up_s=0.2, down_s=0.4) | S.Clip()),
)

actions = dict(
    flash_pulse=L.Named('rawloud') | S.RefractoryPulse(0.5, 2, 40),
    #flash_pulse=S.TriggerPulse(state='flash', secs=3),
    into=Into(),
    css_action=state.CssAction(),
    sonar_action=state.SonarAction(threshold=0.3),
)

animation = dict(
    heart=S.TransientPulse('event', 'heart') | S.RateLimit(5) | S.Tocos(),  #| S.Lin(-5, 10) | S.Int() | S.Clip(),
    heart_a=(
        S.Saw(hz=L.Named('arousal') | S.Lin(0, 2))
        | S.Lin(0, 3) | S.Clip() | S.Lin(0, 2) | S.Tocos()
    ),
)

kinect = dict(
    closest=S.KinectDistance() | S.Min(5) | S.To(1, 0, 0, 5),
)

numbers = dict(
    fc=S.ActionLatch('fc=(.*)', 0, int),
    n_people=L.Named('people') | S.Length(),
)

audio_runner = make_runner(audio)
integrator_runner = make_runner(
    generated, states, css, ooo, actions, animation, numbers, kinect,
)

defaults = dict(
    t=0,
    iso=0,
    rawloud=0,
    loud=0,
    sonar=1,
    state=state.State(),
    animation='off',
    scene='S1',
    target_css=None,
    fc=0,
    people=[],
    css_alpha=10,
    palette='gabe_red',
    image='mac_pizza',
    v0=0, v1=0, v2=0,
)

transients = ('action', 'midi', 'signal')
hidden = ('people', 'target_css', 'css_alpha')
special = ('logmel', 'mfccs', 't')
vars_ = ('image', 'palette', 'v0', 'v1', 'v2')
loops = dict(
    css_action='action',
    sonar_action='action',
)

cc = lambda *x: functools.reduce(operator.add, map(list, x), [])
monitor_def = dict(
    graphs=dict(
        audio=audio.keys(),
        ooo=ooo.keys(),
        sensor=['sonar', 'presence'],
        kinect=kinect.keys(),
        generated=generated.keys(),
        animation=animation.keys(),
        actions=actions.keys(),
        css=css.keys(),
    ),
    transients=transients + ('css_action',),
    selected=['heart', 'sonar'],
    features=dict(
        numbers=numbers.keys(),
    ),
    hidden=cc(states, transients, hidden, special, vars_),
)
