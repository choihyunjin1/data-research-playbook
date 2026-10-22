"""Portable contracts extracted/adapted from the synthetic Ocean evolution lab.

These functions check input behavior, not model quality or scientific truth.
"""
from decimal import Decimal, InvalidOperation
import numpy as np
import pandas as pd


def exact_integer(value, *, name="identifier", minimum=0, maximum=2**53):
    """Reject a fractional identity before a lossy cast; accept integral strings.

An upstream float may already have lost precision. This function cannot recover
digits lost before it receives the value. Bounds are explicit business choices.
"""
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (str, int, float, np.integer, np.floating, Decimal)
    ):
        raise ValueError(f"{name} must be a numeric integer identity")
    try:
        numeric = value if isinstance(value, Decimal) else Decimal(str(value))
        if not numeric.is_finite() or not minimum <= numeric <= maximum:
            raise ValueError(f"{name} must be finite within {minimum}..{maximum}")
        if numeric != numeric.to_integral_value():
            raise ValueError(f"{name} must be integral before conversion")
        return int(numeric)
    except (InvalidOperation, TypeError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite exact integer identity") from exc


def finite_clip(values, lower, upper):
    """Reject NaN/Inf before clipping; preserve clipping of finite outliers."""
    if not np.isfinite([lower, upper]).all() or lower > upper:
        raise ValueError("finite ordered clip bounds required")
    try:
        a = np.asarray(values, dtype=float)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("numeric values required") from exc
    if not np.isfinite(a).all():
        raise ValueError("values must be finite BEFORE clipping")
    return np.clip(a, lower, upper)


def boundary_mean(times, values, blocks, *, half_window="30min"):
    """Centered mean inside contiguous evaluation blocks; return support counts.

One series per call. Missing timestamps are not filled. Blocks must be explicit,
nonmissing labels, aligned with sorted unique timestamps; a label cannot recur
after another block. This is retrospective, not a causal forecast transform.
Both time-window endpoints are included. This is not a drop-in replacement for
pandas rolling(), whose default interval closure differs at exact boundaries.
"""
    if any(isinstance(t, (int, float, bool, np.number)) for t in times):
        raise ValueError("timestamps must not be numeric aliases")
    ts = pd.DatetimeIndex(pd.to_datetime(times, utc=True, errors="raise"))
    a = np.asarray(values, dtype=float)
    b = np.asarray(blocks, dtype=object)
    if not len(ts) or a.shape != (len(ts),) or b.shape != (len(ts),):
        raise ValueError("nonempty aligned one-dimensional inputs required")
    if ts.hasnans or not ts.is_unique or not ts.is_monotonic_increasing:
        raise ValueError("timestamps must be finite, sorted and unique")
    if not np.isfinite(a).all() or pd.isna(b).any():
        raise ValueError("finite values and nonmissing blocks required")
    if any(isinstance(x, str) and not x.strip() for x in b):
        raise ValueError("blank block")
    try:
        codes, _ = pd.factorize(b, sort=False)
    except TypeError as exc:
        raise ValueError("block labels must be hashable") from exc
    transitions = codes[np.r_[True, codes[1:] != codes[:-1]]]
    if len(np.unique(transitions)) != len(transitions):
        raise ValueError("each block label must form a contiguous run")
    width = pd.Timedelta(half_window)
    if pd.isna(width) or width < pd.Timedelta(0):
        raise ValueError("nonnegative finite half_window required")
    ticks = ts.as_unit("ns").asi8
    result = np.empty_like(a); support = np.zeros(len(a), dtype=int)
    for code in np.unique(codes):
        ix = np.flatnonzero(codes == code); t = ticks[ix]
        for k, tick in enumerate(t):
            lo = np.searchsorted(t, int(tick) - width.value, side="left")
            hi = np.searchsorted(t, int(tick) + width.value, side="right")
            support[ix[k]] = hi-lo
            result[ix[k]] = np.sum(a[ix[lo:hi]] / (hi-lo))
    if not np.isfinite(result).all():
        raise ValueError("nonfinite mean")
    return result, support
