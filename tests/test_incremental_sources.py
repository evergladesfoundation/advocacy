from datetime import date

from everglades_monitor.config import Config
from everglades_monitor.sources.sam import check_sam
from everglades_monitor.sources.usaspending import check_usaspending
from everglades_monitor.sources.acquisition import check_acquisition

from conftest import FakeFetcher


def test_sam_skipped_without_key():
    config = Config(today=date(2026, 9, 11), state_path=None, sam_api_key=None)  # type: ignore[arg-type]
    result = check_sam(FakeFetcher(), config, None)
    assert result.skipped and "SAM_API_KEY" in result.skipped
    assert result.hits == []


def test_sam_parses_opportunities():
    fetcher = FakeFetcher(
        {
            "opportunities/v2/search": {
                "totalRecords": 1,
                "opportunitiesData": [
                    {
                        "noticeId": "abc123",
                        "title": "Everglades canal maintenance",
                        "postedDate": "2026-09-10",
                        "uiLink": "https://sam.gov/opp/abc123/view",
                        "description": "Work in the Everglades",
                        "fullParentPathName": "DOI.NPS",
                    }
                ],
            }
        }
    )
    config = Config(today=date(2026, 9, 11), state_path=None, sam_api_key="k")  # type: ignore[arg-type]
    result = check_sam(fetcher, config, "2026-09-10")
    assert len(result.hits) == 1
    assert result.hits[0].item_id == "sam-gov:abc123"


def test_usaspending_parses_awards():
    fetcher = FakeFetcher(
        {
            "spending_by_award": {
                "results": [
                    {
                        "generated_internal_id": "CONT_AWD_1",
                        "Award ID": "140P5426P0034",
                        "Recipient Name": "Hawkins",
                        "Award Amount": 105625,
                        "Description": "Chemicals for Everglades National Park",
                        "Awarding Agency": "Department of the Interior",
                        "Last Modified Date": "2026-09-10 12:00:00",
                    }
                ]
            }
        }
    )
    config = Config(today=date(2026, 9, 11), state_path=None)  # type: ignore[arg-type]
    result = check_usaspending(fetcher, config, None)
    assert len(result.hits) == 1
    assert "Hawkins" in result.hits[0].snippet
    assert result.hits[0].url.endswith("CONT_AWD_1")


ACQ_HTML = """
<html><body>
<ol class="search-results">
  <li class="search-result">
    <div class="views-field views-field-title">
      <span class="field-content"><a href="/far/everglades-clause">Everglades clause</a></span>
    </div>
    <div class="views-field views-field-search-api-excerpt">
      <span class="field-content">Mentions the <strong>Everglades</strong>.</span>
    </div>
    <div class="views-field views-field-type"><span class="field-content">FAR</span></div>
  </li>
</ol>
</body></html>
"""


def test_acquisition_parses_search_results():
    fetcher = FakeFetcher({"/search/advanced": ACQ_HTML})
    config = Config(today=date(2026, 9, 11), state_path=None)  # type: ignore[arg-type]
    result = check_acquisition(fetcher, config)
    assert len(result.hits) == 1
    assert result.hits[0].title == "Everglades clause"
    assert result.hits[0].url.endswith("/far/everglades-clause")
    assert "FAR" in result.hits[0].snippet
