from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from cdmp_monitor.models import Application, Attachment


@dataclass
class FiledItem:
    application: Application
    attachment: Attachment
    summary: str
    link: str = ""


@dataclass
class AppFailure:
    application: Application
    message: str


@dataclass
class RunReport:
    run_date: date
    checked: int
    total: int
    filed: list[FiledItem] = field(default_factory=list)
    failures: list[AppFailure] = field(default_factory=list)
    silent_new: int = 0

    @property
    def ok(self) -> bool:
        return not self.failures


def render_digest(report: RunReport) -> str:
    lines = [
        f"CDMP application check {report.run_date.isoformat()}",
        "",
        f"Checked {report.checked} of {report.total} applications successfully.",
        "",
    ]
    if report.filed:
        lines.append("New attachments:")
        for item in report.filed:
            label = item.application.cdmp_number or item.application.plan_guid
            lines.append(
                f"- {label}: {item.attachment.file_name} "
                f"(uploaded {item.attachment.uploaded_date})"
            )
            if item.attachment.notes:
                lines.append(f"  Notes: {item.attachment.notes}")
            lines.append(f"  Summary: {item.summary}")
            if item.link:
                lines.append(f"  Link: {item.link}")
        lines.append("")
    else:
        lines.append("No new attachments.")
        lines.append("")
    if report.silent_new:
        lines.append(
            f"{report.silent_new} older attachment(s) were new to the state store "
            "and were recorded without an alert."
        )
        lines.append("")
    if report.failures:
        lines.append("Applications that failed to check:")
        for failure in report.failures:
            label = failure.application.cdmp_number or failure.application.plan_guid
            lines.append(f"- {label}: {failure.message}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def digest_subject(report: RunReport) -> str:
    subject = f"CDMP application check {report.run_date.isoformat()}"
    if report.failures:
        return subject + " — failures"
    if not report.filed:
        return subject + " — nothing new"
    return subject
