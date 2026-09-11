from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from everglades_monitor.config import load_config
from everglades_monitor.runner import execute


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Daily Everglades policy monitor: search today's Federal Register "
        "and Congressional Record, incremental contracting sources, and meeting pages."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the digest without sending email or writing state.",
    )
    parser.add_argument(
        "--date",
        type=date.fromisoformat,
        help="Run as of YYYY-MM-DD (default: today).",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("data/state.json"),
        help="Path to the seen-item state file.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args(argv)
    config = load_config(
        today=args.date or date.today(),
        state_path=args.state,
        dry_run=args.dry_run,
    )
    execute(config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
