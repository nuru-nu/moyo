import logic as L, signals as S


def get_data():
    signals = dict(
        _pitch=(
            S.Pitcher(tolerance=0.7) | S.Limiter(minv=0, maxv=400) |
            S.Exponential(alpha=0.8)
        ),
        loud=S.Louder(n=10) | S.Linear(mult=5) | S.Clip(),
        overdrive=S.Overdrive(0.8),
        peak=S.Max(),
        tf=S.KerasDetector(
            model='tmo_wp_20_50_linear', preprocessor='wp_20_50'),
        tf2=L.Named('tf') | S.MovingAverage(n=5) | S.Exp(alpha=2),
        iso=(
            L.Named('tf') |
            S.Median(n=10, threshold=0.7)
        ),
        iso2=(
            L.Named('tf') |
            S.Median(n=10, threshold=0.7)
        ) | S.Exponential(alpha=0.95),
        sig1=(
            S.Louder(n=10) | S.Linear(mult=20)
        ) * (
            L.Named('tf') |
            S.Median(n=10, threshold=0.7)
        ),
        breadth=(
            S.FreqBreadth(threshold=-1) | S.Linear(mult=1 / 20) |
            S.Clip(0, 1) | S.MovingAverage(n=5)
        ),
        low=(
            S.FreqBand(hzmin=0, hzmax=800, hzslope=100) |
            S.Linear(shift=3, mult=1 / 5) | S.Clip() | S.MovingAverage(n=5)
        ),
        medium=(
            S.FreqBand(hzmin=800, hzmax=2500, hzslope=400) |
            S.Linear(shift=3, mult=1) | S.Clip() | S.MovingAverage(n=5)
        ),
        high=(
            S.FreqBand(hzmin=2500, hzmax=1e10, hzslope=500) |
            S.Linear(shift=3, mult=1 / 5) | S.Clip() | S.MovingAverage(n=5)
        ),
        ooo=(
            L.Named('iso') |
            S.Ramp(up_s=2, down_s=2) | S.Hyst(up_th=0.5, down_th=0.2) |
            S.Ramp(up_s=5, down_s=0.5) | S.Tocos()
        ) * (
            L.Named('left_drone') | S.Linear(shift=-1, mult=-10) | S.Clip()
        ) * (
            L.Named('right_drone') | S.Linear(shift=-1, mult=-10) | S.Clip()
        ),

        state=S.State(),

        left_drone=S.RndRamp([1, 20], [5, 10], [2, 4]),
        right_drone=S.RndRamp([5, 10], [5, 10], [2, 4]),

        bass_ooo=S.RndRamp([20, 30], [3, 4], [1, 4], state='ooo'),
        ooo_intensity=(
            L.Named('ooo') | S.Ramp(up_s=0.05, down_s=0.5) | S.Clip()),
    )

    return dict(
        runner=L.SignalRunner(signals, ('features', 't', 'signalin', 'state'))
    )
