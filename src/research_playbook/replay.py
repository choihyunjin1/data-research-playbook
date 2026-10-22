"""Portable, offline replay of the fixed Ocean gap-repair study.

Only an exact, user-supplied public NetCDF snapshot is accepted. The original
research directories and raw source are never modified. A replay is not new
holdout evidence. Call ``replay(input_root, output)`` from a source checkout.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
import uuid


CASE_ID = "ocean-gap-repair"
EXPECTED_METHOD_SHA = "6ae98feb21786c52ccc15d7f344e2f340b2c3a2a1bbd5ad18e7d9fa5a7f3a5f0"
EXPECTED_SELECTOR_SHA = "c64514bbafa145509472589cf708738117f18fd302f121816f96579b5dbbce0e"
ABSOLUTE_TOLERANCE = 2e-11


class ReplayError(ValueError):
    """A replay precondition or historical-equivalence check failed."""


def _case_root() -> Path:
    return Path(__file__).resolve().parents[2] / "cases" / CASE_ID


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_case(case_root: Path):
    contract = _read(case_root / "config/replay-contract.json")
    if contract["case_id"] != CASE_ID:
        raise ReplayError("Unknown case contract")
    for relative, expected in contract["component_sha256"].items():
        candidate = (case_root / relative).resolve()
        if not candidate.is_relative_to(case_root.resolve()) or not candidate.is_file():
            raise ReplayError(f"Missing or unsafe replay component: {relative}")
        if _sha(candidate) != expected:
            raise ReplayError(f"Replay component SHA mismatch: {relative}")
    for name, expected in (("method.py", EXPECTED_METHOD_SHA), ("selector.py", EXPECTED_SELECTOR_SHA)):
        if _sha(case_root / "frozen" / name) != expected:
            raise ReplayError(f"Frozen calculation changed: {name}")
    site = _read(case_root / "config/site.json")
    if "local_source_path" in site:
        raise ReplayError("Portable configuration must not contain a local source path")
    filename = site["source_filename"]
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise ReplayError("Source filename must be a basename")
    if site["depths_m"] != [33.0, 44.0, 55.0] or site["instrument_indices"] != [280, 278, 284]:
        raise ReplayError("Historical depth/instrument contract changed")
    return contract, site


def _preflight(input_root: Path, output: Path, case_root: Path | None = None):
    case_root = (case_root or _case_root()).resolve()
    supplied_output = Path(output).expanduser()
    if supplied_output.exists() or supplied_output.is_symlink():
        raise ReplayError("Output must not exist; choose a new replay directory")
    output = supplied_output.resolve()
    input_root = Path(input_root).expanduser().resolve()
    if not input_root.is_dir():
        raise ReplayError("Input root must be an existing directory containing the verified NetCDF")
    if output.is_relative_to(input_root) or output.is_relative_to(case_root):
        raise ReplayError("Output must be separate from the raw-input and case directories")
    contract, site = _validate_case(case_root)
    source = input_root / site["source_filename"]
    if not source.is_file():
        raise ReplayError(f"Required raw NetCDF is missing: {site['source_filename']}")
    if _sha(source) != site["source_sha256"]:
        raise ReplayError("Raw NetCDF SHA-256 mismatch; no output was created")
    return case_root, source, output, contract, site


def _load_source(name: str, path: Path):
    """Load our hash-checked source without creating __pycache__ files."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


@contextmanager
def _case_modules(case_root: Path, output: Path, source: Path):
    prefix = f"_research_replay_{uuid.uuid4().hex}"
    try:
        for suffix, directory in (("", case_root), (".frozen", case_root / "frozen"), (".replay", case_root / "replay")):
            package = types.ModuleType(prefix + suffix)
            package.__path__ = [str(directory)]
            package.__package__ = prefix + suffix
            sys.modules[prefix + suffix] = package
        context = types.ModuleType(prefix + ".replay.context")
        context.ROOT, context.SOURCE, context.CASE_ROOT = output, source, case_root
        context.CONTRACT_SHA = _sha(case_root / "config/replay-contract.json")
        context.now, context.sha = _now, _sha
        context.save = lambda name, value: _save(output / name, value)
        context.check_freeze = lambda: _validate_case(case_root)[0]
        sys.modules[context.__name__] = context
        modules = {}
        for name in ("method", "selector"):
            modules[name] = _load_source(prefix + ".frozen." + name, case_root / "frozen" / (name + ".py"))
        for name in ("extract", "analyze", "independent", "fingerprints"):
            modules[name] = _load_source(prefix + ".replay." + name, case_root / "replay" / (name + ".py"))
        yield modules
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]


