


def naive(values, horizon):
    """Baseline 1: every future year equals the last known value."""
    return [values[-1]] * horizon


def linear_trend(values, horizon, window=10):
    """Baseline 2: fit a straight line to the last `window` years and extend it."""
    recent = values[-window:]
    n = len(recent)
    xs = range(n)
    x_mean = (n - 1) / 2
    y_mean = sum(recent) / n
    slope = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, recent)) / sum(
        (x - x_mean) ** 2 for x in xs
    )
    last_fit = y_mean + slope * (n - 1 - x_mean)
    return [last_fit + slope * h for h in range(1, horizon + 1)]


def _damped_holt_run(values, alpha, beta, phi):
    """Run the smoothing once. Returns the final level, trend and one-step errors."""
    level, trend = values[0], values[1] - values[0]
    errors = []
    for y in values[1:]:
        prediction = level + phi * trend
        errors.append(y - prediction)
        new_level = alpha * y + (1 - alpha) * (level + phi * trend)
        trend = beta * (new_level - level) + (1 - beta) * phi * trend
        level = new_level
    return level, trend, errors


def damped_holt(values, horizon):
    """
    Model: exponential smoothing with a damped trend.
    It tracks a level and a trend, and phi (< 1) makes the trend fade over time,
    so forecasts flatten out instead of running off forever.
    Settings are picked by trying a grid and keeping the one with the smallest errors.
    """
    best = None
    for alpha in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
        for beta in [0.05, 0.1, 0.2, 0.3, 0.4, 0.5]:
            for phi in [0.8, 0.85, 0.9, 0.95, 0.98]:
                level, trend, errors = _damped_holt_run(values, alpha, beta, phi)
                sse = sum(e * e for e in errors)
                if best is None or sse < best[0]:
                    best = (sse, level, trend, phi, errors)

    _, level, trend, phi, errors = best
    forecasts, damp = [], 0.0
    for h in range(1, horizon + 1):
        damp += phi ** h
        forecasts.append(level + damp * trend)
    return forecasts, errors


MODELS = {
    "naive": lambda v, h: naive(v, h),
    "linear_trend": lambda v, h: linear_trend(v, h),
    "damped_holt": lambda v, h: damped_holt(v, h)[0],
        "level_rule": lambda v, h: (
        damped_holt(v, h)[0] if v[-1] >= 50 else linear_trend(v, h)
    ),
    "blend": lambda v, h: [
        (a + b) / 2 for a, b in zip(linear_trend(v, h), damped_holt(v, h)[0])
    ],
}