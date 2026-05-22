"""Reports blueprint for ticket analytics and reporting."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from flask import Blueprint, Response, current_app, render_template

from servicedesk.auth.decorators import technician_required
from servicedesk.config import load_navbar
from servicedesk.models.change import Change
from servicedesk.models.ticket import Ticket
from servicedesk.storage.csv_export import export_tickets_csv
from servicedesk.storage.yaml_store import YamlStore

if TYPE_CHECKING:
    from collections.abc import Callable

logger: logging.Logger = logging.getLogger(__name__)

reports_bp: Blueprint = Blueprint("reports", __name__, template_folder="../templates")


@reports_bp.context_processor
def inject_navbar() -> dict[str, object]:
    """Inject employee navbar config into templates."""
    config_path = current_app.config["CONFIG_PATH"]
    navbar = load_navbar(config_path / "employee_navbar.yml")
    return {"employee_navbar": navbar}


# =============================================================================
# Report Data Collection
# =============================================================================


def _get_status_counts(tickets: list[Ticket]) -> dict[str, int]:
    """Count tickets by status.

    Args:
        tickets: List of tickets to analyze.

    Returns:
        Dictionary mapping status names to counts.
    """
    assert tickets is not None, "tickets cannot be None"

    counts: dict[str, int] = {
        "new": 0,
        "in_progress": 0,
        "on_hold": 0,
        "resolved": 0,
        "cancelled": 0,
    }

    for ticket in tickets:
        status = ticket.ticket_status
        if status in counts:
            counts[status] += 1

    # Postcondition: total should match
    assert sum(counts.values()) <= len(tickets), "Count mismatch"

    return counts


def _get_time_bucket_counts(tickets: list[Ticket]) -> dict[str, int]:
    """Count tickets created within time buckets.

    Args:
        tickets: List of tickets to analyze.

    Returns:
        Dictionary mapping time bucket names to counts.
    """
    assert tickets is not None, "tickets cannot be None"

    now = datetime.now()
    buckets: dict[str, int] = {
        "last_7_days": 0,
        "last_14_days": 0,
        "last_30_days": 0,
        "last_60_days": 0,
        "last_90_days": 0,
    }

    for ticket in tickets:
        created_str = ticket.ticket_created_timestamp
        if not created_str:
            continue

        try:
            created = datetime.fromisoformat(created_str)
            age = now - created

            if age <= timedelta(days=7):
                buckets["last_7_days"] += 1
            if age <= timedelta(days=14):
                buckets["last_14_days"] += 1
            if age <= timedelta(days=30):
                buckets["last_30_days"] += 1
            if age <= timedelta(days=60):
                buckets["last_60_days"] += 1
            if age <= timedelta(days=90):
                buckets["last_90_days"] += 1

        except ValueError:
            logger.warning(f"Invalid timestamp on ticket {ticket.ticket_number}")

    return buckets


def _get_queue_counts(tickets: list[Ticket]) -> dict[str, int]:
    """Count tickets by assigned queue.

    Args:
        tickets: List of tickets to analyze.

    Returns:
        Dictionary mapping queue names to counts.
    """
    assert tickets is not None, "tickets cannot be None"

    counts: dict[str, int] = {}

    for ticket in tickets:
        queue = ticket.assigned_queue
        counts[queue] = counts.get(queue, 0) + 1

    return counts


def _get_impact_counts(tickets: list[Ticket]) -> dict[str, int]:
    """Count tickets by impact level.

    Args:
        tickets: List of tickets to analyze.

    Returns:
        Dictionary mapping impact levels to counts.
    """
    assert tickets is not None, "tickets cannot be None"

    counts: dict[str, int] = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "critical": 0,
    }

    for ticket in tickets:
        impact = ticket.ticket_impact
        if impact in counts:
            counts[impact] += 1

    return counts


def _get_source_counts(tickets: list[Ticket]) -> dict[str, int]:
    """Count tickets by source.

    Args:
        tickets: List of tickets to analyze.

    Returns:
        Dictionary mapping source names to counts.
    """
    assert tickets is not None, "tickets cannot be None"

    counts: dict[str, int] = {}

    for ticket in tickets:
        source = ticket.ticket_source or "web"
        counts[source] = counts.get(source, 0) + 1

    return counts


def _calculate_resolution_stats(tickets: list[Ticket]) -> dict[str, float | int]:
    """Calculate resolution time statistics.

    Args:
        tickets: List of tickets to analyze.

    Returns:
        Dictionary with resolution time statistics.
    """
    assert tickets is not None, "tickets cannot be None"

    resolution_times: list[float] = []

    for ticket in tickets:
        if ticket.ticket_status != "resolved":
            continue
        if not ticket.ticket_created_timestamp or not ticket.ticket_closed_timestamp:
            continue

        try:
            created = datetime.fromisoformat(ticket.ticket_created_timestamp)
            closed = datetime.fromisoformat(ticket.ticket_closed_timestamp)
            resolution_hours = (closed - created).total_seconds() / 3600
            resolution_times.append(resolution_hours)
        except ValueError:
            continue

    if not resolution_times:
        return {
            "avg_resolution_hours": 0.0,
            "min_resolution_hours": 0.0,
            "max_resolution_hours": 0.0,
            "total_resolved": 0,
        }

    return {
        "avg_resolution_hours": sum(resolution_times) / len(resolution_times),
        "min_resolution_hours": min(resolution_times),
        "max_resolution_hours": max(resolution_times),
        "total_resolved": len(resolution_times),
    }


def _get_change_status_counts(changes: list[Change]) -> dict[str, int]:
    """Count changes by status.

    Args:
        changes: List of changes to analyze.

    Returns:
        Dictionary mapping status names to counts.
    """
    assert changes is not None, "changes cannot be None"

    counts: dict[str, int] = {
        "Draft": 0,
        "Pending": 0,
        "Approved": 0,
        "Completed": 0,
        "Rollback": 0,
        "Cancelled": 0,
    }

    for change in changes:
        status = change.change_status
        if status in counts:
            counts[status] += 1

    return counts


def _get_change_risk_counts(changes: list[Change]) -> dict[str, int]:
    """Count changes by risk level.

    Args:
        changes: List of changes to analyze.

    Returns:
        Dictionary mapping risk levels to counts.
    """
    assert changes is not None, "changes cannot be None"

    counts: dict[str, int] = {
        "None": 0,
        "Low": 0,
        "Medium": 0,
        "High": 0,
    }

    for change in changes:
        risk = change.change_risk
        if risk in counts:
            counts[risk] += 1

    return counts


# =============================================================================
# Routes
# =============================================================================


@reports_bp.route("/")
@technician_required
def index() -> str:
    """Redirect to reports dashboard.

    Returns:
        Redirect to dashboard.
    """
    from flask import redirect, url_for
    return redirect(url_for("reports.dashboard"))  # type: ignore[return-value]


@reports_bp.route("/dashboard")
@technician_required
def dashboard() -> str:
    """Reports dashboard with ticket and change analytics.

    Returns:
        Rendered reports dashboard template.
    """
    data_path = current_app.config["DATA_PATH"]

    # Load tickets
    ticket_store: YamlStore[Ticket] = YamlStore(data_path / "tickets.yaml", Ticket)
    tickets = ticket_store.get_all()
    total_tickets = len(tickets)

    # Filter for active (unresolved) tickets
    active_tickets = [
        t for t in tickets
        if t.ticket_status not in ("resolved", "cancelled")
    ]

    # Gather ticket statistics
    status_counts = _get_status_counts(tickets)
    time_buckets = _get_time_bucket_counts(tickets)
    queue_counts = _get_queue_counts(active_tickets)
    impact_counts = _get_impact_counts(active_tickets)
    source_counts = _get_source_counts(tickets)
    resolution_stats = _calculate_resolution_stats(tickets)

    # Load changes
    change_store: YamlStore[Change] = YamlStore(data_path / "changes.yaml", Change)
    changes = change_store.get_all()
    total_changes = len(changes)

    # Filter for active changes
    active_changes = [c for c in changes if c.is_active]

    # Gather change statistics
    change_status_counts = _get_change_status_counts(changes)
    change_risk_counts = _get_change_risk_counts(changes)

    return render_template(
        "reports/dashboard.html",
        total_tickets=total_tickets,
        active_tickets=len(active_tickets),
        status_counts=status_counts,
        time_buckets=time_buckets,
        queue_counts=queue_counts,
        impact_counts=impact_counts,
        source_counts=source_counts,
        resolution_stats=resolution_stats,
        total_changes=total_changes,
        active_changes=len(active_changes),
        change_status_counts=change_status_counts,
        change_risk_counts=change_risk_counts,
    )


@reports_bp.route("/export/tickets")
@technician_required
def export_tickets() -> Response:
    """Export all tickets to CSV.

    Returns:
        CSV file download response.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Ticket] = YamlStore(data_path / "tickets.yaml", Ticket)

    tickets = store.get_all()
    csv_content = export_tickets_csv(tickets)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"tickets_export_{timestamp}.csv"

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@reports_bp.route("/export/tickets/open")
@technician_required
def export_open_tickets() -> Response:
    """Export only open/active tickets to CSV.

    Returns:
        CSV file download response.
    """
    data_path = current_app.config["DATA_PATH"]
    store: YamlStore[Ticket] = YamlStore(data_path / "tickets.yaml", Ticket)

    tickets = store.get_all()
    active_tickets = [
        t for t in tickets
        if t.ticket_status not in ("resolved", "cancelled")
    ]

    csv_content = export_tickets_csv(active_tickets)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"open_tickets_export_{timestamp}.csv"

    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
