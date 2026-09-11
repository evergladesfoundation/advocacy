from __future__ import annotations

from everglades_monitor.config import Config
from everglades_monitor.http_client import Fetcher, HttpError
from everglades_monitor.models import SOURCE_USASPENDING, Hit, SourceResult, make_id
from everglades_monitor.util import lookback_start, parse_money, snippet

USASPENDING_SEARCH = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
AWARD_URL = "https://www.usaspending.gov/award/{award_id}"
FIELDS = [
    "Award ID",
    "Recipient Name",
    "Award Amount",
    "Description",
    "Awarding Agency",
    "Start Date",
    "Last Modified Date",
]
AWARD_GROUPS = [
    ["A", "B", "C", "D"],
    ["IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", "IDV_B_C", "IDV_C", "IDV_D", "IDV_E"],
    ["02", "03", "04", "05", "F001", "F002"],
    ["07", "08", "F003", "F004"],
    ["06", "10", "F006", "F007"],
    ["09", "11", "-1", "F005", "F008", "F009", "F010"],
]


def check_usaspending(
    fetcher: Fetcher, config: Config, last_run_date: str | None
) -> SourceResult:
    result = SourceResult(source=SOURCE_USASPENDING)
    start = lookback_start(config.today, last_run_date)
    errors: list[str] = []
    seen: set[str] = set()

    for codes in AWARD_GROUPS:
        payload = {
            "filters": {
                "keywords": [config.keyword],
                "time_period": [
                    {
                        "start_date": start.isoformat(),
                        "end_date": config.today_iso,
                        "date_type": "last_modified_date",
                    }
                ],
                "award_type_codes": codes,
            },
            "fields": FIELDS,
            "limit": 100,
            "page": 1,
        }
        try:
            data = fetcher.post_json(USASPENDING_SEARCH, payload)
        except HttpError as exc:
            errors.append(str(exc))
            continue
        for item in data.get("results") or []:
            generated = str(item.get("generated_internal_id") or "")
            award_id = str(item.get("Award ID") or generated)
            if not generated or generated in seen:
                continue
            seen.add(generated)
            recipient = item.get("Recipient Name") or ""
            amount = parse_money(item.get("Award Amount"))
            agency = item.get("Awarding Agency") or ""
            description = snippet(item.get("Description"))
            bits = [part for part in (recipient, amount, agency, description) if part]
            result.hits.append(
                Hit(
                    source=SOURCE_USASPENDING,
                    item_id=make_id(SOURCE_USASPENDING, generated),
                    title=award_id,
                    url=AWARD_URL.format(award_id=generated),
                    date=(item.get("Last Modified Date") or item.get("Start Date") or "")[:10]
                    or None,
                    snippet=" — ".join(bits),
                )
            )

    result.notes.append(
        f"Searched USASpending awards mentioning “{config.keyword}” "
        f"modified {start.isoformat()}–{config.today_iso} "
        f"({len(result.hits)} match(es))."
    )
    if errors and not result.hits:
        result.error = "; ".join(errors)
    elif errors:
        result.notes.append("Some award-type groups failed: " + "; ".join(errors))
    return result
