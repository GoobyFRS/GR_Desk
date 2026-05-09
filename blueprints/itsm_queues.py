#!/usr/bin/env python3
"""ITSM queue management module.

Provides routes for viewing and managing ticket queues including
triage, support, and billing queues.
"""

import logging
from typing import Any

from flask import Blueprint, jsonify, render_template, request, session

from decorators import manager_required, technician_required
from local_handlers.local_config_loader import load_core_config
from local_handlers.local_storage_handler import load_tickets, save_tickets

core_config = load_core_config()
LOG_LEVEL: str = core_config["logging"]["level"]
LOG_FILE: str = core_config["logging"]["file"]
BUILD_ID: str = "1.0.0"

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

itsm_queues_bp = Blueprint("itsm_queues", __name__, url_prefix="/itsm/queue")

QUEUE_TYPES: dict[str, str] = {
    "triage": "Unassigned Tickets",
    "support": "Support Queue",
    "billing": "Billing Queue",
}


def get_queue_tickets(queue_name: str) -> list[dict[str, Any]]:
    """Get tickets filtered by queue name.

    Args:
        queue_name: The queue to filter by (triage, support, billing).

    Returns:
        List of ticket dictionaries matching the queue criteria.
    """
    tickets = load_tickets()

    if queue_name == "triage":
        return [
            t for t in tickets
            if t.get("assigned_technician") is None
            and t.get("ticket_status") != "closed"
        ]
    elif queue_name == "support":
        return [
            t for t in tickets
            if t.get("assigned_queue") == "support"
            and t.get("ticket_status") != "closed"
        ]
    elif queue_name == "billing":
        return [
            t for t in tickets
            if t.get("assigned_queue") == "billing"
            and t.get("ticket_status") != "closed"
        ]

    return []


@itsm_queues_bp.route("/triage")
@technician_required
def triage_queue() -> str:
    """Display the triage queue with unassigned tickets.

    Returns:
        Rendered queue template.
    """
    tickets = get_queue_tickets("triage")
    return render_template(
        "itsm_queue.html",
        queue_name="triage",
        queue_display="Triage Queue (Unassigned)",
        tickets=tickets,
        loggedInTech=session["technician"],
        BUILDID=BUILD_ID,
    )


@itsm_queues_bp.route("/support")
@technician_required
def support_queue() -> str:
    """Display the support queue.

    Returns:
        Rendered queue template.
    """
    tickets = get_queue_tickets("support")
    return render_template(
        "itsm_queue.html",
        queue_name="support",
        queue_display="Support Queue",
        tickets=tickets,
        loggedInTech=session["technician"],
        BUILDID=BUILD_ID,
    )


@itsm_queues_bp.route("/billing")
@technician_required
def billing_queue() -> str:
    """Display the billing queue.

    Returns:
        Rendered queue template.
    """
    tickets = get_queue_tickets("billing")
    return render_template(
        "itsm_queue.html",
        queue_name="billing",
        queue_display="Billing Queue",
        tickets=tickets,
        loggedInTech=session["technician"],
        BUILDID=BUILD_ID,
    )


@itsm_queues_bp.route("/<queue_name>/assign/<ticket_number>", methods=["POST"])
@manager_required
def assign_ticket(queue_name: str, ticket_number: str) -> tuple[Any, int]:
    """Assign a ticket to a technician and queue.

    Args:
        queue_name: The queue to assign the ticket to.
        ticket_number: The ticket number to assign.

    Returns:
        JSON response with success or error message and HTTP status code.
    """
    assigned_person = request.form.get("assigned_person")

    if queue_name not in QUEUE_TYPES:
        return jsonify({"error": "Invalid queue"}), 400

    if not assigned_person:
        return jsonify({"error": "Assigned person required"}), 400

    tickets = load_tickets()

    for ticket in tickets:
        if ticket["ticket_number"] != ticket_number:
            continue

        ticket["assigned_technician"] = assigned_person
        ticket["assigned_queue"] = queue_name
        save_tickets(tickets)

        logging.info(f"Ticket {ticket_number} assigned to {assigned_person}")
        return jsonify({
            "success": True,
            "message": f"Ticket assigned to {assigned_person}"
        }), 200

    return jsonify({"error": "Ticket not found"}), 404
