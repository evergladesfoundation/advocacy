from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from html import unescape
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def collapse_ws(text: str) -> str:
    return WHITESPACE_RE.sub(" ", unescape(text)).strip()


def strip_tags(html: str) -> str:
    return collapse_ws(TAG_RE.sub(" ", html))


def snippet(text: str | None, limit: int = 240) -> str:
    cleaned = collapse_ws(text or "")
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def absolute_url(base: str, href: str | None) -> str | None:
    if not href:
        return None
    href = href.strip()
    if not href or href.startswith(("javascript:", "mailto:", "tel:")):
        return None
    return urljoin(base, href)


def is_skippable_href(href: str) -> bool:
    lowered = href.lower()
    return lowered.startswith(("#", "javascript:", "mailto:", "tel:")) or "zoom.us" in lowered


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def parse_iso_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def mmddyyyy(value: date) -> str:
    return value.strftime("%m/%d/%Y")


def lookback_start(today: date, last_run_date: str | None, *, default_days: int = 2) -> date:
    previous = parse_iso_date(last_run_date)
    if previous:
        return min(previous, today) - timedelta(days=1)
    return today - timedelta(days=default_days)


def parse_money(value: object) -> str:
    try:
        amount = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    return f"${amount:,.0f}"


def now_utc_iso() -> str:
    return (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )


def host(url: str) -> str:
    return urlparse(url).netloc
