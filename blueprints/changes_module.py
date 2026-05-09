#!/usr/bin/env python3
"""Change Management module for change request operations.

Provides routes for viewing, creating, updating, and exporting change
requests with implementation plans, test plans, and rollback procedures.
"""

import csv
import io
import logging
from typing import Any

from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from decorators import technician_required
import local_handlers.local_changes_handler as local_changes_handler
from local_handlers.local_config_loader import load_core_config

core_config = load_core_config()
LOG_LEVEL: str = core_config["logging"]["level"]
LOG_FILE: str = core_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

changes_module_bp = Blueprint("changes", __name__, url_prefix="/changes")

VALID_CHANGE_STATUSES: list[str] = [
    "new", "in_progress", "on_hold", "completed", "cancelled"
]


@changes_module_bp.route("/", methods=["GET"])
@technician_required
def changes_home() -> str:
    """Display the changes dashboard with open change requests.

    Shows all change requests that are not completed or cancelled.

    Returns:
        Rendered HTML template for the changes dashboard.
    """
    changes = local_changes_handler.load_changes()
    open_changes = [
        c for c in changes
        if c["change_status"] not in ["completed", "cancelled"]
    ]
    return render_template(
        "changes_dashboard.html",
        changes=open_changes,
        loggedInTech=session["technician"],
    )


@changes_module_bp.route("/submit-new", methods=["GET", "POST"])
@technician_required
def submit_new_change() -> str | tuple[Any, int]:
    """Create a new change request.

    Handles GET requests (display form) and POST requests (create change).

    Returns:
        For GET: Rendered change creation form.
        For POST: Redirect to dashboard on success, or JSON error response.
    """
    if request.method == "POST":
        return _handle_create_change()

    return render_template(
        "changes_submit.html",
        loggedInTech=session["technician"],
    )


def _handle_create_change() -> tuple[Any, int] | Any:
    """Process change request creation form submission.

    Returns:
        Redirect to dashboard on success, or JSON error tuple on failure.
    """
    try:
        requestor = session["technician"]
        subject = request.form.get("change_subject")
        description = request.form.get("change_description")

        if not subject or not description:
            return jsonify({"error": "Subject and description are required"}), 400

        change = local_changes_handler.create_change(
            change_requestor=requestor,
            change_subject=subject,
            change_description=description,
            change_rollback_plan=request.form.get("change_rollback_plan"),
            change_implement_plan=request.form.get("change_implement_plan"),
            change_test_plan=request.form.get("change_test_plan"),
            change_start_timestamp=request.form.get("change_start_timestamp"),
            change_end_timestamp=request.form.get("change_end_timestamp"),
        )

        changes = local_changes_handler.load_changes()
        changes.append(change)
        local_changes_handler.save_changes(changes)

        logging.info(
            f"Change request {change['change_number']} created by {requestor}"
        )
        return redirect(url_for("changes.changes_home"))

    except Exception as e:
        logging.error(f"Error creating change: {e}")
        return jsonify({"error": str(e)}), 500


@changes_module_bp.route("/console/<change_number>", methods=["GET", "POST"])
@technician_required
def changes_console(change_number: str) -> str | tuple[Any, int]:
    """Display or update a change request in the console.

    Handles both GET requests (display change) and POST requests (update status).

    Args:
        change_number: The unique change request identifier.

    Returns:
        For GET: Rendered change console template or 404 page.
        For POST: JSON response with success/error message.
    """
    if request.method == "POST":
        return _handle_change_status_update(change_number)

    change = local_changes_handler.find_change_by_number(change_number)

    if not change:
        return render_template("404.html"), 404

    return render_template(
        "changes_console.html",
        change=change,
        loggedInTech=session["technician"],
    )


def _handle_change_status_update(change_number: str) -> tuple[Any, int]:
    """Handle status update for a change request.

    Args:
        change_number: The unique change request identifier.

    Returns:
        JSON response tuple with success/error message and HTTP status code.
    """
    action = request.form.get("action")

    if action != "status":
        return jsonify({"error": "Invalid action"}), 400

    new_status = request.form.get("status")

    if new_status not in VALID_CHANGE_STATUSES:
        return jsonify({"error": "Invalid status"}), 400

    if local_changes_handler.update_change_status(change_number, new_status):
        logging.info(f"Change {change_number} status updated to {new_status}")
        return jsonify({
            "success": True,
            "message": f"Status updated to {new_status}"
        }), 200

    return jsonify({"error": "Change not found"}), 404


CSV_CHANGE_HEADERS: list[str] = [
    "Change Number",
    "Subject",
    "Status",
    "Requestor",
    "Implementor",
    "Start Date",
    "End Date",
]


@changes_module_bp.route("/export/csv", methods=["GET"])
@technician_required
def export_changes_csv() -> Response:
    """Export open change requests to CSV format.

    Returns:
        CSV file download response with change request data.
    """
    changes = local_changes_handler.load_changes()
    open_changes = [
        c for c in changes
        if c["change_status"] not in ["completed", "cancelled"]
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_CHANGE_HEADERS)

    for change in open_changes:
        writer.writerow([
            change.get("change_number"),
            change.get("change_subject"),
            change.get("change_status"),
            change.get("change_requestor"),
            change.get("change_implementor", "Unassigned"),
            change.get("change_start_timestamp", ""),
            change.get("change_end_timestamp", ""),
        ])

    output.seek(0)
    logging.info(f"Exported {len(open_changes)} changes to CSV")

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=changes.csv"},
    )
