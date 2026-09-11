from __future__ import annotations

from everglades_monitor.config import Config
from everglades_monitor.http_client import Fetcher, HttpError
from everglades_monitor.models import SOURCE_SAM, Hit, SourceResult, make_id
from everglades_monitor.util import lookback_start, mmddyyyy, snippet

SAM_SEARCH = "https://api.sam.gov/opportunities/v2/search"


def check_sam(fetcher: Fetcher, config: Config, last_run_date: str | None) -> SourceResult:
    result = SourceResult(source=SOURCE_SAM)
    if not config.sam_api_key:
        result.skipped = "skipped — add SAM_API_KEY"
        return result

    start = lookback_start(config.today, last_run_date)
    params = {
        "api_key": config.sam_api_key,
        "title": config.keyword,
        "postedFrom": mmddyyyy(start),
        "postedTo": mmddyyyy(config.today),
        "limit": "100",
        "offset": "0",
    }
    try:
        data = fetcher.get_json(SAM_SEARCH, params=params)
    except HttpError as exc:
        result.error = f"SAM.gov search failed: {exc}"
        return result

    opportunities = data.get("opportunitiesData") or data.get("opportunities") or []
    total = data.get("totalRecords", len(opportunities))
    result.notes.append(
        f"Searched SAM.gov opportunities titled with “{config.keyword}” "
        f"posted {start.isoformat()}–{config.today_iso} ({total} record(s))."
    )
    for item in opportunities:
        notice_id = str(item.get("noticeId") or item.get("noticeid") or "")
        title = item.get("title") or notice_id
        posted = (item.get("postedDate") or "")[:10]
        ui_link = item.get("uiLink") or (
            f"https://sam.gov/opp/{notice_id}/view" if notice_id else ""
        )
        if not notice_id or not ui_link:
            continue
        desc = snippet(item.get("description") or item.get("type"))
        office = item.get("fullParentPathName") or item.get("department") or ""
        result.hits.append(
            Hit(
                source=SOURCE_SAM,
                item_id=make_id(SOURCE_SAM, notice_id),
                title=title,
                url=ui_link,
                date=posted or None,
                snippet=" — ".join(part for part in (office, desc) if part),
            )
        )
    return result
