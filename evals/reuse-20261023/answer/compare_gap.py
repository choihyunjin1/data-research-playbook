"""Compare one synthetic masked day; no fitting and no output-file writes."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
FROZEN = Path(__file__).resolve().parents[3] / "cases/ocean-gap-repair/frozen/method.py"
spec = importlib.util.spec_from_file_location("frozen_gap_method", FROZEN)
method = importlib.util.module_from_spec(spec)
spec.loader.exec_module(method)

frame = pd.read_csv(ROOT / "gap-example.csv")
np.testing.assert_array_equal(frame["hour"], np.arange(-1, 25))
complete = frame[["top", "target", "bottom"]].to_numpy(dtype=float)
truth_day = complete[1:25, 1].copy()  # scoring only, never passed into predict
start, length = 9, 6  # central six hours of 00:00..23:00: 09:00..14:00
q = 1 + start


def masked_input(source):
    masked = source.copy()
    masked[q:q + length, 1] = np.nan
    return masked


masked = masked_input(complete)
means, fills, supported = method.predict(masked, start, length)
unmasked_rejected = False
try:
    method.predict(complete, start, length)
except ValueError as exc:
    assert str(exc) == "Mask hidden target first"
    unmasked_rejected = True
assert unmasked_rejected

# A hidden-answer mutation must not change the input delivered to the method.
mutated = complete.copy()
mutated[q:q + length, 1] = [12345, -9999, 1e6, -1e6, 6789, -4321]
masked_mutant = masked_input(mutated)
np.testing.assert_array_equal(masked, masked_mutant)
mutant_means, mutant_fills, mutant_supported = method.predict(masked_mutant, start, length)
assert means == mutant_means and supported == mutant_supported
for name in fills:
    np.testing.assert_array_equal(fills[name], mutant_fills[name])

truth_mean = float(truth_day.mean())
np.testing.assert_allclose(means["temporal"], 10.0, rtol=0, atol=1e-12)
np.testing.assert_allclose(means["bridge"], 9.75, rtol=0, atol=1e-12)
assert supported
np.testing.assert_array_equal(complete, frame[["top", "target", "bottom"]].to_numpy(dtype=float))

report = {
    "source": "provided synthetic CSV; one day only; no real-site performance inference",
    "evaluation_hours": list(range(24)),
    "masked_hours": list(range(start, start + length)),
    "visible_boundary_hours": [start - 1, start + length],
    "default_frozen_depths": list(method.DEPTHS),
    "truth_daily_mean": truth_mean,
    "remaining_count": 24 - length,
    "remaining_daily_mean": means["remaining"],
    "bridge_supported": supported,
    "unmasked_input_rejected": unmasked_rejected,
    "hidden_truth_mutation_invariance": True,
    "methods": {
        name: {
            "fills": fills[name].tolist(),
            "daily_mean": means[name],
            "signed_daily_mean_error": means[name] - truth_mean,
            "absolute_daily_mean_error": abs(means[name] - truth_mean),
            "squared_daily_mean_error": (means[name] - truth_mean) ** 2,
        }
        for name in ("temporal", "bridge")
    },
}
print(json.dumps(report, indent=2, allow_nan=False))
