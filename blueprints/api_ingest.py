#!/usr/bin/env python3
"""API ingest module for webhook integrations.

Handles incoming webhooks from external services (Tailscale, Uptime Kuma,
GoobyDNS) and creates corresponding support tickets.
"""

from datetime import datetime
from typing import Any

from flask import Blueprint, jsonify, request
import logging

from local_handlers.local_config_loader import load_core_config
import local_handlers.local_storage_handler as local_storage_handler
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
def tailscale_webhook() -> tuple[dict[str, Any], int]:
    """Handle Tailscale webhook notifications.

    Creates a support ticket from incoming Tailscale events.

    Returns:
        JSON response with ticket number or error message and HTTP status code.
    """
    TAILSCALE_NOTIFY_EMAIL: str = (
        api_ingest_bp.config.get("TAILSCALE_NOTIFY_EMAIL", "noreply@tailscale.example.org")
        if hasattr(api_ingest_bp, "config")
        else "noreply@tailscale.example.org"
    )

    try:
        payload = request.json
        if not payload:
            logging.warning("API INGEST - Tailscale webhook sent an empty payload.")
            return jsonify({"error": "Empty payload"}), 400

        import json
        formatted_ts_webhook_body = json.dumps(payload, indent=4)

        requestor_name = "Tailscale"
        requestor_email = TAILSCALE_NOTIFY_EMAIL
        ticket_subject = "Tailscale Notification"
        ticket_message = formatted_ts_webhook_body
        ticket_impact = "Medium"
        ticket_urgency = "Medium"
        request_type = "Change"
        ticket_number = local_storage_handler.generate_ticket_number()

        new_ticket: dict[str, Any] = {
            "ticket_number": ticket_number,
            "requestor_name": requestor_name,
            "requestor_email": requestor_email,
            "ticket_subject": ticket_subject,
            "ticket_message": ticket_message,
            "request_type": request_type,
            "ticket_impact": ticket_impact,
            "ticket_urgency": ticket_urgency,
            "ticket_status": "Open",
            "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket_notes": [],
        }

        tickets = local_storage_handler.load_tickets()
        tickets.append(new_ticket)
        local_storage_handler.save_tickets(tickets)
        logging.info(f"Tailscale Notification — {ticket_number} created successfully.")

        try:
            local_webhook_handler.notify_ticket_event(
                ticket_number=ticket_number,
                ticket_status="Open",
                ticket_subject=ticket_subject,
            )
            logging.info(
                f"API INGEST - Ticket {ticket_number} status "
                "notifications sent successfully."
            )
        except Exception as e:
            logging.error(
                f"API INGEST - Failed to send ticket status update "
                f"notifications for {ticket_number}: {str(e)}"
            )

        return jsonify({"status": "success", "ticket": ticket_number}), 200

    except Exception as e:
        logging.critical(f"API INGEST - Tailscale webhook error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@api_ingest_bp.route("/uptime-kuma", methods=["POST"])
def uptime_kuma_webhook() -> tuple[dict[str, Any], int]:
    """Handle Uptime Kuma webhook notifications.

    Creates a support ticket from Uptime Kuma monitoring events.

    Returns:
        JSON response with ticket number or error message and HTTP status code.
    """
    try:
        if not request.is_json:
            logging.warning(
                "API INGEST - Uptime-Kuma webhook sent invalid content type."
            )
            return jsonify({"error": "Invalid content type"}), 400
            return jsonify({"error": "Invalid content type"}), 400
        payload = request.json
        logging.info(f"API INGEST -Uptime Kuma payload received: {payload}")

        heartbeat = payload.get("heartbeat", {})
        monitor = payload.get("monitor", {})

        status = heartbeat.get("status")
        monitor_name = monitor.get("name", "Unknown Monitor")
        monitor_url = monitor.get("url", "Unknown URL")
        message = heartbeat.get("msg", payload.get("msg", "No message"))

        status_text = {
            0: "DOWN",
            1: "UP",
            2: "PENDING",
            3: "MAINTENANCE"
        }.get(status, "UNKNOWN")

        if status not in [0, 2]:
            logging.info(f"API INGEST - Skipping ticket creation for {monitor_name} (status={status_text}).")
            return jsonify({"status": "ignored", "reason": f"status {status_text} not tracked"}), 200

        if status == 0:
            ticket_subject = f"Uptime Kuma Alert - {monitor_name} is DOWN"
            ticket_impact = "High"
            ticket_urgency = "High"
            request_type = "Incident"
        elif status == 2:
            ticket_subject = f"Uptime Kuma Alert - {monitor_name} is PENDING"
            ticket_impact = "Medium"
            ticket_urgency = "Medium"
            request_type = "Incident"

        ticket_message = json.dumps(payload, indent=4)
        ticket_number = generate_ticket_number()

        new_ticket = {
            "ticket_number": ticket_number,
            "requestor_name": "Uptime Kuma",
            "requestor_email": "noreply@uptimekuma.example.org",
            "ticket_subject": ticket_subject,
            "ticket_message": ticket_message,
            "request_type": request_type,
            "ticket_impact": ticket_impact,
            "ticket_urgency": ticket_urgency,
            "ticket_status": "Open",
            "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket_notes": []
        }

        tickets = load_tickets()
        tickets.append(new_ticket)
        save_tickets(tickets)

        logging.info(f"API INGEST -Uptime-Kuma Notification {ticket_number} created successfully (Status: {status_text}).")

        try:
            local_webhook_handler.notify_ticket_event(
                ticket_number=ticket_number,
                ticket_status="Open",
                ticket_subject=ticket_subject
            )
            logging.info(f"API INGEST -Ticket {ticket_number} status update notifications sent successfully.")
        except Exception as e:
            logging.error(f"API INGEST - Failed to send ticket status update notifications for {ticket_number}: {str(e)}")

        return jsonify({"status": "success", "ticket": ticket_number}), 200

    except Exception as e:
        logging.critical(f"API INGEST - Uptime Kuma webhook error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
"""
@api_ingest_bp.route("/goobyddns", methods=["POST"])
def goobyddns_webhook():

new_ticket = {
            "ticket_number": ticket_number,
            "requestor_name": "GoobyDDNS",
            "requestor_email": "noreply@goobyddns.example.org",
            "ticket_subject": ticket_subject,
            "ticket_message": ticket_message,
            "request_type": request_type,
            "ticket_impact": Low,
            "ticket_urgency": Low,
            "ticket_status": "Open",
            "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ticket_notes": []
        }
"""
    