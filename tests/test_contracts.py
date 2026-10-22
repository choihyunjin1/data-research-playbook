import unittest
from decimal import Decimal
import numpy as np
from research_playbook.contracts import exact_integer, finite_clip, boundary_mean


class ContractTests(unittest.TestCase):
    def test_valid_identity(self):
        for value in [2, 2.0, "2.0", Decimal("2"), np.int64(2)]:
            self.assertEqual(exact_integer(value), 2)

    def test_invalid_identity(self):
        for value in [2.9, "2.000000000000000000001", True, None, float("nan"), "Inf", [], -1, "1e100000"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                exact_integer(value)

    def test_finite_clip_preserves_normal_behavior(self):
        a = np.array([-2., 20., 150.]); before = a.copy()
        np.testing.assert_array_equal(finite_clip(a, 0, 100), [0, 20, 100])
        np.testing.assert_array_equal(a, before)

    def test_nonfinite_clip_and_invalid_bounds(self):
        for value in [float("inf"), -float("inf"), float("nan")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                finite_clip([value], 0, 100)
        with self.assertRaises(ValueError): finite_clip([1], 10, 0)

    def test_boundary_isolation_and_support(self):
        ts = ["2025-01-01T00:00Z", "2025-01-01T00:10Z", "2025-01-01T00:20Z", "2025-01-01T00:30Z"]
        out, n = boundary_mean(ts, [10, 12, 100, 102], ["a", "a", "b", "b"])
        np.testing.assert_array_equal(out, [11, 11, 101, 101]); np.testing.assert_array_equal(n, [2]*4)
        changed, _ = boundary_mean(ts, [10, 12, -999, 999], ["a", "a", "b", "b"])
        np.testing.assert_array_equal(changed[:2], out[:2])

    def test_missing_timestamps_are_not_filled(self):
        out, n = boundary_mean(["2025-01-01T00:00Z", "2025-01-02T00:00Z"], [1, 10], ["a", "a"])
        np.testing.assert_array_equal(out, [1, 10]); np.testing.assert_array_equal(n, [1, 1])

    def test_bad_block_contract(self):
        ts = ["2025-01-01T00:00Z", "2025-01-01T00:10Z", "2025-01-01T00:20Z"]
        for blocks in [["a", "b", "a"], ["a", None, "a"], ["a", "", "b"]]:
            with self.subTest(blocks=blocks), self.assertRaises(ValueError): boundary_mean(ts, [1, 2, 3], blocks)
        with self.assertRaises(ValueError): boundary_mean(ts[::-1], [1, 2, 3], [1]*3)

    def test_zero_window(self):
        out, n = boundary_mean(["2025-01-01T00:00Z"], [1], [1], half_window="0s")
        np.testing.assert_array_equal(out, [1]); self.assertEqual(n[0], 1)

    def test_both_window_endpoints_are_included(self):
        ts = ["2025-01-01T00:00Z", "2025-01-01T00:30Z", "2025-01-01T01:00Z"]
        out, n = boundary_mean(ts, [0, 30, 90], ["a"]*3)
        self.assertEqual(out[1], 40); self.assertEqual(n[1], 3)


if __name__ == "__main__": unittest.main()
