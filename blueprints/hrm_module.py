#!/usr/bin/env python3
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, Response
import io, csv, logging
from datetime import datetime
from functools import wraps
from decorators import technician_required, manager_required, admin_required
import local_handlers.local_employee_handler as local_employee_handler
from local_handlers.local_config_loader import load_core_config

core_config = load_core_config()
LOG_LEVEL = core_config["logging"]["level"]
LOG_FILE = core_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s"
)

hrm_module_bp = Blueprint("hrm", __name__, url_prefix="/hrm")

@hrm_module_bp.route("/dashboard")
@manager_required
def hrm_dashboard():
    employees = local_employee_handler.load_employees()
    return render_template("hrm_dashboard.html", employees=employees,
                         loggedInTech=session["technician"])


@hrm_module_bp.route('/')
def hrm_root():
    return redirect(url_for('hrm.hrm_dashboard'))

@hrm_module_bp.route("/submit-new", methods=["GET", "POST"])
@admin_required
def submit_new_employee():
    if request.method == "POST":
        try:
            first_name = request.form.get("employee_first_name")
            last_name = request.form.get("employee_last_name")
            email = request.form.get("employee_contact_email")
            username = request.form.get("tech_username")

            if not first_name or not last_name or not email:
                return jsonify({"error": "Missing required fields"}), 400

            employee = local_employee_handler.create_employee(
                employee_first_name=first_name,
                employee_last_name=last_name,
                employee_contact_email=email,
                employee_preferred_name=request.form.get("employee_preferred_name", first_name),
                employee_ingame_username=request.form.get("employee_ingame_username", ""),
                employee_role=request.form.get("employee_role", "technician"),
                access_role=request.form.get("access_role", "technician"),
                assigned_business_unit=request.form.get("assigned_business_unit", "support"),
                tech_username=username,
                employee_dob=request.form.get("employee_dob"),
                employee_state=request.form.get("employee_state")
            )

            employees = local_employee_handler.load_employees()
            employees.append(employee)
            local_employee_handler.save_employees(employees)

            logging.info(f"Employee {employee['employee_id']} created by {session['technician']}")
            return redirect(url_for("hrm.hrm_dashboard"))

        except Exception as e:
            logging.error(f"Error creating employee: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return render_template("hrm_form.html", loggedInTech=session["technician"], mode="create")

@hrm_module_bp.route("/profile/<employee_uuid>")
@manager_required
def employee_profile(employee_uuid):
    employee = local_employee_handler.find_employee_by_uuid(employee_uuid)

    if not employee:
        return render_template("404.html"), 404

    return render_template("hrm_profile.html", employee=employee,
                         loggedInTech=session["technician"])

@hrm_module_bp.route("/profile/<employee_uuid>/edit", methods=["GET", "POST"])
@admin_required
def edit_employee(employee_uuid):
    if request.method == "POST":
        updates = {
            "employee_role": request.form.get("employee_role"),
            "access_role": request.form.get("access_role"),
            "assigned_business_unit": request.form.get("assigned_business_unit"),
            "total_pto_available": int(request.form.get("total_pto_available", 0)),
            "is_on_probation": request.form.get("is_on_probation") == "on",
            "employee_compensation": request.form.get("employee_compensation")
        }

        if local_employee_handler.update_employee(employee_uuid, updates):
            logging.info(f"Employee {employee_uuid} updated by {session['technician']}")
            return redirect(url_for("hrm.employee_profile", employee_uuid=employee_uuid))
        else:
            return render_template("404.html"), 404

    employee = local_employee_handler.find_employee_by_uuid(employee_uuid)

    if not employee:
        return render_template("404.html"), 404

    return render_template("hrm_form.html", employee=employee,
                         loggedInTech=session["technician"], mode="edit")

@hrm_module_bp.route("/export/csv")
@manager_required
def export_employees_csv():
    employees = local_employee_handler.load_employees()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Employee ID",
        "Name",
        "Email",
        "Role",
        "Access Level",
        "Department",
        "Hire Date",
        "Status"
    ])

    for employee in employees:
        is_active = employee.get("employee_termination_date") is None
        writer.writerow([
            employee.get("employee_id"),
            f"{employee.get('employee_first_name')} {employee.get('employee_last_name')}",
            employee.get("employee_contact_email"),
            employee.get("employee_role"),
            employee.get("access_role"),
            employee.get("assigned_business_unit"),
            employee.get("employee_hire_date"),
            "Active" if is_active else "Terminated"
        ])

    output.seek(0)
    logging.info(f"Exported {len(employees)} employees to CSV")

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"}
    )
