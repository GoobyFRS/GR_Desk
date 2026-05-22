"""Changes blueprint for IT change management."""

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
from servicedesk.config import load_navbar
from servicedesk.models.change import Change
from servicedesk.models.employee import Employee
from servicedesk.models.service import Service
from servicedesk.storage.counter_sync import sync_change_counter
from servicedesk.storage.csv_export import export_changes_csv
from servicedesk.storage.yaml_store import YamlStore

changes_bp = Blueprint("changes", __name__, template_folder="../templates")


@changes_bp.context_processor
def inject_navbar() -> dict[str, object]:
    """Inject employee navbar config into templates."""
    config_path = current_app.config["CONFIG_PATH"]
    navbar = load_navbar(config_path / "employee_navbar.yml")
    return {"employee_navbar": navbar}


@changes_bp.route("/")
@technician_required
def index() -> str:
    """Redirect to dashboard.

    Returns:
        Redirect to changes dashboard.
    """
    return redirect(url_for("changes.dashboard"))  # type: ignore[return-value]


@changes_bp.route("/dashboard")
@technician_required
def dashboard() -> str:
    """Changes dashboard showing all changes.

    Returns:
        Rendered dashboard template.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Change] = YamlStore(data_path / "changes.yaml", Change)

    changes = store.get_all()

    # Sort by change number (descending - newest first)
    changes.sort(key=lambda c: c.change_number, reverse=True)

    return render_template("changes/dashboard.html", changes=changes)


@changes_bp.route("/export")
@technician_required
def export() -> Response:
    """Export changes to CSV.

    Returns:
        CSV file download response.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Change] = YamlStore(data_path / "changes.yaml", Change)

    changes = store.get_all()
    csv_content = export_changes_csv(changes)

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=changes.csv"},
    )


@changes_bp.route("/profile/<change_number>")
@technician_required
def profile(change_number: str) -> str:
    """Display change profile.

    Args:
        change_number: The change number (CHG-YYYY-NNNN).

    Returns:
        Rendered profile template.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Change] = YamlStore(data_path / "changes.yaml", Change)

    change = store.get_by_field("change_number", change_number)

    if change is None:
        flash(f"Change {change_number} not found.", "danger")
        return redirect(url_for("changes.dashboard"))  # type: ignore[return-value]

    # Get linked entities
    employee_store: YamlStore[Employee] = YamlStore(
        data_path / "employees.yaml", Employee
    )
    service_store: YamlStore[Service] = YamlStore(
        data_path / "services.yaml", Service
    )

    requestor = None
    if change.requestor_uuid:
        requestor = employee_store.get_by_id(change.requestor_uuid)

    implementor = None
    if change.implementor_uuid:
        implementor = employee_store.get_by_id(change.implementor_uuid)

    impacted_service = None
    if change.impacted_service_uuid:
        impacted_service = service_store.get_by_id(change.impacted_service_uuid)

    # Get lists for dropdowns
    employees = employee_store.get_all()
    services = service_store.get_all()

    config = current_app.config["APP_CONFIG"]
    change_config = config.get("changes", {})

    return render_template(
        "changes/profile.html",
        change=change,
        requestor=requestor,
        implementor=implementor,
        impacted_service=impacted_service,
        employees=employees,
        services=services,
        statuses=change_config.get("statuses", []),
        risks=change_config.get("risks", []),
    )


@changes_bp.route("/profile/<change_number>/edit", methods=["POST"])
@technician_required
def edit_profile(change_number: str) -> str:
    """Update change profile.

    Args:
        change_number: The change number (CHG-YYYY-NNNN).

    Returns:
        Redirect to profile page.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Change] = YamlStore(data_path / "changes.yaml", Change)

    change = store.get_by_field("change_number", change_number)

    if change is None:
        flash(f"Change {change_number} not found.", "danger")
        return redirect(url_for("changes.dashboard"))  # type: ignore[return-value]

    # Get the new status from form
    new_status = request.form.get("change_status", change.change_status)

    # Update plan fields first (needed for validation)
    change.implement_plan = request.form.get("implement_plan", change.implement_plan)
    change.test_accept_plan = request.form.get("test_accept_plan", change.test_accept_plan)
    change.rollback_plan = request.form.get("rollback_plan", change.rollback_plan)

    # Validate: Cannot leave Draft without complete plans
    if change.change_status == "Draft" and new_status != "Draft":
        if not change.has_complete_plans:
            flash(
                "Cannot change status from Draft: All plan fields "
                "(Implement, Test/Accept, Rollback) must be filled.",
                "danger",
            )
            return redirect(url_for("changes.profile", change_number=change_number))  # type: ignore[return-value]

    # Update status after validation
    change.change_status = new_status

    # Update other fields
    change.change_risk = request.form.get("change_risk", change.change_risk)
    change.planned_start_timestamp = request.form.get(
        "planned_start_timestamp", change.planned_start_timestamp
    )
    change.planned_end_timestamp = request.form.get(
        "planned_end_timestamp", change.planned_end_timestamp
    )

    # Update linked entities
    requestor_id = request.form.get("requestor_id", "").strip()
    implementor_id = request.form.get("implementor_id", "").strip()
    impacted_service_id = request.form.get("impacted_service_id", "").strip()

    employee_store: YamlStore[Employee] = YamlStore(
        data_path / "employees.yaml", Employee
    )
    service_store: YamlStore[Service] = YamlStore(
        data_path / "services.yaml", Service
    )

    # Update requestor
    if requestor_id:
        requestor = employee_store.get_by_field("employee_id", requestor_id)
        if requestor:
            change.requestor_uuid = requestor.uuid
            change.requestor_id = requestor.employee_id
    else:
        change.requestor_uuid = ""
        change.requestor_id = ""

    # Update implementor
    if implementor_id:
        implementor = employee_store.get_by_field("employee_id", implementor_id)
        if implementor:
            change.implementor_uuid = implementor.uuid
            change.implementor_id = implementor.employee_id
    else:
        change.implementor_uuid = ""
        change.implementor_id = ""

    # Update impacted service
    if impacted_service_id:
        service = service_store.get_by_field("service_id", impacted_service_id)
        if service:
            change.impacted_service_uuid = service.uuid
            change.impacted_service_id = service.service_id
    else:
        change.impacted_service_uuid = ""
        change.impacted_service_id = ""

    change.update_timestamp()
    store.save(change)
    flash("Change updated successfully.", "success")

    return redirect(url_for("changes.profile", change_number=change_number))  # type: ignore[return-value]


