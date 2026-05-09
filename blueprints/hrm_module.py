#!/usr/bin/env python3
"""Human Resource Management module for employee operations.

Provides routes for viewing, creating, editing, and exporting employee
records with role-based access control for managers and administrators.
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

from decorators import admin_required, manager_required
import local_handlers.local_authentication_handler as local_authentication_handler
import local_handlers.local_employee_handler as local_employee_handler
from local_handlers.local_config_loader import load_core_config

core_config = load_core_config()
LOG_LEVEL: str = core_config["logging"]["level"]
LOG_FILE: str = core_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

hrm_module_bp = Blueprint("hrm", __name__, url_prefix="/hrm")


@hrm_module_bp.route("/dashboard")
@manager_required
def hrm_dashboard() -> str:
    """Display the HRM dashboard with all employees.

    Returns:
        Rendered HTML template for the HRM dashboard.
    """
    employees = local_employee_handler.load_employees()
    return render_template(
        "hrm_dashboard.html",
        employees=employees,
        loggedInTech=session["technician"],
    )


@hrm_module_bp.route("/")
def hrm_root() -> Any:
    """Redirect root HRM path to dashboard.

    Returns:
        Redirect response to HRM dashboard.
    """
    return redirect(url_for("hrm.hrm_dashboard"))


@hrm_module_bp.route("/submit-new", methods=["GET", "POST"])
@admin_required
def submit_new_employee() -> str | tuple[Any, int]:
    """Create a new employee record.

    Handles GET requests (display form) and POST requests (create employee).

    Returns:
        For GET: Rendered employee creation form.
        For POST: Redirect to dashboard on success, or JSON error response.
    """
    if request.method == "POST":
        return _handle_create_employee()

    return render_template(
        "hrm_form.html",
        loggedInTech=session["technician"],
        mode="create",
    )


def _handle_create_employee() -> tuple[Any, int] | Any:
    """Process employee creation form submission.

    Returns:
        Redirect to dashboard on success, or JSON error tuple on failure.
    """
    try:
        first_name = request.form.get("employee_first_name")
        last_name = request.form.get("employee_last_name")
        email = request.form.get("employee_email")
        username = request.form.get("employee_username")
        password = request.form.get("password")

        if not first_name or not last_name or not email or not username or not password:
            return jsonify({"error": "Missing required fields"}), 400

        # Hash the password
        password_hash = local_authentication_handler.hash_password(password)

        employee = local_employee_handler.create_employee(
            employee_first_name=first_name,
            employee_last_name=last_name,
            employee_email=email,
            employee_username=username,
            password_hash=password_hash,
            employee_preferred_name=request.form.get(
                "employee_preferred_name", first_name
            ),
            employee_phone=request.form.get("employee_phone"),
            employee_timezone=request.form.get("employee_timezone", "UTC"),
            employee_ingame_username=request.form.get("employee_ingame_username"),
            employee_chat_userid=request.form.get("employee_chat_userid"),
            employee_dob=request.form.get("employee_dob"),
            employee_hire_date=request.form.get("employee_hire_date"),
            employee_role=request.form.get("employee_role", "technician"),
            access_role=request.form.get("access_role", "technician"),
            assigned_business_unit=request.form.get(
                "assigned_business_unit", "support"
            ),
            compensation_type=request.form.get("compensation_type", "hourly"),
            base_salary=_parse_float(request.form.get("base_salary")),
            hourly_rate=_parse_float(request.form.get("hourly_rate")),
            salary_exempt=request.form.get("salary_exempt", "no"),
            is_bonus_eligible=request.form.get("is_bonus_eligible", "no"),
            bonus_rate=_parse_float(request.form.get("bonus_rate")) or 0,
            total_pto_available=_parse_int(request.form.get("total_pto_available")) or 0,
            reports_to=request.form.get("reports_to") or None,
            account_locked=request.form.get("account_locked") != "false",
        )

        employees = local_employee_handler.load_employees()
        employees.append(employee)
        local_employee_handler.save_employees(employees)

        logging.info(
            f"Employee {employee['employee_id']} created by {session['technician']}"
        )
        return redirect(url_for("hrm.hrm_dashboard"))

    except Exception as e:
        logging.error(f"Error creating employee: {e}")
        return jsonify({"error": str(e)}), 500


def _parse_float(value: str | None) -> float | None:
    """Parse an optional float value from form data.

    Args:
        value: String value to parse, or None.

    Returns:
        Parsed float, or None if value is empty/invalid.
    """
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_int(value: str | None) -> int | None:
    """Parse an optional integer value from form data.

    Args:
        value: String value to parse, or None.

    Returns:
        Parsed integer, or None if value is empty/invalid.
    """
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


@hrm_module_bp.route("/profile/<employee_uuid>")
@manager_required
def employee_profile(employee_uuid: str) -> str | tuple[str, int]:
    """Display an employee's profile.

    Args:
        employee_uuid: The unique identifier for the employee.

    Returns:
        Rendered employee profile template or 404 page.
    """
    employee = local_employee_handler.find_employee_by_uuid(employee_uuid)

    if not employee:
        return render_template("404.html"), 404

    return render_template(
        "hrm_profile.html",
        employee=employee,
        loggedInTech=session["technician"],
    )


@hrm_module_bp.route("/profile/<employee_uuid>/edit", methods=["GET", "POST"])
@admin_required
def edit_employee(employee_uuid: str) -> str | tuple[str, int] | Any:
    """Edit an employee's record.

    Handles GET requests (display edit form) and POST requests (save changes).

    Args:
        employee_uuid: The unique identifier for the employee.

    Returns:
        For GET: Rendered edit form or 404 page.
        For POST: Redirect to profile on success, or 404 page on failure.
    """
    if request.method == "POST":
        return _handle_edit_employee(employee_uuid)

    employee = local_employee_handler.find_employee_by_uuid(employee_uuid)

    if not employee:
        return render_template("404.html"), 404

    return render_template(
        "hrm_form.html",
        employee=employee,
        loggedInTech=session["technician"],
        mode="edit",
    )


def _handle_edit_employee(employee_uuid: str) -> tuple[str, int] | Any:
    """Process employee edit form submission.

    Args:
        employee_uuid: The unique identifier for the employee.

    Returns:
        Redirect to profile on success, or 404 page tuple on failure.
    """
    updates: dict[str, Any] = {}

    # String fields
    string_fields = [
        "employee_preferred_name", "employee_phone", "employee_timezone",
        "employee_ingame_username", "employee_chat_userid", "employee_role",
        "access_role", "assigned_business_unit", "compensation_type",
        "salary_exempt", "is_bonus_eligible", "employment_status",
        "rehire_status", "reports_to"
    ]
    for field in string_fields:
        value = request.form.get(field)
        if value is not None:
            updates[field] = value or None

    # Float fields
    float_fields = ["base_salary", "hourly_rate", "bonus_rate"]
    for field in float_fields:
        value = request.form.get(field)
        if value is not None:
            updates[field] = _parse_float(value)

    # Integer fields
    int_fields = ["total_pto_available", "failed_login_attempts"]
    for field in int_fields:
        value = request.form.get(field)
        if value is not None:
            updates[field] = _parse_int(value)

    # Boolean fields
    bool_fields = [
        "mfa_enabled", "account_locked",
        "has_freshrss_access", "has_jellyfin_access", "has_nextcloud_access",
        "has_tailnet_access", "has_gitea_access", "has_discord_access",
        "has_slack_access"
    ]
    for field in bool_fields:
        value = request.form.get(field)
        if value is not None:
            updates[field] = value == "true" or value == "on"

    # Date fields
    date_fields = ["employee_dob", "employee_hire_date", "employee_termination_date"]
    for field in date_fields:
        value = request.form.get(field)
        if value is not None:
            updates[field] = value or None

    if local_employee_handler.update_employee(employee_uuid, updates):
        logging.info(
            f"Employee {employee_uuid} updated by {session['technician']}"
        )
        return redirect(
            url_for("hrm.employee_profile", employee_uuid=employee_uuid)
        )

    return render_template("404.html"), 404


@hrm_module_bp.route("/profile/<employee_uuid>/reset-password", methods=["POST"])
@admin_required
def reset_employee_password(employee_uuid: str) -> tuple[Any, int]:
    """Reset an employee's password.

    Args:
        employee_uuid: The unique identifier for the employee.

    Returns:
        JSON response with success or error message and HTTP status code.
    """
    new_password = request.form.get("new_password")

    if not new_password:
        return jsonify({"error": "Password is required"}), 400

    password_hash = local_authentication_handler.hash_password(new_password)
    updates = {
        "password_hash": password_hash,
        "account_locked": False,
        "failed_login_attempts": 0,
    }

    if local_employee_handler.update_employee(employee_uuid, updates):
        logging.info(
            f"Password reset for {employee_uuid} by {session['technician']}"
        )
        return jsonify({"success": True, "message": "Password reset successfully"}), 200

    return jsonify({"error": "Employee not found"}), 404


@hrm_module_bp.route("/profile/<employee_uuid>/unlock", methods=["POST"])
@admin_required
def unlock_employee_account(employee_uuid: str) -> tuple[Any, int]:
    """Unlock an employee's account.

    Args:
        employee_uuid: The unique identifier for the employee.

    Returns:
        JSON response with success or error message and HTTP status code.
    """
    updates = {
        "account_locked": False,
        "failed_login_attempts": 0,
    }

    if local_employee_handler.update_employee(employee_uuid, updates):
        logging.info(
            f"Account unlocked for {employee_uuid} by {session['technician']}"
        )
        return jsonify({"success": True, "message": "Account unlocked"}), 200

    return jsonify({"error": "Employee not found"}), 404


CSV_EXPORT_HEADERS: list[str] = [
    "Employee ID",
    "Name",
    "Username",
    "Email",
    "Role",
    "Access Level",
    "Department",
    "Hire Date",
    "Status",
]


@hrm_module_bp.route("/export/csv")
@manager_required
def export_employees_csv() -> Response:
    """Export all employees to CSV format.

    Returns:
        CSV file download response with employee data.
    """
    employees = local_employee_handler.load_employees()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_EXPORT_HEADERS)

    for employee in employees:
        writer.writerow([
            employee.get("employee_id"),
            f"{employee.get('employee_first_name')} "
            f"{employee.get('employee_last_name')}",
            employee.get("employee_username"),
            employee.get("employee_email"),
            employee.get("employee_role"),
            employee.get("access_role"),
            employee.get("assigned_business_unit"),
            employee.get("employee_hire_date"),
            employee.get("employment_status", "active"),
        ])

    output.seek(0)
    logging.info(f"Exported {len(employees)} employees to CSV")

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )
