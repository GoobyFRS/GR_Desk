#!/usr/bin/env python3
"""API ingest module for webhook integrations.

Handles incoming webhooks from external services (Tailscale, Uptime Kuma,
GoobyDNS) and creates corresponding support tickets.
"""

import json
import logging
from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify, request

from local_handlers.local_config_loader import load_core_config
from local_handlers.local_storage_handler import (
    generate_ticket_number,
    load_tickets,
    save_tickets,
)
import local_handlers.local_webhook_handler as local_webhook_handler

core_yaml_config = load_core_config()
LOG_LEVEL: str = core_yaml_config["logging"]["level"]
LOG_FILE: str = core_yaml_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

api_ingest_bp = Blueprint("api_ingest", __name__, url_prefix="/api")

DEFAULT_TAILSCALE_EMAIL: str = "noreply@tailscale.example.org"
DEFAULT_UPTIME_KUMA_EMAIL: str = "noreply@uptimekuma.example.org"

UPTIME_KUMA_STATUS_MAP: dict[int, str] = {
    0: "DOWN",
    1: "UP",
    2: "PENDING",
    3: "MAINTENANCE",
}


@api_ingest_bp.route("/status", methods=["GET"])
def api_status() -> tuple[dict[str, Any], int]:
    """Check API status and GR_Desk installation.

    Returns:
        JSON response with API status information and 200 status code.
    """
    return (
        jsonify(
            {
                "is_gr_desk": True,
                "installed": True,
                "edition": "community",
                "license_key": None,
            }
        ),
        200,
    )


@api_ingest_bp.route("/tailscale", methods=["POST"])
def tailscale_webhook() -> tuple[Any, int]:
    """Handle Tailscale webhook notifications.

    Creates a support ticket from incoming Tailscale events.

    Returns:
        JSON response with ticket number or error message and HTTP status code.
    """
    tailscale_email: str = _get_tailscale_email()

    try:
        payload = request.json
        if not payload:
            logging.warning("API INGEST - Tailscale webhook sent an empty payload.")
            return jsonify({"error": "Empty payload"}), 400

        ticket_number = generate_ticket_number()
        ticket_subject = "Tailscale Notification"

        new_ticket: dict[str, Any] = {
            "ticket_number": ticket_number,
            "requestor_name": "Tailscale",
            "requestor_email": tailscale_email,
            "ticket_subject": ticket_subject,
            "ticket_message": json.dumps(payload, indent=4),
            "request_type": "Change",
            "ticket_impact": "Medium",
            "ticket_urgency": "Medium",
            "ticket_status": "Open",
            "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket_worknotes": [],
        }

        tickets = load_tickets()
        tickets.append(new_ticket)
        save_tickets(tickets)
        logging.info(f"Tailscale Notification — {ticket_number} created successfully.")

        _send_ticket_webhook(ticket_number, "Open", ticket_subject)

        return jsonify({"status": "success", "ticket": ticket_number}), 200

    except Exception as e:
        logging.critical(f"API INGEST - Tailscale webhook error: {e}")
        return jsonify({"error": "Internal server error"}), 500


def _get_tailscale_email() -> str:
    """Get the Tailscale notification email from configuration.

    Returns:
        Email address for Tailscale notifications.
    """
    if hasattr(api_ingest_bp, "config") and api_ingest_bp.config:
        return api_ingest_bp.config.get(
            "TAILSCALE_NOTIFY_EMAIL", DEFAULT_TAILSCALE_EMAIL
        )
    return DEFAULT_TAILSCALE_EMAIL


def _send_ticket_webhook(
    ticket_number: str, ticket_status: str, ticket_subject: str
) -> None:
    """Send webhook notification for a new ticket.

    Args:
        ticket_number: The unique ticket identifier.
        ticket_status: The ticket status.
        ticket_subject: The ticket subject line.
    """
    try:
        local_webhook_handler.notify_ticket_event(
            ticket_number=ticket_number,
            ticket_status=ticket_status,
            ticket_subject=ticket_subject,
        )
        logging.info(
            f"API INGEST - Ticket {ticket_number} notifications sent successfully."
        )
    except Exception as e:
        logging.error(
            f"API INGEST - Failed to send notifications for {ticket_number}: {e}"
        )


