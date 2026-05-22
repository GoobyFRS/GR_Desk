"""HR blueprint for employee management."""

from __future__ import annotations

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)

from servicedesk.auth.decorators import admin_required
from servicedesk.auth.utils import hash_password
from servicedesk.config import load_business_units, load_navbar, load_titles
from servicedesk.models.employee import Employee
from servicedesk.storage.counter_sync import sync_employee_counter
from servicedesk.storage.csv_export import export_employees_csv
from servicedesk.storage.yaml_store import YamlStore

hr_bp = Blueprint("hr", __name__, template_folder="../templates")


@hr_bp.context_processor
def inject_navbar() -> dict[str, object]:
    """Inject employee navbar config into templates."""
    config_path = current_app.config["CONFIG_PATH"]
    navbar = load_navbar(config_path / "employee_navbar.yml")
    return {"employee_navbar": navbar}


@hr_bp.route("/")
@admin_required
def index() -> str:
    """Redirect to dashboard.

    Returns:
        Redirect to HR dashboard.
    """
    return redirect(url_for("hr.dashboard"))  # type: ignore[return-value]


@hr_bp.route("/dashboard")
@admin_required
def dashboard() -> str:
    """HR dashboard showing all employees.

    Returns:
        Rendered dashboard template.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Employee] = YamlStore(data_path / "employees.yaml", Employee)

    employees = store.get_all()

    # Sort by employee ID
    employees.sort(key=lambda e: e.employee_id)

    return render_template("hr/dashboard.html", employees=employees)


@hr_bp.route("/export")
@admin_required
def export() -> Response:
    """Export employees to CSV.

    Returns:
        CSV file download response.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Employee] = YamlStore(data_path / "employees.yaml", Employee)

    employees = store.get_all()
    csv_content = export_employees_csv(employees)

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"},
    )


@hr_bp.route("/profile/<employee_id>")
@admin_required
def profile(employee_id: str) -> str:
    """Display employee profile.

    Args:
        employee_id: The employee ID (EM-NNNN).

    Returns:
        Rendered profile template.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Employee] = YamlStore(data_path / "employees.yaml", Employee)

    employee = store.get_by_field("employee_id", employee_id)

    if employee is None:
        flash(f"Employee {employee_id} not found.", "danger")
        return redirect(url_for("hr.dashboard"))  # type: ignore[return-value]

    config_path = current_app.config["CONFIG_PATH"]
    titles = load_titles(config_path / "employee_titles.yml")
    business_units = load_business_units(config_path / "business_units.yml")

    config = current_app.config["APP_CONFIG"]
    employee_config = config.get("employees", {})

    return render_template(
        "hr/profile.html",
        employee=employee,
        titles=titles,
        business_units=business_units,
        access_roles=employee_config.get("access_roles", []),
        queues=employee_config.get("assignment_queues", []),
    )


@hr_bp.route("/profile/<employee_id>/edit", methods=["POST"])
@admin_required
def edit_profile(employee_id: str) -> str:
    """Update employee profile.

    Args:
        employee_id: The employee ID (EM-NNNN).

    Returns:
        Redirect to profile page.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Employee] = YamlStore(data_path / "employees.yaml", Employee)

    employee = store.get_by_field("employee_id", employee_id)

    if employee is None:
        flash(f"Employee {employee_id} not found.", "danger")
        return redirect(url_for("hr.dashboard"))  # type: ignore[return-value]

    # Personal information
    employee.employee_first_name = request.form.get("first_name", employee.employee_first_name)
    employee.employee_last_name = request.form.get("last_name", employee.employee_last_name)
    employee.employee_preferred_name = request.form.get("preferred_name", employee.employee_preferred_name)
    employee.employee_email = request.form.get("email", employee.employee_email)
    employee.employee_phone = request.form.get("phone", employee.employee_phone)
    employee.employee_dob = request.form.get("dob") or employee.employee_dob
    employee.employee_timezone = request.form.get("timezone", employee.employee_timezone)
    employee.employee_ingame_username = request.form.get("ingame_username", employee.employee_ingame_username)
    employee.employee_chat_userid = request.form.get("chat_userid", employee.employee_chat_userid)

    # Employment details
    employee.employee_title = request.form.get("title", employee.employee_title)
    employee.employee_access_role = request.form.get("access_role", employee.employee_access_role)
    employee.employee_assignment_queue = request.form.get("assignment_queue", employee.employee_assignment_queue)
    employee.assigned_business_unit = request.form.get("business_unit", employee.assigned_business_unit)
    employee.reports_to = request.form.get("reports_to") or employee.reports_to
    employee.employee_hire_date = request.form.get("hire_date", employee.employee_hire_date)

    # Compensation
    employee.employee_compensation_type = request.form.get("compensation_type", employee.employee_compensation_type)
    employee.employee_hourly_rate = float(request.form.get("hourly_rate", 0) or 0)
    employee.employee_base_salary = float(request.form.get("base_salary", 0) or 0)
    employee.employee_salary_exempt = request.form.get("salary_exempt") == "on"
    employee.is_bonus_eligible = request.form.get("bonus_eligible") == "on"
    employee.employee_bonus_rate = float(request.form.get("bonus_rate", 0) or 0)
    employee.employee_total_pto_available = float(request.form.get("pto_available", 0) or 0)

    # Platform access flags
    employee.has_freshrss_access = request.form.get("has_freshrss_access") == "on"
    employee.has_jellyfin_access = request.form.get("has_jellyfin_access") == "on"
    employee.has_nextcloud_access = request.form.get("has_nextcloud_access") == "on"
    employee.has_tailnet_access = request.form.get("has_tailnet_access") == "on"
    employee.has_gitea_access = request.form.get("has_gitea_access") == "on"
    employee.has_discord_access = request.form.get("has_discord_access") == "on"
    employee.has_slack_access = request.form.get("has_slack_access") == "on"

    # Account status
    if request.form.get("unlock_account") == "on":
        employee.unlock_account()

    store.save(employee)
    flash("Employee profile updated.", "success")

    return redirect(url_for("hr.profile", employee_id=employee_id))  # type: ignore[return-value]


