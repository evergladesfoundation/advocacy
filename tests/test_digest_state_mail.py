from datetime import date
from pathlib import Path

from everglades_monitor.config import Config, MailConfig
from everglades_monitor.digest import subject_line
from everglades_monitor.mailer import send_email
from everglades_monitor.models import (
    KIND_AGENDA,
    KIND_HIT,
    SOURCE_ACQUISITION,
    SOURCE_FEDERAL_REGISTER,
    SOURCE_FWC,
    Hit,
    SourceResult,
)
from everglades_monitor.runner import apply_state, build_output
from everglades_monitor.state import load_state, save_state

from conftest import FakeFetcher


def test_subject_all_clear_and_counts():
    empty = [SourceResult(source=SOURCE_FEDERAL_REGISTER)]
    assert "all clear" in subject_line("2026-09-11", empty)
    results = [
        SourceResult(
            source=SOURCE_FEDERAL_REGISTER,
            hits=[
                Hit(
                    SOURCE_FEDERAL_REGISTER,
                    "a",
                    "T",
                    "http://x",
                    kind=KIND_HIT,
                )
            ],
        ),
        SourceResult(
            source=SOURCE_FWC,
            hits=[
                Hit(SOURCE_FWC, "b", "M", "http://y", kind=KIND_AGENDA),
                Hit(SOURCE_FWC, "c", "N", "http://z", kind=KIND_AGENDA),
            ],
        ),
    ]
    subject = subject_line("2026-09-11", results)
    assert "1 hit" in subject
    assert "2 new meetings" in subject


def test_apply_state_baselines_listing_sources_once(tmp_path: Path):
    hits = [
        Hit(SOURCE_ACQUISITION, "acquisition-gov:u1", "One", "http://u1"),
        Hit(SOURCE_ACQUISITION, "acquisition-gov:u2", "Two", "http://u2"),
    ]
    first = [SourceResult(source=SOURCE_ACQUISITION, hits=list(hits))]
    state: dict = {"seen_ids": [], "baselined_sources": []}
    apply_state(first, state)
    assert first[0].hits == []
    assert SOURCE_ACQUISITION in state["baselined_sources"]
    assert len(state["seen_ids"]) == 2

    second = [
        SourceResult(
            source=SOURCE_ACQUISITION,
            hits=[
                *hits,
                Hit(SOURCE_ACQUISITION, "acquisition-gov:u3", "Three", "http://u3"),
            ],
        )
    ]
    apply_state(second, state)
    assert [hit.item_id for hit in second[0].hits] == ["acquisition-gov:u3"]


def test_apply_state_skips_unnotify_and_dedupes():
    result = SourceResult(
        source=SOURCE_FWC,
        hits=[
            Hit(SOURCE_FWC, "fwc:1", "empty", "http://x", kind=KIND_AGENDA, notify=False),
            Hit(SOURCE_FWC, "fwc:2", "posted", "http://y", kind=KIND_AGENDA, notify=True),
        ],
    )
    state = {"seen_ids": [], "baselined_sources": [SOURCE_FWC]}
    apply_state([result], state)
    assert [hit.item_id for hit in result.hits] == ["fwc:2"]
    assert "fwc:1" in state["seen_ids"]


def test_state_roundtrip(tmp_path: Path):
    path = tmp_path / "state.json"
    save_state(path, {"seen_ids": ["b", "a"], "baselined_sources": ["sfwmd-meetings"]})
    loaded = load_state(path)
    assert loaded["seen_ids"] == ["a", "b"]


class DummySMTP:
    def __init__(self) -> None:
        self.sent = None
        self.logged_in = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def login(self, username, password):
        self.logged_in = (username, password)

    def send_message(self, message):
        self.sent = message


def test_send_email_builds_multipart_message():
    smtp = DummySMTP()
    mail = MailConfig(
        host="smtp.example.com",
        port=587,
        username="user",
        password="pass",
        mail_from="monitor@example.com",
        mail_to=["policy@example.com"],
    )
    send_email(
        mail,
        subject="hello",
        text_body="text",
        html_body="<p>html</p>",
        smtp_factory=lambda _mail: smtp,
    )
    assert smtp.logged_in == ("user", "pass")
    assert smtp.sent["Subject"] == "hello"
    assert smtp.sent["To"] == "policy@example.com"


def test_build_output_dry_run_path(tmp_path: Path):
    fetcher = FakeFetcher(
        {
            "issues/current.json": {"meta": {"publication_date": "2026-09-11"}},
            "documents.json": {"count": 0, "results": []},
            "/collections/CREC/": {"packages": []},
            "spending_by_award": {"results": []},
            "/search/advanced": "<html><body><p>No Results.</p></body></html>",
            "news-events/meetings": "<html><body></body></html>",
            "/scg": "<html><body></body></html>",
            "commission-meetings/": "<html><body></body></html>",
        }
    )
    config = Config(
        today=date(2026, 9, 11),
        state_path=tmp_path / "state.json",
        dry_run=True,
        sam_api_key=None,
    )
    output = build_output(config, fetcher=fetcher)
    assert "all clear" in output.subject
    sam = next(r for r in output.results if r.source == "sam-gov")
    assert sam.skipped
