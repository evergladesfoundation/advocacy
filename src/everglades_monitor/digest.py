from __future__ import annotations

from html import escape

from everglades_monitor.models import KIND_HIT, Hit, SourceResult
from everglades_monitor.util import now_utc_iso


def count_keyword_hits(results: list[SourceResult]) -> int:
    return sum(
        1
        for result in results
        for hit in result.hits
        if hit.kind == KIND_HIT
    )


def count_meeting_flags(results: list[SourceResult]) -> int:
    return sum(
        1
        for result in results
        for hit in result.hits
        if hit.kind != KIND_HIT
    )


def subject_line(run_date: str, results: list[SourceResult]) -> str:
    hits = count_keyword_hits(results)
    meetings = count_meeting_flags(results)
    if hits == 0 and meetings == 0:
        return f"[Everglades Monitor] {run_date} — all clear"
    parts = []
    if hits:
        parts.append(f"{hits} hit{'s' if hits != 1 else ''}")
    if meetings:
        parts.append(f"{meetings} new meeting{'s' if meetings != 1 else ''}")
    return f"[Everglades Monitor] {run_date} — {', '.join(parts)}"


def render_text(run_date: str, results: list[SourceResult]) -> str:
    lines = [
        f"Everglades daily policy monitor — {run_date}",
        "",
    ]
    for result in results:
        lines.append(result.label)
        lines.append("-" * len(result.label))
        if result.skipped:
            lines.append(result.skipped)
        if result.error:
            lines.append(f"Error: {result.error}")
        for note in result.notes:
            lines.append(note)
        if not result.skipped and not result.error and not result.hits:
            lines.append("No new items.")
        for hit in result.hits:
            date = f" ({hit.date})" if hit.date else ""
            lines.append(f"* {hit.title}{date}")
            if hit.snippet:
                lines.append(f"  {hit.snippet}")
            lines.append(f"  {hit.url}")
        lines.append("")
    lines.append(f"Run finished at {now_utc_iso()}.")
    return "\n".join(lines).rstrip() + "\n"


def render_html(run_date: str, results: list[SourceResult]) -> str:
    sections = []
    for result in results:
        body = []
        if result.skipped:
            body.append(f"<p><em>{escape(result.skipped)}</em></p>")
        if result.error:
            body.append(f"<p><strong>Error:</strong> {escape(result.error)}</p>")
        for note in result.notes:
            body.append(f"<p>{escape(note)}</p>")
        if not result.skipped and not result.error and not result.hits:
            body.append("<p>No new items.</p>")
        if result.hits:
            body.append("<ul>")
            for hit in result.hits:
                body.append(_hit_html(hit))
            body.append("</ul>")
        sections.append(
            f"<section><h2>{escape(result.label)}</h2>{''.join(body)}</section>"
        )
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Everglades monitor {escape(run_date)}</title></head>
<body style="font-family: Georgia, serif; line-height: 1.45; color: #222; max-width: 720px;">
  <h1>Everglades daily policy monitor</h1>
  <p>{escape(run_date)}</p>
  {''.join(sections)}
  <p style="color:#666;font-size:13px;">Run finished at {escape(now_utc_iso())}.</p>
</body>
</html>
"""


def _hit_html(hit: Hit) -> str:
    date = f" <span style='color:#555'>({escape(hit.date)})</span>" if hit.date else ""
    snippet = f"<br><span style='color:#444'>{escape(hit.snippet)}</span>" if hit.snippet else ""
    return (
        "<li>"
        f"<a href=\"{escape(hit.url, quote=True)}\">{escape(hit.title)}</a>"
        f"{date}{snippet}"
        "</li>"
    )