@api_ingest_bp.route("/uptime-kuma", methods=["POST"])
def uptime_kuma_webhook() -> tuple[Any, int]:
    """Handle Uptime Kuma webhook notifications.

    Creates a support ticket from Uptime Kuma monitoring events.
    Only creates tickets for DOWN (0) and PENDING (2) statuses.

    Returns:
        JSON response with ticket number or error message and HTTP status code.
    """
    try:
        if not request.is_json:
            logging.warning(
                "API INGEST - Uptime-Kuma webhook sent invalid content type."
            )
            return jsonify({"error": "Invalid content type"}), 400

        payload = request.json
        logging.info(f"API INGEST - Uptime Kuma payload received: {payload}")

        heartbeat = payload.get("heartbeat", {})
        monitor = payload.get("monitor", {})

        status = heartbeat.get("status")
        monitor_name = monitor.get("name", "Unknown Monitor")
        status_text = UPTIME_KUMA_STATUS_MAP.get(status, "UNKNOWN")

        # Only create tickets for DOWN or PENDING statuses
        if status not in [0, 2]:
            logging.info(
                f"API INGEST - Skipping ticket for {monitor_name} "
                f"(status={status_text})."
            )
            return jsonify({
                "status": "ignored",
                "reason": f"status {status_text} not tracked"
            }), 200

        ticket_info = _build_uptime_kuma_ticket_info(status, monitor_name)
        ticket_number = generate_ticket_number()

        new_ticket: dict[str, Any] = {
            "ticket_number": ticket_number,
            "requestor_name": "Uptime Kuma",
            "requestor_email": DEFAULT_UPTIME_KUMA_EMAIL,
            "ticket_subject": ticket_info["subject"],
            "ticket_message": json.dumps(payload, indent=4),
            "request_type": ticket_info["request_type"],
            "ticket_impact": ticket_info["impact"],
            "ticket_urgency": ticket_info["urgency"],
            "ticket_status": "Open",
            "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket_worknotes": [],
        }

        tickets = load_tickets()
        tickets.append(new_ticket)
        save_tickets(tickets)

        logging.info(
            f"API INGEST - Uptime-Kuma Notification {ticket_number} "
            f"created successfully (Status: {status_text})."
        )

        _send_ticket_webhook(ticket_number, "Open", ticket_info["subject"])

        return jsonify({"status": "success", "ticket": ticket_number}), 200

    except Exception as e:
        logging.critical(f"API INGEST - Uptime Kuma webhook error: {e}")
        return jsonify({"error": "Internal server error"}), 500


def _build_uptime_kuma_ticket_info(
    status: int, monitor_name: str
) -> dict[str, str]:
    """Build ticket metadata based on Uptime Kuma status.

    Args:
        status: The Uptime Kuma status code (0=DOWN, 2=PENDING).
        monitor_name: The name of the monitored service.

    Returns:
        Dictionary with subject, impact, urgency, and request_type.
    """
    if status == 0:
        return {
            "subject": f"Uptime Kuma Alert - {monitor_name} is DOWN",
            "impact": "High",
            "urgency": "High",
            "request_type": "Incident",
        }
    # status == 2 (PENDING)
    return {
        "subject": f"Uptime Kuma Alert - {monitor_name} is PENDING",
        "impact": "Medium",
        "urgency": "Medium",
        "request_type": "Incident",
    }


# TODO: Implement GoobyDDNS webhook handler when ready
# @api_ingest_bp.route("/goobyddns", methods=["POST"])
# def goobyddns_webhook() -> tuple[Any, int]:
#     """Handle GoobyDDNS webhook notifications."""
#     pass
