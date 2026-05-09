#!/usr/bin/env python3
"""Email handler for ticket notifications and reply processing.

Sends email notifications for ticket events and monitors IMAP inbox
for email replies, automatically appending them as ticket notes.
Requires EMAIL_ENABLED=true and valid SMTP/IMAP configuration.
"""

__all__ = ["send_email", "extract_email_body", "fetch_email_replies"]

import email
import imaplib
import logging
import os
import re
import smtplib
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from dotenv import load_dotenv

from local_handlers.local_config_loader import load_core_config
from local_handlers.local_storage_handler import load_tickets, save_tickets

load_dotenv(".env")
EMAIL_PASSWORD: str | None = os.getenv("EMAIL_PASSWORD")

core_yaml_config = load_core_config()
EMAIL_ENABLED: bool = core_yaml_config["email"]["enabled"]
EMAIL_ACCOUNT: str = core_yaml_config["email"]["account"]
IMAP_SERVER: str = core_yaml_config["email"]["imap_server"]
SMTP_SERVER: str = core_yaml_config["email"]["smtp_server"]
SMTP_PORT: int = core_yaml_config["email"]["smtp_port"]
LOG_LEVEL: str = core_yaml_config["logging"]["level"]
LOG_FILE: str = core_yaml_config["logging"]["file"]

# Bounded iteration limit for email processing
MAX_EMAILS_PER_FETCH: int = 100
TICKET_NUMBER_PATTERN: re.Pattern[str] = re.compile(r"TKT-\d{4}-\d+")

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def send_email(
    requestor_email: str,
    ticket_subject: str,
    ticket_message: str,
    html: bool = True,
) -> bool:
    """Send an email notification via configured SMTP server.

    Args:
        requestor_email: Recipient email address.
        ticket_subject: Email subject line.
        ticket_message: Email body content.
        html: If True, sends as HTML; if False, sends as plain text.

    Returns:
        True if email was sent successfully, False otherwise.
    """
    if not EMAIL_ENABLED:
        logging.info("EMAIL HANDLER - Email skipped; EMAIL_ENABLED=False.")
        return False

    if not EMAIL_ACCOUNT or not EMAIL_PASSWORD or not SMTP_SERVER:
        logging.error(
            "EMAIL HANDLER - Email configuration incomplete. "
            "Check core_configuration.yml and .env."
        )
        return False

    msg = MIMEMultipart()
    msg["Subject"] = ticket_subject
    msg["From"] = EMAIL_ACCOUNT
    msg["To"] = requestor_email
    msg.attach(MIMEText(ticket_message, "html" if html else "plain"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ACCOUNT, requestor_email, msg.as_string())

        logging.info(f"EMAIL HANDLER - Email sent to {requestor_email}")
        return True

    except smtplib.SMTPAuthenticationError:
        logging.error(
            "EMAIL HANDLER - SMTP authentication failed. "
            "Check EMAIL_ACCOUNT and EMAIL_PASSWORD in .env"
        )
        return False
    except smtplib.SMTPException as e:
        logging.error(f"EMAIL HANDLER - SMTP error: {e}")
        return False
    except Exception as e:
        logging.error(f"EMAIL HANDLER - Email sending failed: {e}")
        return False


def extract_email_body(msg: email.message.Message) -> str:
    """Extract the plaintext body from an email message.

    Traverses multipart messages to find plaintext or HTML content,
    skipping attachments.

    Args:
        msg: An email.message.Message object.

    Returns:
        The extracted email body as a string. Empty string if no body found.
    """
    logging.debug("EMAIL HANDLER - Extracting email body.")
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdisp = str(part.get("Content-Disposition"))
            if "attachment" in cdisp:
                continue
            try:
                if ctype == "text/plain":
                    return part.get_payload(decode=True).decode(
                        errors="ignore"
                    ).strip()
                elif ctype == "text/html" and not body:
                    body = part.get_payload(decode=True).decode(
                        errors="ignore"
                    ).strip()
            except Exception as e:
                logging.warning(
                    f"EMAIL HANDLER - Failed decoding email part: {e}"
                )
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                errors="ignore"
            ).strip()
        except Exception as e:
            logging.error(f"EMAIL HANDLER - Failed decoding email: {e}")
    return body


