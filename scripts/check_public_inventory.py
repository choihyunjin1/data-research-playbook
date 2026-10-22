"""Check explicit public-path selection, never infer publication permission.

Both PUBLIC_MANIFEST.json and provenance/PUBLIC_FILES.json require inventory
entries. The manifest's self-exclusion applies only to its byte fingerprints.
This is a structural check: a nonempty attestation does not prove that its
rights or privacy assessment is correct, or still current after a file edit.
"""

import argparse
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = "provenance/PUBLIC_FILES.json"
REVIEW_FIELDS = ("purpose", "rights", "selection", "privacy_review")
PLACEHOLDERS = {
    "unknown", "unreviewed", "pending", "todo", "tbd", "n/a",
    "미확인", "검토 전", "검토 필요", "보류",
}


def safe_relative_path(value):
    """Accept canonical, portable relative paths without normalizing them."""
    if not isinstance(value, str) or not value or value != value.strip():
        return False
    if value.startswith("/") or "\\" in value or ":" in value:
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    return all(part not in ("", ".", "..") for part in value.split("/"))


def validate_inventory(document, tracked_paths):
    """Compare inventory metadata with Git's selected paths, without writes."""
    errors = []
    tracked = set(tracked_paths)
    for path in sorted(tracked):
        if not safe_relative_path(path):
            errors.append({"path": path, "reason": "unsafe tracked path"})

    if not isinstance(document, dict) or not isinstance(document.get("entries"), list):
        entries = []
        errors.append({"path": INVENTORY, "reason": "entries must be a JSON list"})
    else:
        entries = document["entries"]

    listed = set()
    for position, entry in enumerate(entries):
        label = f"entry[{position}]"
        if not isinstance(entry, dict):
            errors.append({"path": label, "reason": "entry must be an object"})
            continue
        path = entry.get("path")
        if not safe_relative_path(path):
            errors.append({"path": label, "reason": "unsafe or missing inventory path"})
            continue
        if path in listed:
            errors.append({"path": path, "reason": "duplicate inventory entry"})
        listed.add(path)
        for field in REVIEW_FIELDS:
            value = entry.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append({"path": path, "reason": f"missing {field} attestation"})
            elif value.strip().casefold() in PLACEHOLDERS:
                errors.append({"path": path, "reason": f"unreviewed {field} attestation"})

    missing = sorted(tracked - listed)
    stale = sorted(listed - tracked)
    errors.extend({"path": path, "reason": "tracked path has no inventory entry"} for path in missing)
    errors.extend({"path": path, "reason": "inventory path is not tracked"} for path in stale)
    return {
        "scope": "tracked-path coverage and explicit review fields; not rights/privacy certification",
        "tracked_files": len(tracked),
        "inventory_entries": len(entries),
        "missing_tracked": missing,
        "stale_entries": stale,
        "errors": errors,
        "status": "FAIL" if errors else "PASS",
    }


def git_paths(root, *, untracked=False):
    args = ["git", "ls-files", "-z"]
    if untracked:
        args.extend(["--others", "--exclude-standard"])
    raw = subprocess.check_output(args, cwd=root, stderr=subprocess.PIPE)
    return [path for path in raw.decode("utf-8").split("\0") if path]


def check(root=ROOT):
    """Check worktree metadata against tracked paths, including staged additions."""
    root = Path(root).resolve()
    tracked = git_paths(root)
    try:
        document = json.loads((root / INVENTORY).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return {
            "scope": "tracked-path coverage; inventory could not be read",
            "errors": [{"path": INVENTORY, "reason": f"invalid inventory: {type(exc).__name__}"}],
            "status": "FAIL",
        }
    result = validate_inventory(document, tracked)
    for name in tracked:
        if not safe_relative_path(name):
            continue
        path = root / name
        # A selected symlink must not silently expand publication scope.
        if any(part.is_symlink() for part in (path, *path.parents) if part != root and root in part.parents):
            result["errors"].append({"path": name, "reason": "symlink path needs separate publication policy"})
        elif not path.is_file() or not path.resolve().is_relative_to(root):
            result["errors"].append({"path": name, "reason": "tracked path is not a local regular file"})
    result["status"] = "FAIL" if result["errors"] else "PASS"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true", help="verify tracked selection (default)")
    mode.add_argument("--list-pending", action="store_true", help="read-only report, including untracked candidates")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root; defaults to this checkout")
    args = parser.parse_args(argv)
    try:
        result = check(args.root)
        if args.list_pending:
            result["untracked_candidates"] = sorted(git_paths(args.root, untracked=True))
            result["pending_notice"] = "Candidates are not approved; manually review before adding metadata or staging."
    except (OSError, UnicodeError, subprocess.CalledProcessError) as exc:
        result = {"status": "FAIL", "errors": [{"reason": f"cannot inspect repository: {type(exc).__name__}"}]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
