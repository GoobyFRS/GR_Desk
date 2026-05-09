#!/usr/bin/env python3
"""ITSM Core module for ticket management operations.

Provides routes for viewing, updating, and managing IT service tickets
including status changes, note additions, and ticket console views.
"""

import logging
from datetime import datetime
from typing import Any

from flask import (
    Blueprint,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from decorators import technician_required
from local_handlers.local_config_loader import load_core_config
from local_handlers.local_storage_handler import load_tickets, save_tickets
import local_handlers.local_webhook_handler as local_webhook_handler

core_config = load_core_config()
BUILD_ID: str = "1.0.0"

itsm_core_bp = Blueprint("itsm_core", __name__, url_prefix="/itsm")

@itsm_core_bp.route("/dashboard")
@technician_required
def itsm_dashboard() -> str:
    """Display the ITSM dashboard with open tickets.

    Shows all tickets that are not closed or cancelled.

    Returns:
        Rendered HTML template for the ITSM dashboard.
    """
    tickets = load_tickets()
    open_tickets = [
        t for t in tickets
        if t["ticket_status"] not in ["closed", "cancelled"]
    ]
    return render_template(
        "itsm_dashboard.html",
        tickets=open_tickets,
        loggedInTech=session["technician"],
        BUILDID=BUILD_ID,
    )


@itsm_core_bp.route("/")
def itsm_root() -> Any:
    """Redirect root ITSM path to dashboard.

    Returns:
        Redirect response to ITSM dashboard.
    """
    return redirect(url_for("itsm_core.itsm_dashboard"))

VALID_TICKET_STATUSES: list[str] = [
    "new", "in_progress", "on_hold", "closed", "cancelled"
]


@itsm_core_bp.route("/console/<ticket_number>", methods=["GET", "POST"])
@technician_required
def itsm_console(ticket_number: str) -> tuple[Any, int] | str:
    """Display or update a ticket in the ITSM console.

    Handles both GET requests (display ticket) and POST requests
    (update status or add notes).

    Args:
        ticket_number: The unique ticket identifier.

    Returns:
        For GET: Rendered ticket console template or 404 page.
        For POST: JSON response with success/error message.
    """
    if request.method == "POST":
        return _handle_console_post(ticket_number)

    return _handle_console_get(ticket_number)


def _handle_console_post(ticket_number: str) -> tuple[Any, int]:
    """Handle POST requests for ticket console actions.

    Args:
        ticket_number: The unique ticket identifier.

    Returns:
        JSON response tuple with message and HTTP status code.
    """
    action = request.form.get("action")

    if action == "status":
        return _update_ticket_status(ticket_number)
    elif action == "note":
        return _add_ticket_note(ticket_number)

    return jsonify({"error": "Invalid action"}), 400


def _update_ticket_status(ticket_number: str) -> tuple[Any, int]:
    """Update the status of a ticket.

    Args:
        ticket_number: The unique ticket identifier.

    Returns:
        JSON response tuple with success/error message and HTTP status code.
    """
    new_status = request.form.get("status")

    if new_status not in VALID_TICKET_STATUSES:
        return jsonify({"error": "Invalid status"}), 400

    tickets = load_tickets()
    for ticket in tickets:
        if ticket["ticket_number"] != ticket_number:
            continue

        ticket["ticket_status"] = new_status

        if new_status == "closed":
            ticket["ticket_closed_timestamp"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        elif new_status == "in_progress":
            ticket["ticket_acknowledged_timestamp"] = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

        save_tickets(tickets)
        logging.info(
            f"Ticket {ticket_number} status updated to {new_status} "
            f"by {session['technician']}"
        )

        _send_webhook_notification(
            ticket_number, new_status, ticket.get("ticket_subject", "")
        )

        return jsonify({
            "success": True,
            "message": f"Ticket updated to {new_status}"
        }), 200

    return jsonify({"error": "Ticket not found"}), 404


def _add_ticket_note(ticket_number: str) -> tuple[Any, int]:
    """Add a note to a ticket.

    Args:
        ticket_number: The unique ticket identifier.

    Returns:
        JSON response tuple with success/error message and HTTP status code.
    """
    note_content = request.form.get("note")
    if not note_content:
        return jsonify({"error": "Note cannot be empty"}), 400

    tickets = load_tickets()
    for ticket in tickets:
        if ticket["ticket_number"] != ticket_number:
            continue

        note_entry = {
            "author": session["technician"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": note_content,
        }
        ticket["ticket_worknotes"].append(note_entry)
        save_tickets(tickets)
        logging.info(
            f"Note added to {ticket_number} by {session['technician']}"
        )
        return jsonify({"success": True, "message": "Note added successfully"}), 200

    return jsonify({"error": "Ticket not found"}), 404


def _send_webhook_notification(
    ticket_number: str, ticket_status: str, ticket_subject: str
) -> None:
    """Send webhook notification for ticket event.

    Args:
        ticket_number: The unique ticket identifier.
        ticket_status: The new ticket status.
        ticket_subject: The ticket subject line.
    """
    try:
        local_webhook_handler.notify_ticket_event(
            ticket_number=ticket_number,
            ticket_status=ticket_status,
            ticket_subject=ticket_subject,
        )
    except Exception as e:
        logging.error(f"Webhook notification failed: {e}")


def _handle_console_get(ticket_number: str) -> tuple[str, int] | str:
    """Handle GET request for ticket console display.

    Args:
        ticket_number: The unique ticket identifier.

    Returns:
        Rendered ticket console template or 404 page with status code.
    """
    tickets = load_tickets()
    ticket = next(
        (t for t in tickets if t["ticket_number"] == ticket_number), None
    )

    if not ticket:
        return render_template("404.html"), 404

    return render_template(
        "itsm_console.html",
        ticket=ticket,
        loggedInTech=session["technician"],
        BUILDID=BUILD_ID,
    )
