{
    'pitch0': S.Pitcher(tolerance=0.7),
    'pitch': S.Pitcher(tolerance=0.7) | S.Exponential(alpha=0.8),
    'pitch_lim': S.Pitcher(tolerance=0.7)| S.Limiter(maxv=400) | S.Exponential(alpha=0.8),
    'loud': S.Louder(n=10) | S.F(mult=20),
    'loud2': S.Louder(n=10) | S.F(mult=20),
    'tf': S.KerasDetector.get('tmo_wp_20_50_linear', 'wp_20_50'),
    'iso': S.KerasDetector.get('tmo_wp_20_50_linear', 'wp_20_50') | S.Median(
        n=10, threshold=0.7),
    'sig1': (
        S.Louder(n=10) | S.F(mult=20)
    ) * (
        S.KerasDetector.get('tmo_wp_20_50_linear', 'wp_20_50') | S.Median(
            n=10, threshold=0.7)
    )

}
