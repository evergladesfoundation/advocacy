from __future__ import annotations

import logging
from dataclasses import dataclass

from everglades_monitor.config import Config
from everglades_monitor.digest import render_html, render_text, subject_line
from everglades_monitor.http_client import Fetcher
from everglades_monitor.mailer import send_email
from everglades_monitor.models import BASELINE_SOURCES, SourceResult
from everglades_monitor.sources.acquisition import check_acquisition
from everglades_monitor.sources.congressional_record import check_congressional_record
from everglades_monitor.sources.federal_register import check_federal_register
from everglades_monitor.sources.meetings import check_fwc, check_scg, check_sfwmd
from everglades_monitor.sources.sam import check_sam
from everglades_monitor.sources.usaspending import check_usaspending
from everglades_monitor.state import load_state, save_state

log = logging.getLogger(__name__)


@dataclass
class RunOutput:
    results: list[SourceResult]
    subject: str
    text_body: str
    html_body: str
    state: dict


def collect_results(fetcher: Fetcher, config: Config, state: dict) -> list[SourceResult]:
    last_run = state.get("last_run_date")
    results: list[SourceResult] = []
    checks = [
        ("Federal Register", lambda: check_federal_register(fetcher, config)),
        ("Congressional Record", lambda: check_congressional_record(fetcher, config)),
        ("SAM.gov", lambda: check_sam(fetcher, config, last_run)),
        ("USASpending.gov", lambda: check_usaspending(fetcher, config, last_run)),
        ("Acquisition.gov", lambda: check_acquisition(fetcher, config)),
        ("SFWMD", lambda: check_sfwmd(fetcher, config)),
        ("SCG", lambda: check_scg(fetcher, config)),
        ("FWC", lambda: check_fwc(fetcher, config)),
    ]
    for label, fn in checks:
        try:
            results.append(fn())
        except Exception as exc:  # noqa: BLE001 — isolate source failures
            log.exception("Source %s failed", label)
            from everglades_monitor.models import SourceResult as SR

            source_id = {
                "Federal Register": "federal-register",
                "Congressional Record": "congressional-record",
                "SAM.gov": "sam-gov",
                "USASpending.gov": "usaspending",
                "Acquisition.gov": "acquisition-gov",
                "SFWMD": "sfwmd-meetings",
                "SCG": "scg-meetings",
                "FWC": "fwc-meetings",
            }[label]
            results.append(SR(source=source_id, error=str(exc)))
    return results


def apply_state(results: list[SourceResult], state: dict) -> list[SourceResult]:
    seen = set(state.get("seen_ids") or [])
    baselined = set(state.get("baselined_sources") or [])
    next_seen = set(seen)
    next_baselined = set(baselined)

    for result in results:
        all_hits = list(result.hits)
        if result.error or result.skipped:
            continue
        if result.source in BASELINE_SOURCES and result.source not in baselined:
            result.notes.append(
                f"Baselined {len(all_hits)} item(s); future posts will be flagged."
            )
            result.hits = []
            next_seen.update(hit.item_id for hit in all_hits)
            next_baselined.add(result.source)
            continue
        new_hits = [
            hit for hit in all_hits if hit.item_id not in seen and hit.notify
        ]
        result.hits = new_hits
        next_seen.update(hit.item_id for hit in all_hits)

        if result.source == "federal-register" and result.issue_date:
            state["last_fr_issue"] = result.issue_date
        if result.source == "congressional-record" and result.issue_date:
            state["last_crec_package"] = result.issue_date

    state["seen_ids"] = sorted(next_seen)
    state["baselined_sources"] = sorted(next_baselined)
    return results


def build_output(config: Config, fetcher: Fetcher | None = None) -> RunOutput:
    state = load_state(config.state_path)
    owns = fetcher is None
    client = fetcher or Fetcher(user_agent=config.user_agent, timeout=config.timeout_seconds)
    try:
        results = collect_results(client, config, state)
    finally:
        if owns:
            client.close()
    apply_state(results, state)
    state["last_run_date"] = config.today_iso
    subject = subject_line(config.today_iso, results)
    return RunOutput(
        results=results,
        subject=subject,
        text_body=render_text(config.today_iso, results),
        html_body=render_html(config.today_iso, results),
        state=state,
    )


def execute(config: Config, fetcher: Fetcher | None = None, smtp_factory=None) -> RunOutput:
    output = build_output(config, fetcher=fetcher)
    print(output.subject)
    print(output.text_body)
    if config.dry_run:
        log.info("Dry run: not sending email or writing state")
        return output
    if config.mail is None:
        raise SystemExit(
            "Email is not configured. Set MAIL_TO, MAIL_FROM, SMTP_HOST "
            "(and SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD) or pass --dry-run."
        )
    send_email(
        config.mail,
        subject=output.subject,
        text_body=output.text_body,
        html_body=output.html_body,
        smtp_factory=smtp_factory,
    )
    save_state(config.state_path, output.state)
    return output
