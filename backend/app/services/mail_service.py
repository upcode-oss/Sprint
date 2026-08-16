import smtplib
import ssl
from email.message import EmailMessage

from app.core.installation import installation_store
from app.models.identity import SMTPConfiguration
from app.schemas.setup import SMTPSetup


def _send(
    host: str,
    port: int,
    username: str | None,
    password: str | None,
    encryption: str,
    message: EmailMessage,
) -> None:
    context = ssl.create_default_context()
    if encryption == "tls":
        client: smtplib.SMTP = smtplib.SMTP_SSL(host, port, timeout=10, context=context)
    else:
        client = smtplib.SMTP(host, port, timeout=10)
    try:
        if encryption == "starttls":
            client.starttls(context=context)
        if username:
            client.login(username, password or "")
        client.send_message(message)
    finally:
        client.quit()


def send_test_email(configuration: SMTPSetup, recipient: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Upcode Harbor SMTP test"
    message["From"] = f"{configuration.from_name} <{configuration.from_address}>"
    message["To"] = recipient
    message.set_content("Your Upcode Harbor SMTP configuration works.")
    _send(
        configuration.host or "",
        configuration.port or 0,
        configuration.username,
        configuration.password.get_secret_value() if configuration.password else None,
        configuration.encryption,
        message,
    )


def send_email(configuration: SMTPConfiguration, recipient: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{configuration.from_name} <{configuration.from_address}>"
    message["To"] = recipient
    message.set_content(body)
    password = (
        installation_store.decrypt(configuration.password_encrypted)
        if configuration.password_encrypted
        else None
    )
    _send(
        configuration.host,
        configuration.port,
        configuration.username,
        password,
        configuration.encryption,
        message,
    )
