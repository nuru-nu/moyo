{
    'pitch': S.Pitcher(tolerance=0.7) | S.Exponential(alpha=0.8),
    'loud': S.Louder() | S.F(mult=20),
}
