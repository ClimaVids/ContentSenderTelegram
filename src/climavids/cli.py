from __future__ import annotations

import argparse
from climavids.pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["dry-run", "health"])
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()
    if args.command == "dry-run":
        items = run(dry_run=True, limit=args.limit)
        print(f"generated={len(items)}")
    else:
        print("health=ok")


if __name__ == "__main__":
    main()
