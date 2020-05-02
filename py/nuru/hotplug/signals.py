import importlib

from smanmi import effects as E, midi, logic as L, signals as S

from .. import settings
from .. import state


importlib.reload(E)
importlib.reload(S)
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


audio_runner = L.SignalRunner(dict(
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

    #std3=S.SinT(hz=0.5) | S.Lin(shift=0.75, mult=0.25),
))

integrator_runner = L.SignalRunner(dict(
    # only compute if we have `audio_runner` input signals
    loud_=L.Named('loud'),

    # state
    state=state.Rizhom(),

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
    heart=S.MidiPulse(midi.Note(0, 'C', 2)) | S.Lin(-5, 10) | S.Int(),

    # non-audio input
    into=Into(),

    # derived
    ooo=(
        L.Named('iso') |
        S.ClampSlope(up_s=2, down_s=2) | S.Hyst(up_th=0.5, down_th=0.2) |
        S.ClampSlope(up_s=5, down_s=0.5) | S.Tocos()
    ) | S.InState('ooo'),
    bass_ooo=S.RndRamp([20, 30], [3, 4], [1, 4], state='ooo'),
    ooo_intensity=(
        L.Named('ooo') | S.ClampSlope(up_s=0.2, down_s=0.4) | S.Clip()),
    #flash_pulse=S.TriggerPulse(state='flash', secs=3),

    # output
    flash_pulse=L.Named('rawloud') | S.RefractoryPulse(0.5, 2, 40),
))
