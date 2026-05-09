"""Outbound webhook handlers for notifications.

Supports sending notifications to:
- Discord
- Slack
- Microsoft Teams
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if TYPE_CHECKING:
    from servicedesk.models.ticket import Ticket

logger: logging.Logger = logging.getLogger(__name__)

# Thread pool for async webhook delivery
_executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=5)


def _get_webhook_config() -> dict[str, Any]:
    """Get webhook configuration from app config.

    Returns:
        Webhook configuration dictionary.
    """
    try:
        from flask import current_app
        config = current_app.config.get("APP_CONFIG", {})
        return config.get("webhooks", {}).get("egress", {})
    except RuntimeError:
        # Outside of application context
        return {}


def _send_webhook(url: str, payload: dict[str, Any], headers: dict[str, str]) -> bool:
    """Send a webhook request.

    Args:
        url: Webhook URL.
        payload: JSON payload to send.
        headers: HTTP headers.

    Returns:
        True if successful, False otherwise.
    """
    if not url:
        return False

    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers=headers, method="POST")

        with urlopen(req, timeout=10) as response:
            if response.status < 300:
                logger.info(f"Webhook sent successfully to {url[:50]}...")
                return True
            else:
                logger.warning(f"Webhook returned status {response.status}")
                return False

    except HTTPError as e:
        logger.error(f"Webhook HTTP error: {e.code} - {e.reason}")
        return False
    except URLError as e:
        logger.error(f"Webhook URL error: {e.reason}")
        return False
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return False


# =============================================================================
# Discord Webhooks
# https://discord.com/developers/docs/resources/webhook#execute-webhook
# =============================================================================

def _send_discord_webhook(ticket: Ticket, event_type: str) -> bool:
    """Send notification to Discord webhook.

    Args:
        ticket: The ticket to notify about.
        event_type: Type of event (created, updated, resolved).

    Returns:
        True if successful.
    """
    config = _get_webhook_config().get("discord", {})

    if not config.get("enabled", False):
        return False

    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        logger.warning("Discord webhook enabled but no URL configured")
        return False

    # Build Discord embed
    color = _get_discord_color(ticket, event_type)
    title = _get_notification_title(event_type)

    embed = {
        "title": f"{title}: {ticket.ticket_number}",
        "description": ticket.ticket_subject,
        "color": color,
        "fields": [
            {
                "name": "Status",
                "value": ticket.ticket_status.replace("_", " ").title(),
                "inline": True,
            },
            {
                "name": "Priority",
                "value": f"{ticket.ticket_impact.title()} / {ticket.ticket_urgency.title()}",
                "inline": True,
            },
            {
                "name": "Queue",
                "value": ticket.assigned_queue.title(),
                "inline": True,
            },
            {
                "name": "Requestor",
                "value": ticket.requestor_name,
                "inline": True,
            },
            {
                "name": "Type",
                "value": ticket.ticket_type,
                "inline": True,
            },
            {
                "name": "Source",
                "value": ticket.ticket_source or "Web",
                "inline": True,
            },
        ],
        "footer": {
            "text": f"Service Desk | {ticket.ticket_created_timestamp}",
        },
    }

    # Add description preview if available
    if ticket.ticket_body and len(ticket.ticket_body) > 0:
        preview = ticket.ticket_body[:200]
        if len(ticket.ticket_body) > 200:
            preview += "..."
        embed["fields"].append({
            "name": "Description",
            "value": f"```{preview}```",
            "inline": False,
        })

    payload = {
        "username": config.get("username", "Service Desk"),
        "avatar_url": config.get("avatar_url", ""),
        "embeds": [embed],
    }

    headers = {
        "Content-Type": "application/json",
    }

    return _send_webhook(webhook_url, payload, headers)


def _get_discord_color(ticket: Ticket, event_type: str) -> int:
    """Get Discord embed color based on ticket state.

    Args:
        ticket: The ticket.
        event_type: Event type.

    Returns:
        Discord color integer.
    """
    if event_type == "resolved":
        return 0x27AE60  # Green

    impact_colors = {
        "critical": 0xE74C3C,  # Red
        "high": 0xE67E22,      # Orange
        "medium": 0xF1C40F,    # Yellow
        "low": 0x3498DB,       # Blue
    }
    return impact_colors.get(ticket.ticket_impact, 0x95A5A6)


# =============================================================================
# Slack Webhooks
# https://api.slack.com/messaging/webhooks
# =============================================================================

def _send_slack_webhook(ticket: Ticket, event_type: str) -> bool:
    """Send notification to Slack webhook.

    Args:
        ticket: The ticket to notify about.
        event_type: Type of event (created, updated, resolved).

    Returns:
        True if successful.
    """
    config = _get_webhook_config().get("slack", {})

    if not config.get("enabled", False):
        return False

    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        logger.warning("Slack webhook enabled but no URL configured")
        return False

    # Build Slack blocks
    title = _get_notification_title(event_type)
    color = _get_slack_color(ticket, event_type)

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"{title}: {ticket.ticket_number}",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{ticket.ticket_subject}*",
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Status:*\n{ticket.ticket_status.replace('_', ' ').title()}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Priority:*\n{ticket.ticket_impact.title()} / {ticket.ticket_urgency.title()}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Queue:*\n{ticket.assigned_queue.title()}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Requestor:*\n{ticket.requestor_name}",
                            },
                        ],
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"Type: {ticket.ticket_type} | Source: {ticket.ticket_source or 'Web'} | {ticket.ticket_created_timestamp}",
                            },
                        ],
                    },
                ],
            },
        ],
    }

    # Add description preview
    if ticket.ticket_body and len(ticket.ticket_body) > 0:
        preview = ticket.ticket_body[:300]
        if len(ticket.ticket_body) > 300:
            preview += "..."
        payload["attachments"][0]["blocks"].insert(2, {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```{preview}```",
            },
        })

    headers = {
        "Content-Type": "application/json",
    }

    return _send_webhook(webhook_url, payload, headers)


def _get_slack_color(ticket: Ticket, event_type: str) -> str:
    """Get Slack attachment color based on ticket state.

    Args:
        ticket: The ticket.
        event_type: Event type.

    Returns:
        Hex color string.
    """
    if event_type == "resolved":
        return "#27AE60"

    impact_colors = {
        "critical": "#E74C3C",
        "high": "#E67E22",
        "medium": "#F1C40F",
        "low": "#3498DB",
    }
    return impact_colors.get(ticket.ticket_impact, "#95A5A6")


# =============================================================================
# Microsoft Teams Webhooks
# https://docs.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook
# =============================================================================

def _send_teams_webhook(ticket: Ticket, event_type: str) -> bool:
    """Send notification to Microsoft Teams webhook.

    Args:
        ticket: The ticket to notify about.
        event_type: Type of event (created, updated, resolved).

    Returns:
        True if successful.
    """
    config = _get_webhook_config().get("teams365", {})

    if not config.get("enabled", False):
        return False

    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        logger.warning("Teams webhook enabled but no URL configured")
        return False

    # Build Teams Adaptive Card
    title = _get_notification_title(event_type)
    color = _get_teams_color(ticket, event_type)

    # Microsoft Teams uses Adaptive Cards or legacy MessageCard format
    # Using MessageCard for broader compatibility
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": color,
        "summary": f"{title}: {ticket.ticket_number}",
        "sections": [
            {
                "activityTitle": f"{title}: {ticket.ticket_number}",
                "activitySubtitle": ticket.ticket_subject,
                "facts": [
                    {
                        "name": "Status",
                        "value": ticket.ticket_status.replace("_", " ").title(),
                    },
                    {
                        "name": "Priority",
                        "value": f"{ticket.ticket_impact.title()} / {ticket.ticket_urgency.title()}",
                    },
                    {
                        "name": "Queue",
                        "value": ticket.assigned_queue.title(),
                    },
                    {
                        "name": "Requestor",
                        "value": ticket.requestor_name,
                    },
                    {
                        "name": "Type",
                        "value": ticket.ticket_type,
                    },
                    {
                        "name": "Source",
                        "value": ticket.ticket_source or "Web",
                    },
                ],
                "markdown": True,
            },
        ],
    }

    # Add description preview
    if ticket.ticket_body and len(ticket.ticket_body) > 0:
        preview = ticket.ticket_body[:300]
        if len(ticket.ticket_body) > 300:
            preview += "..."
        payload["sections"][0]["text"] = f"**Description:**\n```\n{preview}\n```"

    headers = {
        "Content-Type": "application/json",
    }

    return _send_webhook(webhook_url, payload, headers)


def _get_teams_color(ticket: Ticket, event_type: str) -> str:
    """Get Teams theme color based on ticket state.

    Args:
        ticket: The ticket.
        event_type: Event type.

    Returns:
        Hex color string (without #).
    """
    if event_type == "resolved":
        return "27AE60"

    impact_colors = {
        "critical": "E74C3C",
        "high": "E67E22",
        "medium": "F1C40F",
        "low": "3498DB",
    }
    return impact_colors.get(ticket.ticket_impact, "95A5A6")


# =============================================================================
# Public API
# =============================================================================

def _get_notification_title(event_type: str) -> str:
    """Get notification title based on event type.

    Args:
        event_type: The event type.

    Returns:
        Human-readable title.
    """
    titles = {
        "created": "New Ticket",
        "updated": "Ticket Updated",
        "resolved": "Ticket Resolved",
        "escalated": "Ticket Escalated",
        "assigned": "Ticket Assigned",
    }
    return titles.get(event_type, "Ticket Notification")


def send_ticket_created_webhook(ticket: Ticket) -> None:
    """Send webhook notifications for newly created ticket.

    Args:
        ticket: The created ticket.
    """
    _executor.submit(_send_all_webhooks, ticket, "created")


def send_ticket_updated_webhook(ticket: Ticket) -> None:
    """Send webhook notifications for updated ticket.

    Args:
        ticket: The updated ticket.
    """
    _executor.submit(_send_all_webhooks, ticket, "updated")


def send_ticket_resolved_webhook(ticket: Ticket) -> None:
    """Send webhook notifications for resolved ticket.

    Args:
        ticket: The resolved ticket.
    """
    _executor.submit(_send_all_webhooks, ticket, "resolved")


def _send_all_webhooks(ticket: Ticket, event_type: str) -> None:
    """Send webhooks to all configured destinations.

    Args:
        ticket: The ticket.
        event_type: Type of event.
    """
    results = {
        "discord": _send_discord_webhook(ticket, event_type),
        "slack": _send_slack_webhook(ticket, event_type),
        "teams": _send_teams_webhook(ticket, event_type),
    }

    enabled = [name for name, success in results.items() if success]
    if enabled:
        logger.info(f"Sent {event_type} webhook for {ticket.ticket_number} to: {', '.join(enabled)}")
