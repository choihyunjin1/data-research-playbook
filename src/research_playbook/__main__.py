import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description="Small offline examples and fixed historical replay")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="synthetic examples; no network or raw data")
    r = sub.add_parser("replay", help="fixed case replay from a supplied source snapshot")
    r.add_argument("--case", required=True, choices=["ocean-gap-repair"])
    r.add_argument("--input-root", type=Path, required=True)
    r.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.command == "demo":
            from .demo import run
            result = run()
        else:
            from .replay import replay
            result = replay(args.input_root, args.output)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, FileNotFoundError, FileExistsError) as exc:
        p.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
