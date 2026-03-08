from dataclasses import dataclass
import logging
import smtplib
from email.message import EmailMessage

from config import settings

logger = logging.getLogger(__name__)


class EmailError(Exception):
    pass


class EmailNotConfiguredError(EmailError):
    pass


class EmailDeliveryError(EmailError):
    pass


@dataclass
class EmailSendResult:
    sent: bool
    detail: str


def email_is_configured() -> bool:
    return all(
        [
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD,
            settings.FROM_EMAIL,
        ]
    )


def ensure_email_configured() -> None:
    if not email_is_configured():
        raise EmailNotConfiguredError(
            "SMTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and FROM_EMAIL."
        )


def send_email(
    to_email: str,
    subject: str,
    body: str,
    *,
    raise_on_failure: bool = False,
) -> EmailSendResult:
    if not email_is_configured():
        detail = (
            "SMTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, and FROM_EMAIL."
        )
        logger.warning("email_not_configured", extra={"to_email": to_email})
        if raise_on_failure:
            raise EmailNotConfiguredError(detail)
        return EmailSendResult(sent=False, detail=detail)

    msg = EmailMessage()
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, int(settings.SMTP_PORT)) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            logger.info("email_sent", extra={"to_email": to_email})
            return EmailSendResult(sent=True, detail="Email sent successfully.")
    except Exception as exc:
        logger.exception("email_send_failed", extra={"to_email": to_email})
        if raise_on_failure:
            raise EmailDeliveryError("SMTP delivery failed.") from exc
        return EmailSendResult(sent=False, detail="SMTP delivery failed.")
