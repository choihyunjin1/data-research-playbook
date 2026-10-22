"""Offline synthetic examples in inventory and power-meter domains."""
from .contracts import exact_integer, finite_clip, boundary_mean


def run():
    rejected = []
    for value in ("2.9", "2.000000000000000000001", True):
        try:
            exact_integer(value, name="warehouse_id", minimum=1, maximum=99)
        except ValueError:
            rejected.append(repr(value))
    try:
        finite_clip([float("inf")], 0, 100)
    except ValueError:
        bad_prediction_rejected = True
    times = ["2025-01-01T00:00Z", "2025-01-01T00:10Z", "2025-01-01T00:20Z", "2025-01-01T00:30Z"]
    means, support = boundary_mean(times, [10, 12, 100, 102], ["train", "train", "validation", "validation"])
    return {"source": "synthetic; no real observations or model fitting", "valid_warehouse_id": exact_integer("2.0"),
            "rejected_identifiers": rejected, "nonfinite_prediction_rejected": bad_prediction_rejected,
            "finite_outlier_clip": finite_clip([-2, 20, 150], 0, 100).tolist(),
            "meter_boundary_mean": means.tolist(), "support": support.tolist(),
            "scope": "input-contract examples, not evidence of field performance"}
