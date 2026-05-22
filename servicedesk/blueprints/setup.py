"""Setup wizard blueprint for initial configuration."""

from __future__ import annotations

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from servicedesk.auth.utils import hash_password
from servicedesk.models.employee import Employee
from servicedesk.storage.yaml_store import YamlStore

setup_bp = Blueprint("setup", __name__, template_folder="../templates")


@setup_bp.route("/", methods=["GET", "POST"])
@setup_bp.route("/wizard", methods=["GET", "POST"])
def wizard() -> str:
    """First-run setup wizard to create initial admin account.

    Returns:
        Rendered template or redirect.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Employee] = YamlStore(data_path / "employees.yaml", Employee)

    # If employees exist, redirect to login
    if not store.is_empty():
        flash("Setup already completed.", "info")
        return redirect(url_for("public.login"))  # type: ignore[return-value]

    if request.method == "POST":
        # Get form data
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

        # Validate
        errors = []

        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email:
            errors.append("Email is required.")
        if not password:
            errors.append("Password is required.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != password_confirm:
            errors.append("Passwords do not match.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "setup/wizard.html",
                first_name=first_name,
                last_name=last_name,
                email=email,
            )

        # Create admin employee
        admin = Employee(
            employee_first_name=first_name,
            employee_last_name=last_name,
            employee_email=email,
            password_hash=hash_password(password),
            employee_access_role="admin",
            employee_title="System Administrator",
            employee_account_locked=False,
        )

        store.save(admin)
        Employee.set_counter(1)

        flash("Admin account created successfully! Please log in.", "success")
        return redirect(url_for("public.login"))  # type: ignore[return-value]

    return render_template("setup/wizard.html")
