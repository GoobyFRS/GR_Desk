"""CSV export utilities."""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING, Callable, TypeVar

if TYPE_CHECKING:
    from servicedesk.models.change import Change
    from servicedesk.models.customer import Customer
    from servicedesk.models.employee import Employee
    from servicedesk.models.service import Service
    from servicedesk.models.ticket import Ticket

T = TypeVar("T")


def export_to_csv(
    items: list[T],
    to_dict: Callable[[T], dict[str, object]],
    exclude_fields: list[str] | None = None,
) -> str:
    """Export a list of items to CSV format.

    Args:
        items: List of items to export.
        to_dict: Function to convert item to dictionary.
        exclude_fields: Fields to exclude from export (e.g., password_hash).

    Returns:
        CSV formatted string.
    """
    if not items:
        return ""

    exclude_fields = exclude_fields or []

    # Get all field names from first item
    first_dict = to_dict(items[0])
    fieldnames = [k for k in first_dict.keys() if k not in exclude_fields]

    # Precondition: ensure we have fields to export
    assert fieldnames, "No fields available for export"

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")

    writer.writeheader()
    for item in items:
        item_dict = to_dict(item)
        # Filter out excluded fields
        filtered_dict = {k: v for k, v in item_dict.items() if k not in exclude_fields}
        writer.writerow(filtered_dict)

    result = output.getvalue()

    # Postcondition: result should contain header row at minimum
    assert result, "CSV export produced empty output"

    return result


def export_tickets_csv(tickets: list[Ticket]) -> str:
    """Export tickets to CSV, excluding sensitive fields.

    Args:
        tickets: List of Ticket objects.

    Returns:
        CSV formatted string.
    """
    return export_to_csv(
        tickets,
        lambda t: t.to_dict(),
        exclude_fields=[],
    )


def export_employees_csv(employees: list[Employee]) -> str:
    """Export employees to CSV, excluding sensitive fields.

    Args:
        employees: List of Employee objects.

    Returns:
        CSV formatted string.
    """
    return export_to_csv(
        employees,
        lambda e: e.to_dict(include_password=False),
        exclude_fields=["password_hash"],
    )


def export_customers_csv(customers: list[Customer]) -> str:
    """Export customers to CSV, excluding sensitive fields.

    Args:
        customers: List of Customer objects.

    Returns:
        CSV formatted string.
    """
    return export_to_csv(
        customers,
        lambda c: c.to_dict(include_password=False),
        exclude_fields=["password_hash"],
    )


def export_services_csv(services: list[Service]) -> str:
    """Export services to CSV, excluding sensitive fields.

    Args:
        services: List of Service objects.

    Returns:
        CSV formatted string.
    """
    return export_to_csv(
        services,
        lambda s: s.to_dict(),
        exclude_fields=["service_rcon_pwd"],
    )


def export_changes_csv(changes: list[Change]) -> str:
    """Export changes to CSV.

    Args:
        changes: List of Change objects.

    Returns:
        CSV formatted string.
    """
    return export_to_csv(
        changes,
        lambda c: c.to_dict(),
        exclude_fields=[],
    )
