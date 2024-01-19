import functools
import importlib
import operator

from smanmi import effects as E, midi, logic as L, signals as S

from .. import settings
from .. import state

importlib.reload(E)
importlib.reload(S)
importlib.reload(state)
E.init(settings)
S.init(settings)
N = L.N

R_Z2 = 2


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
    #     S.Medianse(n=10, threshold=0.7)
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
    sonar=S.Overridable(S.Sonar(N.sonar_0), N.sonar_override),
    pir=S.Overridable(N.pir_0, N.pir_override),
    # touch=N.touch_raw | S.From(0, 400) | S.MovingAverage(n=1),
    # touch=N.touch_raw | S.From(0, 500) | S.MovingAverage(n=3),
    # touch=N.touch_raw | S.From(0, 1000),
)

touch_from = [200] * 16
touch_n = len(touch_from)
touch_raws = [f'touch_raw_{i}' for i in range(touch_n)]
touchs = [touch_raw.replace('_raw', '') for touch_raw in touch_raws]
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
    rnd1=S.RndWalk(10) | S.MovingAverage(n=10),
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
    valence=N.css | S.ElementAt(0) | S.From(-1, 1),
    # 0..1
    arousal=N.css | S.ElementAt(1) | S.From(-1, 1),
)

state_signals = dict(
    dt=S.Dt(),
    # state=state.Rizhom(),
    state=S.ActionLatch('state=(.*)', N.state),
    wakeup=state.Reservoir(
        state.STATE_WAKEUP,
        start=0,
        diff=1 / 5,
    ),
    active=state.Reservoir(
        state.STATE_AWAKE,
        start=1,
        diff=((N.closest | S.To(0, .4)) + S.Const(-1 / 180)),
    ),
    charge=S.ActionOnOff('charge=on', 'charge=off') | S.Ramps(0.17, 0.75),
    animation=S.ActionLatch('animation=(.*)', N.animation),
    scene=S.ActionLatch('scene=(.*)', N.scene),
    mode=S.ActionLatch('mode=(.*)', N.mode),
    # One of these is selected by "mode".
    state_one=state.One(r_z2=R_Z2,
                        sig=N.state_one,
                        wakeup_duration=10,
                        sonar_threshold=0.1),
    state_kosmos=state.Kosmos(sig=N.state_kosmos),
    state_kraftwerk=state.Kraftwerk(sig=N.state_kraftwerk),
    state_rnca=state.RNCA(secs=60),
    css=state.Css(alpha=L.Named('css_alpha')),
)

action_signals = dict(
    flash_pulse=L.Named('rawloud') | S.RefractoryPulse(0.5, 2, 40),
    #flash_pulse=S.TriggerPulse(state='flash', secs=3),
    into=Into(),
    state_action=state.SimpleStateAction(),
    css_action=state.CssAction(threshold=0.0),
    sonar_action=state.SonarAction(threshold=0.3),
    heart_action=state.ArtificialHeart(
        N.heart_sim, N.arousal | S.To(.5, 1.2), 0.15),
)

animation_signals = dict(
    heart=S.TransientPulse('event', 'heart') | S.RateLimit(8, 2)
        | S.Tocos(),  #| S.Lin(-5, 10) | S.Int() | S.Clip(),
    # TODO flashing "charge"
)

