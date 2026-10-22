"""Run with -B: read-only imports, synthetic assertions, stdout only."""
import importlib.util
import json
from decimal import Decimal
from pathlib import Path
import unittest

import numpy as np
from research_playbook.contracts import boundary_mean
import meter_fixed as fixed


ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("meter_candidate", ROOT / "meter_candidate.py")
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
TIMES = [f"2026-01-01T00:{minute:02d}:00Z" for minute in (0, 10, 20, 30)]


class ReuseTests(unittest.TestCase):
    def test_identity_valid_regression(self):
        for value in (1, 999, 2, 2.0, "2", "2.0", Decimal("2"), np.int64(2)):
            with self.subTest(value=value):
                self.assertEqual(fixed.device_id(value), original.device_id(value))

    def test_identity_invalid_before_cast(self):
        for value in (2.9, "2.000000000000000000001", True, np.bool_(True), 0, 1000,
                      None, float("nan"), float("inf"), "1e100000", []):
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                fixed.device_id(value)

    def test_finite_clipping_regression_and_no_mutation(self):
        values = np.array([[-2.0, 20.0, 150.0]])
        before = values.copy()
        np.testing.assert_array_equal(fixed.cap_prediction(values), original.cap_prediction(values))
        np.testing.assert_array_equal(fixed.cap_prediction(values), [[0, 20, 100]])
        np.testing.assert_array_equal(values, before)

    def test_nonfinite_clipping_rejected(self):
        for value in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                fixed.cap_prediction([value])

    def test_single_block_regression(self):
        for times, values in ((TIMES, [10, 12, 100, 102]),
                              (TIMES[::-1], [102, 100, 12, 10]),
                              ([TIMES[0], TIMES[0], TIMES[1]], [10, 20, 30]),
                              ([], [])):
            blocks = ["same"] * len(times)
            with self.subTest(times=times):
                np.testing.assert_array_equal(
                    fixed.average_prediction(times, values, blocks),
                    original.average_prediction(times, values, blocks),
                )

    def test_exact_window_edge_not_blind_wrapper(self):
        times = [TIMES[0], TIMES[3]]
        old = original.average_prediction(times, [10, 20], ["a", "a"])
        library, _ = boundary_mean(times, [10, 20], ["a", "a"])
        np.testing.assert_array_equal(old, [15, 20])
        np.testing.assert_array_equal(library, [15, 15])
        np.testing.assert_array_equal(fixed.average_prediction(times, [10, 20], ["a", "a"]), old)

    def test_block_isolation(self):
        np.testing.assert_array_equal(
            fixed.average_prediction(TIMES, [10, 12, 100, 102], ["a", "a", "b", "b"]),
            [11, 11, 101, 101],
        )

    def test_other_block_mutation_both_directions(self):
        blocks = ["a", "a", "b", "b"]
        base = fixed.average_prediction(TIMES, [10, 12, 100, 102], blocks)
        b_changed = fixed.average_prediction(TIMES, [10, 12, -999, 999], blocks)
        a_changed = fixed.average_prediction(TIMES, [-999, 999, 100, 102], blocks)
        np.testing.assert_array_equal(base[:2], b_changed[:2])
        np.testing.assert_array_equal(base[2:], a_changed[2:])

    def test_actual_distance_no_timestamp_fill(self):
        times = ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"]
        np.testing.assert_array_equal(fixed.average_prediction(times, [1, 10], ["a", "a"]), [1, 10])

    def test_average_invalid_values_and_blocks(self):
        for values, blocks in (([1, np.nan], ["a", "b"]), ([1, np.inf], ["a", "b"]),
                               ([1, 2], ["a", None]), ([1, 2], ["a", " "]),
                               ([1, 2], ["a"]), ([[1, 2]], ["a", "b"])):
            with self.subTest(values=values, blocks=blocks), self.assertRaises(ValueError):
                fixed.average_prediction(TIMES[:2], values, blocks)
        with self.assertRaises(ValueError):
            fixed.average_prediction(TIMES[:3], [1, 2, 3], ["a", "b", "a"])

    def test_average_bad_time_and_no_mutation(self):
        with self.assertRaises(ValueError):
            fixed.average_prediction([TIMES[0], TIMES[2], TIMES[1]], [1, 2, 3], ["a"] * 3)
        with self.assertRaises(ValueError):
            fixed.average_prediction([TIMES[0], None], [1, 2], ["a", "b"])
        values = np.array([10, 12, 100, 102.0])
        before = values.copy()
        fixed.average_prediction(TIMES, values, ["a", "a", "b", "b"])
        np.testing.assert_array_equal(values, before)


if __name__ == "__main__":
    print(json.dumps({
        "original_fractional_id": original.device_id(2.9),
        "original_precise_fractional_string": original.device_id("2.000000000000000000001"),
        "original_out_of_range_ids": [original.device_id(0), original.device_id(1000)],
        "original_inf_clip": original.cap_prediction([np.inf, -np.inf]).tolist(),
        "original_nan_survives": bool(np.isnan(original.cap_prediction([np.nan])[0])),
        "original_mixed_mean": original.average_prediction(TIMES, [10, 12, 100, 102], ["a", "a", "b", "b"]).tolist(),
        "fixed_isolated_mean": fixed.average_prediction(TIMES, [10, 12, 100, 102], ["a", "a", "b", "b"]).tolist(),
    }, indent=2), flush=True)
    unittest.main(verbosity=2)
