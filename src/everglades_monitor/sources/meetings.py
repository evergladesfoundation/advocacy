from __future__ import annotations

import hashlib
import re
from everglades_monitor.config import Config
from everglades_monitor.http_client import Fetcher, HttpError
from everglades_monitor.models import (
    KIND_AGENDA,
    KIND_MEETING,
    SOURCE_FWC,
    SOURCE_SCG,
    SOURCE_SFWMD,
    Hit,
    SourceResult,
    make_id,
)
from everglades_monitor.util import absolute_url, is_skippable_href, snippet, soup

SFWMD_URL = "https://www.sfwmd.gov/news-events/meetings"
SCG_URL = "https://www.evergladesrestoration.gov/scg"
FWC_URL = "https://myfwc.com/about/commission/commission-meetings/"
SCG_BASE = "https://www.evergladesrestoration.gov"
FWC_BASE = "https://myfwc.com"


def check_sfwmd(fetcher: Fetcher, config: Config) -> SourceResult:
    result = SourceResult(source=SOURCE_SFWMD)
    try:
        html = fetcher.get_text(SFWMD_URL)
    except HttpError as exc:
        result.error = f"SFWMD meetings page failed: {exc}"
        return result

    page = soup(html)
    panel = page.select_one(".panel-body") or page
    seen: set[str] = set()
    for item in panel.select("li"):
        link = item.find("a", href=True)
        if link is None:
            continue
        href = absolute_url(SFWMD_URL, link.get("href"))
        title = link.get_text(" ", strip=True)
        if not href or not title or is_skippable_href(href):
            continue
        if "/event/" not in href and "sfwmd.gov" not in href:
            continue
        date_el = item.find("strong")
        date_text = date_el.get_text(" ", strip=True) if date_el else ""
        extra_links = []
        for extra in item.find_all("a", href=True):
            extra_href = absolute_url(SFWMD_URL, extra.get("href"))
            if extra_href and extra_href != href and not is_skippable_href(extra_href):
                extra_links.append(extra_href)
        item_key = "|".join([href, *sorted(extra_links)])
        if item_key in seen:
            continue
        seen.add(item_key)
        extras = f"Materials: {', '.join(extra_links)}" if extra_links else ""
        result.hits.append(
            Hit(
                source=SOURCE_SFWMD,
                item_id=make_id(SOURCE_SFWMD, item_key),
                title=title,
                url=href,
                date=date_text or None,
                snippet=snippet(" — ".join(part for part in (date_text, extras) if part)),
                kind=KIND_AGENDA if extra_links else KIND_MEETING,
            )
        )
    result.notes.append(f"Listed {len(result.hits)} SFWMD upcoming meeting(s).")
    return result


def check_scg(fetcher: Fetcher, config: Config) -> SourceResult:
    result = SourceResult(source=SOURCE_SCG)
    try:
        html = fetcher.get_text(SCG_URL)
    except HttpError as exc:
        result.error = f"SCG page failed: {exc}"
        return result

    page = soup(html)
    meetings: list[tuple[str, str]] = []
    seen_hrefs: set[str] = set()
    for link in page.find_all("a", href=True):
        href = absolute_url(SCG_BASE + "/", link.get("href"))
        title = link.get_text(" ", strip=True)
        if not href or not title:
            continue
        path = href.lower()
        if "/science-coordination-group/" not in path:
            continue
        if any(skip in path for skip in ("membership", "archives", "/tag/", "operating")):
            continue
        if title.lower().startswith("read more"):
            continue
        if href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        meetings.append((title, href))
        result.hits.append(
            Hit(
                source=SOURCE_SCG,
                item_id=make_id(SOURCE_SCG, href),
                title=title,
                url=href,
                snippet="SCG / Working Group meeting listing",
                kind=KIND_MEETING,
            )
        )

    if meetings:
        latest_title, latest_url = meetings[0]
        _add_scg_materials(fetcher, result, latest_title, latest_url)

    result.notes.append(f"Listed {len(meetings)} SCG meeting page(s).")
    return result