def fetch_email_replies() -> None:
    """Fetch unread IMAP emails and append them as ticket notes.

    Connects to IMAP server, retrieves unread emails (bounded to
    MAX_EMAILS_PER_FETCH), matches subject line to ticket numbers,
    and appends email body to ticket notes.
    """
    if not EMAIL_ENABLED:
        logging.debug("EMAIL HANDLER - Skipping IMAP fetch; EMAIL_ENABLED=False.")
        return

    logging.debug("EMAIL HANDLER - Checking IMAP for new email replies.")

    try:
        mail = _connect_to_imap()
        if not mail:
            return

        email_ids = _get_unread_email_ids(mail)
        if not email_ids:
            mail.logout()
            return

        _process_email_replies(mail, email_ids)
        mail.logout()

    except imaplib.IMAP4.error as e:
        logging.error(f"EMAIL HANDLER - IMAP error: {e}")
    except Exception as e:
        logging.error(f"EMAIL HANDLER - Unexpected error: {e}")


def _connect_to_imap() -> imaplib.IMAP4_SSL | None:
    """Establish connection to IMAP server.

    Returns:
        IMAP4_SSL connection object, or None if connection fails.
    """
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select("inbox")
        return mail
    except imaplib.IMAP4.error as e:
        logging.error(f"EMAIL HANDLER - IMAP connection failed: {e}")
        return None


def _get_unread_email_ids(mail: imaplib.IMAP4_SSL) -> list[bytes]:
    """Get list of unread email IDs from IMAP server.

    Args:
        mail: Active IMAP connection.

    Returns:
        List of email IDs (bytes), limited to MAX_EMAILS_PER_FETCH.
    """
    status, messages = mail.search(None, "UNSEEN")
    if status != "OK":
        logging.error("EMAIL HANDLER - IMAP search failed.")
        return []

    email_ids = messages[0].split()
    # Bound the number of emails processed per fetch
    return email_ids[:MAX_EMAILS_PER_FETCH]


def _process_email_replies(
    mail: imaplib.IMAP4_SSL, email_ids: list[bytes]
) -> None:
    """Process a list of emails and append matching replies to tickets.

    Args:
        mail: Active IMAP connection.
        email_ids: List of email IDs to process.
    """
    tickets = load_tickets()
    modified = False

    for email_id in email_ids:
        result = _process_single_email(mail, email_id, tickets)
        if result:
            modified = True

    if modified:
        save_tickets(tickets)


def _process_single_email(
    mail: imaplib.IMAP4_SSL,
    email_id: bytes,
    tickets: list[dict[str, Any]],
) -> bool:
    """Process a single email and append to matching ticket if found.

    Args:
        mail: Active IMAP connection.
        email_id: The email ID to fetch and process.
        tickets: List of tickets to match against.

    Returns:
        True if a ticket was updated, False otherwise.
    """
    status, msg_data = mail.fetch(email_id, "(RFC822)")
    if status != "OK":
        return False

    for part in msg_data:
        if not isinstance(part, tuple):
            continue

        msg = email.message_from_bytes(part[1])
        subject = _decode_email_subject(msg)
        ticket_id = _extract_ticket_id(subject)

        if not ticket_id:
            continue

        return _append_reply_to_ticket(msg, ticket_id, tickets)

    return False


def _decode_email_subject(msg: email.message.Message) -> str:
    """Decode email subject header to string.

    Args:
        msg: Email message object.

    Returns:
        Decoded subject string.
    """
    subject_raw, encoding = decode_header(msg["Subject"])[0]
    if isinstance(subject_raw, bytes):
        return subject_raw.decode(encoding or "utf-8", errors="ignore")
    return str(subject_raw) if subject_raw else ""


def _extract_ticket_id(subject: str) -> str | None:
    """Extract ticket ID from email subject line.

    Args:
        subject: Email subject string.

    Returns:
        Ticket ID string if found, None otherwise.
    """
    match = TICKET_NUMBER_PATTERN.search(subject)
    return match.group(0) if match else None


def _append_reply_to_ticket(
    msg: email.message.Message,
    ticket_id: str,
    tickets: list[dict[str, Any]],
) -> bool:
    """Append email body to matching ticket's notes.

    Args:
        msg: Email message object.
        ticket_id: Ticket ID to match.
        tickets: List of tickets to search.

    Returns:
        True if ticket was found and updated, False otherwise.
    """
    body = extract_email_body(msg)

    for ticket in tickets:
        if ticket["ticket_number"] != ticket_id:
            continue

        ticket.setdefault("ticket_worknotes", []).append(body)
        logging.info(f"EMAIL HANDLER - Email reply added to {ticket_id}.")
        return True

    return False
