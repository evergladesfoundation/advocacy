from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage


@dataclass(frozen=True)
class MailSettings:
    mail_to: tuple[str, ...]
    mail_from: str
    host: str
    port: int
    username: str
    password: str


def load_mail_settings() -> MailSettings:
    recipients = [part.strip() for part in os.environ.get("MAIL_TO", "").split(",") if part.strip()]
    host = os.environ.get("SMTP_HOST", "").strip()
    mail_from = os.environ.get("MAIL_FROM", "").strip()
    if not recipients or not host or not mail_from:
        raise RuntimeError("Email needs MAIL_TO, MAIL_FROM, and SMTP_HOST")
    port = int(os.environ.get("SMTP_PORT", "587"))
    return MailSettings(
        mail_to=tuple(recipients),
        mail_from=mail_from,
        host=host,
        port=port,
        username=os.environ.get("SMTP_USERNAME", "").strip(),
        password=os.environ.get("SMTP_PASSWORD", ""),
    )


def send_email(settings: MailSettings, *, subject: str, body: str, smtp_factory=None) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.mail_from
    message["To"] = ", ".join(settings.mail_to)
    message.set_content(body)
    factory = smtp_factory or _smtp
    with factory(settings) as smtp:
        if settings.username:
            smtp.login(settings.username, settings.password)
        smtp.send_message(message)


def _smtp(settings: MailSettings):
    if settings.port == 465:
        return smtplib.SMTP_SSL(settings.host, settings.port, timeout=30)
    smtp = smtplib.SMTP(settings.host, settings.port, timeout=30)
    smtp.starttls()
    return smtp
