#!/usr/bin/env python3
"""Services module for managing provisioned services.

Provides routes for viewing, creating, updating, and managing
service records including game servers and cloud resources.
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
import local_handlers.local_services_handler as local_services_handler
from local_handlers.local_config_loader import load_core_config

core_config = load_core_config()
LOG_LEVEL: str = core_config["logging"]["level"]
LOG_FILE: str = core_config["logging"]["file"]

logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s - %(levelname)s - %(message)s",
)

services_module_bp = Blueprint("services", __name__, url_prefix="/services")

VALID_SERVICE_STATUSES: list[str] = [
    "active", "suspended", "terminated", "pending", "maintenance"
]
VALID_PROVISIONING_STATUSES: list[str] = [
    "pending", "provisioning", "active", "failed", "deprovisioning"
]


@services_module_bp.route("/", methods=["GET"])
@technician_required
def services_dashboard() -> str:
    """Display the services dashboard with active services.

    Shows all services that are not terminated.

    Returns:
        Rendered HTML template for the services dashboard.
    """
    services = local_services_handler.load_services()
    active_services = [
        s for s in services
        if s.get("service_status") != "terminated"
    ]
    return render_template(
        "services_dashboard.html",
        services=active_services,
        loggedInTech=session["technician"],
    )


@services_module_bp.route("/all", methods=["GET"])
@technician_required
def services_all() -> str:
    """Display all services including terminated.

    Returns:
        Rendered HTML template showing all services.
    """
    services = local_services_handler.load_services()
    return render_template(
        "services_dashboard.html",
        services=services,
        loggedInTech=session["technician"],
        show_all=True,
    )


@services_module_bp.route("/create", methods=["GET", "POST"])
@technician_required
def create_service() -> str | tuple[Any, int] | Any:
    """Create a new service record.

    Handles GET requests (display form) and POST requests (create service).

    Returns:
        For GET: Rendered service creation form.
        For POST: Redirect to dashboard on success, or JSON error response.
    """
    if request.method == "POST":
        return _handle_create_service()

    return render_template(
        "services_create.html",
        loggedInTech=session["technician"],
    )


def _handle_create_service() -> tuple[Any, int] | Any:
    """Process service creation form submission.

    Returns:
        Redirect to dashboard on success, or JSON error tuple on failure.
    """
    try:
        service_name = request.form.get("service_name")
        service_type = request.form.get("service_type")

        if not service_name or not service_type:
            return jsonify({"error": "Service name and type are required"}), 400

        # Parse integer fields safely
        allocated_ram = _parse_int_field(request.form.get("allocated_ram_mb"))
        allocated_disk = _parse_int_field(request.form.get("allocated_disk_gb"))
        allocated_cpu = _parse_int_field(request.form.get("allocated_cpu_cores"))
        player_limit = _parse_int_field(request.form.get("player_limit"))
        rcon_port = _parse_int_field(request.form.get("service_rcon_port"))

        service = local_services_handler.create_service(
            service_name=service_name,
            service_type=service_type,
            customer_uuid=request.form.get("customer_uuid") or None,
            customer_id=request.form.get("customer_id") or None,
            service_sku=request.form.get("service_sku") or None,
            service_ip=request.form.get("service_ip") or None,
            service_subdomain=request.form.get("service_subdomain") or None,
            service_provision_source=request.form.get("service_provision_source") or None,
            service_rcon_port=rcon_port,
            service_rcon_pwd=request.form.get("service_rcon_pwd") or None,
            node_id=request.form.get("node_id") or None,
            cluster_id=request.form.get("cluster_id") or None,
            region=request.form.get("region") or None,
            allocated_ram_mb=allocated_ram,
            allocated_disk_gb=allocated_disk,
            allocated_cpu_cores=allocated_cpu,
            minecraft_version=request.form.get("minecraft_version") or None,
            server_type=request.form.get("server_type") or None,
            modpack_name=request.form.get("modpack_name") or None,
            player_limit=player_limit,
        )

        services = local_services_handler.load_services()
        services.append(service)
        local_services_handler.save_services(services)

        logging.info(
            f"Service {service['service_id']} created by {session['technician']}"
        )
        return redirect(url_for("services.services_dashboard"))

    except Exception as e:
        logging.error(f"Error creating service: {e}")
        return jsonify({"error": str(e)}), 500


def _parse_int_field(value: str | None) -> int | None:
    """Parse an optional integer field from form data.

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


