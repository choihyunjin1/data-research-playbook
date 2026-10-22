"""Minimal contract repair; the supplied candidate remains unchanged."""
import numpy as np
import pandas as pd
from research_playbook.contracts import exact_integer, finite_clip


def device_id(value):
    return exact_integer(value, name="device_id", minimum=1, maximum=999)


def cap_prediction(values):
    return finite_clip(values, 0, 100)


def average_prediction(times, values, blocks):
    ts = pd.DatetimeIndex(pd.to_datetime(times, utc=True))
    a = np.asarray(values, dtype=float)
    b = np.asarray(blocks, dtype=object)
    if a.shape != (len(ts),) or b.shape != (len(ts),):
        raise ValueError("aligned one-dimensional values and blocks required")
    if not np.isfinite(a).all() or pd.isna(b).any():
        raise ValueError("finite values and nonmissing blocks required")
    if any(isinstance(label, str) and not label.strip() for label in b):
        raise ValueError("blank block label")
    if ts.hasnans or not (ts.is_monotonic_increasing or ts.is_monotonic_decreasing):
        raise ValueError("finite monotonic timestamps required")
    codes, _ = pd.factorize(b, sort=False)
    runs = codes[np.r_[True, codes[1:] != codes[:-1]]] if len(codes) else codes
    if len(np.unique(runs)) != len(runs):
        raise ValueError("each evaluation block label must be contiguous")
    result = np.empty_like(a)
    for code in np.unique(codes):
        ix = np.flatnonzero(codes == code)
        series = pd.Series(a[ix], index=ts[ix])
        # Preserve the candidate's pandas window endpoint convention.
        result[ix] = series.rolling(
            "60min", center=True, min_periods=1, closed="right"
        ).mean().to_numpy()
    if not np.isfinite(result).all():
        raise ValueError("nonfinite mean")
    return result
