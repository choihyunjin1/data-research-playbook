"""MIT. Synthetic association/observation contracts, not real crawler validation."""

import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest


CASE = Path(__file__).resolve().parents[1] / "cases" / "savetax-crawler" / "synthetic_replay.py"
SPEC = importlib.util.spec_from_file_location("savetax_synthetic_replay", CASE)
replay = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = replay
SPEC.loader.exec_module(replay)


class SaveTaxSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.case = replay.shared_url_fixture()
        self.addCleanup(self.case.close)

    def test_normal_comparable_price_preserves_distinct_registration_amount(self):
        row = self.case.snapshot()["rows"][0]
        self.assertEqual(row["registration_price_minor"], 2400)
        self.assertEqual(row["seller_observed_price_minor"], 1200)
        self.assertEqual(row["comparable_market_price_minor"], 1200)
        self.assertEqual(row["state"], "comparable_in_synthetic_fixture")

    def test_shared_url_quarantine_excludes_only_the_wrong_association(self):
        self.case.quarantine("source-mislinked", "synthetic model conflict")
        result = self.case.snapshot()
        good, wrong, unsearched = result["rows"]
        self.assertEqual(good["url"], wrong["url"])
        self.assertEqual(good["comparable_market_price_minor"], 1200)
        self.assertIsNone(wrong["comparable_market_price_minor"])
        self.assertEqual(wrong["state"], "association_quarantined")
        self.assertEqual(unsearched["state"], "no_source")
        self.assertEqual(result["seller_pages_with_latest_price"], 1)
        self.assertEqual(result["comparable_market_price_rows"], 1)

    def test_quarantine_preserves_original_observations_and_history(self):
        raw_before = list(map(tuple, self.case.db.execute("SELECT * FROM observations")))
        history_before = list(map(tuple, self.case.db.execute("SELECT * FROM history ORDER BY event_id")))
        self.case.quarantine("source-mislinked", "synthetic mismatch")
        self.case.quarantine("source-mislinked", "same hold again")
        self.assertEqual(list(map(tuple, self.case.db.execute("SELECT * FROM observations"))), raw_before)
        history_after = list(map(tuple, self.case.db.execute("SELECT * FROM history ORDER BY event_id")))
        self.assertEqual(history_after[:len(history_before)], history_before)
        self.assertEqual(len(history_after), len(history_before) + 1)
        self.assertEqual(history_after[-1][1:], ("source-mislinked", "quarantined", "synthetic mismatch"))
        with self.assertRaises(KeyError):
            self.case.quarantine("nonexistent-source", "must not affect any shared URL")

    def test_latest_unknown_does_not_backfill_even_after_older_import(self):
        self.case.observe("fiction-page", 20, None, "Invented latest page without a price.")
        self.case.observe("fiction-page", 15, 1100, "Invented older observation imported later.")
        result = self.case.snapshot()
        for row in result["rows"][:2]:
            self.assertEqual(row["latest_observation_tick"], 20)
            self.assertIsNone(row["seller_observed_price_minor"])
            self.assertIsNone(row["comparable_market_price_minor"])
            self.assertEqual(row["state"], "latest_price_unknown")
        self.assertEqual(result["seller_pages_with_latest_price"], 0)
        self.assertEqual(self.case.db.execute("SELECT COUNT(*) FROM observations").fetchone()[0], 3)

    def test_complete_inventory_does_not_mean_comparable_market_coverage(self):
        case = replay.Replay([replay.Item("unconfirmed", 1, 900)])
        self.addCleanup(case.close)
        case.add_document("page", "https://example.invalid/unconfirmed")
        case.add_source("source", "unconfirmed", "page", comparison_ready=False)
        case.observe("page", 1, 700, "Invented price; package and tax terms unknown.")
        result = case.snapshot()
        self.assertTrue(result["snapshot_complete"])
        self.assertEqual(result["inventory_rows"], result["snapshot_rows"])
        self.assertEqual(result["seller_pages_with_latest_price"], 1)
        self.assertEqual(result["comparable_market_price_rows"], 0)
        self.assertEqual(result["rows"][0]["state"], "conditions_unconfirmed")

    def test_fixed_order_and_500_row_batches_survive_shuffled_input(self):
        items = [replay.Item(f"fiction-{n}", n, 100) for n in range(1, 502)]
        case = replay.Replay(reversed(items))
        self.addCleanup(case.close)
        batches = case.batches()
        self.assertEqual([len(batch) for batch in batches], [500, 1])
        self.assertEqual([item for batch in batches for item in batch], [i.item_id for i in items])
        self.assertEqual([r["item_id"] for r in case.snapshot()["rows"]], [i.item_id for i in items])
        for size in (0, -1, True, 2.5):
            with self.subTest(size=size), self.assertRaises(ValueError):
                case.batches(size)

    def test_duplicates_missing_rows_and_invalid_observations_are_rejected(self):
        rows = self.case.snapshot()["rows"]
        for invalid in (rows + rows[:1], rows[:-1], list(reversed(rows)), rows + [{"item_id": "extra"}]):
            with self.subTest(rows=len(invalid)), self.assertRaises(ValueError):
                replay.validate_snapshot(invalid, self.case.expected_ids)
        for items in ([replay.Item("a", 1, 1), replay.Item("a", 2, 1)],
                      [replay.Item("a", 1, 1), replay.Item("b", 3, 1)]):
            with self.subTest(items=items), self.assertRaises(ValueError):
                replay.Replay(items)
        for amount in (0, -1, True, 1.5, "100"):
            with self.subTest(amount=amount), self.assertRaises(ValueError):
                self.case.observe("fiction-page", 30, amount, "Invalid synthetic price.")
        with self.assertRaises(sqlite3.IntegrityError):
            self.case.observe("fiction-page", 10, 1300, "Cannot overwrite an earlier observation.")
        self.assertEqual(self.case.snapshot()["rows"][0]["seller_observed_price_minor"], 1200)

    def test_cli_is_labeled_synthetic_and_preserves_stage_results(self):
        run = subprocess.run([sys.executable, "-B", str(CASE)], check=True, capture_output=True, text=True)
        result = json.loads(run.stdout)
        self.assertTrue(result["synthetic"])
        self.assertEqual(result["preserved_observations"], 2)
        self.assertEqual(result["preserved_history_events"], 3)
        stages = [result[key] for key in ("initial_incorrect_fixture", "after_association_quarantine",
                                         "after_latest_price_unknown")]
        self.assertEqual([stage["comparable_market_price_rows"] for stage in stages], [2, 1, 0])
        self.assertTrue(all(stage["snapshot_complete"] for stage in stages))


if __name__ == "__main__":
    unittest.main()