def _add_scg_materials(
    fetcher: Fetcher, result: SourceResult, meeting_title: str, meeting_url: str
) -> None:
    try:
        html = fetcher.get_text(meeting_url)
    except HttpError as exc:
        result.notes.append(f"Could not load latest SCG meeting page: {exc}")
        return
    page = soup(html)
    for link in page.find_all("a", href=True):
        href = absolute_url(meeting_url, link.get("href"))
        title = link.get_text(" ", strip=True)
        if not href or not title:
            continue
        lowered = href.lower()
        if not (lowered.endswith(".pdf") or "/s/" in lowered):
            continue
        result.hits.append(
            Hit(
                source=SOURCE_SCG,
                item_id=make_id(SOURCE_SCG, href),
                title=f"{title} ({meeting_title})",
                url=href,
                snippet=f"Handout/agenda on {meeting_title}",
                kind=KIND_AGENDA,
            )
        )


def check_fwc(fetcher: Fetcher, config: Config) -> SourceResult:
    result = SourceResult(source=SOURCE_FWC)
    try:
        html = fetcher.get_text(FWC_URL)
    except HttpError as exc:
        result.error = f"FWC meetings page failed: {exc}"
        return result

    page = soup(html)
    next_agenda_url = _next_meeting_agenda_url(page)
    current_year = config.today.year
    for listing in page.select(".commission-meeting-list"):
        heading = listing.find("h2")
        year = _parse_year(heading.get_text(" ", strip=True) if heading else "")
        if year is not None and year < current_year:
            continue
        for item in listing.select("li"):
            date_el = item.find("h3")
            if date_el is None:
                continue
            date_text = date_el.get_text(" ", strip=True)
            location = item.find("small")
            location_text = location.get_text(" ", strip=True) if location else ""
            agenda = item.find("a", href=True, string=re.compile(r"agenda", re.I))
            if agenda is None:
                agenda = item.find("a", href=True)
            href = absolute_url(FWC_BASE, agenda.get("href") if agenda else None)
            if not href:
                continue
            result.hits.append(
                Hit(
                    source=SOURCE_FWC,
                    item_id=make_id(SOURCE_FWC, href),
                    title=f"FWC Commission Meeting — {date_text}",
                    url=href,
                    date=date_text,
                    snippet=snippet(location_text or date_text),
                    kind=KIND_MEETING,
                )
            )

    if next_agenda_url:
        _add_fwc_agenda_status(fetcher, result, next_agenda_url)

    result.notes.append(f"Listed {len(result.hits)} current/future FWC meeting(s).")
    return result


def _next_meeting_agenda_url(page) -> str | None:
    heading = page.find("h2", string=re.compile(r"Next Meeting", re.I))
    if heading is None:
        return None
    container = heading.find_parent("div") or heading.parent
    link = container.find("a", href=True) if container else None
    return absolute_url(FWC_BASE, link.get("href") if link else None)


def _add_fwc_agenda_status(fetcher: Fetcher, result: SourceResult, url: str) -> None:
    try:
        html = fetcher.get_text(url)
    except HttpError as exc:
        result.notes.append(f"Could not load FWC next-meeting agenda page: {exc}")
        return
    page = soup(html)
    content = page.select_one(".meeting-content")
    inner = (content.decode_contents() if content else "").strip()
    pdfs = []
    scope = content or page
    for link in scope.find_all("a", href=True):
        href = absolute_url(url, link.get("href"))
        if href and href.lower().endswith(".pdf"):
            pdfs.append(href)
    digest = hashlib.sha256(inner.encode("utf-8")).hexdigest()[:16]
    posted = bool(inner) or bool(pdfs)
    title = page.find("h1")
    meeting_name = title.get_text(" ", strip=True) if title else url
    result.hits.append(
        Hit(
            source=SOURCE_FWC,
            item_id=make_id(SOURCE_FWC, f"agenda:{url}:{digest}"),
            title=(
                f"FWC agenda posted — {meeting_name}"
                if posted
                else f"FWC agenda not yet posted — {meeting_name}"
            ),
            url=url,
            snippet=(
                snippet(f"{len(pdfs)} PDF(s); content hash {digest}")
                if posted
                else "Agenda page is still empty"
            ),
            kind=KIND_AGENDA,
            notify=posted,
        )
    )


def _parse_year(text: str) -> int | None:
    match = re.search(r"(20\d{2})", text)
    return int(match.group(1)) if match else None


def check_meetings(fetcher: Fetcher, config: Config) -> list[SourceResult]:
    return [
        check_sfwmd(fetcher, config),
        check_scg(fetcher, config),
        check_fwc(fetcher, config),
    ]
