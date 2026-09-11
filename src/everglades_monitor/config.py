from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from everglades_monitor import KEYWORD, USER_AGENT


@dataclass(frozen=True)
class MailConfig:
    host: str
    port: int
    username: str
    password: str
    mail_from: str
    mail_to: list[str]


@dataclass(frozen=True)
class Config:
    today: date
    state_path: Path
    dry_run: bool = False
    keyword: str = KEYWORD
    user_agent: str = USER_AGENT
    sam_api_key: str | None = None
    govinfo_api_key: str = "DEMO_KEY"
    mail: MailConfig | None = None
    timeout_seconds: float = 30.0

    @property
    def today_iso(self) -> str:
        return self.today.isoformat()


def _optional_env(name: str) -> str | None:
    value = os.environ.get(name, "").strip()
    return value or None


def load_mail_config() -> MailConfig | None:
    host = _optional_env("SMTP_HOST")
    mail_from = _optional_env("MAIL_FROM")
    mail_to_raw = _optional_env("MAIL_TO")
    if not host or not mail_from or not mail_to_raw:
        return None
    recipients = [part.strip() for part in mail_to_raw.split(",") if part.strip()]
    if not recipients:
        return None
    port = int(os.environ.get("SMTP_PORT", "587"))
    return MailConfig(
        host=host,
        port=port,
        username=os.environ.get("SMTP_USERNAME", ""),
        password=os.environ.get("SMTP_PASSWORD", ""),
        mail_from=mail_from,
        mail_to=recipients,
    )


def load_config(*, today: date, state_path: Path, dry_run: bool) -> Config:
    govinfo = (
        _optional_env("GOVINFO_API_KEY")
        or _optional_env("CONGRESS_API_KEY")
        or "DEMO_KEY"
    )
    return Config(
        today=today,
        state_path=state_path,
        dry_run=dry_run,
        sam_api_key=_optional_env("SAM_API_KEY"),
        govinfo_api_key=govinfo,
        mail=load_mail_config(),
    )
