#!/usr/bin/env python3
import json
import uuid
from datetime import datetime
import local_handlers.local_config_loader as local_config_loader

core_config = local_config_loader.load_core_config()
CHANGES_FILE = core_config.get("changes_file", "./my_data/changes.json")

def load_changes():
    try:
        with open(CHANGES_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # If the file is missing or empty/invalid JSON, treat as empty list
        return []

def save_changes(changes):
    with open(CHANGES_FILE, "w") as f:
        json.dump(changes, f, indent=4)

def get_next_change_number():
    changes = load_changes()
    current_year = datetime.now().year
    current_year_changes = [c for c in changes if c["change_number"].startswith(f"CHG{current_year}")]
    next_count = len(current_year_changes) + 1
    return f"CHG{current_year}-{str(next_count).zfill(4)}"

def create_change(change_requestor, change_subject, change_description, **kwargs):
    change = {
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
        "created_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return change

def find_change_by_number(change_number):
    changes = load_changes()
    return next((c for c in changes if c["change_number"] == change_number), None)

def update_change_status(change_number, new_status):
    valid_statuses = ["new", "in_progress", "on_hold", "completed", "cancelled"]
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status: {new_status}")

    changes = load_changes()
    for change in changes:
        if change["change_number"] == change_number:
            change["change_status"] = new_status
            save_changes(changes)
            return True
    return False
