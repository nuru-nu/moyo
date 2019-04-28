import signals as S


def get_data():
    return dict(
        _pitch=(
            S.Pitcher(tolerance=0.7) | S.Limiter(maxv=400) |
            S.Exponential(alpha=0.8)
        ),
        loud=S.Louder(n=10),
        overdrive=S.Overdrive(),
        peak=S.Max(),
        tf=S.KerasDetector.get('tmo_wp_20_50_linear', 'wp_20_50'),
        iso=(
            S.KerasDetector.get('tmo_wp_20_50_linear', 'wp_20_50') |
            S.Median(n=10, threshold=0.7)
        ),
        sig1=(
            S.Louder(n=10) | S.F(mult=20)
        ) * (
            S.KerasDetector.get('tmo_wp_20_50_linear', 'wp_20_50') |
            S.Median(n=10, threshold=0.7)
        ),
        breadth=(
            S.FreqBreadth(-1) | S.F(mult=1 / 20) | S.Clip(0, 1) |
            S.MovingAverage(5)
        ),
        low=(
            S.FreqBand(hzmin=0, hzmax=800, hzslope=100) |
            S.F(shift=3, mult=1 / 5) | S.Clip() | S.MovingAverage(5)
        ),
        medium=(
            S.FreqBand(hzmin=800, hzmax=2500, hzslope=500) |
            S.F(shift=3, mult=1 / 5) | S.Clip() | S.MovingAverage(5)
        ),
        high=(
            S.FreqBand(hzmin=2500, hzmax=1e10, hzslope=500) |
            S.F(shift=3, mult=1 / 5) | S.Clip() | S.MovingAverage(5)
        ),
    )
