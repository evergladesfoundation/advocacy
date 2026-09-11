from __future__ import annotations

from everglades_monitor.config import Config
from everglades_monitor.http_client import Fetcher, HttpError
from everglades_monitor.models import SOURCE_ACQUISITION, Hit, SourceResult, make_id
from everglades_monitor.util import absolute_url, snippet, soup, strip_tags

ACQUISITION_SEARCH = "https://www.acquisition.gov/search/advanced"
BASE = "https://www.acquisition.gov/"


def check_acquisition(fetcher: Fetcher, config: Config) -> SourceResult:
    result = SourceResult(source=SOURCE_ACQUISITION)
    try:
        html = fetcher.get_text(ACQUISITION_SEARCH, params={"keys": config.keyword})
    except HttpError as exc:
        result.error = f"Acquisition.gov search failed: {exc}"
        return result

    page = soup(html)
    items = page.select("ol.search-results li.search-result")
    result.notes.append(
        f"Searched Acquisition.gov for “{config.keyword}” ({len(items)} result(s))."
    )
    for item in items:
        link = item.select_one(".views-field-title a[href]")
        if link is None:
            continue
        href = absolute_url(BASE, link.get("href"))
        title = link.get_text(" ", strip=True)
        if not href or not title:
            continue
        excerpt_el = item.select_one(".views-field-search-api-excerpt")
        type_el = item.select_one(".views-field-type")
        excerpt = snippet(strip_tags(excerpt_el.decode_contents()) if excerpt_el else "")
        doc_type = type_el.get_text(" ", strip=True) if type_el else ""
        result.hits.append(
            Hit(
                source=SOURCE_ACQUISITION,
                item_id=make_id(SOURCE_ACQUISITION, href),
                title=title,
                url=href,
                snippet=" — ".join(part for part in (doc_type, excerpt) if part),
            )
        )
    return result
