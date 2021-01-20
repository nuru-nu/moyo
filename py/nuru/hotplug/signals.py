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


# Signals groups
################

audio_signals = dict(
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
    iso=(L.Named('tf') | S.Median(n=10, threshold=0.7)),
    iso2=(L.Named('tf') | S.Median(n=10, threshold=0.7))
    | S.Exponential(alpha=0.95),
    # sig1=(
    #     S.Louder(n=10) | S.Lin(mult=20)
    # ) * (
    #     L.Named('tf') |
    #     S.Median(n=10, threshold=0.7)
    # ),

    # logmel
    breadth=(S.FreqBreadth(threshold=-1) | S.Lin(mult=1 / 20) | S.Clip(0, 1)
             | S.MovingAverage(n=5)),
    low=(S.FreqBand(fmin=0, fmax=10, df=1.2) | S.Lin(shift=3 / 5, mult=1 / 5)
         | S.Clip() | S.MovingAverage(n=5)),
    medium=(S.FreqBand(fmin=10, fmax=30, df=5) | S.Lin(shift=3) | S.Clip()
            | S.MovingAverage(n=5)),
    high=(S.FreqBand(fmin=31, fmax=1e10, df=6) | S.Lin(shift=3 / 5, mult=1 / 5)
          | S.Clip() | S.MovingAverage(n=5)),

    #std3=S.Sin(hz=0.5) | S.Lin(shift=0.75, mult=0.25),
)

ooo_signals = dict(
    ooo=(L.Named('iso') | S.ClampSlope(up_s=2, down_s=2) | S.Hyst(
        up_th=0.5, down_th=0.2) | S.ClampSlope(up_s=5, down_s=0.5) | S.Tocos())
    | S.InState('ooo'),
    bass_ooo=S.RndRamp([20, 30], [3, 4], [1, 4], state='ooo'),
    ooo_intensity=(L.Named('ooo') | S.ClampSlope(up_s=0.2, down_s=0.4)
                   | S.Clip()),
)

sensor_signals = dict(sonar=S.Overridable(L.Named('sonar_sensor'),
                                          L.Named('sonar_override')), )

generated_signals = dict(
    saw_v=S.Saw(hz=L.Named('valence')),
    saw_a=S.Saw(hz=L.Named('arousal')),
    saw_ac2=L.Named('saw_a') | S.Lin(0, 2) | S.Tocos(),
    std2=S.Saw(hz=0.5),
    std22=S.Saw(hz=1.0),
    std2_cos2=L.Named('std2') | S.Lin(mult=2) | S.Tocos(),
    std3=S.Saw(hz=0.5),
    saw_slow=S.Saw(hz=0.05),
    cos2_slow=S.Saw(hz=0.2) | S.Lin(mult=2) | S.Tocos(),
    drone1=(S.RndRamp(break_minmax=[1, 5], duration_minmax=[3, 10])
            | S.InState('std') | S.MovingAverage(secs=0.5)),
    drone2=(S.RndRamp(break_minmax=[1, 5], duration_minmax=[3, 10])
            | S.InState('std') | S.MovingAverage(secs=0.5)),
    drone3=S.RndRamp(),
)

css_signals = dict(
    randval=(S.Const(0.5) +
             (S.RandomPulse(hz=0.1, duration=1) | S.To(0, 0.5)) +
             (S.RandomPulse(hz=0.1, duration=1) | S.To(0, -0.5))),
    # 0..1
    valence=L.Named('css') | S.ElementAt(0) | S.Lin(0.5, 0.5),
    # 0..1
    arousal=L.Named('css') | S.ElementAt(1) | S.Lin(0.5, 0.5),
)

state_signals = dict(
    css=state.Css(alpha=L.Named('css_alpha')),
    state=state.Rizhom(),
    scene=S.ActionLatch('scene=(.*)', 'S1'),
    animation=S.ActionLatch('animation=(.*)', 'S1'),
)

action_signals = dict(
    flash_pulse=L.Named('rawloud') | S.RefractoryPulse(0.5, 2, 40),
    #flash_pulse=S.TriggerPulse(state='flash', secs=3),
    into=Into(),
    css_action=state.CssAction(threshold=0.0),
    sonar_action=state.SonarAction(threshold=0.3),
    charge=S.ActionOnOff('charge=on', 'charge=off') | S.Ramps(0.06, 0.8),
)

animation_signals = dict(
    heart=S.TransientPulse('event', 'heart') | S.RateLimit(10, 2)
    | S.Tocos(),  #| S.Lin(-5, 10) | S.Int() | S.Clip(),
    heart_a=(S.Saw(hz=L.Named('arousal') | S.Lin(0, 2))
             | S.Lin(0, 3) | S.Clip() | S.Lin(0, 2) | S.Tocos()),
)

kinect_signals = dict(
    people=S.Overridable(L.Named('people_sensor'), L.Named('people_override')),
    closest=S.KinectDistance() | S.With(3.8) | S.Min() | S.From(4, 0) | S.F(S.sinramp),
)

numbers_features = dict(
    fc=S.ActionLatch('fc=(.*)', 0, int),
    n_people=L.Named('people') | S.Length(),
)

# Signal runners
################

def make_runner(*dicts):
    signals = {}
    for d in dicts:
        signals.update(d)
    return L.SignalRunner(signals)


audio_runner = make_runner(audio_signals)
integrator_runner = make_runner(
    generated_signals,
    state_signals,
    css_signals,
    ooo_signals,
    action_signals,
    animation_signals,
    numbers_features,
    kinect_signals,
    sensor_signals,
)

# Signal metadata
#################

defaults = dict(
    t=0,
    iso=0,
    rawloud=0,
    loud=0,
    sonar_sensor=1,
    sonar_override=None,
    state=state.State(),
    animation='S1',
    scene='S1',
    target_css=None,
    fc=0,
    people_sensor=[],
    people_override=None,
    css_alpha=10,
    palette='gabe_red',
    image='mac_pizza',
    v0=0,
    v1=0,
    v2=0,
)

transients = ('action', 'midi', 'signal', 'event')
transient_loops = dict(
    css_action='action',
    sonar_action='action',
)

cc = lambda *x: functools.reduce(operator.add, map(list, x), [])
monitor_def = dict(
    graphs=dict(
        audio=audio_signals.keys(),
        ooo=ooo_signals.keys(),
        sensor=['sonar', 'presence'],
        kinect=kinect_signals.keys(),
        generated=generated_signals.keys(),
        animation=animation_signals.keys(),
        actions=action_signals.keys(),
        css=css_signals.keys(),
    ),
    transients=cc(transients, transient_loops),
    selected=['heart', 'sonar', 'charge'],
    features=dict(numbers=numbers_features.keys()),
    hidden=[
        # state
        'scene',
        'animation',
        # css
        'css',
        'target_css',
        'css_alpha',
        # kinect
        'people',
        'people_sensor',
        'people_override',
        # sonar
        'sonar_override',
        'sonar_sensor',
        # recorder
        'recorder',
        'playback_t',
        'logmel',
        'mfccs',
        't',
        # vars
        'image',
        'palette',
        'v0',
        'v1',
        'v2',
    ],
)
