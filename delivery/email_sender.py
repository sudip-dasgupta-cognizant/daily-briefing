"""Email delivery module for the Daily Briefing application.

Sends the completed MP3 briefing to the configured recipient using Gmail's
SMTP server with STARTTLS on port 587.  Authentication uses a Gmail App
Password stored in the .env file — no OAuth flow required.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import date

from dotenv import load_dotenv

load_dotenv(override=True)

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587

_EMAIL_BODY = """\
Good morning! Your personalized AI briefing for today is attached.
Press play and enjoy your morning.

— Your Daily Briefing Bot"""


def send_briefing(mp3_path: str) -> None:
    """Compose and send the daily briefing email with the MP3 attached.

    Loads credentials from the environment, validates that the MP3 file
    exists, builds a multipart MIME message (plain-text body + MP3
    attachment), connects to Gmail SMTP on port 587 via STARTTLS, and
    sends the message.  The connection is always closed cleanly, even if
    sending fails.

    Args:
        mp3_path: Path to the MP3 file to attach.  Can be absolute or
            relative to the current working directory.  Must exist on disk
            before calling this function.

    Returns:
        None

    Raises:
        FileNotFoundError: If ``mp3_path`` does not point to an existing
            file.  Message includes the resolved path so it is easy to
            diagnose.
        RuntimeError: With the message
            ``"SMTP connection failed — check your network or firewall"``
            if the TCP connection to ``smtp.gmail.com:587`` cannot be
            established.
        RuntimeError: With the message
            ``"Gmail authentication failed — check GMAIL_ADDRESS and
            GMAIL_APP_PASSWORD in .env"`` if the App Password or address
            is rejected by Gmail.

    Example:
        >>> send_briefing("output/Sudip_20260625.mp3")
    """
    gmail_address = os.getenv("GMAIL_ADDRESS", "").strip()
    gmail_app_password = os.getenv("GMAIL_APP_PASSWORD", "").strip()
    to_email = os.getenv("TO_EMAIL", "").strip()

    resolved = os.path.abspath(mp3_path)
    if not os.path.isfile(resolved):
        raise FileNotFoundError(
            f"MP3 file not found: '{resolved}'. "
            "Run the TTS step before sending the email."
        )

    message = _build_message(gmail_address, to_email, resolved)

    try:
        server = smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=15)
    except (OSError, smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected) as exc:
        raise RuntimeError(
            "SMTP connection failed — check your network or firewall"
        ) from exc

    try:
        server.ehlo()
        server.starttls()
        server.ehlo()
        try:
            server.login(gmail_address, gmail_app_password)
        except smtplib.SMTPAuthenticationError as exc:
            raise RuntimeError(
                "Gmail authentication failed — check GMAIL_ADDRESS and "
                "GMAIL_APP_PASSWORD in .env"
            ) from exc
        server.sendmail(gmail_address, to_email, message.as_string())
    finally:
        server.quit()


def _build_message(
    from_addr: str,
    to_addr: str,
    mp3_path: str,
) -> MIMEMultipart:
    """Construct the multipart MIME message with body and MP3 attachment.

    Args:
        from_addr: The sender's Gmail address (used in the ``From`` header).
        to_addr: The recipient's email address (used in the ``To`` header).
        mp3_path: Absolute path to the MP3 file to attach.

    Returns:
        A ``MIMEMultipart`` object ready to be passed to
        ``smtplib.SMTP.sendmail``.

    Raises:
        OSError: If ``mp3_path`` cannot be opened for reading.

    Example:
        >>> msg = _build_message("a@gmail.com", "b@gmail.com", "/tmp/brief.mp3")
        >>> msg["Subject"].startswith("Your Morning Briefing")
        True
    """
    _d = date.today()
    subject = f"Your Morning Briefing — {_d.strftime('%A')} {_d.day} {_d.strftime('%B %Y')}"

    message = MIMEMultipart()
    message["From"] = from_addr
    message["To"] = to_addr
    message["Subject"] = subject

    message.attach(MIMEText(_EMAIL_BODY, "plain"))

    attachment_name = os.path.basename(mp3_path)
    with open(mp3_path, "rb") as mp3_file:
        part = MIMEBase("audio", "mpeg")
        part.set_payload(mp3_file.read())

    encoders.encode_base64(part)
    part.add_header(
        "Content-Disposition",
        "attachment",
        filename=attachment_name,
    )
    message.attach(part)

    return message
