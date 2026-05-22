"""ITSM blueprint for ticket management."""

from __future__ import annotations

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user

from servicedesk.auth.decorators import technician_required
from servicedesk.config import load_navbar
from servicedesk.models.ticket import Ticket
from servicedesk.storage.yaml_store import YamlStore
from servicedesk.webhooks.egress import (
    send_ticket_resolved_webhook,
    send_ticket_updated_webhook,
)

itsm_bp = Blueprint("itsm", __name__, template_folder="../templates")


@itsm_bp.context_processor
def inject_navbar() -> dict[str, object]:
    """Inject employee navbar config into templates."""
    config_path = current_app.config["CONFIG_PATH"]
    navbar = load_navbar(config_path / "employee_navbar.yml")
    return {"employee_navbar": navbar}


@itsm_bp.route("/")
@technician_required
def index() -> str:
    """Redirect to dashboard.

    Returns:
        Redirect to ITSM dashboard.
    """
    return redirect(url_for("itsm.dashboard"))  # type: ignore[return-value]


@itsm_bp.route("/dashboard")
@technician_required
def dashboard() -> str:
    """ITSM dashboard showing support queue tickets.

    Returns:
        Rendered dashboard template.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Ticket] = YamlStore(data_path / "tickets.yaml", Ticket)

    # Get unresolved tickets in support queue
    all_tickets = store.get_all()
    tickets = [
        t
        for t in all_tickets
        if t.assigned_queue == "support" and t.ticket_status not in ("resolved", "cancelled")
    ]

    # Sort by created timestamp (newest first)
    tickets.sort(key=lambda t: t.ticket_created_timestamp, reverse=True)

    config = current_app.config["APP_CONFIG"]
    ticket_config = config.get("tickets", {})

    return render_template(
        "itsm/dashboard.html",
        tickets=tickets,
        queue_name="support",
        statuses=ticket_config.get("statuses", []),
    )


@itsm_bp.route("/queues/<queue_name>")
@technician_required
def queue(queue_name: str) -> str:
    """Display tickets in a specific queue.

    Args:
        queue_name: Name of the queue to display.

    Returns:
        Rendered queue template.
    """
    config = current_app.config["APP_CONFIG"]
    ticket_config = config.get("tickets", {})
    valid_queues = ticket_config.get("queues", ["support", "escalation", "billing"])

    if queue_name not in valid_queues:
        flash(f"Invalid queue: {queue_name}", "danger")
        return redirect(url_for("itsm.dashboard"))  # type: ignore[return-value]

    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Ticket] = YamlStore(data_path / "tickets.yaml", Ticket)

    # Get unresolved tickets in the specified queue
    all_tickets = store.get_all()
    tickets = [
        t
        for t in all_tickets
        if t.assigned_queue == queue_name and t.ticket_status not in ("resolved", "cancelled")
    ]

    # Sort by created timestamp (newest first)
    tickets.sort(key=lambda t: t.ticket_created_timestamp, reverse=True)

    return render_template(
        "itsm/queue.html",
        tickets=tickets,
        queue_name=queue_name,
        statuses=ticket_config.get("statuses", []),
    )


@itsm_bp.route("/console/<ticket_number>", methods=["GET", "POST"])
@technician_required
def console(ticket_number: str) -> str:
    """Display and edit a single ticket.

    Args:
        ticket_number: The ticket number (INC-YYYY-NNNN).

    Returns:
        Rendered ticket console template.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Ticket] = YamlStore(data_path / "tickets.yaml", Ticket)

    ticket = store.get_by_field("ticket_number", ticket_number)

    if ticket is None:
        flash(f"Ticket {ticket_number} not found.", "danger")
        return redirect(url_for("itsm.dashboard"))  # type: ignore[return-value]

    config = current_app.config["APP_CONFIG"]
    ticket_config = config.get("tickets", {})

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_status":
            new_status = request.form.get("status")
            if new_status in ticket_config.get("statuses", []):
                ticket.ticket_status = new_status
                if new_status == "resolved":
                    resolution = request.form.get("resolution_notes", "")
                    ticket.resolve(resolution or "Resolved")
                    store.save(ticket)
                    send_ticket_resolved_webhook(ticket)
                else:
                    store.save(ticket)
                    send_ticket_updated_webhook(ticket)
                flash(f"Status updated to {new_status}.", "success")

        elif action == "add_worknote":
            worknote = request.form.get("worknote", "").strip()
            if worknote:
                author = current_user.full_name if current_user.is_authenticated else "System"
                ticket.add_worknote(author, worknote)
                store.save(ticket)
                flash("Work note added.", "success")

        elif action == "assign":
            ticket.assigned_technician = current_user.employee_id
            if ticket.ticket_acknowledged_timestamp is None:
                from datetime import datetime
                ticket.ticket_acknowledged_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
            store.save(ticket)
            flash("Ticket assigned to you.", "success")

        elif action == "escalate":
            ticket.escalate()
            store.save(ticket)
            flash("Ticket escalated.", "warning")

        elif action == "change_queue":
            new_queue = request.form.get("queue")
            if new_queue in ticket_config.get("queues", []):
                ticket.assigned_queue = new_queue
                store.save(ticket)
                flash(f"Ticket moved to {new_queue} queue.", "success")

        return redirect(url_for("itsm.console", ticket_number=ticket_number))  # type: ignore[return-value]

    return render_template(
        "itsm/console.html",
        ticket=ticket,
        statuses=ticket_config.get("statuses", []),
        queues=ticket_config.get("queues", []),
        impacts=ticket_config.get("impacts", []),
        urgencies=ticket_config.get("urgencies", []),
    )
