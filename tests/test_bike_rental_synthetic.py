"""MIT. Arithmetic and invalid-input tests for one synthetic case only."""

import copy
import csv
import importlib.util
import json
from pathlib import Path
import unittest


CASE = Path(__file__).resolve().parents[1] / "cases" / "bike-rental-synthetic"
SPEC = importlib.util.spec_from_file_location("bike_evaluate", CASE / "evaluate.py")
evaluation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluation)


class BikeSyntheticTests(unittest.TestCase):
    def setUp(self):
        with (CASE / "results-input.csv").open(encoding="utf-8", newline="") as stream:
            self.rows = list(csv.DictReader(stream))

    def test_fixed_totals_and_full_denominator(self):
        result = evaluation.evaluate(self.rows)
        self.assertEqual([(r["truth"], r["time"], r["neighbor"], r["selected"])
                          for r in result["daily_totals"]],
                         [(110, 100, 110, 110), (150, 140, 150, 140),
                          (60, 60, 80, 60), (60, 60, 80, 60)])
        self.assertEqual(result["metrics"]["time"]["mse"], 50)
        self.assertEqual(result["metrics"]["neighbor"]["mse"], 200)
        self.assertEqual(result["metrics"]["selected"]["mse"], 25)
        self.assertEqual(result["metrics"]["selected"]["rmse"], 5)
        self.assertEqual(result["accounting"], {"denominator_days": 4, "missed_gain": 25,
                         "avoided_harm": 200, "selected_minus_neighbor_mse": -175})

    def test_saved_result_equivalence(self):
        self.assertEqual(evaluation.calculate(CASE / "results-input.csv"),
                         json.loads((CASE / "results.json").read_text(encoding="utf-8")))

    def test_observed_zero_is_not_missing(self):
        self.rows[8]["time_estimate"] = "999"
        self.rows[8]["neighbor_estimate"] = "999"
        self.assertEqual(evaluation.reconstruct(self.rows)[2]["time"], 60)

    def test_truth_mutation_cannot_change_reconstruction_of_saved_outputs(self):
        changed = copy.deepcopy(self.rows)
        for row in changed:
            row["true_count"] = "999"
        self.assertEqual(evaluation.reconstruct(changed), evaluation.reconstruct(self.rows))
        self.assertNotEqual(evaluation.evaluate(changed)["metrics"], evaluation.evaluate(self.rows)["metrics"])

    def test_order_does_not_change_results(self):
        self.assertEqual(evaluation.evaluate(list(reversed(self.rows))), evaluation.evaluate(self.rows))

    def test_empty_duplicate_and_incomplete_cohorts_fail(self):
        for rows in ([], self.rows + [self.rows[0]], self.rows[1:]):
            with self.subTest(rows=len(rows)), self.assertRaises(ValueError):
                evaluation.evaluate(rows)

    def test_invalid_counts_and_missing_candidate_fail(self):
        for field, index in (("true_count", 0), ("observed_count", 0),
                             ("time_estimate", 1), ("neighbor_estimate", 1)):
            values = ["-1", "2.5", "NaN", "Inf", ""] if field != "observed_count" else ["-1", "2.5", "NaN", "Inf"]
            for value in values:
                changed = copy.deepcopy(self.rows)
                changed[index][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    evaluation.evaluate(changed)

    def test_invalid_hour_or_choice_fail(self):
        for field, value in (("hour", "4"), ("hour", "1.5"), ("choice", "oracle"), ("choice", "time")):
            changed = copy.deepcopy(self.rows)
            changed[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                evaluation.evaluate(changed)


if __name__ == "__main__":
    unittest.main()
