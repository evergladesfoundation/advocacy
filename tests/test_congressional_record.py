from datetime import date

from everglades_monitor.config import Config
from everglades_monitor.sources.congressional_record import check_congressional_record

from conftest import FakeFetcher


def test_congressional_record_searches_latest_package_only():
    fetcher = FakeFetcher(
        {
            "/collections/CREC/": {
                "packages": [
                    {
                        "packageId": "CREC-1996-07-10",
                        "dateIssued": "1996-07-10",
                        "title": "old",
                    },
                    {
                        "packageId": "CREC-2026-09-10",
                        "dateIssued": "2026-09-10",
                        "title": "Congressional Record Volume 172, Issue 143",
                    },
                ]
            },
            "/search": {
                "count": 1,
                "results": [
                    {
                        "title": "Everglades funding colloquy",
                        "packageId": "CREC-2026-09-10",
                        "granuleId": "CREC-2026-09-10-pt1-PgS100",
                        "dateIssued": "2026-09-10",
                    }
                ],
            },
        }
    )
    config = Config(today=date(2026, 9, 11), state_path=None)  # type: ignore[arg-type]
    result = check_congressional_record(fetcher, config)
    assert result.issue_date == "2026-09-10"
    assert len(result.hits) == 1
    assert "CREC-2026-09-10-pt1-PgS100" in result.hits[0].url
    assert any("No new Congressional Record issue" in note for note in result.notes)
    posted = [url for method, url in fetcher.calls if method == "POST"]
    assert posted and "search" in posted[0]
