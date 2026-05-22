"""CRM blueprint for customer management."""

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

from servicedesk.auth.decorators import technician_required
from servicedesk.auth.utils import hash_password
from servicedesk.config import load_navbar
from servicedesk.models.customer import Customer
from servicedesk.storage.counter_sync import sync_customer_counter
from servicedesk.storage.csv_export import export_customers_csv
from servicedesk.storage.yaml_store import YamlStore

crm_bp = Blueprint("crm", __name__, template_folder="../templates")


@crm_bp.context_processor
def inject_navbar() -> dict[str, object]:
    """Inject employee navbar config into templates."""
    config_path = current_app.config["CONFIG_PATH"]
    navbar = load_navbar(config_path / "employee_navbar.yml")
    return {"employee_navbar": navbar}


@crm_bp.route("/")
@technician_required
def index() -> str:
    """Redirect to dashboard.

    Returns:
        Redirect to CRM dashboard.
    """
    return redirect(url_for("crm.dashboard"))  # type: ignore[return-value]


@crm_bp.route("/dashboard")
@technician_required
def dashboard() -> str:
    """CRM dashboard showing all customers.

    Returns:
        Rendered dashboard template.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Customer] = YamlStore(data_path / "customers.yaml", Customer)

    customers = store.get_all()

    # Sort by customer ID
    customers.sort(key=lambda c: c.customer_id)

    return render_template("crm/dashboard.html", customers=customers)


@crm_bp.route("/export")
@technician_required
def export() -> Response:
    """Export customers to CSV.

    Returns:
        CSV file download response.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Customer] = YamlStore(data_path / "customers.yaml", Customer)

    customers = store.get_all()
    csv_content = export_customers_csv(customers)

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"},
    )


@crm_bp.route("/profile/<uuid>")
@technician_required
def profile(uuid: str) -> str:
    """Display customer profile.

    Args:
        uuid: The customer UUID.

    Returns:
        Rendered profile template.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Customer] = YamlStore(data_path / "customers.yaml", Customer)

    customer = store.get_by_id(uuid)

    if customer is None:
        flash("Customer not found.", "danger")
        return redirect(url_for("crm.dashboard"))  # type: ignore[return-value]

    config = current_app.config["APP_CONFIG"]
    customer_config = config.get("customers", {})

    return render_template(
        "crm/profile.html",
        customer=customer,
        statuses=customer_config.get("statuses", []),
        fraud_risk_levels=customer_config.get("fraud_risk_levels", []),
    )


@crm_bp.route("/profile/<uuid>/edit", methods=["POST"])
@technician_required
def edit_profile(uuid: str) -> str:
    """Update customer profile.

    Args:
        uuid: The customer UUID.

    Returns:
        Redirect to profile page.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Customer] = YamlStore(data_path / "customers.yaml", Customer)

    customer = store.get_by_id(uuid)

    if customer is None:
        flash("Customer not found.", "danger")
        return redirect(url_for("crm.dashboard"))  # type: ignore[return-value]

    # Update fields from form
    customer.customer_first_name = request.form.get("first_name", customer.customer_first_name)
    customer.customer_last_name = request.form.get("last_name", customer.customer_last_name)
    customer.customer_preferred_name = request.form.get("preferred_name", customer.customer_preferred_name)
    customer.customer_contact_email = request.form.get("email", customer.customer_contact_email)
    customer.customer_ingame_username = request.form.get("ingame_username", customer.customer_ingame_username)
    customer.customer_discord_user_id = request.form.get("discord_user_id", customer.customer_discord_user_id)
    customer.customer_account_status = request.form.get("account_status", customer.customer_account_status)
    customer.customer_fraud_risk = request.form.get("fraud_risk", customer.customer_fraud_risk)
    customer.customer_vip_status = request.form.get("vip_status") == "on"
    customer.is_content_creator = request.form.get("is_content_creator") == "on"
    customer.marketing_opt_in = request.form.get("marketing_opt_in") == "on"
    customer.maintenance_notifications_enabled = request.form.get("maintenance_notifications") == "on"
    customer.customer_status_reason = request.form.get("status_reason", customer.customer_status_reason)

    # Platform access
    customer.has_freshrss_access = request.form.get("has_freshrss_access") == "on"
    customer.freshrss_username = request.form.get("freshrss_username", customer.freshrss_username)
    customer.has_jellyfin_access = request.form.get("has_jellyfin_access") == "on"
    customer.jellyfin_username = request.form.get("jellyfin_username", customer.jellyfin_username)
    customer.has_nextcloud_access = request.form.get("has_nextcloud_access") == "on"
    customer.nextcloud_username = request.form.get("nextcloud_username", customer.nextcloud_username)

    store.save(customer)
    flash("Customer profile updated.", "success")

    return redirect(url_for("crm.profile", uuid=uuid))  # type: ignore[return-value]


