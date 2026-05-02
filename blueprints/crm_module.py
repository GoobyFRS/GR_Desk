#!/usr/bin/env python3
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, Response
import io, csv, logging
from functools import wraps
from decorators import technician_required, manager_required
import local_handlers.local_customer_handler as local_customer_handler
from local_handlers.local_config_loader import load_core_config

core_config = load_core_config()
LOG_LEVEL = core_config["logging"]["level"]
LOG_FILE = core_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s"
)

crm_module_bp = Blueprint("crm", __name__, url_prefix="/crm")

@crm_module_bp.route("/dashboard")
@technician_required
def crm_dashboard():
    customers = local_customer_handler.load_customers()
    return render_template("crm_dashboard.html", customers=customers,
                         loggedInTech=session["technician"])


@crm_module_bp.route('/')
def crm_root():
    return redirect(url_for('crm.crm_dashboard'))

@crm_module_bp.route("/submit-new", methods=["GET", "POST"])
@technician_required
def submit_new_customer():
    if request.method == "POST":
        try:
            username = request.form.get("customer_username")
            first_name = request.form.get("customer_first_name")
            last_name = request.form.get("customer_last_name")
            email = request.form.get("customer_contact_email")
            ingame_username = request.form.get("customer_ingame_username", "")

            if not username or not first_name or not last_name or not email:
                return jsonify({"error": "Missing required fields"}), 400

            customer = local_customer_handler.create_customer(
                customer_username=username,
                customer_first_name=first_name,
                customer_last_name=last_name,
                customer_contact_email=email,
                customer_ingame_username=ingame_username,
                customer_vip_status=request.form.get("customer_vip_status") == "on"
            )

            customers = local_customer_handler.load_customers()
            customers.append(customer)
            local_customer_handler.save_customers(customers)

            logging.info(f"Customer {customer['customer_id']} created by {session['technician']}")
            return redirect(url_for("crm.crm_dashboard"))

        except Exception as e:
            logging.error(f"Error creating customer: {str(e)}")
            return jsonify({"error": str(e)}), 500

    return render_template("crm_form.html", loggedInTech=session["technician"], mode="create")

@crm_module_bp.route("/profile/<customer_uuid>")
@technician_required
def customer_profile(customer_uuid):
    customer = local_customer_handler.find_customer_by_uuid(customer_uuid)

    if not customer:
        return render_template("404.html"), 404

    return render_template("crm_profile.html", customer=customer,
                         loggedInTech=session["technician"])

@crm_module_bp.route("/profile/<customer_uuid>/edit", methods=["GET", "POST"])
@manager_required
def edit_customer(customer_uuid):
    if request.method == "POST":
        updates = {
            "customer_prefered_name": request.form.get("customer_prefered_name"),
            "customer_account_status": request.form.get("customer_account_status"),
            "customer_fraud_risk": request.form.get("customer_fraud_risk"),
            "customer_vip_status": request.form.get("customer_vip_status") == "on"
        }

        if local_customer_handler.update_customer(customer_uuid, updates):
            logging.info(f"Customer {customer_uuid} updated by {session['technician']}")
            return redirect(url_for("crm.customer_profile", customer_uuid=customer_uuid))
        else:
            return render_template("404.html"), 404

    customer = local_customer_handler.find_customer_by_uuid(customer_uuid)

    if not customer:
        return render_template("404.html"), 404

    return render_template("crm_form.html", customer=customer,
                         loggedInTech=session["technician"], mode="edit")

@crm_module_bp.route("/export/csv")
@technician_required
def export_customers_csv():
    customers = local_customer_handler.load_customers()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Customer ID",
        "Username",
        "Name",
        "Email",
        "Account Status",
        "Fraud Risk",
        "VIP Status"
    ])

    for customer in customers:
        writer.writerow([
            customer.get("customer_id"),
            customer.get("customer_username"),
            f"{customer.get('customer_first_name')} {customer.get('customer_last_name')}",
            customer.get("customer_contact_email"),
            customer.get("customer_account_status"),
            customer.get("customer_fraud_risk"),
            "Yes" if customer.get("customer_vip_status") else "No"
        ])

    output.seek(0)
    logging.info(f"Exported {len(customers)} customers to CSV")

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv"}
    )
