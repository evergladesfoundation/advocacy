from __future__ import annotations

from datetime import timedelta

from everglades_monitor.config import Config
from everglades_monitor.http_client import Fetcher, HttpError
from everglades_monitor.models import (
    SOURCE_CONGRESSIONAL_RECORD,
    Hit,
    SourceResult,
    make_id,
)
from everglades_monitor.util import snippet

GOVINFO_COLLECTIONS = "https://api.govinfo.gov/collections/CREC/{since}"
GOVINFO_PACKAGE = "https://api.govinfo.gov/packages/{package_id}/summary"
GOVINFO_SEARCH = "https://api.govinfo.gov/search"
DETAILS_URL = "https://www.govinfo.gov/app/details/{package_id}/{granule_id}"


def check_congressional_record(fetcher: Fetcher, config: Config) -> SourceResult:
    result = SourceResult(source=SOURCE_CONGRESSIONAL_RECORD)
    params = {"api_key": config.govinfo_api_key}
    try:
        package_id, issue_date, title = _latest_issue(fetcher, config, params)
    except HttpError as exc:
        result.error = f"Could not resolve latest Congressional Record issue: {exc}"
        return result

    if not package_id:
        result.notes.append(
            f"No Congressional Record issue found in the last 14 days "
            f"(checked through {config.today_iso})."
        )
        return result

    result.issue_date = issue_date
    if issue_date != config.today_iso:
        result.notes.append(
            f"No new Congressional Record issue on {config.today_iso}; "
            f"searching latest issue {package_id} ({issue_date})."
        )
    else:
        result.notes.append(f"Searching {title or package_id} for “{config.keyword}”.")

    payload = {
        "query": f'collection:CREC publishdate:{issue_date} "{config.keyword}"',
        "pageSize": 100,
        "offsetMark": "*",
        "historical": False,
        "resultLevel": "default",
    }
    try:
        data = fetcher.post_json(GOVINFO_SEARCH, payload, params=params)
    except HttpError as exc:
        result.error = f"GovInfo search failed: {exc}"
        return result

    matches = data.get("results") or []
    result.notes.append(
        f"Searched Congressional Record {package_id} for “{config.keyword}” "
        f"({data.get('count', len(matches))} match(es))."
    )
    for item in matches:
        granule = item.get("granuleId") or item.get("packageId")
        if not granule:
            continue
        pkg = item.get("packageId") or package_id
        url = DETAILS_URL.format(package_id=pkg, granule_id=granule)
        result.hits.append(
            Hit(
                source=SOURCE_CONGRESSIONAL_RECORD,
                item_id=make_id(SOURCE_CONGRESSIONAL_RECORD, granule),
                title=item.get("title") or granule,
                url=url,
                date=item.get("dateIssued") or issue_date,
                snippet=snippet(item.get("title")),
            )
        )
    return result


def _latest_issue(
    fetcher: Fetcher,
    config: Config,
    params: dict[str, str],
) -> tuple[str | None, str | None, str | None]:
    since = (config.today - timedelta(days=14)).strftime("%Y-%m-%dT00:00:00Z")
    url = GOVINFO_COLLECTIONS.format(since=since)
    data = fetcher.get_json(url, params={**params, "offsetMark": "*", "pageSize": "50"})
    cutoff = (config.today - timedelta(days=14)).isoformat()
    newest: tuple[str, str, str | None] | None = None
    for package in data.get("packages") or []:
        issued = package.get("dateIssued")
        package_id = package.get("packageId")
        if not issued or not package_id or issued < cutoff:
            continue
        if newest is None or issued > newest[1]:
            newest = (package_id, issued, package.get("title"))
    if newest:
        return newest

    # Direct lookup for today's package if collections omitted it.
    today_id = f"CREC-{config.today_iso}"
    response = fetcher.get(GOVINFO_PACKAGE.format(package_id=today_id), params=params)
    if response.status_code == 200:
        body = response.json()
        return today_id, body.get("dateIssued") or config.today_iso, body.get("title")
    return None, None, None
