#!/usr/bin/env python3
from flask import Blueprint, render_template, request, session, jsonify
import json
import logging
from decorators import technician_required, manager_required
from local_handlers.local_config_loader import load_core_config

core_config = load_core_config()
TICKETS_FILE = core_config["tickets_file"]
BUILDID = "1.0.0"

itsm_queues_bp = Blueprint('itsm_queues', __name__, url_prefix='/itsm/queue')

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

QUEUE_TYPES = {
    'triage': 'Unassigned Tickets',
    'support': 'Support Queue',
    'billing': 'Billing Queue'
}

def get_queue_tickets(queue_name):
    tickets = load_tickets()
    if queue_name == 'triage':
        return [t for t in tickets if t.get("assigned_support_person") is None and t["ticket_status"] != "closed"]
    elif queue_name == 'support':
        return [t for t in tickets if t.get("assigned_team_queue") == "support" and t["ticket_status"] != "closed"]
    elif queue_name == 'billing':
        return [t for t in tickets if t.get("assigned_team_queue") == "billing" and t["ticket_status"] != "closed"]
    return []

@itsm_queues_bp.route('/triage')
@technician_required
def triage_queue():
    tickets = get_queue_tickets('triage')
    return render_template("itsm_queue.html", queue_name='triage',
                         queue_display='Triage Queue (Unassigned)',
                         tickets=tickets, loggedInTech=session["technician"],
                         BUILDID=BUILDID)

@itsm_queues_bp.route('/support')
@technician_required
def support_queue():
    tickets = get_queue_tickets('support')
    return render_template("itsm_queue.html", queue_name='support',
                         queue_display='Support Queue',
                         tickets=tickets, loggedInTech=session["technician"],
                         BUILDID=BUILDID)

@itsm_queues_bp.route('/billing')
@technician_required
def billing_queue():
    tickets = get_queue_tickets('billing')
    return render_template("itsm_queue.html", queue_name='billing',
                         queue_display='Billing Queue',
                         tickets=tickets, loggedInTech=session["technician"],
                         BUILDID=BUILDID)

@itsm_queues_bp.route('/<queue_name>/assign/<ticket_number>', methods=["POST"])
@manager_required
def assign_ticket(queue_name, ticket_number):
    assigned_person = request.form.get("assigned_person")

    if queue_name not in QUEUE_TYPES:
        return jsonify({"error": "Invalid queue"}), 400

    if not assigned_person:
        return jsonify({"error": "Assigned person required"}), 400

    tickets = load_tickets()
    for ticket in tickets:
        if ticket["ticket_number"] == ticket_number:
            ticket["assigned_support_person"] = assigned_person
            ticket["assigned_team_queue"] = queue_name
            save_tickets(tickets)
            logging.info(f"Ticket {ticket_number} assigned to {assigned_person}")
            return jsonify({"success": True, "message": f"Ticket assigned to {assigned_person}"})

    return jsonify({"error": "Ticket not found"}), 404
