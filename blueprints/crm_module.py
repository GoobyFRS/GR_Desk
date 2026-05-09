#!/usr/bin/env python3
"""Customer Relationship Management module for customer operations.

Provides routes for viewing, creating, editing, and exporting customer
records with role-based access control for technicians and managers.
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

from decorators import manager_required, technician_required
import local_handlers.local_customer_handler as local_customer_handler
from local_handlers.local_config_loader import load_core_config

core_config = load_core_config()
LOG_LEVEL: str = core_config["logging"]["level"]
LOG_FILE: str = core_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

crm_module_bp = Blueprint("crm", __name__, url_prefix="/crm")


@crm_module_bp.route("/dashboard")
@technician_required
def crm_dashboard() -> str:
    """Display the CRM dashboard with all customers.

    Returns:
        Rendered HTML template for the CRM dashboard.
    """
    customers = local_customer_handler.load_customers()
    return render_template(
        "crm_dashboard.html",
        customers=customers,
        loggedInTech=session["technician"],
    )


@crm_module_bp.route("/")
def crm_root() -> Any:
    """Redirect root CRM path to dashboard.

    Returns:
        Redirect response to CRM dashboard.
    """
    return redirect(url_for("crm.crm_dashboard"))


@crm_module_bp.route("/submit-new", methods=["GET", "POST"])
@technician_required
def submit_new_customer() -> str | tuple[Any, int]:
    """Create a new customer record.

    Handles GET requests (display form) and POST requests (create customer).

    Returns:
        For GET: Rendered customer creation form.
        For POST: Redirect to dashboard on success, or JSON error response.
    """
    if request.method == "POST":
        return _handle_create_customer()

    return render_template(
        "crm_form.html",
        loggedInTech=session["technician"],
        mode="create",
    )


def _handle_create_customer() -> tuple[Any, int] | Any:
    """Process customer creation form submission.

    Returns:
        Redirect to dashboard on success, or JSON error tuple on failure.
    """
    try:
        first_name = request.form.get("customer_first_name")
        last_name = request.form.get("customer_last_name")
        email = request.form.get("customer_contact_email")

        if not first_name or not last_name or not email:
            return jsonify({"error": "Missing required fields"}), 400

        vip_status = "yes" if request.form.get("customer_vip_status") == "on" else "no"

        customer = local_customer_handler.create_customer(
            customer_first_name=first_name,
            customer_last_name=last_name,
            customer_contact_email=email,
            customer_preferred_name=request.form.get(
                "customer_preferred_name", first_name
            ),
            customer_ingame_username=request.form.get("customer_ingame_username"),
            customer_discord_user_id=request.form.get("customer_discord_user_id"),
            customer_vip_status=vip_status,
            customer_fraud_risk=request.form.get("customer_fraud_risk", "low"),
            is_content_creator="yes" if request.form.get("is_content_creator") == "on" else "no",
            preferred_contact_method=request.form.get("preferred_contact_method", "email"),
            marketing_opt_in=request.form.get("marketing_opt_in") == "on",
            maintenance_notifications_enabled=request.form.get(
                "maintenance_notifications_enabled"
            ) != "off",
        )

        customers = local_customer_handler.load_customers()
        customers.append(customer)
        local_customer_handler.save_customers(customers)

        logging.info(
            f"Customer {customer['customer_id']} created by {session['technician']}"
        )
        return redirect(url_for("crm.crm_dashboard"))

    except Exception as e:
        logging.error(f"Error creating customer: {e}")
        return jsonify({"error": str(e)}), 500


@crm_module_bp.route("/profile/<customer_uuid>")
@technician_required
def customer_profile(customer_uuid: str) -> str | tuple[str, int]:
    """Display a customer's profile.

    Args:
        customer_uuid: The unique identifier for the customer.

    Returns:
        Rendered customer profile template or 404 page.
    """
    customer = local_customer_handler.find_customer_by_uuid(customer_uuid)

    if not customer:
        return render_template("404.html"), 404

    return render_template(
        "crm_profile.html",
        customer=customer,
        loggedInTech=session["technician"],
    )


@crm_module_bp.route("/profile/<customer_uuid>/edit", methods=["GET", "POST"])
@manager_required
def edit_customer(customer_uuid: str) -> str | tuple[str, int] | Any:
    """Edit a customer's record.

    Handles GET requests (display edit form) and POST requests (save changes).

    Args:
        customer_uuid: The unique identifier for the customer.

    Returns:
        For GET: Rendered edit form or 404 page.
        For POST: Redirect to profile on success, or 404 page on failure.
    """
    if request.method == "POST":
        return _handle_edit_customer(customer_uuid)

    customer = local_customer_handler.find_customer_by_uuid(customer_uuid)

    if not customer:
        return render_template("404.html"), 404

    return render_template(
        "crm_form.html",
        customer=customer,
        loggedInTech=session["technician"],
        mode="edit",
    )


def _handle_edit_customer(customer_uuid: str) -> tuple[str, int] | Any:
    """Process customer edit form submission.

    Args:
        customer_uuid: The unique identifier for the customer.

    Returns:
        Redirect to profile on success, or 404 page tuple on failure.
    """
    updates: dict[str, Any] = {}

    # String fields
    string_fields = [
        "customer_preferred_name", "customer_ingame_username",
        "customer_discord_user_id", "customer_account_status",
        "customer_fraud_risk", "customer_status_reason",
        "preferred_contact_method", "vat_taxid"
    ]
    for field in string_fields:
        value = request.form.get(field)
        if value is not None:
            updates[field] = value or None

    # Yes/No string fields
    yesno_fields = ["customer_vip_status", "is_content_creator"]
    for field in yesno_fields:
        value = request.form.get(field)
        if value is not None:
            updates[field] = "yes" if value == "on" or value == "yes" else "no"

    # Boolean fields
    bool_fields = [
        "customer_mfa_enabled", "customer_account_locked",
        "marketing_opt_in", "maintenance_notifications_enabled",
        "has_freshrss_access", "has_jellyfin_access", "has_nextcloud_access"
    ]
    for field in bool_fields:
        value = request.form.get(field)
        if value is not None:
            updates[field] = value == "on" or value == "true"

    # Float fields
    float_fields = ["customer_account_value", "customer_total_lifetime_value"]
    for field in float_fields:
        value = request.form.get(field)
        if value is not None:
            try:
                updates[field] = float(value) if value else 0.0
            except ValueError:
                pass

    if local_customer_handler.update_customer(customer_uuid, updates):
        logging.info(
            f"Customer {customer_uuid} updated by {session['technician']}"
        )
        return redirect(
            url_for("crm.customer_profile", customer_uuid=customer_uuid)
        )

    return render_template("404.html"), 404


CSV_CUSTOMER_HEADERS: list[str] = [
    "Customer ID",
    "Name",
    "Email",
    "Account Status",
    "Fraud Risk",
    "VIP Status",
    "Lifetime Value",
    "Created Date",
]


@crm_module_bp.route("/export/csv")
@technician_required
def export_customers_csv() -> Response:
    """Export all customers to CSV format.

    Returns:
        CSV file download response with customer data.
    """
    customers = local_customer_handler.load_customers()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_CUSTOMER_HEADERS)

    for customer in customers:
        vip = customer.get("customer_vip_status", "no")
        writer.writerow([
            customer.get("customer_id"),
            f"{customer.get('customer_first_name')} "
            f"{customer.get('customer_last_name')}",
            customer.get("customer_contact_email"),
            customer.get("customer_account_status"),
            customer.get("customer_fraud_risk"),
            "Yes" if vip == "yes" else "No",
            customer.get("customer_total_lifetime_value", 0),
            customer.get("customer_account_created_date"),
        ])

    output.seek(0)
    logging.info(f"Exported {len(customers)} customers to CSV")

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"},
    )