kinect_signals = dict(
    likes=S.KinectLike(r_z2=R_Z2, dl_dt=1/10),
    people=S.Overridable(
        L.Named('people_sensor'),
        L.Named('people_override'),
    ),
    people_2=S.Overridable(
        L.Named('people_sensor') | S.KinectFix(
            phantoms=(),
            dphi=N.kinect_dphi | S.From(0, 1) | S.To(0, 360),
        ),
        L.Named('people_override'),
    ),
    connection=L.Named('closest') | S.ConnectionMeter(
        decay_rate=1 / 10, 
        acceptance_rate=1 / 10,
    ),
    ready_to_respond=L.Named("connection") | S.Thr(1),
    # annoyance_build_up=L.Named('listening_gpt') * (S.Const(1) - L.Named("ready_to_respond")) | S.MovingAverage(n=50),
    closest=(
        S.KinectDistance()
        | S.With(6.5) | S.Min() | S.From(6.5, 0)
        # | S.F(S.sinramp),
    ),
    distance=S.KinectDistance(),
    mvmt=S.KinectMovement(5),
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

# Used when initializing new signals (i.e. after deleting tmp/integrator.json)
defaults = dict(
    t=0,
    dt=0,
    iso=0,
    rawloud=0,
    loud=0,
    sonar_0=40,
    pir_0=0,
    sonar_override=None,
    pir_override=None,
    # state=state.State(),
    state_one=state.One.INITIAL_STATE,
    state_kosmos=state.Kosmos.INITIAL_STATE,
    state_kraftwerk=state.Kraftwerk.INITIAL_STATE,
    state=state.STATE_SLEEP,
    mode='manual',
    animation='nca',
    charge=0,
    scene='sleep',
    target_css=None,
    fc=0,
    people_sensor=[],
    people_sensor_2=[],
    people_override=None,
    mvmt=0,
    kinect_dphi=0.39,
    kinect_alg='merged',
    css_alpha=10,
    palette='gabe_red',
    image='mac_pizza',
    nca='smeared_0041',
    nca_speed=1,
    nca_clip=True,
    nca_wrap=True,
    nca2='smeared_0041',
    nca_speed2=1,
    nca_clip2=True,
    nca_wrap2=True,
    v0=0.5,
    v1=0.5,
    v2=0.5,
    anim_mix=1,
    anim_head=1,
    anim_arms=1,
    anim_both=1,
    anim_hue=0,
    anim_sat=0.5,
    one=1,
    anim_sig='one',
    anim_heart=1,
    heart_sim=0,
    anim_into=0,
    anim_dark=1,
    anim_dbg=0,
    **{
        touch_raw: 0 for touch_raw in touch_raws
    },
)

# TODO? cleanup/unify
transients = ('action', 'midi', 'signal', 'event', 'speech_gpt', 'emo_gpt')
# TODO? implement these as "overwrites"
transient_loops = dict(
    css_action='action',
    sonar_action='action',
    state_action='action',
    heart_action='event',
)

cc = lambda *x: functools.reduce(operator.add, map(list, x), [])
modes = ['rnca', 'manual', 'css', 'simple', 'one', 'kosmos', 'kraftwerk']
monitor_def = dict(
    graphs=dict(
        audio=audio_signals.keys(),
        ooo=ooo_signals.keys(),
        sensor=['sonar', 'pir', 'presence'] + [f'touch_{i}' for i in range(touch_n)],
        state=['wakeup', 'active', 'charge'],
        kinect=kinect_signals.keys(),
        generated=generated_signals.keys(),
        animation=animation_signals.keys(),
        actions=action_signals.keys(),
        css=css_signals.keys(),
    ),
    transients=cc(transients, transient_loops),
    selected={
        'default': ['heart', 'rnd1'],
        'sensors': ['closest', 'mvmt', 'sonar', 'pir', 'connection'],
        'touch': touchs,
        'state': ['wakeup', 'active', 'pir', 'closest', 'charge'],
        'gpt': ['thinking_gpt', 'speaking_gpt', 'listening_gpt', 'gpt_response_dt_min'],
        'empty': [],
    },
    preset_signals=[
        'animation',
        'anim_both', 'anim_head', 'anim_arms', 'anim_mix',
        'anim_hue', 'anim_sat',
        'nca', 'nca_speed', 'nca_wrapx', 'nca_clip',
        'nca2', 'nca_speed2', 'nca_wrapx2', 'nca_clip2',
    ],
    # selected=['heart', 'sonar', 'charge', 'rnd1'] + [f'touch_{i}' for i in range(touch_n)],
    # selected=['heart'] + ['touch_9'],  #[f'touch_{i}' for i in range(touch_n)],
    features=dict(
        numbers=numbers_features.keys(),
        state=['state'],
    ),
    hidden=[
        # utility
        'one',
        'dt',
        'heart_sim',
        # state
        'state_one',
        'state_kosmos',
        'state_kraftwerk',
        'rec_state',
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
        'people_sensor_2',
        'people_override',
        'kinect_alg',
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
        'nca',
        'nca_speed',
        'nca_clip',
        'nca_wrap',
        'nca_wrapx',
        'nca2',
        'nca_speed2',
        'nca_clip2',
        'nca_wrap2',
        'nca_wrapx2',
        # anim
        'hue',
        'anim_both',
        'anim_head',
        'anim_arms',
        'anim_hue',
        'anim_sat',
        'anim_sig',
        'anim_heart',
        'anim_into',
        'anim_dark',
        'anim_dbg',
    ],
)
