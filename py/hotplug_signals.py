import effects as E, logic as L, ml, signals as S


def get_data():
    signals = dict(
        # _pitch=(
        #     S.Pitcher(tolerance=0.7) | S.Limiter(minv=0, maxv=400) |
        #     S.Exponential(alpha=0.8)
        # ),
        loud=S.Louder(n=10) | S.ClipToMaxOfMin(),
        overdrive=S.Overdrive(0.8),
        peak=S.Max(),
        tf=ml.KerasDetector(model='tmo_wp_20_50_linear'),
        tf2=ml.KerasDetector(model='s2_linear_wp_10_10'),
        tf3=ml.KerasDetector(model='s2_linear_wp_20_20'),
        iso=(
            L.Named('tf') |
            S.Median(n=10, threshold=0.7)
        ),
        iso2=(
            L.Named('tf') |
            S.Median(n=10, threshold=0.7)
        ) | S.Exponential(alpha=0.95),
        sig1=(
            S.Louder(n=10) | S.Lin(mult=20)
        ) * (
            L.Named('tf') |
            S.Median(n=10, threshold=0.7)
        ),
        breadth=(
            S.FreqBreadth(threshold=-1) | S.Lin(mult=1 / 20) |
            S.Clip(0, 1) | S.MovingAverage(n=5)
        ),
        low=(
            S.FreqBand(hzmin=0, hzmax=800, hzslope=100) |
            S.Lin(shift=3, mult=1 / 5) | S.Clip() | S.MovingAverage(n=5)
        ),
        medium=(
            S.FreqBand(hzmin=800, hzmax=2500, hzslope=400) |
            S.Lin(shift=3, mult=1) | S.Clip() | S.MovingAverage(n=5)
        ),
        high=(
            S.FreqBand(hzmin=2500, hzmax=1e10, hzslope=500) |
            S.Lin(shift=3, mult=1 / 5) | S.Clip() | S.MovingAverage(n=5)
        ),
        ooo=(
            L.Named('iso') |
            S.Ramp(up_s=2, down_s=2) | S.Hyst(up_th=0.5, down_th=0.2) |
            S.Ramp(up_s=5, down_s=0.5) | S.Tocos()
        ) * (
            L.Named('left_drone') | S.Lin(shift=-1, mult=-10) | S.Clip()
        ) * (
            L.Named('right_drone') | S.Lin(shift=-1, mult=-10) | S.Clip()
        ),
        sonar=S.Sonar(),
        sonar_good=S.SonarGood(),

        state=S.State(),

        left_drone=S.RndRamp([1, 5], [5, 10], [8, 8]) | S.NotInState('test'),
        right_drone=S.RndRamp([1, 5], [5, 10], [2, 2]) | S.NotInState('test'),

        bass_ooo=S.RndRamp([20, 30], [3, 4], [1, 4], state='ooo'),
        ooo_intensity=(
            L.Named('ooo') | S.Ramp(up_s=0.1, down_s=0.5) | S.Clip()),

        ring1=S.Saw(hz=1, dt=0),
        ring2=S.Saw(hz=1, dt=0.5),
    )

    return dict(
        additional_monitor_address=('localhost', 6999),
        microphone_effect=E.Compressor(2) | E.Recording('play'),
        runner=L.SignalRunner(signals, ('features', 't', 'signalin', 'state'))
    )
