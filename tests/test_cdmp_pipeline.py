from contextlib import contextmanager
from datetime import date
from pathlib import Path

import pytest

from cdmp_monitor.dates import is_recent
from cdmp_monitor.diff import diff_attachments
from cdmp_monitor.digest import AppFailure, FiledItem, RunReport, render_digest
from cdmp_monitor.models import Application, Attachment
from cdmp_monitor.runner import run
from cdmp_monitor.sharepoint import SharePointConfigError, content_url, upload_file
from cdmp_monitor.state import known_keys, load_state, remember, save_state
from cdmp_monitor.summarize import FACTUAL_PROMPT, FALLBACK_SUMMARY, summarize_pdf

RUN_DATE = date(2026, 9, 25)
APP = Application(
    cdmp_number="CDMP20250017",
    plan_guid="c9762e73-fa94-4c81-be60-9d14a52dbd8c",
    sharepoint_folder_url="CDMP/CDMP20250017",
)
OLD = Attachment("history.pdf", "01/01/2020", "Other")
WEEK_EDGE = Attachment("edge.pdf", "09/18/2026", "Other")
TOO_OLD = Attachment("stale.pdf", "09/17/2026", "Other")
RECENT = Attachment("DEM - CDMP20250017 9-24-2026.pdf", "09/24/2026", "DEM Comments")
SAME_NAME_A = Attachment("CDMP20250017 MDFR.pdf", "03/31/2026", "Comment Response Letter")
SAME_NAME_B = Attachment("CDMP20250017 MDFR.pdf", "08/27/2025", "MDSO")


def test_seven_day_window_includes_the_boundary_and_excludes_the_day_before():
    assert is_recent("09/18/2026", RUN_DATE)
    assert is_recent("09/25/2026", RUN_DATE)
    assert not is_recent("09/17/2026", RUN_DATE)


def test_empty_state_does_not_alert_on_history_older_than_seven_days():
    history = [OLD, TOO_OLD, SAME_NAME_A, SAME_NAME_B]
    plan_diff = diff_attachments(history, set(), RUN_DATE)
    assert plan_diff.alertable == []
    assert len(plan_diff.recorded_only) == 4


def test_second_run_reports_nothing_new(tmp_path: Path):
    state = {"plans": {}}
    remember(state, APP.plan_guid, [OLD, RECENT])
    path = tmp_path / "state.json"
    save_state(path, state)
    loaded = load_state(path)
    plan_diff = diff_attachments([OLD, RECENT], known_keys(loaded, APP.plan_guid), RUN_DATE)
    assert plan_diff.new_items == []


def test_fake_recent_row_is_alerted_and_fake_old_row_is_only_recorded():
    plan_diff = diff_attachments([RECENT, WEEK_EDGE, TOO_OLD], set(), RUN_DATE)
    assert plan_diff.alertable == [RECENT, WEEK_EDGE]
    assert plan_diff.recorded_only == [TOO_OLD]


def test_same_filename_on_two_dates_can_both_be_new():
    plan_diff = diff_attachments([SAME_NAME_A, SAME_NAME_B], set(), RUN_DATE)
    assert {item.uploaded_date for item in plan_diff.recorded_only} == {
        "03/31/2026",
        "08/27/2025",
    }


def test_digest_separates_new_files_from_failures_and_includes_the_heartbeat():
    report = RunReport(
        run_date=RUN_DATE,
        checked=6,
        total=7,
        filed=[
            FiledItem(
                application=APP,
                attachment=RECENT,
                summary="A DEM comment memo dated 9/24/2026.",
                link="https://example.test/file",
            )
        ],
        failures=[AppFailure(Application("", "missing-guid"), "Attachments tab did not render")],
        silent_new=12,
    )
    text = render_digest(report)
    assert "Checked 6 of 7 applications successfully." in text
    assert "New attachments:" in text
    assert "DEM - CDMP20250017 9-24-2026.pdf" in text
    assert "Applications that failed to check:" in text
    assert "missing-guid: Attachments tab did not render" in text
    assert text.index("New attachments:") < text.index("Applications that failed to check:")


