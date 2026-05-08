#!/usr/bin/env python3
"""Change request management and data persistence.

Handles all change request operations including creation, retrieval,
status updates, and storage. Changes are tracked with implementation
plans, test plans, and rollback procedures for safe deployments.
"""

import json
import uuid
from datetime import datetime
from typing import Any

import local_handlers.local_config_loader as local_config_loader

core_config = local_config_loader.load_core_config()
CHANGES_FILE: str = core_config.get("changes_file", "./my_data/changes.json")

VALID_CHANGE_STATUSES = ["new", "in_progress", "on_hold", "completed", "cancelled"]


def load_changes() -> list[dict[str, Any]]:
    """Load all change requests from JSON storage.

    Returns:
        List of change request dictionaries. Empty list if file missing or invalid.
    """
    try:
        with open(CHANGES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_changes(changes: list[dict[str, Any]]) -> None:
    """Persist change requests to JSON storage.

    Args:
        changes: List of change request dictionaries to save.
    """
    with open(CHANGES_FILE, "w") as f:
        json.dump(changes, f, indent=4)


def get_next_change_number() -> str:
    """Generate next sequential change request number.

    Returns:
        Change number in format 'CHG####-####' (e.g., 'CHG2025-0001').
    """
    changes = load_changes()
    current_year = datetime.now().year
    current_year_changes = [
        c
        for c in changes
        if c["change_number"].startswith(f"CHG{current_year}")
    ]
    next_count = len(current_year_changes) + 1
    return f"CHG{current_year}-{str(next_count).zfill(4)}"


def create_change(
    change_requestor: str,
    change_subject: str,
    change_description: str,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a new change request.

    Args:
        change_requestor: Name or ID of person requesting the change.
        change_subject: Short title of the change.
        change_description: Detailed description of the change.
        **kwargs: Optional fields including assigned_team_queue,
            change_implementor, change_rollback_plan, change_implement_plan,
            change_test_plan, change_start_timestamp, change_end_timestamp,
            change_to_appid.

    Returns:
        Dictionary representing the new change request with UUID and
        auto-generated change_number.
    """
    change: dict[str, Any] = {
        "uuid": str(uuid.uuid4()),
        "change_number": get_next_change_number(),
        "change_status": "new",
        "change_requestor": change_requestor,
        "assigned_team_queue": kwargs.get("assigned_team_queue", "support"),
        "change_implementor": kwargs.get("change_implementor"),
        "change_subject": change_subject,
        "change_description": change_description,
        "change_rollback_plan": kwargs.get("change_rollback_plan"),
        "change_implement_plan": kwargs.get("change_implement_plan"),
        "change_test_plan": kwargs.get("change_test_plan"),
        "change_start_timestamp": kwargs.get("change_start_timestamp"),
        "change_end_timestamp": kwargs.get("change_end_timestamp"),
        "change_to_appid": kwargs.get("change_to_appid"),
        "created_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return change


def find_change_by_number(change_number: str) -> dict[str, Any] | None:
    """Find a change request by its change number.

    Args:
        change_number: The change number to search for.

    Returns:
        Change request dictionary if found, None otherwise.
    """
    changes = load_changes()
    return next(
        (c for c in changes if c["change_number"] == change_number), None
    )


def update_change_status(change_number: str, new_status: str) -> bool:
    """Update the status of a change request.

    Args:
        change_number: The change number to update.
        new_status: The new status. Must be one of: new, in_progress,
            on_hold, completed, cancelled.

    Returns:
        True if update was successful, False if change not found.

    Raises:
        ValueError: If new_status is not a valid status.
    """
    if new_status not in VALID_CHANGE_STATUSES:
        raise ValueError(f"Invalid status: {new_status}. "  f"Must be one of {VALID_CHANGE_STATUSES}")

    changes = load_changes()
    for change in changes:
        if change["change_number"] == change_number:
            change["change_status"] = new_status
            save_changes(changes)
            return True
    return False
