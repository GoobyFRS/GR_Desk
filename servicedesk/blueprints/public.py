"""Public-facing blueprint for home, login, signup, and ticket submission."""

from __future__ import annotations

from urllib.parse import urlparse

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_user, logout_user

from servicedesk.auth.decorators import setup_required
from servicedesk.auth.utils import hash_password, verify_password
from servicedesk.config import load_navbar
from servicedesk.models.customer import Customer
from servicedesk.models.employee import Employee
from servicedesk.models.ticket import Ticket
from servicedesk.storage.counter_sync import sync_customer_counter, sync_ticket_counter
from servicedesk.storage.yaml_store import YamlStore
from servicedesk.webhooks.egress import send_ticket_created_webhook

public_bp = Blueprint("public", __name__, template_folder="../templates")


@public_bp.context_processor
def inject_navbar() -> dict[str, object]:
    """Inject public navbar config into templates."""
    config_path = current_app.config["CONFIG_PATH"]
    navbar = load_navbar(config_path / "public_navbar.yml")
    return {"public_navbar": navbar}


@public_bp.route("/")
@setup_required
def index() -> str:
    """Home page with ticket submission form.

    Returns:
        Rendered home page template.
    """
    config = current_app.config["APP_CONFIG"]
    ticket_config = config.get("tickets", {})

    return render_template(
        "public/index.html",
        ticket_types=ticket_config.get("types", ["General", "Technical", "Billing"]),
        impacts=ticket_config.get("impacts", ["low", "medium", "high", "critical"]),
        urgencies=ticket_config.get("urgencies", ["low", "medium", "high", "critical"]),
    )


@public_bp.route("/submit-ticket", methods=["POST"])
@setup_required
def submit_ticket() -> str:
    """Handle ticket submission from public form.

    Returns:
        Redirect to home or ticket confirmation.
    """
    data_path = current_app.config["DATA_PATH"]
    ticket_store: YamlStore[Ticket] = YamlStore(data_path / "tickets.yaml", Ticket)

    # Sync ticket counter
    sync_ticket_counter(ticket_store.get_all())

    # Get form data
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    ticket_type = request.form.get("ticket_type", "General")
    subject = request.form.get("subject", "").strip()
    description = request.form.get("description", "").strip()
    impact = request.form.get("impact", "low")
    urgency = request.form.get("urgency", "low")

    # Validate
    errors: list[str] = []
    if not name:
        errors.append("Name is required.")
    if not email:
        errors.append("Email is required.")
    if not subject:
        errors.append("Subject is required.")
    if not description:
        errors.append("Description is required.")

    if errors:
        for error in errors:
            flash(error, "danger")
        return redirect(url_for("public.index"))  # type: ignore[return-value]

    # Check if customer is VIP
    customer_store: YamlStore[Customer] = YamlStore(
        data_path / "customers.yaml", Customer
    )
    customer = customer_store.get_by_field("customer_contact_email", email)
    is_vip = customer.customer_vip_status if customer else False

    # Create ticket
    ticket = Ticket(
        requestor_name=name,
        requestor_username=email,
        ticket_type=ticket_type,
        ticket_subject=subject,
        ticket_body=description,
        ticket_impact=impact,
        ticket_urgency=urgency,
        requestor_vip_status=is_vip,
    )

    ticket_store.save(ticket)

    # Send outbound webhook notifications
    send_ticket_created_webhook(ticket)

    flash(
        f"Ticket {ticket.ticket_number} submitted successfully! "
        "We will contact you shortly.",
        "success",
    )
    return redirect(url_for("public.index"))  # type: ignore[return-value]


@public_bp.route("/login", methods=["GET", "POST"])
@setup_required
def login() -> str:
    """Employee login page.

    Returns:
        Rendered login template or redirect.
    """
    if current_user.is_authenticated:
        return redirect(url_for("itsm.dashboard"))  # type: ignore[return-value]

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        data_path = current_app.config["DATA_PATH"]
        store: YamlStore[Employee] = YamlStore(data_path / "employees.yaml", Employee)

        employee = store.get_by_field("employee_email", email)

        if employee is None:
            flash("Invalid email or password.", "danger")
            return render_template("public/login.html", email=email)

        if employee.employee_account_locked:
            flash("Account is locked. Please contact an administrator.", "danger")
            return render_template("public/login.html", email=email)

        if not verify_password(password, employee.password_hash):
            employee.record_failed_login()
            store.save(employee)
            flash("Invalid email or password.", "danger")
            return render_template("public/login.html", email=email)

        # Successful login
        employee.record_login()
        store.save(employee)

        login_user(employee)
        flash(f"Welcome back, {employee.display_name}!", "success")

        # Validate next_page to prevent open redirect attacks
        next_page = request.args.get("next", "")
        if next_page:
            parsed = urlparse(next_page)
            # Only allow relative URLs (no scheme or netloc)
            if not parsed.netloc and not parsed.scheme:
                return redirect(next_page)  # type: ignore[return-value]

        return redirect(url_for("itsm.dashboard"))  # type: ignore[return-value]

    return render_template("public/login.html")


@public_bp.route("/logout")
def logout() -> str:
    """Log out the current user.

    Returns:
        Redirect to home page.
    """
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("public.index"))  # type: ignore[return-value]


@public_bp.route("/signup", methods=["GET", "POST"])
@setup_required
def signup() -> str:
    """Customer signup page.

    Returns:
        Rendered signup template or redirect.
    """
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")

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
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != password_confirm:
            errors.append("Passwords do not match.")

        data_path = current_app.config["DATA_PATH"]
        customer_store: YamlStore[Customer] = YamlStore(
            data_path / "customers.yaml", Customer
        )

        # Check for existing email
        existing = customer_store.get_by_field("customer_contact_email", email)
        if existing:
            errors.append("An account with this email already exists.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "public/signup.html",
                first_name=first_name,
                last_name=last_name,
                email=email,
            )

        # Sync customer counter
        sync_customer_counter(customer_store.get_all())

        # Create customer
        customer = Customer(
            customer_first_name=first_name,
            customer_last_name=last_name,
            customer_contact_email=email,
            password_hash=hash_password(password),
        )

        customer_store.save(customer)

        flash("Account created successfully! You can now submit tickets.", "success")
        return redirect(url_for("public.index"))  # type: ignore[return-value]

    return render_template("public/signup.html")
