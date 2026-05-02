#!/usr/bin/env python3
import json
import logging
from datetime import datetime
from decorators import technician_required, manager_required

from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for

import local_handlers.local_webhook_handler as local_webhook_handler
from local_handlers.local_config_loader import load_core_config

core_config = load_core_config()
TICKETS_FILE = core_config["tickets_file"]
BUILDID = "1.0.0"

itsm_core_bp = Blueprint('itsm_core', __name__, url_prefix='/itsm')

def load_tickets():
    try:
        with open(TICKETS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        logging.error("Ticket file is empty or invalid JSON; treating as empty list.")
        return []

def save_tickets(tickets):
    with open(TICKETS_FILE, "w") as f:
        json.dump(tickets, f, indent=4)

@itsm_core_bp.route('/dashboard')
@technician_required
def itsm_dashboard():
    tickets = load_tickets()
    open_tickets = [t for t in tickets if t["ticket_status"] not in ["closed", "cancelled"]]
    return render_template("itsm_dashboard.html", tickets=open_tickets,
                         loggedInTech=session["technician"], BUILDID=BUILDID)


@itsm_core_bp.route('/')
def itsm_root():
    return redirect(url_for('itsm_core.itsm_dashboard'))

@itsm_core_bp.route('/console/<ticket_number>', methods=["GET", "POST"])
@technician_required
def itsm_console(ticket_number):
    if request.method == "POST":
        action = request.form.get("action")

        if action == "status":
            new_status = request.form.get("status")
            valid_statuses = ["new", "in_progress", "on_hold", "closed", "cancelled"]

            if new_status not in valid_statuses:
                return jsonify({"error": "Invalid status"}), 400

            tickets = load_tickets()
            for ticket in tickets:
                if ticket["ticket_number"] == ticket_number:
                    old_status = ticket["ticket_status"]
                    ticket["ticket_status"] = new_status

                    if new_status == "closed":
                        ticket["ticket_closed_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    elif new_status == "in_progress":
                        ticket["ticket_acknowledged_timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    save_tickets(tickets)
                    logging.info(f"Ticket {ticket_number} status updated to {new_status} by {session['technician']}")

                    try:
                        local_webhook_handler.notify_ticket_event(
                            ticket_number=ticket_number,
                            ticket_status=new_status,
                            ticket_subject=ticket.get("ticket_subject", "")
                        )
                    except Exception as e:
                        logging.error(f"Webhook notification failed: {str(e)}")

                    return jsonify({"success": True, "message": f"Ticket updated to {new_status}"})

            return jsonify({"error": "Ticket not found"}), 404

        elif action == "note":
            note_content = request.form.get("note")
            if not note_content:
                return jsonify({"error": "Note cannot be empty"}), 400

            tickets = load_tickets()
            for ticket in tickets:
                if ticket["ticket_number"] == ticket_number:
                    note_entry = {
                        "author": session["technician"],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "content": note_content
                    }
                    ticket["ticket_worknotes"].append(note_entry)
                    save_tickets(tickets)
                    logging.info(f"Note added to {ticket_number} by {session['technician']}")
                    return jsonify({"success": True, "message": "Note added successfully"})

            return jsonify({"error": "Ticket not found"}), 404

    # GET request - display ticket console
    tickets = load_tickets()
    ticket = next((t for t in tickets if t["ticket_number"] == ticket_number), None)

    if not ticket:
        return render_template("404.html"), 404

    return render_template("itsm_console.html", ticket=ticket,
                         loggedInTech=session["technician"], BUILDID=BUILDID)
