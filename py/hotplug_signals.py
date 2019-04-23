{
    'pitch': S.Pitcher(tolerance=0.7) | S.Exponential(alpha=0.8),
    'loud': S.Louder(n=10) | S.F(mult=20),
    'tf': S.KerasDetector.get('tmo_wp_20_50_linear', 'wp_20_50'),
    'iso': S.KerasDetector.get('tmo_wp_20_50_linear', 'wp_20_50') | S.Median(
        n=10, threshold=0.7),
}
