from datetime import date

from everglades_monitor.config import Config
from everglades_monitor.sources.federal_register import check_federal_register

from conftest import FakeFetcher, FakeResponse


def _config() -> Config:
    return Config(today=date(2026, 9, 11), state_path=None)  # type: ignore[arg-type]


def test_federal_register_hits_current_issue():
    fetcher = FakeFetcher(
        {
            "issues/current.json": {"meta": {"publication_date": "2026-09-11"}},
            "documents.json": {
                "count": 1,
                "results": [
                    {
                        "title": "Everglades restoration notice",
                        "html_url": "https://www.federalregister.gov/documents/2026/09/11/2026-99999/everglades",
                        "publication_date": "2026-09-11",
                        "document_number": "2026-99999",
                        "abstract": "A test abstract about the Everglades.",
                        "type": "Notice",
                        "agencies": [{"name": "Interior Department"}],
                    }
                ],
            },
        }
    )
    result = check_federal_register(fetcher, _config())
    assert result.error is None
    assert result.issue_date == "2026-09-11"
    assert len(result.hits) == 1
    assert result.hits[0].item_id == "federal-register:2026-99999"
    assert "Interior Department" in result.hits[0].snippet


def test_federal_register_notes_when_issue_is_not_today():
    fetcher = FakeFetcher(
        {
            "issues/current.json": {"meta": {"publication_date": "2026-09-10"}},
            "documents.json": {"count": 0, "results": []},
        }
    )
    result = check_federal_register(fetcher, _config())
    assert any("No new Federal Register issue" in note for note in result.notes)
    assert result.hits == []


def test_federal_register_current_issue_error():
    fetcher = FakeFetcher(
        {"issues/current.json": FakeResponse(status_code=500, text="boom")}
    )
    result = check_federal_register(fetcher, _config())
    assert result.error
