from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cdmp_monitor.config import (
    CONFIRMED_CDMP_NUMBER,
    find_application,
    load_applications,
)
from cdmp_monitor.scraper import scrape_attachments


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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scrape":
        return _scrape(args.cdmp, args.applications)
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


if __name__ == "__main__":
    sys.exit(main())
