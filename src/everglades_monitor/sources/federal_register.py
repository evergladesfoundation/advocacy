from __future__ import annotations

from everglades_monitor.config import Config
from everglades_monitor.http_client import Fetcher, HttpError
from everglades_monitor.models import (
    SOURCE_FEDERAL_REGISTER,
    Hit,
    SourceResult,
    make_id,
)
from everglades_monitor.util import snippet

FR_CURRENT = "https://www.federalregister.gov/api/v1/issues/current.json"
FR_DOCUMENTS = "https://www.federalregister.gov/api/v1/documents.json"
FR_FIELDS = [
    "title",
    "html_url",
    "publication_date",
    "document_number",
    "abstract",
    "type",
    "agencies",
]


def check_federal_register(fetcher: Fetcher, config: Config) -> SourceResult:
    result = SourceResult(source=SOURCE_FEDERAL_REGISTER)
    try:
        current = fetcher.get_json(FR_CURRENT)
    except HttpError as exc:
        result.error = f"Could not load current issue: {exc}"
        return result

    issue_date = (current.get("meta") or {}).get("publication_date")
    result.issue_date = issue_date
    if not issue_date:
        result.error = "Current Federal Register issue has no publication_date"
        return result

    if issue_date != config.today_iso:
        result.notes.append(
            f"No new Federal Register issue on {config.today_iso}; "
            f"latest published issue is {issue_date}."
        )

    query = [
        ("conditions[term]", config.keyword),
        ("conditions[publication_date][is]", issue_date),
        ("per_page", "100"),
        ("order", "newest"),
    ]
    for field in FR_FIELDS:
        query.append(("fields[]", field))

    try:
        payload = _get_with_query(fetcher, FR_DOCUMENTS, query)
    except HttpError as exc:
        result.error = f"Document search failed: {exc}"
        return result

    count = payload.get("count", 0)
    result.notes.append(
        f"Searched Federal Register issue dated {issue_date} "
        f"for “{config.keyword}” ({count} match(es))."
    )
    for doc in payload.get("results") or []:
        number = str(doc.get("document_number") or "")
        title = doc.get("title") or f"Document {number}"
        url = doc.get("html_url") or ""
        if not number or not url:
            continue
        agencies = []
        for agency in doc.get("agencies") or []:
            name = agency.get("name") if isinstance(agency, dict) else None
            if name:
                agencies.append(name)
        abstract = snippet(doc.get("abstract"))
        extra = ", ".join(agencies)
        kind = doc.get("type") or ""
        bits = [part for part in (kind, extra, abstract) if part]
        result.hits.append(
            Hit(
                source=SOURCE_FEDERAL_REGISTER,
                item_id=make_id(SOURCE_FEDERAL_REGISTER, number),
                title=title,
                url=url,
                date=doc.get("publication_date") or issue_date,
                snippet=" — ".join(bits),
            )
        )
    return result


def _get_with_query(fetcher: Fetcher, url: str, query: list[tuple[str, str]]) -> dict:
    # httpx accepts a list of tuples for repeated query keys.
    response = fetcher.request("GET", url, params=query)
    if response.status_code >= 400:
        raise HttpError(
            f"GET {url} returned {response.status_code}",
            status_code=response.status_code,
        )
    return response.json()