@changes_bp.route("/submit-new", methods=["GET", "POST"])
@technician_required
def submit_new() -> str:
    """Create new change form.

    Returns:
        Rendered form or redirect on success.
    """
    data_path = current_app.config["DATA_PATH"]

    # Get employees and services for dropdowns
    employee_store: YamlStore[Employee] = YamlStore(
        data_path / "employees.yaml", Employee
    )
    service_store: YamlStore[Service] = YamlStore(
        data_path / "services.yaml", Service
    )

    employees = employee_store.get_all()
    services = service_store.get_all()

    config = current_app.config["APP_CONFIG"]
    change_config = config.get("changes", {})

    if request.method == "POST":
        requestor_id = request.form.get("requestor_id", "").strip()
        implementor_id = request.form.get("implementor_id", "").strip()
        impacted_service_id = request.form.get("impacted_service_id", "").strip()
        change_risk = request.form.get("change_risk", "None").strip()
        planned_start = request.form.get("planned_start_timestamp", "").strip()
        planned_end = request.form.get("planned_end_timestamp", "").strip()
        implement_plan = request.form.get("implement_plan", "").strip()
        test_accept_plan = request.form.get("test_accept_plan", "").strip()
        rollback_plan = request.form.get("rollback_plan", "").strip()

        # Validate required fields
        errors = []
        if not requestor_id:
            errors.append("Requestor is required.")
        if not impacted_service_id:
            errors.append("Impacted Service is required.")

        store: YamlStore[Change] = YamlStore(data_path / "changes.yaml", Change)

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template(
                "changes/submit_new.html",
                employees=employees,
                services=services,
                statuses=change_config.get("statuses", []),
                risks=change_config.get("risks", []),
                requestor_id=requestor_id,
                implementor_id=implementor_id,
                impacted_service_id=impacted_service_id,
                change_risk=change_risk,
                planned_start_timestamp=planned_start,
                planned_end_timestamp=planned_end,
                implement_plan=implement_plan,
                test_accept_plan=test_accept_plan,
                rollback_plan=rollback_plan,
            )

        # Resolve linked entities
        requestor_uuid = ""
        if requestor_id:
            requestor = employee_store.get_by_field("employee_id", requestor_id)
            if requestor:
                requestor_uuid = requestor.uuid

        implementor_uuid = ""
        if implementor_id:
            implementor = employee_store.get_by_field("employee_id", implementor_id)
            if implementor:
                implementor_uuid = implementor.uuid

        impacted_service_uuid = ""
        if impacted_service_id:
            service = service_store.get_by_field("service_id", impacted_service_id)
            if service:
                impacted_service_uuid = service.uuid

        # Sync change counter
        sync_change_counter(store.get_all())

        # Create change
        change = Change(
            requestor_uuid=requestor_uuid,
            requestor_id=requestor_id,
            implementor_uuid=implementor_uuid,
            implementor_id=implementor_id,
            impacted_service_uuid=impacted_service_uuid,
            impacted_service_id=impacted_service_id,
            change_risk=change_risk,
            planned_start_timestamp=planned_start,
            planned_end_timestamp=planned_end,
            implement_plan=implement_plan,
            test_accept_plan=test_accept_plan,
            rollback_plan=rollback_plan,
        )

        store.save(change)
        flash(f"Change {change.change_number} created successfully!", "success")

        return redirect(url_for("changes.profile", change_number=change.change_number))  # type: ignore[return-value]

    return render_template(
        "changes/submit_new.html",
        employees=employees,
        services=services,
        statuses=change_config.get("statuses", []),
        risks=change_config.get("risks", []),
    )
