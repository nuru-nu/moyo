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
N = L.N


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
    #    S.Exponential(alpha=0.2)
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
    iso2=(L.Named('tf') | S.Median(n=10, threshold=0.7)),
    # | S.Exponential(alpha=.05)
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

sensor_signals = dict(
    sonar=S.Overridable(N.sonar_0 | S.From(40, 0), N.sonar_override),
    pir=N.pir_0,
    # touch=N.touch_raw | S.From(0, 400) | S.MovingAverage(n=1),
    # touch=N.touch_raw | S.From(0, 500) | S.MovingAverage(n=3),
    # touch=N.touch_raw | S.From(0, 1000),
)

touch_from = [200] * 16
touch_n = len(touch_from)
touch_raws = [f'touch_raw_{i}' for i in range(touch_n)]
for i, from_ in enumerate(touch_from):
    sensor_signals[f'touch_{i}'] = (
        L.Named(f'touch_raw_{i}') | S.From(0, from_) | S.MovingAverage(n=5))

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
    rnd1=S.RndWalk(60) | S.MovingAverage(n=10),
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
    mode=S.ActionLatch('mode=(.*)', N.mode),
    scene=S.ActionLatch('scene=(.*)', N.scene),
    animation=S.ActionLatch('animation=(.*)', N.animation),
)

action_signals = dict(
    flash_pulse=L.Named('rawloud') | S.RefractoryPulse(0.5, 2, 40),
    #flash_pulse=S.TriggerPulse(state='flash', secs=3),
    into=Into(),
    css_action=state.CssAction(threshold=0.0),
    nca_action=state.NcaAction(),
    sonar_action=state.SonarAction(threshold=0.3),
    charge=S.ActionOnOff('charge=on', 'charge=off') | S.Ramps(0.06, 0.8),
)

animation_signals = dict(
    nca=S.ActionLatch('nca=set=(.*)', N.nca),
    heart=S.TransientPulse('event', 'heart') | S.RateLimit(8, 1)
        | S.Tocos(),  #| S.Lin(-5, 10) | S.Int() | S.Clip(),
        heart_a=(S.Saw(hz=L.Named('arousal') | S.Lin(0, 2))
                | S.Lin(0, 3) | S.Clip() | S.Lin(0, 2) | S.Tocos()),
)

kinect_signals = dict(
    people=S.Overridable(
        L.Named('people_sensor') | S.KinectFix(
            phantoms=([0.884383, -4.013486, 0.935697],),
            dphi=N.kinect_dphi | S.From(0, 1) | S.To(-90, 90),
        ),
        L.Named('people_override'),
    ),
    closest=(
        S.KinectDistance()
        | S.With(6.5) | S.Min() | S.From(6.5, 0)
        # | S.F(S.sinramp),
    ),
    distance=S.KinectDistance(),
    mvmt=S.KinectMovement(5) | S.From(0, .5) | S.Clip(),
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
    sonar_0=1,
    pir_0=0,
    sonar_override=None,
    state=state.State(),
    mode='manual',
    animation='S1',
    scene='S1',
    target_css=None,
    fc=0,
    people_sensor=[],
    people_override=None,
    mvmt=0,
    kinect_dphi=0,
    css_alpha=10,
    palette='gabe_red',
    image='mac_pizza',
    nca='smeared_0041',
    v0=0.5,
    v1=0.5,
    v2=0.5,
    nca_speed=1,
    nca_clip=0,
    nca_wrap=0,
    anim_head=1,
    anim_arms=1,
    anim_both=1,
    one=1,
    anim_sig='one',
    **{
        touch_raw: 0 for touch_raw in touch_raws
    },
)

transients = ('action', 'midi', 'signal', 'event')
transient_loops = dict(
    css_action='action',
    sonar_action='action',
    nca_action='action',
)

cc = lambda *x: functools.reduce(operator.add, map(list, x), [])
modes = ('manual', 'css')
monitor_def = dict(
    graphs=dict(
        audio=audio_signals.keys(),
        ooo=ooo_signals.keys(),
        sensor=['sonar', 'pir', 'presence'] + [f'touch_{i}' for i in range(touch_n)],
        kinect=kinect_signals.keys(),
        generated=generated_signals.keys(),
        animation=animation_signals.keys(),
        actions=action_signals.keys(),
        css=css_signals.keys(),
    ),
    transients=cc(transients, transient_loops),
    selected={
        'default': ['heart', 'rnd1'],
        'sensors': ['closest', 'mvmt', 'sonar', 'pir'],
        'empty': [],
    },
    # selected=['heart', 'sonar', 'charge', 'rnd1'] + [f'touch_{i}' for i in range(touch_n)],
    # selected=['heart'] + ['touch_9'],  #[f'touch_{i}' for i in range(touch_n)],
    features=dict(
        numbers=numbers_features.keys(),
        other=['nca'],
    ),
    hidden=[
        'one',
        # state
        'scene',
        'animation',
        'mode',
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
        'sonar_0',
        # recorder
        'recorder',
        'playback_t',
        'logmel',
        'mfccs',
        't',
        # stats
        *touch_raws,
        'pir_0',
        # vars
        'image',
        'palette',
        'v0',
        'v1',
        'v2',
        'kinect_dphi',
        # NCA
        'nca_speed',
        'nca_clip',
        'nca_wrap',
        # anim
        'anim_both',
        'anim_head',
        'anim_arms',
        'anim_sig',
    ],
)