@hr_bp.route("/profile/<employee_id>/reset-password", methods=["POST"])
@admin_required
def reset_password(employee_id: str) -> str:
    """Reset employee password.

    Args:
        employee_id: The employee ID (EM-NNNN).

    Returns:
        Redirect to profile page.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Employee] = YamlStore(data_path / "employees.yaml", Employee)

    employee = store.get_by_field("employee_id", employee_id)

    if employee is None:
        flash(f"Employee {employee_id} not found.", "danger")
        return redirect(url_for("hr.dashboard"))  # type: ignore[return-value]

    # Get password fields from form
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")

    # Validate password
    errors: list[str] = []
    if not new_password:
        errors.append("New password is required.")
    elif len(new_password) < 8:
        errors.append("Password must be at least 8 characters.")
    elif new_password != confirm_password:
        errors.append("Passwords do not match.")

    if errors:
        for error in errors:
            flash(error, "danger")
        return redirect(url_for("hr.profile", employee_id=employee_id))  # type: ignore[return-value]

    # Update password
    employee.password_hash = hash_password(new_password)
    store.save(employee)

    flash(f"Password reset successfully for {employee.full_name}.", "success")
    return redirect(url_for("hr.profile", employee_id=employee_id))  # type: ignore[return-value]


@hr_bp.route("/submit-new", methods=["GET", "POST"])
@admin_required
def submit_new() -> str:
    """Create new employee form.

    Returns:
        Rendered form or redirect on success.
    """
    config_path = current_app.config["CONFIG_PATH"]
    titles = load_titles(config_path / "employee_titles.yml")
    business_units = load_business_units(config_path / "business_units.yml")

    config = current_app.config["APP_CONFIG"]
    employee_config = config.get("employees", {})

    if request.method == "POST":
        # Personal information
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        preferred_name = request.form.get("preferred_name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        dob = request.form.get("dob", "").strip() or None
        timezone = request.form.get("timezone", "UTC").strip()
        ingame_username = request.form.get("ingame_username", "").strip()
        chat_userid = request.form.get("chat_userid", "").strip()

        # Account credentials
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        # Employment details
        title = request.form.get("title", "Support Technician")
        access_role = request.form.get("access_role", "technician")
        assignment_queue = request.form.get("assignment_queue", "support")
        business_unit = request.form.get("business_unit", "support").strip()
        reports_to = request.form.get("reports_to", "").strip() or None
        hire_date = request.form.get("hire_date", "").strip()

        # Compensation
        compensation_type = request.form.get("compensation_type", "hourly")
        hourly_rate = float(request.form.get("hourly_rate", 0) or 0)
        base_salary = float(request.form.get("base_salary", 0) or 0)
        salary_exempt = request.form.get("salary_exempt") == "on"
        bonus_eligible = request.form.get("bonus_eligible") == "on"
        bonus_rate = float(request.form.get("bonus_rate", 0) or 0)
        pto_available = float(request.form.get("pto_available", 0) or 0)

        # Platform access
        has_freshrss = request.form.get("has_freshrss_access") == "on"
        has_jellyfin = request.form.get("has_jellyfin_access") == "on"
        has_nextcloud = request.form.get("has_nextcloud_access") == "on"
        has_tailnet = request.form.get("has_tailnet_access") == "on"
        has_gitea = request.form.get("has_gitea_access") == "on"
        has_discord = request.form.get("has_discord_access") == "on"
        has_slack = request.form.get("has_slack_access") == "on"

        # Validate
        errors: list[str] = []
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email:
            errors.append("Email is required.")
        if not password:
            errors.append("Password is required.")
        elif len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        elif password != password_confirm:
            errors.append("Passwords do not match.")

        data_path = current_app.config["DATA_PATH"]
        store: YamlStore[Employee] = YamlStore(data_path / "employees.yaml", Employee)

        # Check for existing email
        existing = store.get_by_field("employee_email", email)
        if existing:
            errors.append("An employee with this email already exists.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "hr/submit_new.html",
                titles=titles,
                business_units=business_units,
                access_roles=employee_config.get("access_roles", []),
                queues=employee_config.get("assignment_queues", []),
            )

        # Sync employee counter
        sync_employee_counter(store.get_all())

        # Create employee
        employee = Employee(
            employee_first_name=first_name,
            employee_last_name=last_name,
            employee_preferred_name=preferred_name,
            employee_email=email,
            employee_phone=phone,
            employee_dob=dob,
            employee_timezone=timezone,
            employee_ingame_username=ingame_username,
            employee_chat_userid=chat_userid,
            password_hash=hash_password(password),
            employee_title=title,
            employee_access_role=access_role,
            employee_assignment_queue=assignment_queue,
            assigned_business_unit=business_unit,
            reports_to=reports_to,
            employee_hire_date=hire_date if hire_date else "",
            employee_compensation_type=compensation_type,
            employee_hourly_rate=hourly_rate,
            employee_base_salary=base_salary,
            employee_salary_exempt=salary_exempt,
            is_bonus_eligible=bonus_eligible,
            employee_bonus_rate=bonus_rate,
            employee_total_pto_available=pto_available,
            has_freshrss_access=has_freshrss,
            has_jellyfin_access=has_jellyfin,
            has_nextcloud_access=has_nextcloud,
            has_tailnet_access=has_tailnet,
            has_gitea_access=has_gitea,
            has_discord_access=has_discord,
            has_slack_access=has_slack,
            employee_account_locked=False,
        )

        store.save(employee)
        flash(f"Employee {employee.employee_id} created successfully!", "success")

        return redirect(url_for("hr.profile", employee_id=employee.employee_id))  # type: ignore[return-value]

    return render_template(
        "hr/submit_new.html",
        titles=titles,
        business_units=business_units,
        access_roles=employee_config.get("access_roles", []),
        queues=employee_config.get("assignment_queues", []),
    )