@services_module_bp.route("/console/<service_id>", methods=["GET", "POST"])
@technician_required
def services_console(service_id: str) -> str | tuple[Any, int]:
    """Display or update a service in the console.

    Handles both GET requests (display service) and POST requests (update).

    Args:
        service_id: The unique service identifier.

    Returns:
        For GET: Rendered service console template or 404 page.
        For POST: JSON response with success/error message.
    """
    if request.method == "POST":
        return _handle_service_update(service_id)

    service = local_services_handler.find_service_by_id(service_id)

    if not service:
        return render_template("404.html"), 404

    return render_template(
        "services_console.html",
        service=service,
        loggedInTech=session["technician"],
        valid_statuses=VALID_SERVICE_STATUSES,
        valid_provisioning_statuses=VALID_PROVISIONING_STATUSES,
    )


def _handle_service_update(service_id: str) -> tuple[Any, int]:
    """Handle updates to a service record.

    Args:
        service_id: The unique service identifier.

    Returns:
        JSON response tuple with success/error message and HTTP status code.
    """
    action = request.form.get("action")

    if action == "status":
        return _handle_status_update(service_id)
    elif action == "update":
        return _handle_field_update(service_id)

    return jsonify({"error": "Invalid action"}), 400


def _handle_status_update(service_id: str) -> tuple[Any, int]:
    """Handle service status update.

    Args:
        service_id: The unique service identifier.

    Returns:
        JSON response tuple with success/error message and HTTP status code.
    """
    service_status = request.form.get("service_status")
    provisioning_status = request.form.get("provisioning_status")

    if service_status and service_status not in VALID_SERVICE_STATUSES:
        return jsonify({"error": "Invalid service status"}), 400

    if provisioning_status and provisioning_status not in VALID_PROVISIONING_STATUSES:
        return jsonify({"error": "Invalid provisioning status"}), 400

    if local_services_handler.update_service_status(
        service_id, service_status, provisioning_status
    ):
        logging.info(f"Service {service_id} status updated by {session['technician']}")
        return jsonify({
            "success": True,
            "message": "Service status updated"
        }), 200

    return jsonify({"error": "Service not found"}), 404


def _handle_field_update(service_id: str) -> tuple[Any, int]:
    """Handle general field updates for a service.

    Args:
        service_id: The unique service identifier.

    Returns:
        JSON response tuple with success/error message and HTTP status code.
    """
    updates: dict[str, Any] = {}

    # Collect string fields
    string_fields = [
        "service_name", "service_sku", "service_ip", "service_subdomain",
        "node_id", "cluster_id", "region", "minecraft_version",
        "server_type", "modpack_name", "service_rcon_pwd"
    ]
    for field in string_fields:
        value = request.form.get(field)
        if value is not None:
            updates[field] = value or None

    # Collect integer fields
    int_fields = [
        "allocated_ram_mb", "allocated_disk_gb", "allocated_cpu_cores",
        "player_limit", "service_rcon_port"
    ]
    for field in int_fields:
        value = request.form.get(field)
        if value is not None:
            updates[field] = _parse_int_field(value)

    if not updates:
        return jsonify({"error": "No fields to update"}), 400

    if local_services_handler.update_service(service_id, updates):
        logging.info(f"Service {service_id} updated by {session['technician']}")
        return jsonify({
            "success": True,
            "message": "Service updated"
        }), 200

    return jsonify({"error": "Service not found"}), 404


@services_module_bp.route("/customer/<customer_id>", methods=["GET"])
@technician_required
def services_by_customer(customer_id: str) -> str:
    """Display all services for a specific customer.

    Args:
        customer_id: The customer ID (CID) to filter by.

    Returns:
        Rendered template showing customer's services.
    """
    services = local_services_handler.find_services_by_customer(customer_id)
    return render_template(
        "services_dashboard.html",
        services=services,
        loggedInTech=session["technician"],
        customer_filter=customer_id,
    )


CSV_SERVICE_HEADERS: list[str] = [
    "Service ID",
    "Name",
    "Type",
    "Status",
    "Customer ID",
    "Region",
    "IP Address",
    "Created",
]


@services_module_bp.route("/export/csv", methods=["GET"])
@technician_required
def export_services_csv() -> Response:
    """Export active services to CSV format.

    Returns:
        CSV file download response with service data.
    """
    services = local_services_handler.load_services()
    active_services = [
        s for s in services
        if s.get("service_status") != "terminated"
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(CSV_SERVICE_HEADERS)

    for service in active_services:
        writer.writerow([
            service.get("service_id"),
            service.get("service_name"),
            service.get("service_type"),
            service.get("service_status"),
            service.get("customer_id", "N/A"),
            service.get("region", "N/A"),
            service.get("service_ip", "N/A"),
            service.get("service_created_timestamp", ""),
        ])

    output.seek(0)
    logging.info(f"Exported {len(active_services)} services to CSV")

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=services.csv"},
    )
