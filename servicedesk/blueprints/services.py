"""Services blueprint for service database management."""

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
from servicedesk.config import load_navbar, load_service_types
from servicedesk.models.customer import Customer
from servicedesk.models.service import Service
from servicedesk.storage.counter_sync import sync_service_counter
from servicedesk.storage.csv_export import export_services_csv
from servicedesk.storage.yaml_store import YamlStore

services_bp = Blueprint("services", __name__, template_folder="../templates")


@services_bp.context_processor
def inject_navbar() -> dict[str, object]:
    """Inject employee navbar config into templates."""
    config_path = current_app.config["CONFIG_PATH"]
    navbar = load_navbar(config_path / "employee_navbar.yml")
    return {"employee_navbar": navbar}


@services_bp.route("/")
@technician_required
def index() -> str:
    """Redirect to dashboard.

    Returns:
        Redirect to services dashboard.
    """
    return redirect(url_for("services.dashboard"))  # type: ignore[return-value]


@services_bp.route("/dashboard")
@technician_required
def dashboard() -> str:
    """Services dashboard showing all services.

    Returns:
        Rendered dashboard template.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Service] = YamlStore(data_path / "services.yaml", Service)

    services = store.get_all()

    # Sort by service ID
    services.sort(key=lambda s: s.service_id)

    return render_template("services/dashboard.html", services=services)


@services_bp.route("/export")
@technician_required
def export() -> Response:
    """Export services to CSV.

    Returns:
        CSV file download response.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Service] = YamlStore(data_path / "services.yaml", Service)

    services = store.get_all()
    csv_content = export_services_csv(services)

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=services.csv"},
    )


@services_bp.route("/profile/<service_id>")
@technician_required
def profile(service_id: str) -> str:
    """Display service profile.

    Args:
        service_id: The service ID (SVC-NNNN).

    Returns:
        Rendered profile template.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Service] = YamlStore(data_path / "services.yaml", Service)

    service = store.get_by_field("service_id", service_id)

    if service is None:
        flash(f"Service {service_id} not found.", "danger")
        return redirect(url_for("services.dashboard"))  # type: ignore[return-value]

    # Get linked customer if exists
    customer = None
    if service.customer_uuid:
        customer_store: YamlStore[Customer] = YamlStore(
            data_path / "customers.yaml", Customer
        )
        customer = customer_store.get_by_id(service.customer_uuid)

    config_path = current_app.config["CONFIG_PATH"]
    service_types = load_service_types(config_path / "service_types.yml")

    config = current_app.config["APP_CONFIG"]
    service_config = config.get("services", {})

    return render_template(
        "services/profile.html",
        service=service,
        customer=customer,
        service_types=service_types,
        statuses=service_config.get("statuses", []),
    )


@services_bp.route("/profile/<service_id>/edit", methods=["POST"])
@technician_required
def edit_profile(service_id: str) -> str:
    """Update service profile.

    Args:
        service_id: The service ID (SVC-NNNN).

    Returns:
        Redirect to profile page.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Service] = YamlStore(data_path / "services.yaml", Service)

    service = store.get_by_field("service_id", service_id)

    if service is None:
        flash(f"Service {service_id} not found.", "danger")
        return redirect(url_for("services.dashboard"))  # type: ignore[return-value]

    # Update fields from form
    service.service_name = request.form.get("service_name", service.service_name)
    service.service_type = request.form.get("service_type", service.service_type)
    service.service_status = request.form.get("service_status", service.service_status)
    service.service_ip = request.form.get("service_ip", service.service_ip)
    service.service_subdomain = request.form.get("service_subdomain", service.service_subdomain)
    service.region = request.form.get("region", service.region)
    service.node_id = request.form.get("node_id", service.node_id)
    service.cluster_id = request.form.get("cluster_id", service.cluster_id)

    # Resource allocation
    ram_str = request.form.get("allocated_ram_mb", "0")
    disk_str = request.form.get("allocated_disk_gb", "0")
    cpu_str = request.form.get("allocated_cpu_cores", "0")
    try:
        service.allocated_ram_mb = int(ram_str)
        service.allocated_disk_gb = int(disk_str)
        service.allocated_cpu_cores = float(cpu_str)
    except ValueError:
        pass

    # Game server fields
    service.minecraft_version = request.form.get("minecraft_version", service.minecraft_version)
    service.server_type = request.form.get("server_type", service.server_type)
    service.modpack_name = request.form.get("modpack_name", service.modpack_name)
    player_limit_str = request.form.get("player_limit", "0")
    try:
        service.player_limit = int(player_limit_str)
    except ValueError:
        pass

    service.update_timestamp()
    store.save(service)
    flash("Service profile updated.", "success")

    return redirect(url_for("services.profile", service_id=service_id))  # type: ignore[return-value]


@services_bp.route("/submit-new", methods=["GET", "POST"])
@technician_required
def submit_new() -> str:
    """Create new service form.

    Returns:
        Rendered form or redirect on success.
    """
    data_path = current_app.config["DATA_PATH"]
    config_path = current_app.config["CONFIG_PATH"]
    service_types = load_service_types(config_path / "service_types.yml")

    config = current_app.config["APP_CONFIG"]
    service_config = config.get("services", {})

    # Get customers for linking
    customer_store: YamlStore[Customer] = YamlStore(
        data_path / "customers.yaml", Customer
    )
    customers = customer_store.get_all()

    if request.method == "POST":
        service_name = request.form.get("service_name", "").strip()
        service_type = request.form.get("service_type", "").strip()
        customer_id = request.form.get("customer_id", "").strip()
        service_subdomain = request.form.get("service_subdomain", "").strip()

        # Validate
        errors = []
        if not service_name:
            errors.append("Service name is required.")

        store: YamlStore[Service] = YamlStore(data_path / "services.yaml", Service)

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "services/submit_new.html",
                service_name=service_name,
                service_type=service_type,
                service_subdomain=service_subdomain,
                customers=customers,
                service_types=service_types,
                statuses=service_config.get("statuses", []),
            )

        # Find customer if specified
        customer_uuid = ""
        if customer_id:
            customer = customer_store.get_by_field("customer_id", customer_id)
            if customer:
                customer_uuid = customer.uuid

        # Sync service counter
        sync_service_counter(store.get_all())

        # Create service
        service = Service(
            service_name=service_name,
            service_type=service_type,
            customer_uuid=customer_uuid,
            customer_id=customer_id,
            service_subdomain=service_subdomain,
        )

        store.save(service)
        flash(f"Service {service.service_id} created successfully!", "success")

        return redirect(url_for("services.profile", service_id=service.service_id))  # type: ignore[return-value]

    return render_template(
        "services/submit_new.html",
        customers=customers,
        service_types=service_types,
        statuses=service_config.get("statuses", []),
    )
