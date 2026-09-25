from __future__ import annotations

from datetime import date, datetime

PORTAL_DATE = "%m/%d/%Y"
RECENCY_DAYS = 7


def parse_portal_date(value: str) -> date:
    return datetime.strptime(value, PORTAL_DATE).date()


def is_recent(uploaded_date: str, run_date: date, *, days: int = RECENCY_DAYS) -> bool:
    """True when the upload falls on the run date or within the previous `days`."""
    uploaded = parse_portal_date(uploaded_date)
    age = (run_date - uploaded).days
    return 0 <= age <= days
