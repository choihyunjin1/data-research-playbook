"""Non-reversible table fingerprints; no raw or full case table is bundled."""
import csv
import hashlib
import json
import math


def table_fingerprint(path, categorical):
    """Hash typed column streams, independent of CSV newline conventions.

    Numeric floats are encoded with float.hex(), not rounded. The strict historic
    fingerprint supplements (does not replace) independent tolerance-based math.
    No observed value is returned in the fingerprint.
    """
    categorical = set(categorical)
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames
        if not fields or len(set(fields)) != len(fields):
            raise ValueError("Unique nonempty CSV header required")
        if not categorical.issubset(fields):
            raise ValueError("Unknown categorical columns")
        digests = {key: hashlib.sha256() for key in fields}
        missing = {key: 0 for key in fields}
        rows = 0
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Ragged CSV")
            rows += 1
            for key in fields:
                value = row[key]
                if key not in categorical:
                    number = float(value) if value else math.nan
                    if math.isnan(number):
                        value = "NaN"
                        missing[key] += 1
                    else:
                        value = number.hex()
                encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
                digests[key].update(encoded + b"\n")
    return {"rows": rows, "columns": fields,
            "categorical": sorted(categorical),
            "column_sha256": {k: v.hexdigest() for k, v in digests.items()},
            "numeric_missing": {k: missing[k] for k in fields if k not in categorical}}
