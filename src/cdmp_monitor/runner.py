from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

from cdmp_monitor.digest import AppFailure, FiledItem, RunReport, digest_subject, render_digest
from cdmp_monitor.diff import diff_attachments
from cdmp_monitor.mail import load_mail_settings, send_email
from cdmp_monitor.models import Application
from cdmp_monitor.scraper import download_attachment, open_plan, read_attachments
from cdmp_monitor.sharepoint import upload_file
from cdmp_monitor.state import known_keys, load_state, remember, save_state
from cdmp_monitor.summarize import summarize_pdf


def run(
    applications: list[Application],
    *,
    run_date: date,
    state_path: Path,
    log_only: bool = False,
) -> RunReport:
    state = load_state(state_path)
    report = RunReport(run_date=run_date, checked=0, total=len(applications))
    for application in applications:
        try:
            _check_application(application, state, report, run_date=run_date, log_only=log_only)
            report.checked += 1
        except Exception as exc:
            report.failures.append(AppFailure(application, str(exc)))
    save_state(state_path, state)
    text = render_digest(report)
    print(text, end="")
    if not log_only:
        send_email(load_mail_settings(), subject=digest_subject(report), body=text)
    return report


def _check_application(application, state, report: RunReport, *, run_date: date, log_only: bool) -> None:
    seen = known_keys(state, application.plan_guid)
    with open_plan(application.plan_guid) as page:
        current = read_attachments(page)
        plan_diff = diff_attachments(current, seen, run_date)
        remember(state, application.plan_guid, plan_diff.recorded_only)
        report.silent_new += len(plan_diff.recorded_only)
        if log_only:
            for item in plan_diff.alertable:
                report.filed.append(
                    FiledItem(
                        application=application,
                        attachment=item,
                        summary="Log only: not downloaded or summarized.",
                    )
                )
            return
        for item in plan_diff.alertable:
            with tempfile.TemporaryDirectory() as tmp:
                pdf_path = download_attachment(page, item, Path(tmp))
                summary = summarize_pdf(pdf_path)
                link = upload_file(pdf_path, application.sharepoint_folder_url)
            remember(state, application.plan_guid, [item])
            report.filed.append(
                FiledItem(
                    application=application,
                    attachment=item,
                    summary=summary,
                    link=link,
                )
            )
