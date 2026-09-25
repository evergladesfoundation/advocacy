from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from cdmp_monitor.config import (
    CONFIRMED_CDMP_NUMBER,
    find_application,
    load_applications,
)
from cdmp_monitor.runner import run
from cdmp_monitor.scraper import scrape_attachments
from cdmp_monitor.state import DEFAULT_STATE_PATH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check Miami-Dade CDMP plan pages for attachments."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape = subparsers.add_parser(
        "scrape",
        help="Print the rendered attachment list for one plan.",
    )
    scrape.add_argument(
        "--cdmp",
        default=CONFIRMED_CDMP_NUMBER,
        help=f"CDMP number to scrape (default: {CONFIRMED_CDMP_NUMBER}).",
    )
    scrape.add_argument(
        "--applications",
        type=Path,
        default=Path("data/cdmp/applications.json"),
        help="Tracked-applications config.",
    )

    check = subparsers.add_parser(
        "run",
        help="Check every configured plan, then print and email one digest.",
    )
    check.add_argument(
        "--applications",
        type=Path,
        default=Path("data/cdmp/applications.json"),
        help="Tracked-applications config.",
    )
    check.add_argument(
        "--state",
        type=Path,
        default=DEFAULT_STATE_PATH,
        help="JSON file of attachments already seen.",
    )
    check.add_argument(
        "--date",
        type=date.fromisoformat,
        help="Run as of YYYY-MM-DD (default: today).",
    )
    check.add_argument(
        "--log-only",
        action="store_true",
        help="Print the digest. Do not download, summarize, upload, or email.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scrape":
        return _scrape(args.cdmp, args.applications)
    if args.command == "run":
        return _run(args)
    return 2


def _scrape(cdmp_number: str, applications_path: Path) -> int:
    application = find_application(load_applications(applications_path), cdmp_number=cdmp_number)
    attachments = scrape_attachments(application.plan_guid)
    label = application.cdmp_number or application.plan_guid
    print(f"{label}  {application.plan_guid}")
    print(f"{len(attachments)} attachments")
    for item in attachments:
        notes = f"  {item.notes}" if item.notes else ""
        print(f"{item.uploaded_date}  {item.file_name}{notes}")
    return 0


def _run(args) -> int:
    log_only = args.log_only or os.environ.get("CDMP_LOG_ONLY", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    report = run(
        load_applications(args.applications),
        run_date=args.date or date.today(),
        state_path=args.state,
        log_only=log_only,
    )
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