def test_empty_digest_still_has_the_heartbeat():
    text = render_digest(RunReport(run_date=RUN_DATE, checked=7, total=7))
    assert "Checked 7 of 7 applications successfully." in text
    assert "No new attachments." in text


def test_short_pdf_text_uses_the_manual_fallback(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("cdmp_monitor.summarize.extract_pdf_text", lambda path: "scan")
    assert summarize_pdf(tmp_path / "scan.pdf") == FALLBACK_SUMMARY


def test_summary_prompt_stays_factual_and_uses_the_model_only_for_real_text(tmp_path, monkeypatch):
    seen = {}

    def complete(prompt: str) -> str:
        seen["prompt"] = prompt
        return "A 12-page traffic study revision dated 8/20/26."

    monkeypatch.setattr("cdmp_monitor.summarize.extract_pdf_text", lambda path: "x" * 80)
    summary = summarize_pdf(tmp_path / "study.pdf", complete=complete)
    assert summary.startswith("A 12-page traffic study")
    assert "prior comment letter" in FACTUAL_PROMPT
    assert seen["prompt"].startswith(FACTUAL_PROMPT)


def test_upload_without_a_folder_fails_clearly(tmp_path: Path):
    pdf = tmp_path / "file.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    with pytest.raises(SharePointConfigError, match="folder"):
        upload_file(pdf, "  ")


def test_graph_content_url_keeps_the_drive_path():
    url = content_url("drive-1", "CDMP/CDMP20250017/file.pdf")
    assert url == (
        "https://graph.microsoft.com/v1.0/drives/drive-1/root:/"
        "CDMP/CDMP20250017/file.pdf:/content"
    )


def test_run_records_old_files_and_files_a_recent_one(tmp_path: Path, monkeypatch):
    pdf_bytes = b"%PDF-1.4\n" + b"x" * 80

    @contextmanager
    def fake_open(plan_guid, **kwargs):
        yield object()

    def fake_download(page, attachment, dest_dir: Path) -> Path:
        dest_dir.mkdir(parents=True, exist_ok=True)
        target = dest_dir / "file.pdf"
        target.write_bytes(pdf_bytes)
        return target

    monkeypatch.setattr("cdmp_monitor.runner.open_plan", fake_open)
    monkeypatch.setattr("cdmp_monitor.runner.read_attachments", lambda page: [OLD, RECENT])
    monkeypatch.setattr("cdmp_monitor.runner.download_attachment", fake_download)
    monkeypatch.setattr("cdmp_monitor.runner.summarize_pdf", lambda path: "Memo dated 9/24/2026.")
    monkeypatch.setattr(
        "cdmp_monitor.runner.upload_file",
        lambda path, folder: "https://example.test/memo",
    )
    sent = {}
    monkeypatch.setattr("cdmp_monitor.runner.load_mail_settings", lambda: object())
    monkeypatch.setattr(
        "cdmp_monitor.runner.send_email",
        lambda settings, **kwargs: sent.update(kwargs),
    )

    state_path = tmp_path / "state.json"
    report = run([APP], run_date=RUN_DATE, state_path=state_path)
    assert [item.attachment for item in report.filed] == [RECENT]
    assert report.silent_new == 1
    assert report.checked == 1
    assert "Memo dated 9/24/2026." in sent["body"]
    assert known_keys(load_state(state_path), APP.plan_guid) == {OLD.key, RECENT.key}

    second = run([APP], run_date=RUN_DATE, state_path=state_path)
    assert second.filed == []
    assert second.silent_new == 0
    assert "No new attachments." in sent["body"]


def test_log_only_does_not_email_or_mark_recent_files_seen(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "cdmp_monitor.runner.open_plan",
        lambda plan_guid, **kwargs: _yield(object()),
    )
    monkeypatch.setattr("cdmp_monitor.runner.read_attachments", lambda page: [OLD, RECENT])
    monkeypatch.setattr(
        "cdmp_monitor.runner.send_email",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("emailed")),
    )

    state_path = tmp_path / "state.json"
    report = run([APP], run_date=RUN_DATE, state_path=state_path, log_only=True)
    assert report.filed[0].attachment == RECENT
    assert known_keys(load_state(state_path), APP.plan_guid) == {OLD.key}


@contextmanager
def _yield(value):
    yield value
