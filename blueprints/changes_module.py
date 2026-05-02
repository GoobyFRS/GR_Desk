#!/usr/bin/env python3
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, Response
import io, csv, logging
from datetime import datetime
from functools import wraps
from decorators import technician_required, manager_required
import local_handlers.local_changes_handler as local_changes_handler
from local_handlers.local_config_loader import load_core_config

core_config = load_core_config()
LOG_LEVEL = core_config["logging"]["level"]
LOG_FILE = core_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s"
)

changes_module_bp = Blueprint("changes", __name__, url_prefix="/changes")

@changes_module_bp.route("/", methods=["GET"])
@technician_required
def changes_home():
    changes = local_changes_handler.load_changes()
    open_changes = [c for c in changes if c["change_status"] not in ["completed", "cancelled"]]
    return render_template("changes_dashboard.html", changes=open_changes,
                         loggedInTech=session["technician"])

@changes_module_bp.route("/submit-new", methods=["GET", "POST"])
@technician_required
def submit_new_change():
    if request.method == "POST":
        try:
            requestor = session["technician"]
            subject = request.form.get("change_subject")
            description = request.form.get("change_description")
            rollback_plan = request.form.get("change_rollback_plan")
            implement_plan = request.form.get("change_implement_plan")
            test_plan = request.form.get("change_test_plan")
            start_timestamp = request.form.get("change_start_timestamp")
            end_timestamp = request.form.get("change_end_timestamp")

            if not subject or not description:
                return jsonify({"error": "Subject and description are required"}), 400

            change = local_changes_handler.create_change(
                change_requestor=requestor,
                change_subject=subject,
                change_description=description,
                change_rollback_plan=rollback_plan,
                change_implement_plan=implement_plan,
                change_test_plan=test_plan,
                change_start_timestamp=start_timestamp,
                change_end_timestamp=end_timestamp
            )

            changes = local_changes_handler.load_changes()
            changes.append(change)
            local_changes_handler.save_changes(changes)

            logging.info(f"Change request {change['change_number']} created by {requestor}")
            return redirect(url_for("changes.changes_home"))

        except Exception as e:
            logging.error(f"Error creating change: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return render_template("changes_submit.html", loggedInTech=session["technician"])

@changes_module_bp.route("/console/<change_number>", methods=["GET", "POST"])
@technician_required
def changes_console(change_number):
    if request.method == "POST":
        action = request.form.get("action")

        if action == "status":
            new_status = request.form.get("status")
            valid_statuses = ["new", "in_progress", "on_hold", "completed", "cancelled"]

            if new_status not in valid_statuses:
                return jsonify({"error": "Invalid status"}), 400

            if local_changes_handler.update_change_status(change_number, new_status):
                logging.info(f"Change {change_number} status updated to {new_status}")
                return jsonify({"success": True, "message": f"Status updated to {new_status}"})
            else:
                return jsonify({"error": "Change not found"}), 404

    change = local_changes_handler.find_change_by_number(change_number)

    if not change:
        return render_template("404.html"), 404

    return render_template("changes_console.html", change=change,
                         loggedInTech=session["technician"])

@changes_module_bp.route("/export/csv", methods=["GET"])
@technician_required
def export_changes_csv():
    changes = local_changes_handler.load_changes()
    open_changes = [c for c in changes if c["change_status"] not in ["completed", "cancelled"]]

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Change Number",
        "Subject",
        "Status",
        "Requestor",
        "Implementor",
        "Start Date",
        "End Date"
    ])

    for change in open_changes:
        writer.writerow([
            change.get("change_number"),
            change.get("change_subject"),
            change.get("change_status"),
            change.get("change_requestor"),
            change.get("change_implementor", "Unassigned"),
            change.get("change_start_timestamp", ""),
            change.get("change_end_timestamp", "")
        ])

    output.seek(0)
    logging.info(f"Exported {len(open_changes)} changes to CSV")

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=changes.csv"}
    )
