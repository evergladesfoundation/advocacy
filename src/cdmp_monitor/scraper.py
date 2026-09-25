from __future__ import annotations

import re

from cdmp_monitor.models import Attachment

PLAN_URL = (
    "https://energov.miamidade.gov/EnerGov_Prod/SelfService#/plan/{plan_guid}?tab=attachments"
)
_UPLOADED = re.compile(r"^Uploaded:\s*(\d{2}/\d{2}/\d{4})\s*$")
_NOTES = re.compile(r"^Notes:\s*(.*)\s*$")
_LABELS = {"attachment"}


def plan_attachments_url(plan_guid: str) -> str:
    return PLAN_URL.format(plan_guid=plan_guid)


def parse_attachment_card(text: str) -> Attachment | None:
    """Parse one rendered EnerGov attachment card.

    Cards that are the upload drop zone, or that have no file name and date,
    are ignored. The date string is kept as shown on the page.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    uploaded_date = ""
    notes = ""
    file_name = ""
    for index, line in enumerate(lines):
        uploaded = _UPLOADED.match(line)
        if uploaded:
            uploaded_date = uploaded.group(1)
            file_name = _file_name_before(lines[:index])
        notes_match = _NOTES.match(line)
        if notes_match:
            notes = notes_match.group(1).strip()
    if not file_name or not uploaded_date:
        return None
    return Attachment(file_name=file_name, uploaded_date=uploaded_date, notes=notes)


def scrape_attachments(plan_guid: str, *, timeout_ms: int = 45_000) -> list[Attachment]:
    """Open the public attachments tab and return the rendered rows."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright

    url = plan_attachments_url(plan_guid)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_selector(".attachment-card-detail", timeout=timeout_ms)
            except PlaywrightTimeoutError as exc:
                raise RuntimeError(f"Attachments tab did not render for {plan_guid}") from exc
            cards = page.locator(".attachment-card-detail")
            attachments: list[Attachment] = []
            for index in range(cards.count()):
                parsed = parse_attachment_card(cards.nth(index).inner_text())
                if parsed is not None:
                    attachments.append(parsed)
            return attachments
        finally:
            browser.close()


def _file_name_before(lines: list[str]) -> str:
    for line in reversed(lines):
        if line.casefold() in _LABELS or line.startswith("Notes:") or line.startswith("Uploaded:"):
            continue
        return line
    return ""
