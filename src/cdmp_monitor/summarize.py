from __future__ import annotations

import os
from pathlib import Path

FALLBACK_SUMMARY = "could not extract text, opened manually recommended"
MIN_TEXT_CHARS = 40
FACTUAL_PROMPT = (
    "Summarize this Miami-Dade CDMP attachment in a few factual sentences. "
    "State the document type, date, and what the text itself says. "
    "Do not infer editorial relationships, including whether the file answers "
    "a prior comment letter. If the text is not enough to say what the document is, "
    "say so.\n\nDocument text:\n"
)


def extract_pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(parts).strip()


def summarize_pdf(path: Path, *, complete=None) -> str:
    """Factual summary, or the manual-review fallback when text is missing."""
    try:
        text = extract_pdf_text(path)
    except Exception:
        return FALLBACK_SUMMARY
    if len(text) < MIN_TEXT_CHARS:
        return FALLBACK_SUMMARY
    completer = complete or _claude_complete
    summary = completer(FACTUAL_PROMPT + text[:15_000]).strip()
    return summary or FALLBACK_SUMMARY


def _claude_complete(prompt: str) -> str:
    import httpx

    api_key = os.environ.get("CLAUDE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("CLAUDE_API_KEY is not set")
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5").strip()
    response = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 400,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    blocks = response.json().get("content") or []
    return "\n".join(block.get("text", "") for block in blocks if block.get("type") == "text")
