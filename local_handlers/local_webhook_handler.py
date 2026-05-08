#!/usr/bin/env python3
"""Chat platform webhook notifications for ticket events.

Sends ticket notifications to configured chat platforms (Discord, Slack)
via webhook URLs. Supports formatting for each platform's API conventions.
Platform-specific handlers can be easily added by following the existing
pattern of disabled platform checks and payload builders.
"""

__all__ = ["notify_ticket_event"]

import logging
from typing import Any

import requests

import local_handlers.local_config_loader as local_config_loader


def load_webhook_config() -> dict[str, Any]:
    """Load webhook configuration from core configuration.

    Returns:
        Configuration dictionary, or empty dict if config fails to load.
    """
    return local_config_loader.load_core_config() or {}


def is_enabled(service_name: str) -> bool:
    """Check if a webhook service is enabled in configuration.

    Args:
        service_name: The name of the webhook service (e.g., 'discord', 'slack').

    Returns:
        True if service is enabled, False otherwise.
    """
    webhook_service_status = load_webhook_config()
    webhook_service_cfg = webhook_service_status.get(service_name.lower(), {})
    return bool(webhook_service_cfg.get("enabled", False))


def get_webhook_urls() -> tuple[str | None, str | None]:
    """Retrieve webhook URLs for enabled services from configuration.

    Returns:
        Tuple of (discord_url, slack_url). URLs are None if not configured.
    """
    webhook_url_check = load_webhook_config()
    discord_url = webhook_url_check.get("discord", {}).get("webhook_url")
    slack_url = webhook_url_check.get("slack", {}).get("webhook_url")

    return discord_url, slack_url


def notify_ticket_event(
    ticket_number: str, ticket_subject: str, ticket_status: str
) -> dict[str, bool]:
    """Send ticket event notification to all enabled webhook services.

    Formats and sends ticket notifications to configured chat platforms.
    Gracefully skips disabled services without error.

    Args:\n        ticket_number: Unique ticket identifier (e.g., 'TKT-2025-0042').
        ticket_subject: Human-readable ticket subject line.
        ticket_status: Current ticket status (e.g., 'Open', 'In Progress').

    Returns:
        Dictionary mapping service names to success boolean (e.g., {'discord': True}).
    """
    results: dict[str, bool] = {}

    if is_enabled("discord"):
        results["discord"] = send_discord_notification(
            ticket_number, ticket_subject, ticket_status
        )
    else:
        logging.debug("WEBHOOK HANDLER - Discord disabled; skipping.")

    if is_enabled("slack"):
        results["slack"] = send_slack_notification(
            ticket_number, ticket_subject, ticket_status
        )
    else:
        logging.debug("WEBHOOK HANDLER - Slack disabled; skipping.")

    return results


def send_webhook(
    url: str | None, payload: dict[str, Any], service_name: str
) -> bool:
    """Send a generic webhook POST request to the specified URL.

    Args:
        url: The webhook URL to POST to. If None, logs warning and returns False.
        payload: The JSON payload to send.
        service_name: Name of the service for logging purposes.

    Returns:
        True if webhook was sent successfully, False otherwise.
    """
    enabled_service_key = service_name.lower()

    if not is_enabled(enabled_service_key):
        logging.info(f"WEBHOOK HANDLER - {service_name} disabled. Skipping.")
        return False

    if not url:
        logging.warning(
            f"WEBHOOK HANDLER - {service_name} webhook URL missing "
            "in core_configuration.yml"
        )
        return False

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        logging.info(
            f"WEBHOOK HANDLER - Successfully sent notification to {service_name}."
        )
        return True

    except requests.exceptions.Timeout:
        logging.error(f"WEBHOOK HANDLER - {service_name} request timed out.")
    except requests.exceptions.ConnectionError:
        logging.error(f"WEBHOOK HANDLER - Failed to connect to {service_name}.")
    except requests.exceptions.RequestException as e:
        logging.error(f"WEBHOOK HANDLER - {service_name} unexpected error: {e}")

    return False


def send_discord_notification(
    ticket_number: str, ticket_subject: str, ticket_status: str
) -> bool:
    """Build and send Discord embed notification for ticket event.

    Args:
        ticket_number: Unique ticket identifier.
        ticket_subject: Ticket subject line.
        ticket_status: Current ticket status.

    Returns:
        True if sent successfully, False otherwise.
    """
    discord_url, _ = get_webhook_urls()
    new_ticket_status = ticket_status.lower() == "open"
    title = (
        f"New Ticket: {ticket_number} - Subject: {ticket_subject}"
        if new_ticket_status
        else f"Ticket: {ticket_number} updated — Status: {ticket_status}"
    )
    payload: dict[str, Any] = {
        "username": "gr_desk",
        "embeds": [
            {
                "title": title,
                "color": 0x58B9FF if new_ticket_status else 0xFFFF00,
            }
        ],
    }

    return send_webhook(discord_url, payload, "Discord")


def send_slack_notification(
    ticket_number: str, ticket_subject: str, ticket_status: str
) -> bool:
    """Build and send Slack attachment notification for ticket event.

    Args:
        ticket_number: Unique ticket identifier.
        ticket_subject: Ticket subject line.
        ticket_status: Current ticket status.

    Returns:
        True if sent successfully, False otherwise.
    """
    _, slack_url = get_webhook_urls()

    ticket_status_new = ticket_status.lower() == "open"
    title = (
        f"New Ticket: {ticket_number} - Subject: {ticket_subject}"
        if ticket_status_new
        else f"Ticket: {ticket_number} updated — Status: {ticket_status}"
    )
    payload: dict[str, Any] = {
        "username": "gr_desk",
        "attachments": [
            {
                "title": title,
                "color": "#58B9FF" if ticket_status_new else "#FFFF00",
            }
        ],
    }

    return send_webhook(slack_url, payload, "Slack")

# -----------------------------------------------------
# Microsoft Office 365 Teams PAYLOAD
"""
def send_teams365_notification(ticket_number, ticket_subject, ticket_status):
    _, _, teams_url = get_webhook_urls()

    is_new_ticket = ticket_status.lower() == "open"

    title = (
        f"New Ticket Created"
        if is_new_ticket
        else f"Ticket Updated"
    )

    payload = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": f"gr_desk Ticket {ticket_number}",
        "themeColor": "58B9FF" if is_new_ticket else "FFFF00",
        "title": title,
        "sections": [
            {
                "facts": [
                    {"name": "Ticket Number", "value": ticket_number},
                    {"name": "Subject", "value": ticket_subject},
                    {"name": "Status", "value": ticket_status},
                ],
                "markdown": True,
            }
        ],
    }

    return send_webhook(teams_url, payload, "Teams365")
"""
