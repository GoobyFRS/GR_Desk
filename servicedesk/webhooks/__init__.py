"""Webhook modules for Service Desk."""

from servicedesk.webhooks.egress import (
    send_ticket_created_webhook,
    send_ticket_updated_webhook,
    send_ticket_resolved_webhook,
)

__all__ = [
    "send_ticket_created_webhook",
    "send_ticket_updated_webhook",
    "send_ticket_resolved_webhook",
]
