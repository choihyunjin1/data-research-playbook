"""Score fixed synthetic outputs; no candidate generation, fitting or selection.

MIT. This case accepts nonnegative integer counts and exactly hours 0..3
per day. Empty observed_count means missing; observed zero is retained.
All methods use the same complete days, with equal weight per day.
"""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re


CASE = Path(__file__).resolve().parent
FIELDS = (
    "day", "hour", "true_count", "observed_count",
    "time_estimate", "neighbor_estimate", "choice",
)


def count(value, field):
    if not isinstance(value, str) or re.fullmatch(r"[0-9]+", value) is None:
        raise ValueError(f"{field}: expected a nonnegative integer")
    return int(value)


def reconstruct(rows):
    """Reconstruct totals from observed values and saved outputs, not truth.

    This separation does NOT prove that upstream candidates or choices were
    generated without leakage. Their generation evidence was not supplied.
    """
    days = {}
    for row in rows:
        day = row["day"]
        if not day or day != day.strip():
            raise ValueError("day: expected a nonempty label without outer spaces")
        hour = count(row["hour"], "hour")
        if hour not in range(4):
            raise ValueError("hour: expected 0..3")
        choice = row["choice"]
        if choice not in {"time", "neighbor"}:
            raise ValueError("choice: expected a fixed time or neighbor label")
        entry = days.setdefault(day, {"hours": set(), "choice": choice,
                                      "time": 0, "neighbor": 0, "selected": 0})
        if hour in entry["hours"]:
            raise ValueError("duplicate day/hour")
        if choice != entry["choice"]:
            raise ValueError("choice must be consistent within a day")
        entry["hours"].add(hour)
        observed = row["observed_count"]
        if observed == "":
            temporal = count(row["time_estimate"], "time_estimate")
            neighbor = count(row["neighbor_estimate"], "neighbor_estimate")
        else:
            temporal = neighbor = count(observed, "observed_count")
        entry["time"] += temporal
        entry["neighbor"] += neighbor
        entry["selected"] += temporal if choice == "time" else neighbor
    if not days or any(entry["hours"] != {0, 1, 2, 3} for entry in days.values()):
        raise ValueError("each day must contain exactly hours 0..3; no empty cohort")
    return [{"day": day, **{key: value for key, value in entry.items() if key != "hours"}}
            for day, entry in sorted(days.items())]


def evaluate(rows):
    totals = reconstruct(rows)
    truth = {}
    for row in rows:
        truth[row["day"]] = truth.get(row["day"], 0) + count(row["true_count"], "true_count")
    for row in totals:
        row["truth"] = truth[row["day"]]
        for method in ("time", "neighbor", "selected"):
            row[method + "_error"] = row[method] - row["truth"]
    n = len(totals)
    metrics = {}
    for method in ("time", "neighbor", "selected"):
        errors = [row[method + "_error"] for row in totals]
        mse = sum(error ** 2 for error in errors) / n
        metrics[method] = {"days": n, "mae": sum(abs(error) for error in errors) / n,
                           "mse": mse, "rmse": math.sqrt(mse)}
    missed = sum(max(row["time_error"] ** 2 - row["neighbor_error"] ** 2, 0)
                 for row in totals if row["choice"] == "time") / n
    avoided = sum(max(row["neighbor_error"] ** 2 - row["time_error"] ** 2, 0)
                  for row in totals if row["choice"] == "time") / n
    net = metrics["selected"]["mse"] - metrics["neighbor"]["mse"]
    if not math.isclose(net, missed - avoided, abs_tol=1e-12):
        raise AssertionError("same-cohort MSE decomposition failed")
    return {
        "scope": "fixed synthetic saved outputs; 4-hour total per day; not upstream leakage or generalization validation",
        "units": {"totals_mae_rmse": "rental count", "mse_and_accounting": "rental count squared"},
        "cohort": {"days": n, "rows": len(rows), "excluded_days": 0, "weight": "equal per complete day"},
        "daily_totals": totals,
        "metrics": metrics,
        "accounting": {"denominator_days": n, "missed_gain": missed, "avoided_harm": avoided,
                       "selected_minus_neighbor_mse": net},
    }


def calculate(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(FIELDS):
            raise ValueError("unexpected CSV columns")
        rows = list(reader)
    if any(set(row) != set(FIELDS) or any(value is None for value in row.values()) for row in rows):
        raise ValueError("malformed CSV row")
    result = evaluate(rows)
    result["input_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="compare computed values with saved results.json")
    args = parser.parse_args()
    result = calculate(CASE / "results-input.csv")
    if args.verify:
        saved = json.loads((CASE / "results.json").read_text(encoding="utf-8"))
        if saved != result:
            raise SystemExit("saved results differ from fixed-input recalculation")
        print("Synthetic bike-rental totals and MSE accounting PASS")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
