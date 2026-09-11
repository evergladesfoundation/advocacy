from datetime import date

from everglades_monitor.config import Config
from everglades_monitor.sources.meetings import check_fwc, check_scg, check_sfwmd

from conftest import FakeFetcher

SFWMD_HTML = """
<html><body>
<div class="panel panel-default"><div class="panel-body">
<ul>
<li><a href="https://www.sfwmd.gov/event/toc-meeting">Quarterly Meeting of the Everglades Technical Oversight Committee (TOC)</a>:
<strong>September 15, 2026 (Hybrid)</strong>
<ul><li><a href="https://sfwmd-gov.zoom.us/webinar/register/WN_abc">Zoom Registration Link</a></li></ul>
</li>
<li><a href="https://www.sfwmd.gov/event/recreational-public-forum-12">Recreational Public Forum</a>:
<strong>September 28, 2026 (Hybrid)</strong>
</li>
</ul>
</div></div>
</body></html>
"""

SCG_INDEX = """
<html><body>
<a href="/science-coordination-group/membership-and-operating-procedures">Membership and Operating Procedures</a>
<a href="/science-coordination-group/aug25-2026-scg">August 25, 2026 - Joint Science Coordination Group/Working Group Meeting</a>
<a href="/science-coordination-group/apr02-2026-scg">April 2, 2026 - Joint Science Coordination Group/Working Group Meeting</a>
</body></html>
"""

SCG_DETAIL = """
<html><body>
<h3>MEETING HANDOUTS AND PRESENTATIONS:</h3>
<ol>
<li><a href="https://www.evergladesrestoration.gov/s/WG_SCG_Agenda.pdf"><strong>Agenda</strong></a></li>
<li><a href="/s/3_OERI_Update.pdf"><strong>Executive Director’s Report</strong></a></li>
</ol>
</body></html>
"""

FWC_INDEX = """
<html><body>
<h2 class="section-title">Next Meeting</h2>
<p><strong>December 9 - 10, 2026</strong> in St. Augustine <br>
<a href="/about/commission/commission-meetings/december-2026/">Agenda</a></p>
<div class="commission-meeting-list">
  <h2>2027</h2>
  <ul>
    <li><h3>November 3 - 4, 2027</h3><small></small>
      <div><a href="/about/commission/commission-meetings/november-2027/">Agenda</a></div></li>
  </ul>
</div>
<div class="commission-meeting-list">
  <h2>2026</h2>
  <ul>
    <li><h3>December 9 - 10, 2026</h3><small>St. Augustine</small>
      <div><a href="/about/commission/commission-meetings/december-2026/">Agenda</a></div></li>
    <li><h3>August 5 2026</h3><small>Panama City Beach</small>
      <div><a href="/about/commission/commission-meetings/august-2026/">Agenda</a></div></li>
  </ul>
</div>
<div class="commission-meeting-list">
  <h2>2025</h2>
  <ul>
    <li><h3>November 5 - 6, 2025</h3>
      <div><a href="/about/commission/commission-meetings/november-2025/">Agenda</a></div></li>
  </ul>
</div>
</body></html>
"""

FWC_EMPTY_AGENDA = """
<html><body>
<h1 class="page-title">December 2026</h1>
<div class="meeting-content rte"></div>
</body></html>
"""

FWC_POSTED_AGENDA = """
<html><body>
<h1 class="page-title">December 2026</h1>
<div class="meeting-content rte">
  <p>Call to Order</p>
  <a href="/media/agenda.pdf">Agenda PDF</a>
</div>
</body></html>
"""


def _config() -> Config:
    return Config(today=date(2026, 9, 11), state_path=None)  # type: ignore[arg-type]


def test_sfwmd_extracts_upcoming_meetings_and_skips_zoom():
    result = check_sfwmd(FakeFetcher({"news-events/meetings": SFWMD_HTML}), _config())
    assert len(result.hits) == 2
    assert all("zoom.us" not in hit.url for hit in result.hits)
    assert result.hits[0].date and "September 15" in result.hits[0].date


def test_scg_lists_meetings_and_latest_handouts():
    fetcher = FakeFetcher(
        {
            "/scg": SCG_INDEX,
            "aug25-2026-scg": SCG_DETAIL,
        }
    )
    result = check_scg(fetcher, _config())
    titles = [hit.title for hit in result.hits]
    assert any("August 25, 2026" in title for title in titles)
    assert any("Agenda" in title for title in titles)
    assert all("Membership" not in title for title in titles)


def test_fwc_lists_current_year_and_does_not_notify_empty_agenda():
    fetcher = FakeFetcher(
        {
            "commission-meetings/": FWC_INDEX,
            "december-2026": FWC_EMPTY_AGENDA,
        }
    )
    # More specific route should win: FakeFetcher matches first substring in dict
    # insertion order. Put december-2026 first.
    fetcher = FakeFetcher({})
    fetcher.add("december-2026", FWC_EMPTY_AGENDA)
    fetcher.add("commission-meetings/", FWC_INDEX)
    result = check_fwc(fetcher, _config())
    urls = [hit.url for hit in result.hits]
    assert any("november-2027" in url for url in urls)
    assert any("december-2026" in url for url in urls)
    assert all("november-2025" not in url for url in urls)
    agenda_hits = [hit for hit in result.hits if hit.kind == "agenda"]
    assert agenda_hits and agenda_hits[0].notify is False


def test_fwc_notifies_when_agenda_content_appears():
    fetcher = FakeFetcher({})
    fetcher.add("december-2026", FWC_POSTED_AGENDA)
    fetcher.add("commission-meetings/", FWC_INDEX)
    result = check_fwc(fetcher, _config())
    posted = [hit for hit in result.hits if hit.notify and hit.kind == "agenda"]
    assert posted
    assert "agenda posted" in posted[0].title.lower()
