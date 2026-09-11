from __future__ import annotations

import smtplib
from email.message import EmailMessage

from everglades_monitor.config import MailConfig


def send_email(
    mail: MailConfig,
    *,
    subject: str,
    text_body: str,
    html_body: str,
    smtp_factory=None,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = mail.mail_from
    message["To"] = ", ".join(mail.mail_to)
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    factory = smtp_factory or _default_smtp
    with factory(mail) as smtp:
        if mail.username:
            smtp.login(mail.username, mail.password)
        smtp.send_message(message)


def _default_smtp(mail: MailConfig):
    if mail.port == 465:
        smtp = smtplib.SMTP_SSL(mail.host, mail.port, timeout=30)
    else:
        smtp = smtplib.SMTP(mail.host, mail.port, timeout=30)
        smtp.starttls()
    return smtp
