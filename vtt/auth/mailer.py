"""Small SMTP adapter for account-recovery messages."""

import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


class MailDeliveryError(RuntimeError):
    """Raised when the configured account mail transport cannot deliver."""


def send_password_reset_email(*, recipient: str, reset_url: str) -> None:
    """Deliver a password-reset link through the configured SMTP server."""
    server = str(current_app.config.get("MAIL_SERVER") or "").strip()
    sender = str(current_app.config.get("MAIL_DEFAULT_SENDER") or "").strip()
    if not server or not sender:
        raise MailDeliveryError("password reset mail transport is not configured")

    message = EmailMessage()
    message["Subject"] = "Roll-Drauf Passwort zurücksetzen"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Öffne diesen Link, um dein Roll-Drauf-Passwort neu zu setzen:\n\n"
        f"{reset_url}\n\n"
        "Der Link ist eine Stunde gültig und kann nur einmal verwendet werden."
    )

    port = int(current_app.config.get("MAIL_PORT") or 587)
    username = str(current_app.config.get("MAIL_USERNAME") or "").strip()
    password = str(current_app.config.get("MAIL_PASSWORD") or "")
    use_tls = bool(current_app.config.get("MAIL_USE_TLS", True))
    try:
        with smtplib.SMTP(server, port, timeout=10) as smtp:
            smtp.ehlo()
            if use_tls:
                smtp.starttls(context=ssl.create_default_context())
                smtp.ehlo()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise MailDeliveryError("password reset mail delivery failed") from exc
