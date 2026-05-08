#!/usr/bin/env python3
"""Email handler for ticket notifications and reply processing.

Sends email notifications for ticket events and monitors IMAP inbox
for email replies, automatically appending them as ticket notes.
Requires EMAIL_ENABLED=true and valid SMTP/IMAP configuration.
"""

__all__ = ["send_email", "extract_email_body", "fetch_email_replies"]

import email
import imaplib
import json
import logging
import os
import re
import smtplib
from datetime import datetime
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from dotenv import load_dotenv

from local_handlers.local_config_loader import load_core_config

load_dotenv(".env")
EMAIL_PASSWORD: str | None = os.getenv("EMAIL_PASSWORD")

core_yaml_config = load_core_config()
# Configuration variables from core_configuration.yml
EMAIL_ENABLED: bool = core_yaml_config["email"]["enabled"]
EMAIL_ACCOUNT: str = core_yaml_config["email"]["account"]
IMAP_SERVER: str = core_yaml_config["email"]["imap_server"]
SMTP_SERVER: str = core_yaml_config["email"]["smtp_server"]
SMTP_PORT: int = core_yaml_config["email"]["smtp_port"]
TICKETS_FILE: str = core_yaml_config["tickets_file"]
LOG_LEVEL: str = core_yaml_config["logging"]["level"]
LOG_FILE: str = core_yaml_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def load_tickets() -> list[dict[str, Any]]:
    """Load all tickets from JSON storage.

    Returns:
        List of ticket dictionaries. Empty list if file missing or invalid.
    """
    try:
        with open(TICKETS_FILE, "r") as tkt_file:
            return json.load(tkt_file)
    except (FileNotFoundError, json.JSONDecodeError):
        logging.error(
            "EMAIL HANDLER - Ticket file empty or invalid JSON; "
            "treating as empty list."
        )
        return []


def save_tickets(tickets: list[dict[str, Any]]) -> None:
    """Persist tickets to JSON storage.

    Args:
        tickets: List of ticket dictionaries to save.
    """
    with open(TICKETS_FILE, "w") as f:
        json.dump(tickets, f, indent=4)
    logging.debug("EMAIL HANDLER - Ticket database was updated.")


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

    Connects to IMAP server, retrieves unread emails, matches subject
    line to ticket numbers, and appends email body to ticket notes.
    """
    if not EMAIL_ENABLED:
        logging.debug(
            "EMAIL HANDLER - Skipping IMAP fetch; EMAIL_ENABLED=False."
        )
        return
    logging.debug("EMAIL HANDLER - Checking IMAP for new email replies.")

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select("inbox")
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK":
            logging.error("EMAIL HANDLER - IMAP search failed.")
            return
        email_ids = messages[0].split()
        tickets = load_tickets()
        for email_id in email_ids:
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            if status != "OK":
                continue

            for part in msg_data:
                if not isinstance(part, tuple):
                    continue

                msg = email.message_from_bytes(part[1])
                subject_raw, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject_raw, bytes):
                    subject = subject_raw.decode(encoding or "utf-8")
                else:
                    subject = subject_raw
                ticket_match = re.search(r"TKT-\d{4}-\d+", subject)
                if not ticket_match:
                    continue

                ticket_id = ticket_match.group(0)
                body = extract_email_body(msg)
                for t in tickets:
                    if t["ticket_number"] == ticket_id:
                        t["ticket_notes"].append({"ticket_message": body})
                        save_tickets(tickets)
                        logging.info(
                            f"EMAIL HANDLER - Email reply added to {ticket_id}."
                        )
                        break
        mail.logout()

    except imaplib.IMAP4.error as e:
        logging.error(f"EMAIL HANDLER - IMAP error: {e}")
    except Exception as e:
        logging.error(f"EMAIL HANDLER - Unexpected error: {e}")