def _compare_expected(output: Path, case_root: Path, fingerprints):
    """Independent math plus strict all-case digests and small historical tables."""
    import numpy as np
    import pandas as pd
    expectations = _read(case_root / "expected/fingerprints.json")
    checked = {}
    for name, expected in expectations["tables"].items():
        actual = fingerprints.table_fingerprint(output / name, expected["categorical"])
        if actual != expected:
            raise ReplayError(f"Historical whole-table fingerprint mismatch: {name}")
        checked[name] = {"rows": actual["rows"], "columns": len(actual["columns"]), "all_columns_match": True}
    maximum = {}
    for path in sorted((case_root / "expected").glob("*.csv")):
        expected = pd.read_csv(path, float_precision="round_trip")
        actual = pd.read_csv(output / path.name, float_precision="round_trip")
        if list(actual.columns) != list(expected.columns) or actual.shape != expected.shape:
            raise ReplayError(f"Historical schema/shape mismatch: {path.name}")
        largest = 0.0
        for key in expected:
            if pd.api.types.is_numeric_dtype(expected[key]) and not pd.api.types.is_bool_dtype(expected[key]):
                a, b = actual[key].to_numpy(float), expected[key].to_numpy(float)
                if not np.array_equal(np.isnan(a), np.isnan(b)) or not np.array_equal(np.isfinite(a), np.isfinite(b)):
                    raise ReplayError(f"Historical missingness mismatch: {path.name}/{key}")
                finite = np.isfinite(a)
                error = float(np.max(abs(a[finite] - b[finite]))) if finite.any() else 0.0
                if error >= ABSOLUTE_TOLERANCE:
                    raise ReplayError(f"Historical numeric mismatch: {path.name}/{key}: {error}")
                largest = max(largest, error)
            elif not actual[key].fillna("<NA>").equals(expected[key].fillna("<NA>")):
                raise ReplayError(f"Historical category mismatch: {path.name}/{key}")
        maximum[path.name] = largest
    return {"whole_table_fingerprints": checked, "summary_max_absolute_difference": maximum,
            "absolute_tolerance": ABSOLUTE_TOLERANCE,
            "fingerprint_policy": "Exact typed numeric/category column digests; no rounded acceptance"}


def replay(input_root: Path, output: Path) -> dict:
    """Recompute the final study offline, refusing existing output or wrong raw data.

    Preflight creates no output. Runtime failures retain a clearly failed receipt
    in the newly created output; they never overwrite or delete earlier runs.
    Requires numpy==2.3.5, pandas==3.0.1 and netCDF4==1.7.4 for the recorded replay.
    Returns the completed receipt after all source, historical and independent
    formula checks. Results are historical reproduction, not new model evidence.
    """
    if sys.flags.optimize:
        raise ReplayError("Run without Python -O: the historical checks use assertions")
    case_root, source, output, contract, site = _preflight(input_root, output)
    # Fail before mkdir on a missing numerical dependency.
    import numpy
    import pandas
    import netCDF4
    started = _now()
    with _case_modules(case_root, output, source) as modules:
        output.mkdir(parents=True, exist_ok=False)
        try:
            _save(output / "site.json", site)
            modules["extract"].main()
            modules["analyze"].main()
            independent = modules["independent"].main()
            equivalence = _compare_expected(output, case_root, modules["fingerprints"])
            _validate_case(case_root)
            if _sha(source) != site["source_sha256"]:
                raise ReplayError("Raw source changed during replay")
            outputs = {p.relative_to(output).as_posix(): _sha(p) for p in sorted(output.rglob("*")) if p.is_file()}
            receipt = {"status": "REPLAY_PASS", "case_id": CASE_ID, "started_at_utc": started,
                       "completed_at_utc": _now(), "historical_replay": True, "new_holdout": False,
                       "training_runs": 0, "rule_tuning_runs": 0, "network_access": False,
                       "source_filename": source.name, "source_sha256": site["source_sha256"],
                       "replay_contract_sha256": _sha(case_root / "config/replay-contract.json"),
                       "environment": {"python": sys.version.split()[0], "numpy": numpy.__version__,
                                       "pandas": pandas.__version__, "netCDF4": netCDF4.__version__},
                       "cases": independent["cases"], "eligible_dates": independent["eligible_dates"],
                       "source_records": independent["source_records"],
                       "independent_status": independent["status"],
                       "independent_max_absolute_errors": independent["max_absolute_errors"],
                       "historical_equivalence": equivalence, "output_sha256": outputs,
                       "claim_limit": "Numerical reproduction only; no new site, tuning, operational deployment or universal superiority"}
            _save(output / "replay-receipt.json", receipt)
            return receipt
        except Exception as error:
            _save(output / "replay-failure.json", {"status": "REPLAY_FAILED", "at_utc": _now(),
                                                   "error_type": type(error).__name__, "message": str(error),
                                                   "historical_replay": True})
            raise