@crm_bp.route("/submit-new", methods=["GET", "POST"])
@technician_required
def submit_new() -> str:
    """Create new customer form.

    Returns:
        Rendered form or redirect on success.
    """
    config = current_app.config["APP_CONFIG"]
    customer_config = config.get("customers", {})

    if request.method == "POST":
        # Personal information
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        preferred_name = request.form.get("preferred_name", "").strip()
        email = request.form.get("email", "").strip()
        preferred_contact = request.form.get("preferred_contact", "email").strip()

        # Gaming / Platform information
        ingame_username = request.form.get("ingame_username", "").strip()
        discord_user_id = request.form.get("discord_user_id", "").strip()

        # Account settings
        account_status = request.form.get("account_status", "active")
        fraud_risk = request.form.get("fraud_risk", "low")
        account_value = request.form.get("account_value", "").strip()
        vip_status = request.form.get("vip_status") == "on"
        is_content_creator = request.form.get("is_content_creator") == "on"

        # Billing information
        vat_taxid = request.form.get("vat_taxid", "").strip() or None
        lifetime_value = float(request.form.get("lifetime_value", 0) or 0)

        # Communication preferences
        marketing_opt_in = request.form.get("marketing_opt_in") == "on"
        maintenance_notifications = request.form.get("maintenance_notifications") == "on"

        # Platform access
        has_freshrss = request.form.get("has_freshrss_access") == "on"
        freshrss_username = request.form.get("freshrss_username", "").strip()
        has_jellyfin = request.form.get("has_jellyfin_access") == "on"
        jellyfin_username = request.form.get("jellyfin_username", "").strip()
        has_nextcloud = request.form.get("has_nextcloud_access") == "on"
        nextcloud_username = request.form.get("nextcloud_username", "").strip()

        # Validate
        errors: list[str] = []
        if not first_name:
            errors.append("First name is required.")
        if not last_name:
            errors.append("Last name is required.")
        if not email:
            errors.append("Email is required.")

        data_path = current_app.config["DATA_PATH"]
        store: YamlStore[Customer] = YamlStore(data_path / "customers.yaml", Customer)

        # Check for existing email
        existing = store.get_by_field("customer_contact_email", email)
        if existing:
            errors.append("A customer with this email already exists.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "crm/submit_new.html",
                statuses=customer_config.get("statuses", []),
                fraud_risk_levels=customer_config.get("fraud_risk_levels", []),
            )

        # Sync customer counter
        sync_customer_counter(store.get_all())

        # Create customer
        customer = Customer(
            customer_first_name=first_name,
            customer_last_name=last_name,
            customer_preferred_name=preferred_name,
            customer_contact_email=email,
            preferred_contact_method=preferred_contact,
            customer_ingame_username=ingame_username,
            customer_discord_user_id=discord_user_id,
            customer_account_status=account_status,
            customer_fraud_risk=fraud_risk,
            customer_account_value=account_value,
            customer_vip_status=vip_status,
            is_content_creator=is_content_creator,
            vat_taxid=vat_taxid,
            customer_total_lifetime_value=lifetime_value,
            marketing_opt_in=marketing_opt_in,
            maintenance_notifications_enabled=maintenance_notifications,
            has_freshrss_access=has_freshrss,
            freshrss_username=freshrss_username,
            has_jellyfin_access=has_jellyfin,
            jellyfin_username=jellyfin_username,
            has_nextcloud_access=has_nextcloud,
            nextcloud_username=nextcloud_username,
        )

        store.save(customer)
        flash(f"Customer {customer.customer_id} created successfully!", "success")

        return redirect(url_for("crm.profile", uuid=customer.uuid))  # type: ignore[return-value]

    return render_template(
        "crm/submit_new.html",
        statuses=customer_config.get("statuses", []),
        fraud_risk_levels=customer_config.get("fraud_risk_levels", []),
    )
